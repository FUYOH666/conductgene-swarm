"""HTTP client for Services-BGE embedding and reranker."""

from __future__ import annotations

import httpx

from conductgene.config import Settings
from conductgene.logutil import get_logger

logger = get_logger(__name__)


class BgeClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._timeout = settings.service_timeout

    def embed_dense(self, texts: list[str]) -> list[list[float]]:
        if not self._settings.embedding_base_url:
            raise RuntimeError("embedding_base_url not configured")
        url = self._settings.embedding_base_url.rstrip("/") + "/v1/embeddings"
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(
                url,
                json={"input": texts, "return_dense": True, "return_sparse": False},
            )
            resp.raise_for_status()
            data = resp.json()
        vectors: list[list[float]] = []
        for item in sorted(data.get("data", []), key=lambda x: x.get("index", 0)):
            emb = item.get("embedding") or item.get("dense_embedding")
            if emb is None:
                raise RuntimeError("embedding response missing dense vector")
            vectors.append(emb)
        return vectors

    def rerank(self, query: str, documents: list[str], *, top_n: int | None = None) -> list[tuple[int, float]]:
        if not self._settings.reranker_base_url:
            raise RuntimeError("reranker_base_url not configured")
        url = self._settings.reranker_base_url.rstrip("/") + "/v1/rerank"
        payload: dict = {
            "query": query,
            "documents": documents,
            "normalize": True,
        }
        if top_n is not None:
            payload["top_n"] = top_n
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            results = resp.json().get("results", [])
        ranked: list[tuple[int, float]] = []
        for row in results:
            score = row.get("score", row.get("relevance_score"))
            if score is None:
                raise RuntimeError("rerank response missing score field")
            ranked.append((int(row["index"]), float(score)))
        return ranked
