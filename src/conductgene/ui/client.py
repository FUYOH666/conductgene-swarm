"""Thin HTTP client for Streamlit or external demos against the local API."""

from __future__ import annotations

from typing import Any

import httpx

from conductgene.schemas import GeneLearnRequest, SwarmAnalyzeRequest


class ConductGeneClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8090", timeout: float = 120.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def analyze(self, request: SwarmAnalyzeRequest) -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(
                f"{self.base_url}/swarm/analyze",
                json=request.model_dump(exclude_none=True),
            )
            resp.raise_for_status()
            return resp.json()

    def learn_gene(self, request: GeneLearnRequest) -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(
                f"{self.base_url}/genes/learn",
                json=request.model_dump(exclude_none=True),
            )
            resp.raise_for_status()
            return resp.json()

    def rollback_gene(self, gene_id: str) -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(f"{self.base_url}/genes/{gene_id}/rollback")
            resp.raise_for_status()
            return resp.json()

    def export_audit(self) -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(f"{self.base_url}/audit/export")
            resp.raise_for_status()
            return resp.json()

    def evolution_metrics(self, *, refresh: bool = False) -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(
                f"{self.base_url}/metrics/evolution",
                params={"refresh": refresh},
            )
            resp.raise_for_status()
            return resp.json()
