"""Service discovery for BGE, Qdrant, and LLM providers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import httpx

from conductgene.config import Settings

ServiceStatus = Literal["ok", "degraded", "skipped", "error"]


@dataclass(frozen=True)
class ServiceProbeResult:
    service: str
    status: ServiceStatus
    endpoint: str | None
    details: str
    recommended_next_step: str


def _probe_readyz(client: httpx.Client, base_url: str, name: str) -> ServiceProbeResult:
    url = base_url.rstrip("/")
    ready_url = f"{url}/readyz"
    try:
        resp = client.get(ready_url, timeout=5.0)
        if resp.status_code == 200:
            return ServiceProbeResult(
                service=name,
                status="ok",
                endpoint=url,
                details=f"readyz HTTP {resp.status_code}",
                recommended_next_step="Use for retrieval / ingest",
            )
        return ServiceProbeResult(
            service=name,
            status="degraded",
            endpoint=url,
            details=f"readyz HTTP {resp.status_code}",
            recommended_next_step="Check service logs",
        )
    except httpx.HTTPError as exc:
        return ServiceProbeResult(
            service=name,
            status="error",
            endpoint=url,
            details=str(exc),
            recommended_next_step="Start service or fix URL in .env",
        )


def _probe_embedding(client: httpx.Client, settings: Settings) -> ServiceProbeResult:
    if not settings.embedding_base_url:
        return ServiceProbeResult(
            service="embedding",
            status="skipped",
            endpoint=None,
            details="CONDUCTGENE_EMBEDDING_BASE_URL not set",
            recommended_next_step="Set URL for qdrant ingest (MacBook :9001)",
        )
    base = settings.embedding_base_url.rstrip("/")
    ready = _probe_readyz(client, base, "embedding")
    if ready.status != "ok":
        return ready
    try:
        resp = client.post(
            f"{base}/v1/embeddings",
            json={"input": ["conduct QA policy probe"], "return_dense": True},
            timeout=settings.service_timeout,
        )
        if resp.status_code == 200 and resp.json().get("data"):
            return ServiceProbeResult(
                service="embedding",
                status="ok",
                endpoint=base,
                details="embeddings probe succeeded",
                recommended_next_step="Run scripts/ingest_qdrant.py",
            )
        return ServiceProbeResult(
            service="embedding",
            status="degraded",
            endpoint=base,
            details=f"embeddings HTTP {resp.status_code}",
            recommended_next_step="Check BGE-M3 service logs",
        )
    except httpx.HTTPError as exc:
        return ServiceProbeResult(
            service="embedding",
            status="error",
            endpoint=base,
            details=str(exc),
            recommended_next_step="Verify POST /v1/embeddings",
        )


def _probe_reranker(client: httpx.Client, settings: Settings) -> ServiceProbeResult:
    if not settings.reranker_base_url:
        return ServiceProbeResult(
            service="reranker",
            status="skipped",
            endpoint=None,
            details="CONDUCTGENE_RERANKER_BASE_URL not set",
            recommended_next_step="Set URL for qdrant_rerank mode (:9002)",
        )
    base = settings.reranker_base_url.rstrip("/")
    ready = _probe_readyz(client, base, "reranker")
    if ready.status != "ok":
        return ready
    try:
        resp = client.post(
            f"{base}/v1/rerank",
            json={
                "query": "fair debt collection",
                "documents": ["Offer escalation to supervisor", "Threaten arrest"],
                "normalize": True,
            },
            timeout=settings.service_timeout,
        )
        if resp.status_code == 200 and resp.json().get("results") is not None:
            return ServiceProbeResult(
                service="reranker",
                status="ok",
                endpoint=base,
                details="rerank probe succeeded",
                recommended_next_step="Set CONDUCTGENE_ENABLE_RERANKER=true",
            )
        return ServiceProbeResult(
            service="reranker",
            status="degraded",
            endpoint=base,
            details=f"rerank HTTP {resp.status_code}",
            recommended_next_step="Check reranker service logs",
        )
    except httpx.HTTPError as exc:
        return ServiceProbeResult(
            service="reranker",
            status="error",
            endpoint=base,
            details=str(exc),
            recommended_next_step="Verify POST /v1/rerank",
        )


def _probe_qdrant(client: httpx.Client, settings: Settings) -> ServiceProbeResult:
    if not settings.qdrant_url:
        return ServiceProbeResult(
            service="qdrant",
            status="skipped",
            endpoint=None,
            details="CONDUCTGENE_QDRANT_URL not set",
            recommended_next_step="Start Qdrant or set URL for vector retrieval",
        )
    base = settings.qdrant_url.rstrip("/")
    headers = {}
    if settings.qdrant_api_key:
        headers["api-key"] = settings.qdrant_api_key
    try:
        resp = client.get(f"{base}/collections", headers=headers, timeout=5.0)
        if resp.status_code != 200:
            return ServiceProbeResult(
                service="qdrant",
                status="degraded",
                endpoint=base,
                details=f"collections HTTP {resp.status_code}",
                recommended_next_step="Check Qdrant container",
            )
        names = [c.get("name") for c in resp.json().get("result", {}).get("collections", [])]
        coll = settings.qdrant_collection
        if coll in names:
            detail = f"collection '{coll}' exists"
            step = "Retrieval ready after ingest"
            status: ServiceStatus = "ok"
        else:
            detail = f"collection '{coll}' missing (have: {names or 'none'})"
            step = "Run scripts/ingest_qdrant.py"
            status = "degraded"
        return ServiceProbeResult(
            service="qdrant",
            status=status,
            endpoint=base,
            details=detail,
            recommended_next_step=step,
        )
    except httpx.HTTPError as exc:
        return ServiceProbeResult(
            service="qdrant",
            status="error",
            endpoint=base,
            details=str(exc),
            recommended_next_step="docker run -p 6333:6333 qdrant/qdrant",
        )


def _probe_openrouter(client: httpx.Client, settings: Settings) -> ServiceProbeResult:
    if not settings.openrouter_api_key:
        return ServiceProbeResult(
            service="openrouter",
            status="skipped",
            endpoint=settings.openrouter_base_url,
            details="CONDUCTGENE_OPENROUTER_API_KEY not set",
            recommended_next_step="Optional for v0.4 live LLM mode",
        )
    url = settings.openrouter_base_url.rstrip("/") + "/models"
    try:
        resp = client.get(
            url,
            headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
            timeout=settings.service_timeout,
        )
        if resp.status_code == 200:
            return ServiceProbeResult(
                service="openrouter",
                status="ok",
                endpoint=settings.openrouter_base_url,
                details="models endpoint reachable",
                recommended_next_step="Set CONDUCTGENE_LLM_PROVIDER=openrouter",
            )
        return ServiceProbeResult(
            service="openrouter",
            status="degraded",
            endpoint=settings.openrouter_base_url,
            details=f"HTTP {resp.status_code}",
            recommended_next_step="Verify API key",
        )
    except httpx.HTTPError as exc:
        return ServiceProbeResult(
            service="openrouter",
            status="error",
            endpoint=settings.openrouter_base_url,
            details=str(exc),
            recommended_next_step="Check network / key",
        )


def _probe_lmstudio(client: httpx.Client, settings: Settings) -> ServiceProbeResult:
    base = settings.lmstudio_base_url.rstrip("/")
    try:
        resp = client.get(f"{base}/models", timeout=5.0)
        if resp.status_code == 200:
            models = resp.json().get("data", [])
            model_hint = models[0].get("id", "") if models else "no model loaded"
            return ServiceProbeResult(
                service="lmstudio",
                status="ok",
                endpoint=base,
                details=f"OpenAI-compatible /models OK ({model_hint})",
                recommended_next_step="Set CONDUCTGENE_LLM_PROVIDER=lmstudio",
            )
        return ServiceProbeResult(
            service="lmstudio",
            status="degraded",
            endpoint=base,
            details=f"HTTP {resp.status_code}",
            recommended_next_step="Start LM Studio local server on :1234",
        )
    except httpx.HTTPError as exc:
        return ServiceProbeResult(
            service="lmstudio",
            status="error",
            endpoint=base,
            details=str(exc),
            recommended_next_step="Start LM Studio and enable Local Server",
        )


def _probe_instruct(client: httpx.Client, settings: Settings) -> ServiceProbeResult:
    base = settings.llm_base_url.rstrip("/")
    if "your-llm-host" in base:
        return ServiceProbeResult(
            service="instruct",
            status="skipped",
            endpoint=base,
            details="CONDUCTGENE_LLM_BASE_URL is placeholder",
            recommended_next_step="Set instruct gateway URL in .env",
        )
    headers = {}
    if settings.llm_api_key:
        headers["Authorization"] = f"Bearer {settings.llm_api_key}"
    try:
        health = client.get(f"{base.replace('/v1', '')}/healthz", timeout=5.0)
        if health.status_code == 200:
            return ServiceProbeResult(
                service="instruct",
                status="ok",
                endpoint=base,
                details="instruct gateway /healthz OK",
                recommended_next_step="Set CONDUCTGENE_LLM_PROVIDER=instruct",
            )
    except httpx.HTTPError:
        pass
    try:
        resp = client.get(f"{base}/models", headers=headers, timeout=5.0)
        if resp.status_code == 200:
            return ServiceProbeResult(
                service="instruct",
                status="ok",
                endpoint=base,
                details="instruct gateway /v1/models OK",
                recommended_next_step="Set CONDUCTGENE_LLM_PROVIDER=instruct",
            )
        return ServiceProbeResult(
            service="instruct",
            status="degraded",
            endpoint=base,
            details=f"HTTP {resp.status_code}",
            recommended_next_step="Check instruct gateway on :8002",
        )
    except httpx.HTTPError as exc:
        return ServiceProbeResult(
            service="instruct",
            status="error",
            endpoint=base,
            details=str(exc),
            recommended_next_step="Verify TailScale instruct gateway",
        )


def discover_services(settings: Settings) -> list[ServiceProbeResult]:
    """Probe configured external services; never logs secrets."""
    results: list[ServiceProbeResult] = []
    with httpx.Client() as client:
        results.append(_probe_embedding(client, settings))
        results.append(_probe_reranker(client, settings))
        results.append(_probe_qdrant(client, settings))
        results.append(_probe_openrouter(client, settings))
        results.append(_probe_lmstudio(client, settings))
        results.append(_probe_instruct(client, settings))
    return results


def format_service_table(results: list[ServiceProbeResult]) -> str:
    headers = ("service", "status", "endpoint", "details", "recommended_next_step")
    rows = [
        (
            r.service,
            r.status,
            r.endpoint or "-",
            r.details[:60] + ("…" if len(r.details) > 60 else ""),
            r.recommended_next_step[:50],
        )
        for r in results
    ]
    widths = [max(len(h), *(len(row[i]) for row in rows)) for i, h in enumerate(headers)]
    sep = "-" * (sum(widths) + 3 * 4)
    lines = [" | ".join(h.ljust(widths[i]) for i, h in enumerate(headers)), sep]
    for row in rows:
        lines.append(" | ".join(row[i].ljust(widths[i]) for i in range(len(headers))))
    return "\n".join(lines)
