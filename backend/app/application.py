from __future__ import annotations

import re
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers import MockLLMProvider
from app.curriculum import B1_COURSE, DEPENDENCIES, PLACEMENT_ITEMS, SKILLS, VOCABULARY
from app.domain.learning import MasteryService, PlacementEngine, PriorityInput, PersonalizationEngine
from app.models import (
    Assessment,
    AssessmentAttempt,
    LearnerProfile,
    LearningPlan,
    LessonSession,
    Skill,
    SkillDependency,
    User,
    UserError,
    UserSkillState,
    UserVocabularyState,
    VocabularyItem,
)


async def seed_database(db: AsyncSession) -> None:
    if (await db.scalar(select(func.count()).select_from(Skill))) or 0:
        return
    for key, name, category, difficulty, cefr, description in SKILLS:
        db.add(Skill(id=key, name=name, category=category, difficulty=difficulty, cefr=cefr, description=description, career_relevance={"BACKEND": 1.0, "GENERAL_SOFTWARE_ENGINEERING": .75}))
    await db.flush()
    for skill, prerequisite in DEPENDENCIES:
        db.add(SkillDependency(skill_id=skill, prerequisite_id=prerequisite))
    for term, definition, simple, collocations, mistakes in VOCABULARY:
        db.add(VocabularyItem(term=term, definition=definition, simple_definition=simple, native_explanation=f"Термин: {term}", examples=[f"We use {term} when discussing backend systems."], collocations=collocations, common_mistakes=mistakes, tags=["backend", "technical-english"]))
    await db.commit()


class AssessmentService:
    engine = PlacementEngine()

    async def start(self, db: AsyncSession, user: User) -> tuple[Assessment, dict]:
        active = await db.scalar(select(Assessment).where(Assessment.user_id == user.id, Assessment.status == "active"))
        if not active:
            active = Assessment(user_id=user.id)
            db.add(active)
            await db.commit()
            await db.refresh(active)
        return active, self._item(active.question_count)

    async def answer(self, db: AsyncSession, user: User, assessment: Assessment, item_key: str, answer: str) -> dict:
        item = next((item for item in PLACEMENT_ITEMS if item["key"] == item_key), None)
        if item is None:
            raise ValueError("Unknown assessment item")
        if item["type"] == "choice":
            score = 1.0 if answer.strip().lower() == item["answer"].lower() else 0.0
        else:
            score = self._score_text(answer)
        ability, confidence, done = self.engine.update(assessment.ability, assessment.confidence, score, item["difficulty"], assessment.question_count)
        scores = dict(assessment.dimension_scores or {})
        scores[item["dimension"]] = round((scores.get(item["dimension"], score) + score) / 2, 3)
        assessment.ability, assessment.confidence = ability, confidence
        assessment.question_count += 1
        assessment.dimension_scores = scores
        db.add(AssessmentAttempt(assessment_id=assessment.id, item_key=item_key, answer=answer, score=score, dimension=item["dimension"]))
        if done:
            aggregate_ability = sum(scores.values()) / len(scores)
            assessment.ability = round(aggregate_ability, 4)
            assessment.status = "completed"
            profile = await db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == user.id))
            assert profile
            profile.estimated_cefr = self.engine.cefr(aggregate_ability)
            profile.placement_completed = True
            await self._initialize_learning(db, user, profile, scores)
        await db.commit()
        if done:
            return {"completed": True, "result": {"cefr": self.engine.cefr(assessment.ability), "confidence": confidence, "dimensions": scores}}
        return {"completed": False, "progress": assessment.question_count / self.engine.max_questions, "question": self._item(assessment.question_count)}

    @staticmethod
    def _score_text(answer: str) -> float:
        words = re.findall(r"[A-Za-z0-9'-]+", answer.casefold())
        technical_terms = {"api", "authentication", "authorization", "latency", "cache", "caching", "database", "query", "throughput", "bottleneck", "access", "identity"}
        tech_count = sum(word in technical_terms for word in words)
        has_structure = any(marker in words for marker in {"while", "because", "which", "then", "today", "yesterday"})
        has_action = any(marker in words for marker in {"fixed", "improved", "reduced", "identified", "optimized", "added", "introduced", "will"})
        punctuation = bool(re.search(r"[.!?]", answer))
        score = .15 + min(len(words) / 25, .35) + min(tech_count * .06, .30)
        score += .05 if punctuation else 0
        score += .05 if has_structure else 0
        score += .05 if has_action else 0
        return round(min(.95, score), 3)

    @staticmethod
    def _item(index: int) -> dict:
        item = dict(PLACEMENT_ITEMS[min(index, len(PLACEMENT_ITEMS) - 1)])
        item.pop("answer", None)
        return item

    async def _initialize_learning(self, db: AsyncSession, user: User, profile: LearnerProfile, scores: dict[str, float]) -> None:
        skills = (await db.scalars(select(Skill))).all()
        for skill in skills:
            initial = scores.get(skill.category, .42)
            db.add(UserSkillState(user_id=user.id, skill_id=skill.id, mastery=initial, confidence=.55, attempts=0))
        db.add(LearningPlan(user_id=user.id, title="Backend English Accelerator", focus=["API performance explanations", "Present Perfect vs Past Simple", "Technical interview communication"], week_number=1))
        vocabulary = (await db.scalars(select(VocabularyItem))).all()
        for word in vocabulary:
            db.add(UserVocabularyState(user_id=user.id, vocabulary_id=word.id))


