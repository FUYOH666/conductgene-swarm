#!/usr/bin/env python3
"""Ingest synthetic policy KB into Qdrant via BGE embeddings."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from conductgene.config import Settings
from conductgene.kb.memory import MemoryKnowledgeBase
from conductgene.logutil import get_logger, setup_logging
from conductgene.retrieval.bge_client import BgeClient
from conductgene.retrieval.qdrant_store import QdrantRetriever, chunk_payload, stable_chunk_id

logger = get_logger(__name__)


def main() -> int:
    setup_logging()
    settings = Settings()
    settings.resolve_paths(ROOT)

    if not settings.embedding_base_url:
        logger.error("CONDUCTGENE_EMBEDDING_BASE_URL required")
        return 1
    if not settings.qdrant_url:
        logger.error("CONDUCTGENE_QDRANT_URL required")
        return 1

    kb = MemoryKnowledgeBase(settings.kb_dir)
    if kb.chunk_count() == 0:
        logger.error("no KB chunks in %s", settings.kb_dir)
        return 1

    bge = BgeClient(settings)
    sample_vec = bge.embed_dense(["dimension probe"])[0]
    store = QdrantRetriever(settings, vector_size=len(sample_vec))
    store.ensure_collection()

    chunks = kb.chunks
    texts = [c.text for c in chunks]
    vectors = bge.embed_dense(texts)
    ids = [stable_chunk_id(c) for c in chunks]
    payloads = [chunk_payload(c) for c in chunks]

    count = store.upsert_chunks(ids, vectors, payloads)
    logger.info(
        "ingest complete",
        extra={
            "meta": {
                "collection": settings.qdrant_collection,
                "points": count,
                "vector_size": len(sample_vec),
            }
        },
    )

    probe = store.search(vectors[0], top_n=3)
    print(f"Ingested {count} points into '{settings.qdrant_collection}'")
    print("Sample retrieval:")
    for hit in probe:
        print(f"  - {hit.doc_id} score={hit.score:.4f} {hit.text[:80]}...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
