"""Per-run trace observability tests."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from conductgene.audit.store import AuditStore
from conductgene.config import Settings
from conductgene.evolution.genes import GeneStore
from conductgene.kb.memory import MemoryKnowledgeBase
from conductgene.pipeline.swarm import swarm_analyze
from conductgene.schemas import SwarmAnalyzeRequest


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    root = Path(__file__).resolve().parents[1]
    s = Settings(
        mode="mock",
        gene_store_path=tmp_path / "g.jsonl",
        audit_store_path=tmp_path / "a.jsonl",
        gene_audit_store_path=tmp_path / "ga.jsonl",
        kb_dir=root / "data/synthetic/kb",
        scenarios_dir=root / "data/scenarios",
    )
    s.resolve_paths(root)
    return s


@pytest.mark.asyncio
async def test_trace_id_in_result_and_audit(settings: Settings, tmp_path: Path, caplog):
    kb = MemoryKnowledgeBase(settings.kb_dir)
    genes = GeneStore(settings.gene_store_path)
    audit = AuditStore(settings.audit_store_path)

    with caplog.at_level(logging.INFO, logger="conductgene.pipeline.swarm"):
        result = await swarm_analyze(
            settings=settings,
            kb=kb,
            gene_store=genes,
            request=SwarmAnalyzeRequest(
                transcript="Agent: hello, this is Acme. Customer: hi.",
                case_id="TRACE-1",
            ),
            audit_store=audit,
        )

    assert result.trace_id
    record = audit.get("TRACE-1")
    assert record is not None
    assert record.result.trace_id == result.trace_id

    stage_lines = [m for m in caplog.messages if "swarm_stage" in m]
    assert any("stage=retrieval" in m for m in stage_lines)
    assert any("stage=verdict" in m for m in stage_lines)
    assert all(f"trace_id={result.trace_id}" in m for m in stage_lines)
