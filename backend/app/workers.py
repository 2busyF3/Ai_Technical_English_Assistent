import dramatiq
from dramatiq.brokers.redis import RedisBroker

from app.config import get_settings

dramatiq.set_broker(RedisBroker(url=get_settings().redis_url))


@dramatiq.actor(max_retries=3)
def summarize_conversation(session_id: str) -> None:
    """Queue boundary for provider-backed long-term conversation summaries."""
    # The synchronous actor is intentionally small; production provider calls are added here.
    print(f"summary requested for {session_id}")


@dramatiq.actor(max_retries=3)
def embed_knowledge(source_id: str) -> None:
    """Queue boundary for embedding newly ingested knowledge chunks."""
    print(f"embeddings requested for {source_id}")

