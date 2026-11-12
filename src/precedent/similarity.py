"""Similarity search over cases: embeddings plus an optional cross-encoder reranker.

Works with any OpenAI-compatible ``/v1/embeddings`` endpoint and a
``/v1/rerank`` endpoint that takes ``{"query", "documents"}`` (Services-BGE,
Jina, Cohere-compatible gateways). Configure with ``PRECEDENT_EMBED_URL`` and
``PRECEDENT_RERANK_URL``; both default to a local Services-BGE.

The gate can only test cases that have labels. Similarity is how Precedent
reaches the rest: it finds the unlabelled cases a proposed rule is most likely
to affect, so a reviewer labels those first.
"""

from __future__ import annotations

import math
import os
from collections.abc import Sequence
from dataclasses import dataclass

import httpx

DEFAULT_EMBED_URL = "http://127.0.0.1:9001/v1"
DEFAULT_RERANK_URL = "http://127.0.0.1:9002/v1"
DEFAULT_MODEL = "BAAI/bge-m3"


@dataclass(frozen=True)
class Neighbour:
    case_id: str
    score: float


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


class SimilarityClient:
    def __init__(
        self,
        *,
        embed_url: str | None = None,
        rerank_url: str | None = None,
        model: str | None = None,
        timeout: float = 60.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.embed_url = (
            embed_url or os.environ.get("PRECEDENT_EMBED_URL") or DEFAULT_EMBED_URL
        ).rstrip("/")
        rerank = rerank_url if rerank_url is not None else os.environ.get("PRECEDENT_RERANK_URL")
        self.rerank_url = (rerank if rerank is not None else DEFAULT_RERANK_URL).rstrip("/") or None
        self.model = model or os.environ.get("PRECEDENT_EMBED_MODEL") or DEFAULT_MODEL
        self._client = client or httpx.Client(timeout=timeout)
        self._cache: dict[str, list[float]] = {}

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        missing = [t for t in dict.fromkeys(texts) if t not in self._cache]
        for start in range(0, len(missing), 32):
            batch = missing[start : start + 32]
            resp = self._client.post(
                f"{self.embed_url}/embeddings", json={"model": self.model, "input": batch}
            )
            resp.raise_for_status()
            rows = sorted(resp.json()["data"], key=lambda r: r["index"])
            for text, row in zip(batch, rows, strict=True):
                self._cache[text] = [float(x) for x in row["embedding"]]
        return [self._cache[t] for t in texts]

    def rerank(self, query: str, documents: Sequence[str]) -> list[float]:
        if not self.rerank_url or not documents:
            return [0.0] * len(documents)
        resp = self._client.post(
            f"{self.rerank_url}/rerank", json={"query": query, "documents": list(documents)}
        )
        resp.raise_for_status()
        scores = [0.0] * len(documents)
        for row in resp.json()["results"]:
            scores[int(row["index"])] = float(row["relevance_score"])
        return scores

    def nearest(
        self,
        query: str,
        candidates: dict[str, str],
        *,
        k: int = 10,
        shortlist: int = 50,
    ) -> list[Neighbour]:
        """Top ``k`` candidates by embedding similarity, reordered by the reranker."""
        if not candidates:
            return []
        ids = list(candidates)
        q, *vecs = self.embed([query, *(candidates[i] for i in ids)])
        ranked = sorted(zip(ids, (cosine(q, v) for v in vecs), strict=True), key=lambda x: -x[1])
        short = ranked[:shortlist]
        if self.rerank_url:
            scores = self.rerank(query, [candidates[i] for i, _ in short])
            short = sorted(
                ((i, s) for (i, _), s in zip(short, scores, strict=True)), key=lambda x: -x[1]
            )
        return [Neighbour(i, s) for i, s in short[:k]]
