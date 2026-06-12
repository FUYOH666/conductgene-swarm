"""Swarm orchestration pipeline."""

from __future__ import annotations

import time
import uuid

from conductgene.agents.dispatch import (
    run_arbiter_agent,
    run_defender_agent,
    run_prosecutor_agent,
)
from conductgene.agents.roles import (
    apply_genes_to_checklist,
    run_arbiter,
    run_defender,
    run_prosecutor,
)
from conductgene.audit.store import AuditStore
from conductgene.config import Settings
from conductgene.eval.metrics import citation_ok
from conductgene.evolution.genes import GeneStore
from conductgene.kb.memory import MemoryKnowledgeBase
from conductgene.logutil import get_logger
from conductgene.retrieval import retrieve_evidence
from conductgene.schemas import SwarmAnalyzeRequest, SwarmAnalyzeResult

logger = get_logger(__name__)


def _trace_stage(trace_id: str, stage: str, started: float, **fields: object) -> float:
    """Emit a structured per-stage trace event; returns a fresh stage timer."""
    now = time.perf_counter()
    suffix = "".join(f" {k}={v}" for k, v in fields.items())
    logger.info(
        "swarm_stage trace_id=%s stage=%s duration_ms=%.1f%s",
        trace_id,
        stage,
        (now - started) * 1000,
        suffix,
    )
    return now


def _coaching_tips(checklist: list) -> list[str]:
    tips: list[str] = []
    for item in checklist:
        if item.status == "fail" and item.id == "threat_language":
            tips.append("Remove arrest or jail language; offer escalation instead.")
        if item.status == "needs_review" and item.id == "threat_language":
            tips.append("Soften coercive tone; offer repayment or supervisor path.")
        if item.status == "needs_review" and item.id == "escalation_offered":
            tips.append("Explicitly offer supervisor callback per policy SLA.")
    return tips


def _extended_metrics(
    gene_store: GeneStore,
    *,
    abstained: bool,
    result: SwarmAnalyzeResult | None = None,
) -> dict[str, float | int | None]:
    base = gene_store.compute_evolution_metrics()
    if result is not None:
        base["citation_coverage"] = 1.0 if citation_ok(result) else 0.0
    base["abstain_rate"] = 1.0 if abstained else 0.0
    return base


async def swarm_analyze(
    *,
    settings: Settings,
    kb: MemoryKnowledgeBase,
    gene_store: GeneStore,
    request: SwarmAnalyzeRequest,
    request_id: str | None = None,
    audit_store: AuditStore | None = None,
) -> SwarmAnalyzeResult:
    rid = request_id or str(uuid.uuid4())
    trace_id = uuid.uuid4().hex[:16]
    case_id = request.case_id or rid
    transcript = request.transcript.strip()
    run_started = time.perf_counter()
    stage_t = run_started

    evidence, top_score = retrieve_evidence(
        settings,
        kb,
        transcript,
        top_n=settings.rerank_top_n,
        min_score=settings.rerank_min_score,
    )
    stage_t = _trace_stage(
        trace_id,
        "retrieval",
        stage_t,
        case_id=case_id,
        snippets=len(evidence),
        top_score=top_score,
        retrieval_mode=settings.retrieval_mode,
    )

    if request.abstain_when_low_evidence and (
        not evidence or (top_score is not None and top_score < settings.rerank_min_score)
    ):
        empty_prosecutor = run_prosecutor(transcript, evidence)
        empty_defender = run_defender(transcript, evidence)
        _trace_stage(
            trace_id,
            "verdict",
            run_started,
            case_id=case_id,
            abstained=True,
        )
        result = SwarmAnalyzeResult(
            request_id=rid,
            trace_id=trace_id,
            case_id=case_id,
            abstained=True,
            abstain_reason=(
                f"top evidence score {top_score} below threshold {settings.rerank_min_score}"
                if top_score is not None
                else "no evidence retrieved"
            ),
            prosecutor=empty_prosecutor,
            defender=empty_defender,
            arbiter=run_arbiter(empty_prosecutor, empty_defender, evidence),
            checklist=[],
            supervisor_summary="Abstained — insufficient grounded evidence for automated recommendation.",
            coaching_tips=[],
            evidence=evidence,
            evolution_metrics=_extended_metrics(gene_store, abstained=True),
        )
        if audit_store:
            audit_store.append(case_id=case_id, transcript=transcript, result=result)
        return result

    active_genes = gene_store.list_active()
    prosecutor = await run_prosecutor_agent(settings, transcript, evidence)
    stage_t = _trace_stage(trace_id, "prosecutor", stage_t, case_id=case_id)
    defender = await run_defender_agent(settings, transcript, evidence)
    stage_t = _trace_stage(trace_id, "defender", stage_t, case_id=case_id)
    arbiter = await run_arbiter_agent(
        settings,
        transcript,
        prosecutor,
        defender,
        evidence,
        active_genes,
    )
    stage_t = _trace_stage(trace_id, "arbiter", stage_t, case_id=case_id)

    checklist = list(arbiter.checklist)
    genes_applied: list[str] = []

    if request.apply_genes:
        checklist, genes_applied = apply_genes_to_checklist(
            checklist,
            active_genes,
            transcript,
        )

    result = SwarmAnalyzeResult(
        request_id=rid,
        trace_id=trace_id,
        case_id=case_id,
        abstained=False,
        prosecutor=prosecutor,
        defender=defender,
        arbiter=arbiter,
        checklist=checklist,
        supervisor_summary=arbiter.summary,
        coaching_tips=_coaching_tips(checklist),
        evidence=evidence,
        genes_applied=genes_applied,
        evolution_metrics={},
    )
    result.evolution_metrics = _extended_metrics(gene_store, abstained=False, result=result)

    _trace_stage(
        trace_id,
        "verdict",
        run_started,
        case_id=case_id,
        abstained=False,
        checklist_items=len(checklist),
        genes_applied=len(genes_applied),
        mode=settings.mode,
        llm_provider=settings.llm_provider,
    )

    if audit_store:
        audit_store.append(case_id=case_id, transcript=transcript, result=result)

    return result
