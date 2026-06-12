"""Policy Gene SKILL.md export tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from conductgene.evolution.skill_export import export_skill_md, render_skill_md
from conductgene.schemas import PolicyGene


def _gene() -> PolicyGene:
    return PolicyGene(
        id="gene-0001",
        name="implicit_repayment_escalation",
        title="Implicit repayment escalation detection",
        trigger_pattern="repayment",
        action="override_checklist_status",
        target_checklist_id="escalation_offered",
        override_status="pass",
        eval_score_before=0.94,
        eval_score_after=1.0,
        created_at=datetime.now(tz=UTC),
        source_request_id="req-1",
        rationale="Offering a repayment plan counts as escalation per policy 4.2.",
        supervisor_id="supervisor-001",
    )


def test_render_skill_md_contains_gene_rule():
    md = render_skill_md([_gene()], source_version="0.6.0")
    assert md.startswith("---\nname: conductgene-policy-genes")
    assert "Implicit repayment escalation detection" in md
    assert "`escalation_offered`" in md
    assert "`repayment`" in md
    assert "0.94 → 1.00" in md
    assert "supervisor `supervisor-001`" in md


def test_render_skill_md_empty_store():
    md = render_skill_md([], source_version="0.6.0")
    assert "No active Policy Genes" in md


def test_export_skill_md_writes_file(tmp_path: Path):
    out = export_skill_md([_gene()], tmp_path / "skill", source_version="0.6.0")
    assert out == tmp_path / "skill" / "SKILL.md"
    assert "gene-0001" in out.read_text(encoding="utf-8")
