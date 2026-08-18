import argparse
import asyncio
from pathlib import Path

from app.database import SessionLocal
from app.knowledge_service import KnowledgeDocumentParser
from app.models import KnowledgeChunk, KnowledgeSource


async def ingest(path: Path, source_type: str) -> None:
    chunks = KnowledgeDocumentParser().parse(path.name, path.read_bytes())
    async with SessionLocal() as db:
        source = KnowledgeSource(title=path.stem, source_type=source_type, metadata_json={"path":str(path)})
        db.add(source)
        await db.flush()
        for chunk in chunks:
            db.add(KnowledgeChunk(source_id=source.id, content=chunk.content, metadata_json=chunk.metadata, embedding=None))
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
