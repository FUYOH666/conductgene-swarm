"""Tests for service discovery."""

from __future__ import annotations

import httpx
import respx

from conductgene.config import Settings
from conductgene.services.discovery import discover_services


@respx.mock
def test_discover_skips_unconfigured_services():
    settings = Settings(
        _env_file=None,
        embedding_base_url=None,
        reranker_base_url=None,
        qdrant_url=None,
        openrouter_api_key=None,
        lmstudio_base_url="http://127.0.0.1:19999/v1",
        llm_base_url="http://127.0.0.1:19998/v1",
    )
    respx.get("http://127.0.0.1:19999/v1/models").mock(
        return_value=httpx.Response(503, json={"error": "down"})
    )
    respx.get("http://127.0.0.1:19998/v1/models").mock(
        return_value=httpx.Response(503, json={"error": "down"})
    )
    respx.get("http://127.0.0.1:19998/healthz").mock(
        return_value=httpx.Response(503, json={"error": "down"})
    )
    results = discover_services(settings)
    names = {r.service for r in results}
    assert "embedding" in names
    assert all(r.status == "skipped" for r in results if r.service == "embedding")
    instruct = next(r for r in results if r.service == "instruct")
    assert instruct.status in ("skipped", "degraded", "error")


@respx.mock
def test_discover_embedding_ok():
    settings = Settings(
        _env_file=None,
        embedding_base_url="http://127.0.0.1:9001",
        reranker_base_url=None,
        qdrant_url=None,
        openrouter_api_key=None,
        lmstudio_base_url="http://127.0.0.1:19999/v1",
        llm_base_url="http://127.0.0.1:19998/v1",
    )
    respx.get("http://127.0.0.1:19999/v1/models").mock(
        return_value=httpx.Response(503, json={"error": "down"})
    )
    respx.get("http://127.0.0.1:19998/v1/models").mock(
        return_value=httpx.Response(503, json={"error": "down"})
    )
    respx.get("http://127.0.0.1:19998/healthz").mock(
        return_value=httpx.Response(503, json={"error": "down"})
    )
    respx.get("http://127.0.0.1:9001/readyz").mock(return_value=httpx.Response(200, json={"ok": True}))
    respx.post("http://127.0.0.1:9001/v1/embeddings").mock(
        return_value=httpx.Response(200, json={"data": [{"index": 0, "embedding": [0.1]}]})
    )
    results = discover_services(settings)
    emb = next(r for r in results if r.service == "embedding")
    assert emb.status == "ok"
