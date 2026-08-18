import argparse
import asyncio
from pathlib import Path

from app.database import SessionLocal, create_schema
from app.models import KnowledgeChunk, KnowledgeSource


async def ingest(path: Path, source_type: str) -> None:
    await create_schema()
    text = path.read_text(encoding="utf-8", errors="ignore")
    async with SessionLocal() as db:
        source = KnowledgeSource(title=path.stem, source_type=source_type, metadata_json={"path":str(path)})
        db.add(source)
        await db.flush()
        chunks = [text[i:i+1800] for i in range(0, len(text), 1500) if text[i:i+1800].strip()]
        for index, content in enumerate(chunks):
            db.add(KnowledgeChunk(source_id=source.id, content=content, metadata_json={"section":index+1}, embedding=None))
        await db.commit()
    print(f"Ingested {path.name}: {len(chunks)} chunks, source={source.id}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest UTF-8 text/Markdown knowledge")
    parser.add_argument("path", type=Path)
    parser.add_argument("--type", default="CUSTOM_SOURCE")
    args = parser.parse_args()
    asyncio.run(ingest(args.path, args.type))


if __name__ == "__main__":
    main()
