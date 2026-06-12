"""Policy Gene MCP stub tests (tool payload functions, no MCP runtime)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from conductgene.evolution.genes import GeneStore
from conductgene.mcp.server import export_skill_payload, list_genes_payload
from conductgene.schemas import PolicyGene


def _seed_gene(store: GeneStore) -> PolicyGene:
    gene = PolicyGene(
        id="GENE-MCP001",
        name="mcp_test_gene",
        title="MCP test gene",
        trigger_pattern="repayment",
        action="override_checklist_status",
        target_checklist_id="escalation_offered",
        override_status="pass",
        created_at=datetime.now(tz=UTC),
        source_request_id="req-mcp",
        rationale="Repayment plan counts as escalation.",
        supervisor_id="supervisor-001",
    )
    store.append(gene)
    return gene


def test_list_genes_payload_empty(tmp_path: Path):
    store = GeneStore(tmp_path / "genes.jsonl")
    assert list_genes_payload(store) == []


def test_list_genes_payload_returns_active_genes(tmp_path: Path):
    store = GeneStore(tmp_path / "genes.jsonl")
    _seed_gene(store)
    payload = list_genes_payload(store)
    assert len(payload) == 1
    assert payload[0]["id"] == "GENE-MCP001"
    assert payload[0]["override_status"] == "pass"


def test_export_skill_payload_writes_skill_md(tmp_path: Path):
    store = GeneStore(tmp_path / "genes.jsonl")
    _seed_gene(store)
    result = export_skill_payload(store, str(tmp_path / "skill"))
    assert result["active_genes"] == 1
    skill = Path(result["path"])
    assert skill.name == "SKILL.md"
    assert "GENE-MCP001" in skill.read_text(encoding="utf-8")