class LearningService:
    engine = PersonalizationEngine()
    mastery = MasteryService()
    mock = MockLLMProvider()

    async def dashboard(self, db: AsyncSession, user: User) -> dict:
        profile = await db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == user.id))
        states = (await db.scalars(select(UserSkillState).where(UserSkillState.user_id == user.id))).all()
        skills = {s.id: s for s in (await db.scalars(select(Skill))).all()}
        ranked = sorted(states, key=lambda state: self.engine.priority(PriorityInput(state.mastery, state.confidence, 1, 1, 7, 0, 1)), reverse=True)
        due = await db.scalar(select(func.count()).select_from(UserVocabularyState).where(UserVocabularyState.user_id == user.id, UserVocabularyState.due_at <= datetime.now(timezone.utc))) or 0
        errors = (await db.scalars(select(UserError).where(UserError.user_id == user.id).order_by(UserError.occurrences.desc()).limit(3))).all()
        completed_lessons = (await db.scalars(select(LessonSession).where(LessonSession.user_id == user.id, LessonSession.status == "completed"))).all()
        completed_keys = {lesson.summary.get("course_key") for lesson in completed_lessons if lesson.summary}
        next_course = next((course for course in B1_COURSE if course["key"] not in completed_keys), B1_COURSE[0])
        avg = sum(state.mastery for state in states) / len(states) if states else .42
        return {"greeting": f"Ready for your next step, {user.display_name}?", "level": profile.estimated_cefr if profile else "B1", "target": profile.target_cefr if profile else "B2", "streak": profile.streak if profile else 0, "weekly_minutes": profile.total_minutes if profile else 0, "weekly_goal": (profile.daily_learning_minutes * 5 if profile else 100), "overall_progress": round(avg * 100), "due_vocabulary": due, "course_progress": {"completed":len(completed_keys & {course['key'] for course in B1_COURSE}),"total":len(B1_COURSE),"level":"B1"}, "today_lesson": {"title":next_course["title"], "description":next_course["objective"], "duration":next_course["duration"], "skills":[skills[next_course["skill_id"]].name, "Technical vocabulary", "Professional clarity"]}, "attention": [{"id":state.skill_id,"name":skills[state.skill_id].name,"progress":round(state.mastery*100)} for state in ranked[:3]], "recent_errors": [{"type":e.error_type,"original":e.original_fragment,"correction":e.corrected_fragment} for e in errors]}

    async def start_lesson(self, db: AsyncSession, user: User) -> dict:
        active = await db.scalar(select(LessonSession).where(LessonSession.user_id == user.id, LessonSession.status == "active"))
        if not active:
            completed_lessons = (await db.scalars(select(LessonSession).where(LessonSession.user_id == user.id, LessonSession.status == "completed"))).all()
            completed_keys = {lesson.summary.get("course_key") for lesson in completed_lessons if lesson.summary}
            course = next((item for item in B1_COURSE if item["key"] not in completed_keys), B1_COURSE[0])
            active = LessonSession(user_id=user.id, skill_id=course["skill_id"], title=course["title"], summary={"course_key":course["key"],"retry_queue":[]})
            db.add(active)
            await db.commit()
            await db.refresh(active)
        return self.lesson_payload(active)

    async def submit(self, db: AsyncSession, user: User, lesson: LessonSession, answer: str) -> dict:
        course = self._course(lesson)
        exercises = course["exercises"]
        exercise_index = self._current_exercise_index(lesson)
        if exercise_index is None:
            raise ValueError("Lesson has no remaining exercises")
        exercise = exercises[exercise_index]
        if exercise["answer"]:
            score = 1.0 if answer.strip().lower() == exercise["answer"].lower() else .45
            if score < .7:
                await self._save_error(db, user.id, lesson.skill_id, {"error_type":exercise.get("error_type","exercise-error"),"original":answer,"corrected":exercise["answer"],"explanation":exercise.get("explanation","Review the target language pattern.")})
        else:
            score = self._score_open_exercise(exercise, answer)
            if score < .7:
                await self._save_error(db, user.id, lesson.skill_id, {"error_type":exercise.get("error_type","open-answer-clarity"),"original":answer,"corrected":f"Include: {', '.join(exercise.get('rubric_terms', []))}","explanation":exercise.get("explanation","Make the technical meaning explicit and complete.")})
        state = await db.scalar(select(UserSkillState).where(UserSkillState.user_id == user.id, UserSkillState.skill_id == lesson.skill_id))
        if state:
            state.mastery = self.mastery.update(state.mastery, score, .6, .86)
            state.confidence = min(.95, state.confidence + .06)
            state.attempts += 1
            state.last_practiced_at = datetime.now(timezone.utc)
        working_summary = dict(lesson.summary or {})
        retry_queue = list(working_summary.get("retry_queue", []))
        is_initial_pass = lesson.exercise_index < len(exercises)
        if score < .7 and is_initial_pass and exercise_index not in retry_queue:
            retry_queue.append(exercise_index)
        working_summary["retry_queue"] = retry_queue
        lesson.summary = working_summary
        lesson.score += score
        lesson.exercise_index += 1
        completed = lesson.exercise_index >= len(exercises) + len(retry_queue)
        if completed:
            lesson.status = "completed"
            lesson.completed_at = datetime.now(timezone.utc)
            lesson.summary = {"course_key":course["key"],"retry_queue":retry_queue,**course["summary"]}
            profile = await db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == user.id))
            if profile:
                profile.streak += 1
                profile.total_minutes += profile.daily_learning_minutes
        await db.commit()
        if score >= .75:
            feedback = "Strong answer — your technical meaning is clear."
        elif is_initial_pass:
            feedback = "Good direction. I’ve added this pattern to a short review at the end of the lesson."
        else:
            feedback = "This was your review attempt. Check the correction in your lesson summary and Error Memory."
        return {"completed": completed, "score": round(score, 2), "feedback": feedback, "requeued": score < .7 and is_initial_pass, "lesson": self.lesson_payload(lesson)}

    @classmethod
    def _current_exercise_index(cls, lesson: LessonSession) -> int | None:
        exercises = cls._course(lesson)["exercises"]
        if lesson.exercise_index < len(exercises):
            return lesson.exercise_index
        retry_queue = list((lesson.summary or {}).get("retry_queue", []))
        retry_position = lesson.exercise_index - len(exercises)
        return retry_queue[retry_position] if retry_position < len(retry_queue) else None

    @classmethod
    def lesson_payload(cls, lesson: LessonSession) -> dict:
        retry_queue = list((lesson.summary or {}).get("retry_queue", []))
        course = cls._course(lesson)
        exercises = course["exercises"]
        exercise_index = cls._current_exercise_index(lesson)
        exercise = None if lesson.status == "completed" or exercise_index is None else dict(exercises[exercise_index])
        if exercise is not None:
            exercise["is_review"] = lesson.exercise_index >= len(exercises)
            exercise.pop("answer", None)
            exercise.pop("rubric_terms", None)
        return {"id":lesson.id,"title":lesson.title,"status":lesson.status,"step":lesson.exercise_index,"total_steps":len(exercises)+len(retry_queue),"objective":course["objective"],"context":course["context"],"exercise":exercise,"summary":lesson.summary,"course_key":course["key"]}

    @staticmethod
    def _course(lesson: LessonSession) -> dict:
        key = (lesson.summary or {}).get("course_key")
        return next((course for course in B1_COURSE if course["key"] == key), B1_COURSE[0])

    @staticmethod
    def _score_open_exercise(exercise: dict, answer: str) -> float:
        lowered = answer.casefold()
        terms = exercise.get("rubric_terms", [])
        matched = sum(term.casefold() in lowered for term in terms)
        coverage = matched / max(1, len(terms))
        word_count = len(re.findall(r"[A-Za-z0-9'-]+", answer))
        return round(min(.95, .25 + coverage * .5 + min(word_count / 40, .2)), 3)

    @staticmethod
    async def _save_error(db: AsyncSession, user_id: str, skill_id: str, error: dict) -> None:
        item = await db.scalar(select(UserError).where(UserError.user_id == user_id, UserError.error_type == error["error_type"], UserError.skill_id == skill_id))
        if item:
            item.occurrences += 1
            item.last_seen_at = datetime.now(timezone.utc)
        else:
            db.add(UserError(user_id=user_id, skill_id=skill_id, error_type=error["error_type"], original_fragment=error["original"], corrected_fragment=error["corrected"], explanation=error["explanation"], confidence=.86))
