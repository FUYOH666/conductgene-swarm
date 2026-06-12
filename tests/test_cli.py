"""CLI dispatch tests for conductgene.main (in-process, isolated stores)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from conductgene.main import _dispatch

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def cli_env(tmp_path: Path, monkeypatch):
    """Isolate runtime stores and force offline mock mode."""
    monkeypatch.chdir(PROJECT_ROOT)
    monkeypatch.setenv("CONDUCTGENE_MODE", "mock")
    monkeypatch.setenv("CONDUCTGENE_LLM_PROVIDER", "mock")
    monkeypatch.setenv("CONDUCTGENE_RETRIEVAL_MODE", "memory")
    monkeypatch.setenv("CONDUCTGENE_GENE_STORE_PATH", str(tmp_path / "genes.jsonl"))
    monkeypatch.setenv("CONDUCTGENE_AUDIT_STORE_PATH", str(tmp_path / "audit.jsonl"))
    monkeypatch.setenv(
        "CONDUCTGENE_GENE_AUDIT_STORE_PATH", str(tmp_path / "gene_events.jsonl")
    )
    return tmp_path


def _ns(**kwargs) -> argparse.Namespace:
    return argparse.Namespace(**kwargs)


async def test_cli_analyze_scenario_file(cli_env, capsys):
    await _dispatch(
        _ns(
            command="analyze",
            transcript=None,
            file=PROJECT_ROOT / "data/scenarios/collections/case_002_coercive_soft.json",
            case_id=None,
            provider=None,
            model=None,
            mode=None,
        )
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["case_id"] == "CASE-002"
    assert payload["trace_id"]
    assert payload["checklist"]


async def test_cli_genes_list_empty(cli_env, capsys):
    await _dispatch(_ns(command="genes", genes_command=None))
    assert json.loads(capsys.readouterr().out) == []


async def test_cli_demo_then_genes_and_skill_export(cli_env, capsys, tmp_path):
    await _dispatch(_ns(command="demo"))
    capsys.readouterr()

    await _dispatch(_ns(command="genes", genes_command=None))
    genes = json.loads(capsys.readouterr().out)
    assert len(genes) == 1
    assert genes[0]["target_checklist_id"] == "escalation_offered"

    out_dir = tmp_path / "skill"
    await _dispatch(_ns(command="genes", genes_command="export-skill", out=out_dir))
    assert "SKILL.md" in capsys.readouterr().out
    assert "escalation_offered" in (out_dir / "SKILL.md").read_text(encoding="utf-8")


async def test_cli_eval_writes_report(cli_env, capsys, tmp_path):
    out = tmp_path / "eval.json"
    await _dispatch(_ns(command="eval", suite="all", out=out))
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["score"] == 1.0
    assert report["total"] == 16


async def test_cli_learn_stores_gene(cli_env, capsys):
    await _dispatch(
        _ns(
            command="learn",
            request_id="req-cli-1",
            checklist_id="escalation_offered",
            status="pass",
            rationale="Repayment plan counts as escalation.",
            trigger="repayment",
            supervisor_id="cli-supervisor",
        )
    )
    gene = json.loads(capsys.readouterr().out)
    assert gene["target_checklist_id"] == "escalation_offered"
    assert gene["active"] is True
