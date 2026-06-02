"""Tests for ConductGene Swarm."""

from __future__ import annotations

import pytest
from pathlib import Path

from conductgene.audit.gene_events import GeneAuditStore
from conductgene.audit.store import AuditStore
from conductgene.config import Settings
from conductgene.eval.harness import compute_learn_eval_delta, run_eval_suite
from conductgene.eval.metrics import citation_ok
from conductgene.eval.scenarios import load_all_scenarios
from conductgene.evolution.genes import GeneStore
from conductgene.kb.memory import MemoryKnowledgeBase
from conductgene.pipeline.swarm import swarm_analyze
from conductgene.schemas import (
    AgentOpinion,
    ChecklistItem,
    EvidenceSnippet,
    GeneLearnRequest,
    SwarmAnalyzeRequest,
    SwarmAnalyzeResult,
)


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def settings(project_root: Path, tmp_path: Path) -> Settings:
    s = Settings(
        mode="mock",
        gene_store_path=tmp_path / "genes.jsonl",
        audit_store_path=tmp_path / "audit.jsonl",
        gene_audit_store_path=tmp_path / "gene_events.jsonl",
        kb_dir=project_root / "data/synthetic/kb",
        scenarios_dir=project_root / "data/scenarios",
    )
    s.resolve_paths(project_root)
    return s


@pytest.fixture
def kb(settings: Settings) -> MemoryKnowledgeBase:
    return MemoryKnowledgeBase(settings.kb_dir)


@pytest.fixture
def gene_store(settings: Settings) -> GeneStore:
    return GeneStore(settings.gene_store_path)


@pytest.fixture
def audit_store(settings: Settings) -> AuditStore:
    return AuditStore(settings.audit_store_path)


@pytest.fixture
def gene_audit_store(settings: Settings) -> GeneAuditStore:
    return GeneAuditStore(settings.gene_audit_store_path)


@pytest.mark.asyncio
async def test_kb_loads_chunks(kb: MemoryKnowledgeBase):
    assert kb.chunk_count() >= 3


@pytest.mark.asyncio
async def test_case_002_coercive_soft(settings, kb, gene_store, audit_store):
    scenarios = {s.id: s for s in load_all_scenarios(settings.scenarios_dir)}
    sc = scenarios["CASE-002"]
    result = await swarm_analyze(
        settings=settings,
        kb=kb,
        gene_store=gene_store,
        audit_store=audit_store,
        request=SwarmAnalyzeRequest(transcript=sc.transcript, case_id=sc.id, apply_genes=False),
    )
    assert result.abstained is False
    threat = next(c for c in result.checklist if c.id == "threat_language")
    assert threat.status == "needs_review"
    assert threat.cited_chunk_ids
    assert audit_store.get("CASE-002") is not None


@pytest.mark.asyncio
async def test_abstain_case_007(settings, kb, gene_store):
    scenarios = {s.id: s for s in load_all_scenarios(settings.scenarios_dir)}
    result = await swarm_analyze(
        settings=settings,
        kb=kb,
        gene_store=gene_store,
        request=SwarmAnalyzeRequest(transcript=scenarios["CASE-007"].transcript, case_id="CASE-007"),
    )
    assert result.abstained is True


@pytest.mark.asyncio
async def test_gene_learning_case_002_to_005(settings, kb, gene_store):
    scenarios = {s.id: s for s in load_all_scenarios(settings.scenarios_dir)}
    case2, case5 = scenarios["CASE-002"], scenarios["CASE-005"]

    before = await swarm_analyze(
        settings=settings,
        kb=kb,
        gene_store=gene_store,
        request=SwarmAnalyzeRequest(transcript=case5.transcript, case_id=case5.id, apply_genes=False),
    )
    esc_before = next(c for c in before.checklist if c.id == "escalation_offered")
    assert esc_before.status == "needs_review"

    gl = case2.gene_learning
    assert gl is not None
    learn_req = GeneLearnRequest(
        request_id="req-demo",
        checklist_id=gl.checklist_id,
        corrected_status=gl.corrected_status,
        rationale=gl.rationale,
        trigger_pattern=gl.trigger_pattern,
        supervisor_id="test-supervisor",
        case_id=case2.id,
    )
    eval_before, eval_after, _ = await compute_learn_eval_delta(
        settings=settings,
        kb=kb,
        scenarios_dir=settings.scenarios_dir,
        request=learn_req,
    )
    gene_store.learn_from_correction(
        learn_req,
        eval_before=eval_before,
        eval_after=eval_after,
    )

    after = await swarm_analyze(
        settings=settings,
        kb=kb,
        gene_store=gene_store,
        request=SwarmAnalyzeRequest(transcript=case5.transcript, case_id=case5.id, apply_genes=True),
    )
    esc_after = next(c for c in after.checklist if c.id == "escalation_offered")
    assert after.genes_applied
    assert esc_after.status == "pass"


