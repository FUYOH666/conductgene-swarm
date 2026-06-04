"""Tests for service discovery."""

from __future__ import annotations

import httpx
import respx

from conductgene.config import Settings
from conductgene.services.discovery import discover_services


@respx.mock
def test_discover_skips_unconfigured_services():
    settings = Settings()
    results = discover_services(settings)
    names = {r.service for r in results}
    assert "embedding" in names
    assert all(r.status == "skipped" for r in results if r.service == "embedding")


@respx.mock
def test_discover_embedding_ok():
    settings = Settings(embedding_base_url="http://127.0.0.1:9001")
    respx.get("http://127.0.0.1:9001/readyz").mock(return_value=httpx.Response(200, json={"ok": True}))
    respx.post("http://127.0.0.1:9001/v1/embeddings").mock(
        return_value=httpx.Response(200, json={"data": [{"index": 0, "embedding": [0.1]}]})
    )
    results = discover_services(settings)
    emb = next(r for r in results if r.service == "embedding")
    assert emb.status == "ok"
