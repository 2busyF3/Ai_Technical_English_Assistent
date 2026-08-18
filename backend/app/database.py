import asyncio
import logging
from collections.abc import AsyncIterator

from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
logger = logging.getLogger(__name__)
engine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def create_schema(max_attempts: int = 12, retry_delay: float = 2.0) -> None:
    from app import models  # noqa: F401

    for attempt in range(1, max_attempts + 1):
        try:
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
            return
        except (OSError, OperationalError):
            if attempt == max_attempts:
                raise
            logger.warning(
                "database unavailable; retrying startup (%s/%s)",
                attempt,
                max_attempts,
            )
            await engine.dispose()
            await asyncio.sleep(retry_delay)
