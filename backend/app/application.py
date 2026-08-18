from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers import MockLLMProvider
from app.curriculum import DEPENDENCIES, LESSON_EXERCISES, PLACEMENT_ITEMS, SKILLS, VOCABULARY
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
            words = answer.split()
            tech_terms = sum(word.strip(".,").lower() in {"api", "authentication", "authorization", "latency", "cache", "database", "query"} for word in words)
            score = min(1.0, .35 + len(words) / 45 + tech_terms * .08)
        ability, confidence, done = self.engine.update(assessment.ability, assessment.confidence, score, item["difficulty"], assessment.question_count)
        scores = dict(assessment.dimension_scores or {})
        scores[item["dimension"]] = round((scores.get(item["dimension"], score) + score) / 2, 3)
        assessment.ability, assessment.confidence = ability, confidence
        assessment.question_count += 1
        assessment.dimension_scores = scores
        db.add(AssessmentAttempt(assessment_id=assessment.id, item_key=item_key, answer=answer, score=score, dimension=item["dimension"]))
        if done:
            assessment.status = "completed"
            profile = await db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == user.id))
            assert profile
            profile.estimated_cefr = self.engine.cefr(ability)
            profile.placement_completed = True
            await self._initialize_learning(db, user, profile, scores)
        await db.commit()
        if done:
            return {"completed": True, "result": {"cefr": self.engine.cefr(ability), "confidence": confidence, "dimensions": scores}}
        return {"completed": False, "progress": assessment.question_count / self.engine.max_questions, "question": self._item(assessment.question_count)}

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
        avg = sum(state.mastery for state in states) / len(states) if states else .42
        return {"greeting": f"Ready for your next step, {user.display_name}?", "level": profile.estimated_cefr if profile else "B1", "target": profile.target_cefr if profile else "B2", "streak": profile.streak if profile else 0, "weekly_minutes": profile.total_minutes if profile else 0, "weekly_goal": (profile.daily_learning_minutes * 5 if profile else 100), "overall_progress": round(avg * 100), "due_vocabulary": due, "today_lesson": {"title":"Improving API Performance", "description":"Explain performance work in an interview while practising Past Simple and precise backend vocabulary.", "duration": profile.daily_learning_minutes if profile else 20, "skills":["API performance", "Past Simple", "Interview answers"]}, "attention": [{"id":state.skill_id,"name":skills[state.skill_id].name,"progress":round(state.mastery*100)} for state in ranked[:3]], "recent_errors": [{"type":e.error_type,"original":e.original_fragment,"correction":e.corrected_fragment} for e in errors]}

    async def start_lesson(self, db: AsyncSession, user: User) -> dict:
        active = await db.scalar(select(LessonSession).where(LessonSession.user_id == user.id, LessonSession.status == "active"))
        if not active:
            active = LessonSession(user_id=user.id, skill_id="tech.caching", title="Improving API Performance")
            db.add(active)
            await db.commit()
            await db.refresh(active)
        return self.lesson_payload(active)

    async def submit(self, db: AsyncSession, user: User, lesson: LessonSession, answer: str) -> dict:
        exercise_index = self._current_exercise_index(lesson)
        if exercise_index is None:
            raise ValueError("Lesson has no remaining exercises")
        exercise = LESSON_EXERCISES[exercise_index]
        if exercise["answer"]:
            score = 1.0 if answer.strip().lower() == exercise["answer"].lower() else .45
            if score < .7:
                errors = {
                    0: {"error_type":"incorrect-preposition","original":answer,"corrected":exercise["answer"],"explanation":"Use ‘deploy to production’ as the standard IT collocation."},
                    1: {"error_type":"present-perfect-vs-past-simple","original":answer,"corrected":exercise["answer"],"explanation":"Use Past Simple with a finished time marker such as ‘yesterday’."},
                }
                await self._save_error(db, user.id, errors.get(exercise_index, {"error_type":"exercise-error","original":answer,"corrected":exercise["answer"],"explanation":"Review the target language pattern."}))
        else:
            evaluation = await self.mock.generate_structured([{"role":"user","content":answer}], __import__("app.schemas", fromlist=["EvaluationResult"]).EvaluationResult)
            score = (evaluation.technical_correctness + evaluation.grammar_accuracy + evaluation.clarity) / 3
            for error in evaluation.errors:
                await self._save_error(db, user.id, error)
        state = await db.scalar(select(UserSkillState).where(UserSkillState.user_id == user.id, UserSkillState.skill_id == lesson.skill_id))
        if state:
            state.mastery = self.mastery.update(state.mastery, score, .6, .86)
            state.confidence = min(.95, state.confidence + .06)
            state.attempts += 1
            state.last_practiced_at = datetime.now(timezone.utc)
        working_summary = dict(lesson.summary or {})
        retry_queue = list(working_summary.get("retry_queue", []))
        is_initial_pass = lesson.exercise_index < len(LESSON_EXERCISES)
        if score < .7 and is_initial_pass and exercise_index not in retry_queue:
            retry_queue.append(exercise_index)
        working_summary["retry_queue"] = retry_queue
        lesson.summary = working_summary
        lesson.score += score
        lesson.exercise_index += 1
        completed = lesson.exercise_index >= len(LESSON_EXERCISES) + len(retry_queue)
        if completed:
            lesson.status = "completed"
            lesson.completed_at = datetime.now(timezone.utc)
            lesson.summary = {"strong":["Technical vocabulary", "Clear structure"],"needs_work":["Past time markers", "Articles in definitions"],"new_words":["throughput","bottleneck","rollback"],"next_topic":"Caching trade-offs"}
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

    @staticmethod
    def _current_exercise_index(lesson: LessonSession) -> int | None:
        if lesson.exercise_index < len(LESSON_EXERCISES):
            return lesson.exercise_index
        retry_queue = list((lesson.summary or {}).get("retry_queue", []))
        retry_position = lesson.exercise_index - len(LESSON_EXERCISES)
        return retry_queue[retry_position] if retry_position < len(retry_queue) else None

    @classmethod
    def lesson_payload(cls, lesson: LessonSession) -> dict:
        retry_queue = list((lesson.summary or {}).get("retry_queue", []))
        exercise_index = cls._current_exercise_index(lesson)
        exercise = None if lesson.status == "completed" or exercise_index is None else dict(LESSON_EXERCISES[exercise_index])
        if exercise is not None:
            exercise["is_review"] = lesson.exercise_index >= len(LESSON_EXERCISES)
        return {"id":lesson.id,"title":lesson.title,"status":lesson.status,"step":lesson.exercise_index,"total_steps":len(LESSON_EXERCISES)+len(retry_queue),"objective":"Explain past performance improvements with accurate technical vocabulary.","context":"You are answering questions in a backend interview about an API you improved.","exercise":exercise,"summary":lesson.summary}

    @staticmethod
    async def _save_error(db: AsyncSession, user_id: str, error: dict) -> None:
        item = await db.scalar(select(UserError).where(UserError.user_id == user_id, UserError.error_type == error["error_type"], UserError.skill_id == "grammar.present-perfect"))
        if item:
            item.occurrences += 1
            item.last_seen_at = datetime.now(timezone.utc)
        else:
            db.add(UserError(user_id=user_id, skill_id="grammar.present-perfect", error_type=error["error_type"], original_fragment=error["original"], corrected_fragment=error["corrected"], explanation=error["explanation"], confidence=.86))
