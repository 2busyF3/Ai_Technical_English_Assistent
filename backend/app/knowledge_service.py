from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader


@dataclass(frozen=True)
class ParsedChunk:
    content: str
    metadata: dict[str, int | str]


class KnowledgeDocumentParser:
    allowed_extensions = {".txt", ".md", ".pdf"}

    def parse(self, filename: str, raw: bytes) -> list[ParsedChunk]:
        extension = Path(filename).suffix.casefold()
        if extension not in self.allowed_extensions:
            raise ValueError("Only UTF-8 text, Markdown, and text-based PDF files are supported")
        if extension == ".pdf":
            return self._parse_pdf(raw)
        text = raw.decode("utf-8", errors="strict")
        return self._chunk(text, {"format": extension.lstrip(".")})

    def _parse_pdf(self, raw: bytes) -> list[ParsedChunk]:
        try:
            reader = PdfReader(BytesIO(raw))
        except Exception as exc:
            raise ValueError("The PDF could not be read") from exc
        chunks: list[ParsedChunk] = []
        for page_number, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            chunks.extend(self._chunk(text, {"format": "pdf", "page": page_number}))
        if not chunks:
            raise ValueError("The PDF contains no extractable text; scanned PDFs require OCR")
        return chunks

    @staticmethod
    def _chunk(text: str, metadata: dict[str, int | str]) -> list[ParsedChunk]:
        normalized = "\n".join(line.strip() for line in text.splitlines() if line.strip())
        if not normalized:
            return []
        return [
            ParsedChunk(normalized[offset:offset + 1800], {**metadata, "section": index + 1})
            for index, offset in enumerate(range(0, len(normalized), 1500))
            if normalized[offset:offset + 1800].strip()
        ]
