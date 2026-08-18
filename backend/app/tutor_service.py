from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.context import ContextBuilder, TutorContext
from app.ai.providers import OpenAIEmbeddingProvider
from app.config import get_settings
from app.models import (
    ConversationMessage,
    ConversationSession,
    KnowledgeChunk,
    KnowledgeSource,
    LearnerProfile,
    User,
    UserError,
    UserVocabularyState,
    VocabularyItem,
)
from app.rag.retrieval import Candidate, HybridRetriever, RetrievalQuery
from app.schemas import TutorUIBlock


MODE_INSTRUCTIONS = {
    "free_conversation": "Hold a natural technical conversation and correct only high-value language errors.",
    "technical_interview": "Act as a senior backend interviewer. Ask one question at a time, challenge vague claims, and request measurable evidence and trade-offs.",
    "lesson_support": "Help the learner reason about the current exercise without revealing an answer immediately.",
}
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PreparedTutorTurn:
    session_id: str
    messages: list[dict[str, str]]


class TutorContextService:
    def __init__(self, context_builder: ContextBuilder | None = None, retriever: HybridRetriever | None = None):
        self.context_builder = context_builder or ContextBuilder(max_chars=7000, recent_message_limit=0)
        self.retriever = retriever or HybridRetriever()

    async def prepare(
        self,
        db: AsyncSession,
        user: User,
        session: ConversationSession,
        message: str,
        mode: str,
    ) -> PreparedTutorTurn:
        profile = await db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == user.id))
        errors = list((await db.scalars(select(UserError).where(UserError.user_id == user.id).order_by(UserError.occurrences.desc()).limit(5))).all())
        due_rows = (await db.execute(
            select(VocabularyItem.term)
            .join(UserVocabularyState, UserVocabularyState.vocabulary_id == VocabularyItem.id)
            .where(UserVocabularyState.user_id == user.id)
            .order_by(UserVocabularyState.due_at)
            .limit(8)
        )).scalars().all()
        history = list((await db.scalars(
            select(ConversationMessage)
            .where(ConversationMessage.session_id == session.id)
            .order_by(ConversationMessage.created_at.desc())
            .limit(10)
        )).all())
        history.reverse()
        knowledge = await self._knowledge(db, message, profile.specialization if profile else None)
        learner_summary = (
            f"CEFR={profile.estimated_cefr}; target={profile.target_cefr}; "
            f"specialization={profile.specialization}; experience={profile.experience_level}; "
            f"technologies={', '.join(profile.technologies)}; "
            f"native_explanations={'allowed' if profile.native_explanations else 'disabled'}"
            if profile
            else "Technical English learner"
        )
        context = self.context_builder.build(TutorContext(
            learner_summary=learner_summary,
            current_goal=MODE_INSTRUCTIONS.get(mode, MODE_INSTRUCTIONS["free_conversation"]),
            recent_errors=[f"{item.error_type}: {item.original_fragment} -> {item.corrected_fragment}" for item in errors],
            due_vocabulary=list(due_rows),
            recent_messages=[],
            retrieved_knowledge=knowledge,
        ))
        system = (
            "You are FluentStack, a precise and supportive Technical English tutor for software engineers. "
            "Use the learner context below as private guidance. Never invent learner history. Correct important English errors explicitly, "
            "verify technical claims, keep answers concise, and end with one useful next question.\n\n"
            + context
        )
        messages = [{"role": "system", "content": system}]
        messages.extend({"role": item.role, "content": item.content} for item in history)
        messages.append({"role": "user", "content": message})
        return PreparedTutorTurn(session.id, messages)

    async def _knowledge(self, db: AsyncSession, message: str, specialization: str | None) -> list[str]:
        rows = (await db.execute(
            select(KnowledgeChunk, KnowledgeSource)
            .join(KnowledgeSource, KnowledgeSource.id == KnowledgeChunk.source_id)
            .where(KnowledgeSource.status == "ready")
            .order_by(KnowledgeSource.created_at.desc())
            .limit(100)
        )).all()
        candidates = [Candidate(
            chunk.content,
            {**(chunk.metadata_json or {}), **(source.metadata_json or {}), "source_type": source.source_type},
            chunk.embedding,
        ) for chunk, source in rows]
        query_embedding = None
        settings = get_settings()
        if candidates and settings.llm_api_key and any(candidate.embedding for candidate in candidates):
            try:
                provider = OpenAIEmbeddingProvider(settings.llm_api_key, settings.embedding_model)
                query_embedding = (await provider.embed([message]))[0]
                bind = db.get_bind()
                if bind.dialect.name == "postgresql":
                    vector_rows = (await db.execute(
                        select(KnowledgeChunk, KnowledgeSource)
                        .join(KnowledgeSource, KnowledgeSource.id == KnowledgeChunk.source_id)
                        .where(KnowledgeSource.status == "ready", KnowledgeChunk.embedding.is_not(None))
                        .order_by(KnowledgeChunk.embedding.cosine_distance(query_embedding))
                        .limit(40)
                    )).all()
                    candidates = [Candidate(
                        chunk.content,
                        {**(chunk.metadata_json or {}), **(source.metadata_json or {}), "source_type": source.source_type},
                        chunk.embedding,
                    ) for chunk, source in vector_rows]
            except Exception:
                logger.exception("knowledge query embedding failed; using lexical retrieval")
                query_embedding = None
        ranked = self.retriever.rank(
            RetrievalQuery(message, specialization=specialization, limit=4),
            candidates,
            query_embedding=query_embedding,
        )
        return [item.content for item in ranked]


def tutor_ui_blocks(text: str) -> list[TutorUIBlock]:
    """Build deterministic UI affordances without pretending they are AI output."""
    if "deploy" not in text.casefold():
        return []
    return [TutorUIBlock(type="VOCAB_CARD", payload={
        "term": "deploy to production",
        "meaning": "make a release available in the production environment",
        "example": "We deployed the new API to production.",
    })]
