from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers import MockLLMProvider, OpenAILLMProvider
from app.application import AssessmentService, LearningService
from app.config import get_settings
from app.database import get_db
from app.models import (
    Assessment,
    ConversationMessage,
    ConversationSession,
    KnowledgeChunk,
    KnowledgeSource,
    LearnerProfile,
    LearningPlan,
    LessonSession,
    Skill,
    User,
    UserError,
    UserSkillState,
    UserVocabularyState,
    VocabularyItem,
)
from app.schemas import AssessmentAnswer, Credentials, ExerciseAnswer, LoginRequest, OnboardingRequest, TokenResponse, TutorRequest, VocabularyReviewRequest
from app.domain.learning import SRSService, SRSState, VocabularyReviewService
from app.security import create_token, current_user, hash_password, verify_password

router = APIRouter()
assessment_service = AssessmentService()
learning_service = LearningService()


def user_payload(user: User, profile: LearnerProfile | None = None) -> dict:
    return {"id":user.id,"email":user.email,"display_name":user.display_name,"onboarding_completed":bool(profile and profile.onboarding_completed),"placement_completed":bool(profile and profile.placement_completed)}


def profile_payload(profile: LearnerProfile | None) -> dict | None:
    if profile is None:
        return None
    return {column.name: getattr(profile, column.name) for column in profile.__table__.columns}


@router.post("/auth/register", response_model=TokenResponse, status_code=201)
async def register(data: Credentials, db: AsyncSession = Depends(get_db)) -> dict:
    if await db.scalar(select(User).where(func.lower(User.email) == data.email.lower())):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")
    user = User(email=data.email.lower(), password_hash=hash_password(data.password), display_name=data.display_name)
    profile = LearnerProfile(user=user)
    db.add_all([user, profile])
    await db.commit()
    await db.refresh(user)
    await db.refresh(profile)
    return {"access_token":create_token(user.id),"token_type":"bearer","user":user_payload(user, profile)}


@router.post("/auth/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)) -> dict:
    user = await db.scalar(select(User).where(func.lower(User.email) == data.email.lower()))
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email or password is incorrect")
    profile = await db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == user.id))
    return {"access_token":create_token(user.id),"token_type":"bearer","user":user_payload(user, profile)}


@router.get("/me")
async def me(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> dict:
    profile = await db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == user.id))
    return {"user":user_payload(user, profile),"profile":profile_payload(profile)}


@router.put("/onboarding")
async def onboarding(data: OnboardingRequest, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> dict:
    profile = await db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == user.id))
    if not profile:
        profile = LearnerProfile(user_id=user.id)
        db.add(profile)
    for key, value in data.model_dump().items():
        setattr(profile, key, value)
    profile.onboarding_completed = True
    await db.commit()
    return {"profile":profile_payload(profile),"next":"placement"}


