"""Swarm orchestration pipeline."""

from __future__ import annotations

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
    case_id = request.case_id or rid
    transcript = request.transcript.strip()

    evidence, top_score = retrieve_evidence(
        settings,
        kb,
        transcript,
        top_n=settings.rerank_top_n,
        min_score=settings.rerank_min_score,
    )

    if request.abstain_when_low_evidence and (
        not evidence or (top_score is not None and top_score < settings.rerank_min_score)
    ):
        empty_prosecutor = run_prosecutor(transcript, evidence)
        empty_defender = run_defender(transcript, evidence)
        result = SwarmAnalyzeResult(
            request_id=rid,
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
    defender = await run_defender_agent(settings, transcript, evidence)
    arbiter = await run_arbiter_agent(
        settings,
        transcript,
        prosecutor,
        defender,
        evidence,
        active_genes,
    )

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

    logger.info(
        "swarm analyze completed",
        extra={
            "meta": {
                "request_id": rid,
                "case_id": case_id,
                "checklist_items": len(checklist),
                "genes_applied": genes_applied,
                "mode": settings.mode,
                "llm_provider": settings.llm_provider,
                "retrieval_mode": settings.retrieval_mode,
            }
        },
    )

    if audit_store:
        audit_store.append(case_id=case_id, transcript=transcript, result=result)

    return result
