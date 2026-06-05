"""Qdrant vector store for policy KB chunks."""

from __future__ import annotations

import hashlib
import uuid
from typing import Any

from conductgene.config import Settings
from conductgene.kb.memory import KbChunk
from conductgene.logutil import get_logger
from conductgene.schemas import EvidenceSnippet

logger = get_logger(__name__)


def stable_chunk_id(chunk: KbChunk) -> str:
    raw = f"{chunk.doc_id}:{chunk.section or ''}:{chunk.text[:200]}"
    digest = hashlib.sha256(raw.encode()).hexdigest()
    return str(uuid.UUID(digest[:32]))


def chunk_payload(chunk: KbChunk, *, version: str = "1") -> dict[str, Any]:
    return {
        "document_id": chunk.doc_id,
        "source_type": "policy",
        "doc_id": chunk.doc_id,
        "section": chunk.section,
        "text": chunk.text,
        "version": version,
        "tags": ["synthetic", "policy"],
    }


class QdrantRetriever:
    def __init__(self, settings: Settings, vector_size: int = 1024) -> None:
        self._settings = settings
        self._vector_size = vector_size
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http import models as qmodels
        except ImportError as exc:
            raise RuntimeError(
                "qdrant-client not installed; run: uv sync --extra retrieval"
            ) from exc

        self._qmodels = qmodels
        self._client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            timeout=settings.service_timeout,
        )

    def ensure_collection(self) -> None:
        name = self._settings.qdrant_collection
        qmodels = self._qmodels
        collections = self._client.get_collections().collections
        if any(c.name == name for c in collections):
            return
        self._client.create_collection(
            collection_name=name,
            vectors_config=qmodels.VectorParams(
                size=self._vector_size,
                distance=qmodels.Distance.COSINE,
            ),
        )
        logger.info("qdrant collection created", extra={"meta": {"collection": name}})

    def recreate_collection(self) -> None:
        name = self._settings.qdrant_collection
        collections = self._client.get_collections().collections
        if any(c.name == name for c in collections):
            self._client.delete_collection(collection_name=name)
            logger.info("qdrant collection deleted", extra={"meta": {"collection": name}})
        self.ensure_collection()

    def upsert_chunks(self, ids: list[str], vectors: list[list[float]], payloads: list[dict]) -> int:
        qmodels = self._qmodels
        points = [
            qmodels.PointStruct(id=pid, vector=vec, payload=payload)
            for pid, vec, payload in zip(ids, vectors, payloads, strict=True)
        ]
        self._client.upsert(collection_name=self._settings.qdrant_collection, points=points)
        return len(points)

    def search(
        self,
        query_vector: list[float],
        *,
        top_n: int = 8,
    ) -> list[EvidenceSnippet]:
        response = self._client.query_points(
            collection_name=self._settings.qdrant_collection,
            query=query_vector,
            limit=top_n,
        )
        evidence: list[EvidenceSnippet] = []
        for hit in response.points:
            payload = hit.payload or {}
            evidence.append(
                EvidenceSnippet(
                    chunk_id=str(hit.id),
                    doc_id=str(payload.get("doc_id", "unknown")),
                    section=payload.get("section"),
                    text=str(payload.get("text", "")),
                    score=float(hit.score) if hit.score is not None else None,
                )
            )
        return evidence
