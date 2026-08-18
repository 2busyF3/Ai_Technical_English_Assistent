from __future__ import annotations

from dataclasses import dataclass, field
from math import sqrt


@dataclass(frozen=True)
class RetrievalQuery:
    text: str
    source_types: set[str] = field(default_factory=set)
    specialization: str | None = None
    skill: str | None = None
    limit: int = 5


@dataclass(frozen=True)
class Candidate:
    content: str
    metadata: dict[str, object]
    embedding: list[float] | None = None


class HybridRetriever:
    """Portable MVP scorer: metadata gate + exact terms + optional cosine similarity."""

    def rank(self, query: RetrievalQuery, candidates: list[Candidate], query_embedding: list[float] | None = None) -> list[Candidate]:
        terms = {term.strip(".,:;()[]").lower() for term in query.text.split() if len(term) > 2}
        scored: list[tuple[float, Candidate]] = []
        for candidate in candidates:
            meta = candidate.metadata
            if query.source_types and meta.get("source_type") not in query.source_types:
                continue
            if query.specialization and meta.get("specialization") not in (None, query.specialization):
                continue
            if query.skill and meta.get("skill") not in (None, query.skill):
                continue
            words = {word.strip(".,:;()[]").lower() for word in candidate.content.split()}
            lexical = len(terms & words) / max(1, len(terms))
            semantic = self._cosine(query_embedding, candidate.embedding)
            authority = float(meta.get("technical_authority", 0.5))
            scored.append((lexical * 0.5 + semantic * 0.35 + authority * 0.15, candidate))
        return [candidate for _, candidate in sorted(scored, key=lambda pair: pair[0], reverse=True)[: query.limit]]

    @staticmethod
    def _cosine(left: list[float] | None, right: list[float] | None) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0
        denominator = sqrt(sum(x*x for x in left)) * sqrt(sum(x*x for x in right))
        return sum(x*y for x, y in zip(left, right, strict=True)) / denominator if denominator else 0.0

