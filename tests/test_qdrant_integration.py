"""Qdrant integration tests against a real Qdrant instance.

Run only when CONDUCTGENE_QDRANT_URL is set (CI: qdrant service container;
local: `docker run -p 6333:6333 qdrant/qdrant`). A deterministic stub
embedder replaces BGE so no model services are required.
"""

from __future__ import annotations

import os
import random
import uuid

import pytest

from conductgene.config import Settings
from conductgene.kb.memory import KbChunk

QDRANT_URL = os.environ.get("CONDUCTGENE_QDRANT_URL", "")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not QDRANT_URL, reason="CONDUCTGENE_QDRANT_URL not set"),
]

VECTOR_SIZE = 32


def stub_embedding(text: str) -> list[float]:
    """Deterministic pseudo-embedding: identical text → identical vector."""
    rng = random.Random(text)
    return [rng.uniform(-1.0, 1.0) for _ in range(VECTOR_SIZE)]


@pytest.fixture
def retriever():
    from conductgene.retrieval.qdrant_store import QdrantRetriever

    settings = Settings(
        qdrant_url=QDRANT_URL,
        qdrant_collection=f"conductgene_it_{uuid.uuid4().hex[:8]}",
    )
    r = QdrantRetriever(settings, vector_size=VECTOR_SIZE)
    r.ensure_collection()
    yield r
    r._client.delete_collection(collection_name=settings.qdrant_collection)


def _chunks() -> list[KbChunk]:
    return [
        KbChunk(
            chunk_id="c1",
            doc_id="policy-threats",
            section="4.1",
            text="Agents must never use arrest or jail language with customers.",
        ),
        KbChunk(
            chunk_id="c2",
            doc_id="policy-escalation",
            section="4.2",
            text="Offering a repayment plan or supervisor callback counts as escalation.",
        ),
        KbChunk(
            chunk_id="c3",
            doc_id="policy-disclosure",
            section="2.1",
            text="Agents must disclose the company name at the start of every call.",
        ),
    ]


def test_ensure_collection_is_idempotent(retriever):
    retriever.ensure_collection()
    retriever.ensure_collection()


def test_recreate_collection_resets_points(retriever):
    from conductgene.retrieval.qdrant_store import chunk_payload, stable_chunk_id

    chunks = _chunks()
    n = retriever.upsert_chunks(
        ids=[stable_chunk_id(c) for c in chunks],
        vectors=[stub_embedding(c.text) for c in chunks],
        payloads=[chunk_payload(c) for c in chunks],
    )
    assert n == 3
    retriever.recreate_collection()
    hits = retriever.search(stub_embedding(chunks[0].text), top_n=3)
    assert hits == []


def test_upsert_and_search_round_trip(retriever):
    from conductgene.retrieval.qdrant_store import chunk_payload, stable_chunk_id

    chunks = _chunks()
    retriever.upsert_chunks(
        ids=[stable_chunk_id(c) for c in chunks],
        vectors=[stub_embedding(c.text) for c in chunks],
        payloads=[chunk_payload(c) for c in chunks],
    )

    query = _chunks()[1].text  # exact text of the escalation chunk
    hits = retriever.search(stub_embedding(query), top_n=3)

    assert len(hits) == 3
    top = hits[0]
    assert top.doc_id == "policy-escalation"
    assert top.section == "4.2"
    assert "repayment plan" in top.text
    assert top.score is not None and top.score == pytest.approx(1.0, abs=1e-5)
    # Results ordered by descending similarity
    scores = [h.score for h in hits]
    assert scores == sorted(scores, reverse=True)


def test_upsert_is_idempotent_by_stable_id(retriever):
    from conductgene.retrieval.qdrant_store import chunk_payload, stable_chunk_id

    chunks = _chunks()
    for _ in range(2):
        retriever.upsert_chunks(
            ids=[stable_chunk_id(c) for c in chunks],
            vectors=[stub_embedding(c.text) for c in chunks],
            payloads=[chunk_payload(c) for c in chunks],
        )
    hits = retriever.search(stub_embedding(chunks[0].text), top_n=10)
    assert len(hits) == 3