@pytest.mark.asyncio
async def test_rollback_reverts_heldout_behavior(settings, kb, gene_store):
    scenarios = {s.id: s for s in load_all_scenarios(settings.scenarios_dir)}
    case2, case5 = scenarios["CASE-002"], scenarios["CASE-005"]
    gl = case2.gene_learning
    assert gl is not None

    learn_req = GeneLearnRequest(
        request_id="req-rollback",
        checklist_id=gl.checklist_id,
        corrected_status=gl.corrected_status,
        rationale=gl.rationale,
        trigger_pattern=gl.trigger_pattern,
        supervisor_id="rollback-operator",
        case_id=case2.id,
    )
    before, after, _ = await compute_learn_eval_delta(
        settings=settings,
        kb=kb,
        scenarios_dir=settings.scenarios_dir,
        request=learn_req,
    )
    gene = gene_store.learn_from_correction(
        learn_req,
        eval_before=before,
        eval_after=after,
    )

    with_gene = await swarm_analyze(
        settings=settings,
        kb=kb,
        gene_store=gene_store,
        request=SwarmAnalyzeRequest(transcript=case5.transcript, case_id=case5.id, apply_genes=True),
    )
    assert with_gene.genes_applied
    assert next(c for c in with_gene.checklist if c.id == "escalation_offered").status == "pass"

    assert gene_store.rollback(gene.id) is True

    after_rollback = await swarm_analyze(
        settings=settings,
        kb=kb,
        gene_store=gene_store,
        request=SwarmAnalyzeRequest(transcript=case5.transcript, case_id=case5.id, apply_genes=True),
    )
    assert not after_rollback.genes_applied
    assert next(c for c in after_rollback.checklist if c.id == "escalation_offered").status == "needs_review"


@pytest.mark.asyncio
async def test_gene_rollback(settings, gene_store):
    gene = gene_store.learn_from_correction(
        GeneLearnRequest(
            request_id="req1",
            checklist_id="escalation_offered",
            corrected_status="pass",
            rationale="test",
            supervisor_id="sup1",
        )
    )
    assert gene_store.rollback(gene.id) is True
    assert gene_store.count_active() == 0


@pytest.mark.asyncio
async def test_gene_learn_writes_audit_event(settings, gene_store, gene_audit_store):
    gene = gene_store.learn_from_correction(
        GeneLearnRequest(
            request_id="req-audit",
            checklist_id="escalation_offered",
            corrected_status="pass",
            rationale="audit test",
            supervisor_id="sup-audit",
        ),
        eval_before=0.5,
        eval_after=1.0,
    )
    gene_audit_store.append_learned(
        gene,
        GeneLearnRequest(
            request_id="req-audit",
            checklist_id="escalation_offered",
            corrected_status="pass",
            rationale="audit test",
            supervisor_id="sup-audit",
        ),
        eval_before=0.5,
        eval_after=1.0,
    )
    events = gene_audit_store.export_all()
    assert any(e["event_type"] == "gene_learned" for e in events)


