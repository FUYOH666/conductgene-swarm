"""Harmony and consistency tests across manifest, API, and docs."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

from conductgene import __version__
from conductgene.eval.scenarios import load_all_scenarios


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_manifest_loads_sixteen_cases(project_root: Path):
    manifest = yaml.safe_load((project_root / "data/scenarios/manifest.yaml").read_text())
    case_ids = [c["id"] for c in manifest["cases"]]
    assert len(case_ids) == 16
    scenarios = load_all_scenarios(project_root / "data/scenarios")
    assert {s.id for s in scenarios} == set(case_ids)


@pytest.mark.parametrize(
    "persona",
    ["linear_qa_analyst", "nonlinear_supervisor", "strict_compliance", "adversarial_caller", "rollback_operator"],
)
def test_every_persona_represented(project_root: Path, persona: str):
    scenarios = load_all_scenarios(project_root / "data/scenarios")
    assert any(s.persona == persona for s in scenarios)


def test_version_sync(project_root: Path):
    pyproject = (project_root / "pyproject.toml").read_text()
    match = re.search(r'^version = "([^"]+)"', pyproject, re.MULTILINE)
    assert match is not None
    assert match.group(1) == __version__

    card = json.loads((project_root / "docs/a2a-agent-card.json").read_text())
    assert card["version"] == __version__


def test_no_self_evolution_in_public_docs(project_root: Path):
    forbidden = re.compile(r"self[- ]evolution", re.IGNORECASE)
    for path in (project_root / "docs").rglob("*"):
        if path.is_file() and "_archive" not in path.parts:
            if path.suffix in {".md", ".json"}:
                assert not forbidden.search(path.read_text()), f"Found in {path.relative_to(project_root)}"


def test_readme_endpoints_exist_in_api(project_root: Path):
    readme = (project_root / "README.md").read_text()
    app_src = (project_root / "src/conductgene/api/app.py").read_text()
    endpoints = re.findall(r"`(GET|POST|DELETE) (/[^`]+)`", readme)
    assert len(endpoints) >= 9
    for method, path in endpoints:
        route_path = path.split("{")[0].rstrip("/")
        assert route_path in app_src or path.replace("{id}", "{gene_id}") in app_src, (
            f"{method} {path} missing from api/app.py"
        )


def test_audit_export_route_before_case_id(project_root: Path):
    app_src = (project_root / "src/conductgene/api/app.py").read_text()
    export_idx = app_src.index('"/audit/export"')
    case_idx = app_src.index('"/audit/{case_id}"')
    assert export_idx < case_idx


def test_gene_learn_appends_gene_audit(project_root: Path, tmp_path: Path):
    from fastapi.testclient import TestClient
    from conductgene.api import app as api_module
    from conductgene.audit.gene_events import GeneAuditStore
    from conductgene.audit.store import AuditStore
    from conductgene.config import Settings
    from conductgene.evolution.genes import GeneStore
    from conductgene.kb.memory import MemoryKnowledgeBase

    api_module._settings = Settings(
        mode="mock",
        gene_store_path=tmp_path / "g.jsonl",
        audit_store_path=tmp_path / "a.jsonl",
        gene_audit_store_path=tmp_path / "ge.jsonl",
        kb_dir=project_root / "data/synthetic/kb",
        scenarios_dir=project_root / "data/scenarios",
    )
    api_module._settings.resolve_paths(project_root)
    api_module._kb = MemoryKnowledgeBase(api_module._settings.kb_dir)
    api_module._genes = GeneStore(api_module._settings.gene_store_path)
    api_module._audit = AuditStore(api_module._settings.audit_store_path)
    api_module._gene_audit = GeneAuditStore(api_module._settings.gene_audit_store_path)
    api_module._eval_cache = None
    api_module._eval_cache_at = None

    client = TestClient(api_module.app)
    analyze = client.post(
        "/swarm/analyze",
        json={"transcript": "Agent: ABC Collections. repayment path with supervisor.", "case_id": "HARMONY"},
    )
    req_id = analyze.json()["result"]["request_id"]
    client.post(
        "/genes/learn",
        json={
            "request_id": req_id,
            "checklist_id": "escalation_offered",
            "corrected_status": "pass",
            "rationale": "harmony test",
            "trigger_pattern": "repayment",
            "supervisor_id": "harmony",
            "approved": True,
        },
    )
    events = client.get("/audit/export").json()["gene_events"]
    assert any(e["event_type"] == "gene_learned" for e in events)


def test_cli_audit_export(tmp_path: Path, project_root: Path):
    from conductgene.config import Settings
    from conductgene.audit.gene_events import GeneAuditStore
    from conductgene.audit.store import AuditStore

    settings = Settings(
        gene_store_path=tmp_path / "g.jsonl",
        audit_store_path=tmp_path / "a.jsonl",
        gene_audit_store_path=tmp_path / "ge.jsonl",
    )
    settings.resolve_paths(project_root)
    AuditStore(settings.audit_store_path)
    store = GeneAuditStore(settings.gene_audit_store_path)
    store.append_rollback("GENE-TEST")

    out = tmp_path / "export.json"
    import subprocess

    result = subprocess.run(
        ["uv", "run", "conductgene", "audit", "export", "--out", str(out)],
        cwd=project_root,
        capture_output=True,
        text=True,
        env={
            **dict(__import__("os").environ),
            "CONDUCTGENE_GENE_STORE_PATH": str(settings.gene_store_path),
            "CONDUCTGENE_AUDIT_STORE_PATH": str(settings.audit_store_path),
            "CONDUCTGENE_GENE_AUDIT_STORE_PATH": str(settings.gene_audit_store_path),
        },
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(out.read_text())
    assert "gene_events" in payload
