from __future__ import annotations

import asyncio

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from app.database import Base, engine


async def inspect_database() -> str:
    async with engine.begin() as connection:
        tables = await connection.run_sync(lambda sync: set(inspect(sync).get_table_names()))
        if not tables:
            from app import models  # noqa: F401
            if connection.dialect.name == "postgresql":
                await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await connection.run_sync(Base.metadata.create_all)
            action = "stamp_head"
        elif "alembic_version" not in tables:
            action = "stamp_legacy"
        else:
            action = "upgrade"
    await engine.dispose()
    return action


def prepare_database() -> None:
    action = asyncio.run(inspect_database())
    config = Config("alembic.ini")
    if action == "stamp_head":
        command.stamp(config, "head")
    elif action == "stamp_legacy":
        command.stamp(config, "0001")
        command.upgrade(config, "head")
    else:
        command.upgrade(config, "head")


def main() -> None:
    prepare_database()


if __name__ == "__main__":
    main()