@router.post("/assessment/start")
async def start_assessment(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> dict:
    assessment, question = await assessment_service.start(db, user)
    return {"assessment_id":assessment.id,"progress":assessment.question_count / assessment_service.engine.max_questions,"question":question}


@router.post("/assessment/answer")
async def answer_assessment(data: AssessmentAnswer, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> dict:
    assessment = await db.get(Assessment, data.assessment_id)
    if not assessment or assessment.user_id != user.id or assessment.status != "active":
        raise HTTPException(404, "Active assessment not found")
    try:
        return await assessment_service.answer(db, user, assessment, data.item_key, data.answer)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/dashboard")
async def dashboard(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> dict:
    return await learning_service.dashboard(db, user)


@router.get("/learning-plan")
async def learning_plan(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> dict:
    plan = await db.scalar(select(LearningPlan).where(LearningPlan.user_id == user.id).order_by(LearningPlan.created_at.desc()))
    return {"title":plan.title if plan else "Your personalized plan","week":plan.week_number if plan else 1,"focus":plan.focus if plan else [],"days":[{"day":"Monday","topic":"API performance","mode":"Interview","minutes":20,"done":True},{"day":"Tuesday","topic":"Past time in status updates","mode":"Stand-up","minutes":15,"done":False},{"day":"Wednesday","topic":"Caching & Redis","mode":"Technical explanation","minutes":20,"done":False},{"day":"Thursday","topic":"Vocabulary review","mode":"SRS","minutes":10,"done":False},{"day":"Friday","topic":"Backend mock interview","mode":"Roleplay","minutes":25,"done":False}]}


@router.post("/lessons/start")
async def start_lesson(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> dict:
    return await learning_service.start_lesson(db, user)


@router.post("/lessons/{lesson_id}/answer")
async def answer_lesson(lesson_id: str, data: ExerciseAnswer, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> dict:
    lesson = await db.get(LessonSession, lesson_id)
    if not lesson or lesson.user_id != user.id:
        raise HTTPException(404, "Lesson not found")
    if lesson.status != "active":
        raise HTTPException(409, "Lesson is already completed")
    try:
        return await learning_service.submit(db, user, lesson, data.answer)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.get("/vocabulary")
async def vocabulary(q: str = "", user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> dict:
    query = select(VocabularyItem, UserVocabularyState).join(UserVocabularyState, UserVocabularyState.vocabulary_id == VocabularyItem.id).where(UserVocabularyState.user_id == user.id)
    if q:
        query = query.where(or_(VocabularyItem.term.ilike(f"%{q}%"), VocabularyItem.definition.ilike(f"%{q}%")))
    rows = (await db.execute(query.order_by(UserVocabularyState.due_at))).all()
    now = datetime.now(timezone.utc)
    return {"items":[{"id":word.id,"term":word.term,"definition":word.definition,"simple_definition":word.simple_definition,"native_explanation":word.native_explanation,"examples":word.examples,"collocations":word.collocations,"common_mistakes":word.common_mistakes,"cefr":word.cefr,"due":state.due_at <= now,"repetitions":state.repetitions,"interval_days":state.interval_days,"due_at":state.due_at} for word, state in rows]}


@router.post("/vocabulary/{vocabulary_id}/review")
async def review_vocabulary(vocabulary_id: str, data: VocabularyReviewRequest, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> dict:
    row = (await db.execute(select(VocabularyItem, UserVocabularyState).join(UserVocabularyState, UserVocabularyState.vocabulary_id == VocabularyItem.id).where(VocabularyItem.id == vocabulary_id, UserVocabularyState.user_id == user.id))).first()
    if not row:
        raise HTTPException(404, "Vocabulary item not found")
    word, state = row
    sentence = data.context_sentence.strip()
    evaluation = VocabularyReviewService.evaluate(word.term, data.recall_answer, sentence)
    next_state, due_at = SRSService().review(SRSState(state.repetitions, state.interval_days, state.ease_factor), evaluation.quality)
    if evaluation.quality < 3:
        due_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        state.interval_days = 0
    else:
        state.interval_days = next_state.interval_days
    state.repetitions = next_state.repetitions
    state.ease_factor = next_state.ease_factor
    state.due_at = due_at
    await db.commit()
    if not evaluation.contains_term:
        feedback = f"Use the exact term ‘{word.term}’ in your sentence."
    elif not evaluation.context_correct:
        feedback = "Add enough context to show what the term means in a real engineering situation."
    else:
        feedback = "Good contextual use — the technical meaning is clear."
    return {"term":word.term,"recall_correct":evaluation.recall_correct,"context_correct":evaluation.context_correct,"quality":evaluation.quality,"feedback":feedback,"correct_answer":word.term,"example":word.examples[0] if word.examples else "","repetitions":state.repetitions,"interval_days":state.interval_days,"due_at":state.due_at}


@router.get("/errors")
async def errors(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> dict:
    items = (await db.scalars(select(UserError).where(UserError.user_id == user.id).order_by(UserError.occurrences.desc()))).all()
    return {"items":[{"id":e.id,"type":e.error_type,"original":e.original_fragment,"corrected":e.corrected_fragment,"explanation":e.explanation,"occurrences":e.occurrences,"status":e.status,"severity":"important" if e.occurrences > 2 else "useful"} for e in items]}


@router.get("/progress")
async def progress(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> dict:
    states = (await db.execute(select(UserSkillState, Skill).join(Skill, Skill.id == UserSkillState.skill_id).where(UserSkillState.user_id == user.id))).all()
    grouped: dict[str, list[float]] = {}
    for state, skill in states:
        grouped.setdefault(skill.category, []).append(state.mastery)
    profile = await db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == user.id))
    completed_lessons = (await db.scalars(select(LessonSession).where(LessonSession.user_id == user.id, LessonSession.status == "completed"))).all()
    vocabulary_reviews = await db.scalar(select(func.coalesce(func.sum(UserVocabularyState.repetitions), 0)).where(UserVocabularyState.user_id == user.id)) or 0
    today = datetime.now(timezone.utc).date()
    activity = []
    activity_labels = []
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        activity.append(sum(1 for lesson in completed_lessons if lesson.completed_at and lesson.completed_at.date() == day))
        activity_labels.append(day.strftime("%a")[0])
    achievements = []
    if completed_lessons:
        achievements.append("First lesson completed")
    if vocabulary_reviews:
        achievements.append("Backend vocabulary starter")
    if len(completed_lessons) >= 3:
        achievements.append("Three lessons completed")
    return {"categories":[{"name":name.replace("_", " ").title(),"progress":round(sum(values)/len(values)*100)} for name,values in grouped.items()],"activity":activity,"activity_labels":activity_labels,"achievements":achievements,"level":profile.estimated_cefr if profile else "B1","target":profile.target_cefr if profile else "B2","streak":profile.streak if profile else 0,"completed_lessons":len(completed_lessons),"vocabulary_reviews":int(vocabulary_reviews)}


@router.get("/skills")
async def skills(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> dict:
    rows = (await db.execute(select(Skill, UserSkillState).join(UserSkillState, UserSkillState.skill_id == Skill.id).where(UserSkillState.user_id == user.id))).all()
    return {"items":[{"id":skill.id,"name":skill.name,"category":skill.category,"cefr":skill.cefr,"mastery":round(state.mastery*100),"confidence":round(state.confidence*100)} for skill,state in rows]}


@router.get("/practice/documentation")
async def documentation_practice(user: User = Depends(current_user)) -> dict:
    return {"title":"FastAPI dependency injection","source":"Curated from FastAPI concepts","snippet":"A dependency can declare requirements that FastAPI resolves before calling the path operation function. Dependencies may be reused and nested.","terms":[{"term":"dependency","meaning":"a requirement supplied to another component"},{"term":"resolve","meaning":"find or construct the required value"}],"question":"Why are reusable dependencies helpful in an API codebase?"}


@router.get("/practice/interview")
async def interview_practice(user: User = Depends(current_user)) -> dict:
    return {"role":"Senior Backend Engineer interviewer","scenario":"API performance deep dive","questions":["Tell me about an API performance problem you diagnosed.","How did you measure the bottleneck?","What trade-offs did your solution introduce?"],"tip":"Use Context → Action → Measurable result → Trade-off."}


@router.post("/tutor/stream")
async def tutor_stream(data: TutorRequest, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> StreamingResponse:
    session = await db.get(ConversationSession, data.session_id) if data.session_id else None
    if session and session.user_id != user.id:
        raise HTTPException(404, "Conversation not found")
    if not session:
        session = ConversationSession(user_id=user.id, mode=data.mode, title="Backend English practice")
        db.add(session)
        await db.flush()
    db.add(ConversationMessage(session_id=session.id, role="user", content=data.message))
    await db.commit()
    settings = get_settings()
    provider = OpenAILLMProvider(settings.llm_api_key, settings.llm_model) if settings.llm_provider == "openai" and settings.llm_api_key else MockLLMProvider()
    session_id = session.id

    async def events():
        chunks: list[str] = []
        yield f"event: meta\ndata: {json.dumps({'session_id': session_id})}\n\n"
        try:
            async for chunk in provider.stream([{"role":"system","content":"You are a supportive Technical English tutor. Keep flow, focus on high-value corrections, and use backend examples."},{"role":"user","content":data.message}]):
                chunks.append(chunk)
                yield f"event: token\ndata: {json.dumps({'token': chunk})}\n\n"
            async with db.begin():
                db.add(ConversationMessage(session_id=session_id, role="assistant", content="".join(chunks)))
            blocks = MockLLMProvider().tutor_response(data.message).ui_blocks
            yield f"event: done\ndata: {json.dumps({'ui_blocks': [b.model_dump() for b in blocks], 'suggested_actions':['Give a concrete example','Practice an interview answer']})}\n\n"
        except asyncio.CancelledError:
            return
        except Exception:
            yield f"event: error\ndata: {json.dumps({'message':'The tutor could not respond. Please retry.'})}\n\n"
    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})


@router.post("/knowledge/ingest", status_code=202)
async def ingest(file: UploadFile, source_type: str = "CUSTOM_SOURCE", user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> dict:
    raw = await file.read()
    if len(raw) > 10_000_000:
        raise HTTPException(413, "File is too large")
    text = raw.decode("utf-8", errors="ignore")
    source = KnowledgeSource(title=file.filename or "Uploaded source", source_type=source_type, metadata_json={"filename":file.filename})
    db.add(source)
    await db.flush()
    chunks = [text[i:i+1800] for i in range(0, len(text), 1500) if text[i:i+1800].strip()]
    for index, content in enumerate(chunks):
        db.add(KnowledgeChunk(source_id=source.id, content=content, metadata_json={"section":index+1,"source_type":source_type}, embedding=None))
    await db.commit()
    return {"source_id":source.id,"status":"ready","chunks":len(chunks)}
