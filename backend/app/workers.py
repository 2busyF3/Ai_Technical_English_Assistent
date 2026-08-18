import asyncio

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from sqlalchemy import select

from app.ai.providers import OpenAIEmbeddingProvider
from app.config import get_settings
from app.database import SessionLocal, engine
from app.models import KnowledgeChunk, KnowledgeSource

dramatiq.set_broker(RedisBroker(url=get_settings().redis_url))


@dramatiq.actor(max_retries=3)
def embed_knowledge(source_id: str) -> None:
    """Generate and persist embeddings for an ingested knowledge source."""
    asyncio.run(_run_and_dispose(source_id))


async def _run_and_dispose(source_id: str) -> None:
    try:
        await _embed_knowledge(source_id)
    finally:
        # Dramatiq invokes each async job through a fresh event loop.
        await engine.dispose()


async def _embed_knowledge(source_id: str) -> None:
    settings = get_settings()
    if not settings.llm_api_key:
        await _set_source_status(source_id, "failed")
        raise RuntimeError("OpenAI API key is required for knowledge embeddings")
    try:
        async with SessionLocal() as db:
            source = await db.get(KnowledgeSource, source_id)
            if not source:
                return
            chunks = list((await db.scalars(
                select(KnowledgeChunk).where(KnowledgeChunk.source_id == source_id).order_by(KnowledgeChunk.id)
            )).all())
            provider = OpenAIEmbeddingProvider(settings.llm_api_key, settings.embedding_model)
            for offset in range(0, len(chunks), 32):
                batch = chunks[offset:offset + 32]
                vectors = await provider.embed([chunk.content for chunk in batch])
                if len(vectors) != len(batch):
                    raise RuntimeError("Embedding provider returned an unexpected vector count")
                for chunk, vector in zip(batch, vectors, strict=True):
                    chunk.embedding = vector
            source.status = "ready"
            await db.commit()
    except Exception:
        await _set_source_status(source_id, "failed")
        raise


async def _set_source_status(source_id: str, status: str) -> None:
    async with SessionLocal.begin() as db:
        source = await db.get(KnowledgeSource, source_id)
        if source:
            source.status = status
