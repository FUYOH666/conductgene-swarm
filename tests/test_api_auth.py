"""API key auth and rate limiting tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from conductgene.api import app as api_module
from conductgene.config import Settings


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def api_client(project_root: Path, tmp_path: Path):
    """Build a TestClient with isolated stores; settings tweaked per test."""

    def _make(**overrides) -> TestClient:
        from conductgene.audit.gene_events import GeneAuditStore
        from conductgene.audit.store import AuditStore
        from conductgene.evolution.genes import GeneStore
        from conductgene.kb.memory import MemoryKnowledgeBase

        api_module._settings = Settings(
            mode="mock",
            gene_store_path=tmp_path / "g.jsonl",
            audit_store_path=tmp_path / "a.jsonl",
            gene_audit_store_path=tmp_path / "ga.jsonl",
            kb_dir=project_root / "data/synthetic/kb",
            scenarios_dir=project_root / "data/scenarios",
            **overrides,
        )
        api_module._settings.resolve_paths(project_root)
        api_module._kb = MemoryKnowledgeBase(api_module._settings.kb_dir)
        api_module._genes = GeneStore(api_module._settings.gene_store_path)
        api_module._audit = AuditStore(api_module._settings.audit_store_path)
        api_module._gene_audit = GeneAuditStore(
            api_module._settings.gene_audit_store_path
        )
        api_module._eval_cache = None
        api_module._eval_cache_at = None
        api_module._rate_buckets.clear()
        return TestClient(api_module.app)

    yield _make
    # Reset singletons so other test modules rebuild from real settings.
    api_module._settings = None
    api_module._kb = None
    api_module._genes = None
    api_module._audit = None
    api_module._gene_audit = None
    api_module._rate_buckets.clear()


def test_auth_disabled_by_default(api_client):
    client = api_client()
    assert client.get("/genes").status_code == 200


def test_auth_rejects_missing_key(api_client):
    client = api_client(api_key="secret-key")
    resp = client.get("/genes")
    assert resp.status_code == 401
    assert "API key" in resp.json()["detail"]


def test_auth_rejects_wrong_key(api_client):
    client = api_client(api_key="secret-key")
    resp = client.get("/genes", headers={"X-API-Key": "wrong"})
    assert resp.status_code == 401


def test_auth_accepts_valid_key(api_client):
    client = api_client(api_key="secret-key")
    resp = client.get("/genes", headers={"X-API-Key": "secret-key"})
    assert resp.status_code == 200


def test_health_endpoints_stay_open_with_auth(api_client):
    client = api_client(api_key="secret-key")
    assert client.get("/healthz").status_code == 200
    assert client.get("/readyz").status_code == 200


def test_rate_limit_disabled_by_default(api_client):
    client = api_client()
    for _ in range(3):
        resp = client.post(
            "/swarm/analyze",
            json={"case_id": "T-1", "transcript": "Agent: hello. Customer: hi."},
        )
        assert resp.status_code == 200


def test_rate_limit_enforced_on_heavy_endpoints(api_client):
    client = api_client(rate_limit_rpm=2)
    payload = {"case_id": "T-2", "transcript": "Agent: hello. Customer: hi."}
    assert client.post("/swarm/analyze", json=payload).status_code == 200
    assert client.post("/swarm/analyze", json=payload).status_code == 200
    resp = client.post("/swarm/analyze", json=payload)
    assert resp.status_code == 429
    # Light endpoints are not rate limited.
    assert client.get("/genes").status_code == 200
