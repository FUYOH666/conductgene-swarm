"""Keyword overlap retrieval over in-memory KB."""

from __future__ import annotations

import re

from conductgene.kb.memory import KbChunk, MemoryKnowledgeBase
from conductgene.schemas import EvidenceSnippet


def _tokenize(text: str) -> set[str]:
    words = [t.lower() for t in re.findall(r"[a-zA-Z]{3,}", text)]
    tokens = set(words)
    for w in words:
        if len(w) >= 5:
            tokens.add(w[:5])
    return tokens


def _chunk_match_score(query_tokens: set[str], chunk_text: str) -> float:
    chunk_lower = chunk_text.lower()
    chunk_tokens = _tokenize(chunk_text)
    overlap = len(query_tokens & chunk_tokens)
    substring_hits = sum(1 for t in query_tokens if t in chunk_lower)
    hits = max(overlap, substring_hits)
    if hits == 0:
        return 0.0
    return hits / max(min(len(query_tokens), 8), 1)


def retrieve_from_memory(
    kb: MemoryKnowledgeBase,
    query: str,
    *,
    top_n: int = 8,
    min_score: float = 0.35,
) -> tuple[list[EvidenceSnippet], float | None]:
    """Return ranked evidence snippets and top score."""
    query_tokens = _tokenize(query)
    if not query_tokens:
        return [], None

    scored: list[tuple[float, KbChunk]] = []
    for chunk in kb.chunks:
        score = _chunk_match_score(query_tokens, chunk.text)
        if score > 0:
            scored.append((score, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_n]

    evidence = [
        EvidenceSnippet(
            chunk_id=ch.chunk_id,
            doc_id=ch.doc_id,
            section=ch.section,
            text=ch.text,
            score=score,
        )
        for score, ch in top
    ]
    top_score = top[0][0] if top else None

    if top_score is not None and top_score < min_score:
        return evidence, top_score

    return evidence, top_score