def test_citation_ok_rejects_invalid_chunk_ids():
    result = SwarmAnalyzeResult(
        request_id="r1",
        abstained=False,
        prosecutor=AgentOpinion(role="prosecutor", checklist=[], summary=""),
        defender=AgentOpinion(role="defender", checklist=[], summary=""),
        arbiter=AgentOpinion(role="arbiter", checklist=[], summary=""),
        checklist=[
            ChecklistItem(
                id="threat_language",
                status="pass",
                rationale="ok",
                cited_chunk_ids=["FAKE-CHUNK"],
            )
        ],
        supervisor_summary="",
        coaching_tips=[],
        evidence=[
            EvidenceSnippet(chunk_id="REAL-1", doc_id="d1", text="policy", score=0.9),
        ],
    )
    assert citation_ok(result) is False


@pytest.mark.parametrize(
    "persona",
    ["linear_qa_analyst", "nonlinear_supervisor", "strict_compliance", "adversarial_caller", "rollback_operator"],
)
def test_persona_matrix_has_scenarios(settings, persona):
    scenarios = load_all_scenarios(settings.scenarios_dir)
    personas = {s.persona for s in scenarios}
    assert persona in personas


@pytest.mark.asyncio
async def test_case_016_rollback_operator(settings, kb, gene_store):
    scenarios = {s.id: s for s in load_all_scenarios(settings.scenarios_dir)}
    sc = scenarios["CASE-016"]
    assert sc.persona == "rollback_operator"
    result = await swarm_analyze(
        settings=settings,
        kb=kb,
        gene_store=gene_store,
        request=SwarmAnalyzeRequest(transcript=sc.transcript, case_id=sc.id),
    )
    esc = next(c for c in result.checklist if c.id == "escalation_offered")
    assert esc.status == "pass"


@pytest.mark.asyncio
async def test_eval_suite_passes(settings, kb, gene_store):
    resp = await run_eval_suite(
        settings=settings,
        kb=kb,
        gene_store=gene_store,
        scenarios_dir=settings.scenarios_dir,
    )
    assert resp.total >= 16
    failed = [c for c in resp.cases if not c.passed]
    assert not failed, f"Failed cases: {[f.case_id for f in failed]}"
    assert resp.gene_learning and resp.gene_learning.get("improved") is True


def test_healthz_endpoint():
    from fastapi.testclient import TestClient
    from conductgene.api.app import app

    client = TestClient(app)
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_api_spine_contract(settings, tmp_path, project_root):
    from fastapi.testclient import TestClient
    from conductgene.api import app as api_module

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
        json={
            "transcript": "Agent: ABC Collections. If you don't pay today, serious consequences for your account. repayment path available.",
            "case_id": "API-TEST",
        },
    )
    assert analyze.status_code == 200
    body = analyze.json()
    assert body["ok"] is True
    req_id = body["result"]["request_id"]

    learn = client.post(
        "/genes/learn",
        json={
            "request_id": req_id,
            "checklist_id": "escalation_offered",
            "corrected_status": "pass",
            "rationale": "Supervisor approved",
            "trigger_pattern": "repayment",
            "supervisor_id": "sup-api",
            "approved": True,
        },
    )
    assert learn.status_code == 200
    gene_body = learn.json()
    gene_id = gene_body["id"]
    assert gene_body["eval_score_before"] is not None
    assert gene_body["eval_score_after"] is not None

    rollback = client.post(f"/genes/{gene_id}/rollback")
    assert rollback.status_code == 200

    missing = client.post("/genes/GENE-MISSING/rollback")
    assert missing.status_code == 404

    audit = client.get("/audit/API-TEST")
    assert audit.status_code == 200

    export = client.get("/audit/export")
    assert export.status_code == 200
    assert "gene_events" in export.json()

    eval_run = client.post("/eval/run", json={"suite": "all"})
    assert eval_run.status_code == 200
    assert eval_run.json()["total"] >= 16

    metrics = client.get("/metrics/evolution")
    assert metrics.status_code == 200
    assert metrics.json()["eval_cached_at"] is not None


def test_streamlit_ui_imports():
    from conductgene.ui import app as ui_app

    assert callable(ui_app.main)


def test_ui_api_client_module():
    from conductgene.ui import client

    assert hasattr(client, "ConductGeneClient")
