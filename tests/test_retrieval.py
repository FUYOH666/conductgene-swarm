"""Tests for retrieval factory and BGE client."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx

from conductgene.config import Settings
from conductgene.kb.memory import MemoryKnowledgeBase
from conductgene.retrieval import retrieve_evidence
from conductgene.retrieval.bge_client import BgeClient


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def settings(project_root: Path) -> Settings:
    s = Settings(
        retrieval_mode="memory",
        kb_dir=project_root / "data/synthetic/kb",
    )
    s.resolve_paths(project_root)
    return s


@pytest.fixture
def kb(settings: Settings) -> MemoryKnowledgeBase:
    return MemoryKnowledgeBase(settings.kb_dir)


def test_memory_retrieval_unchanged(settings: Settings, kb: MemoryKnowledgeBase):
    evidence, score = retrieve_evidence(
        settings,
        kb,
        "If you don't pay today serious consequences escalation supervisor",
        top_n=5,
        min_score=0.1,
    )
    assert evidence
    assert score is not None
    assert score > 0


@respx.mock
def test_qdrant_mode_falls_back_to_memory_when_services_down(
    kb: MemoryKnowledgeBase, project_root: Path
):
    settings = Settings(
        retrieval_mode="qdrant",
        retrieval_fallback_to_memory=True,
        embedding_base_url="http://127.0.0.1:9001",
        qdrant_url="http://127.0.0.1:6333",
        kb_dir=project_root / "data/synthetic/kb",
    )
    settings.resolve_paths(project_root)
    respx.get("http://127.0.0.1:9001/readyz").mock(return_value=httpx.Response(503))
    evidence, score = retrieve_evidence(
        settings,
        kb,
        "escalation supervisor repayment",
        top_n=5,
        min_score=0.1,
    )
    assert evidence
    assert score is not None


@respx.mock
def test_bge_embed_dense():
    settings = Settings(embedding_base_url="http://127.0.0.1:9001")
    route = respx.post("http://127.0.0.1:9001/v1/embeddings").mock(
        return_value=httpx.Response(
            200,
            json={"data": [{"index": 0, "embedding": [0.1, 0.2, 0.3]}]},
        )
    )
    client = BgeClient(settings)
    vecs = client.embed_dense(["hello"])
    assert route.called
    assert vecs == [[0.1, 0.2, 0.3]]
