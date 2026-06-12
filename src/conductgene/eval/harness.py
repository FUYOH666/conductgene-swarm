"""Eval harness — run synthetic scenario suite."""

from __future__ import annotations

import tempfile
from pathlib import Path

from conductgene.config import Settings
from conductgene.eval.metrics import aggregate_metrics, build_case_result, match_golden
from conductgene.eval.scenarios import Scenario, get_demo_pair, load_all_scenarios
from conductgene.evolution.genes import GeneStore
from conductgene.kb.memory import MemoryKnowledgeBase
from conductgene.pipeline.swarm import swarm_analyze
from conductgene.schemas import EvalRunResponse, GeneLearnRequest, SwarmAnalyzeRequest


async def run_eval_suite(
    *,
    settings: Settings,
    kb: MemoryKnowledgeBase,
    gene_store: GeneStore,
    scenarios_dir: Path,
    suite: str = "all",
    apply_genes: bool = True,
) -> EvalRunResponse:
    scenarios = load_all_scenarios(scenarios_dir, suite=suite)
    case_results = []

    for scenario in scenarios:
        result = await swarm_analyze(
            settings=settings,
            kb=kb,
            gene_store=gene_store,
            request=SwarmAnalyzeRequest(
                transcript=scenario.transcript,
                case_id=scenario.id,
                apply_genes=apply_genes,
            ),
            request_id=f"eval-{scenario.id}",
        )
        golden_dict = scenario.golden.model_dump()
        passed, expected, actual, detail = match_golden(
            result,
            {k: v for k, v in golden_dict.items() if k in (
                "threat_language", "escalation_offered", "company_disclosure", "recording_disclosure"
            ) and v is not None},
            expect_abstain=scenario.golden.abstain,
        )
        case_results.append(
            build_case_result(scenario.id, passed, expected, actual, result, detail)
        )

    score, citation_cov, abstain_rate = aggregate_metrics(case_results)
    gene_learning = await _eval_gene_learning(settings, kb, scenarios_dir)

    return EvalRunResponse(
        suite=suite,
        total=len(case_results),
        passed=sum(1 for r in case_results if r.passed),
        score=score,
        citation_coverage=citation_cov,
        abstain_rate=abstain_rate,
        cases=case_results,
        gene_learning=gene_learning,
    )


async def compute_learn_eval_delta(
    *,
    settings: Settings,
    kb: MemoryKnowledgeBase,
    scenarios_dir: Path,
    request: GeneLearnRequest,
) -> tuple[float, float, int]:
    """Measure held-out eval delta before persisting a supervisor-approved gene."""
    _, heldout = get_demo_pair(scenarios_dir)
    if not heldout:
        return 0.0, 0.0, 0

    with tempfile.TemporaryDirectory() as tmp:
        isolated_genes = GeneStore(Path(tmp) / "genes.jsonl")

        before_heldout = await swarm_analyze(
            settings=settings,
            kb=kb,
            gene_store=isolated_genes,
            request=SwarmAnalyzeRequest(
                transcript=heldout.transcript,
                case_id=heldout.id,
                apply_genes=False,
            ),
        )
        before_score = _case_score(before_heldout, heldout)

        isolated_genes.learn_from_correction(
            request,
            eval_before=before_score,
            eval_after=None,
            heldout_cases=1,
        )

        after_heldout = await swarm_analyze(
            settings=settings,
            kb=kb,
            gene_store=isolated_genes,
            request=SwarmAnalyzeRequest(
                transcript=heldout.transcript,
                case_id=heldout.id,
                apply_genes=True,
            ),
        )
        after_score = _case_score(after_heldout, heldout)
        return before_score, after_score, 1


async def _eval_gene_learning(
    settings: Settings,
    kb: MemoryKnowledgeBase,
    scenarios_dir: Path,
) -> dict[str, float | bool | str | None]:
    learn_case, heldout = get_demo_pair(scenarios_dir)
    if not learn_case or not heldout:
        return {"available": False}

    gl = learn_case.gene_learning
    if not gl:
        return {"available": False}

    request = GeneLearnRequest(
        request_id=f"eval-{learn_case.id}",
        checklist_id=gl.checklist_id,
        corrected_status=gl.corrected_status,
        rationale=gl.rationale,
        trigger_pattern=gl.trigger_pattern,
        name="implicit_escalation_gene",
        title="Implicit escalation offer detection",
        supervisor_id="eval-supervisor",
        case_id=learn_case.id,
    )
    before_score, after_score, _ = await compute_learn_eval_delta(
        settings=settings,
        kb=kb,
        scenarios_dir=scenarios_dir,
        request=request,
    )

    with tempfile.TemporaryDirectory() as tmp:
        isolated_genes = GeneStore(Path(tmp) / "genes.jsonl")
        before_heldout = await swarm_analyze(
            settings=settings,
            kb=kb,
            gene_store=isolated_genes,
            request=SwarmAnalyzeRequest(
                transcript=heldout.transcript,
                case_id=heldout.id,
                apply_genes=False,
            ),
        )
        isolated_genes.learn_from_correction(
            request,
            eval_before=before_score,
            eval_after=after_score,
        )
        after_heldout = await swarm_analyze(
            settings=settings,
            kb=kb,
            gene_store=isolated_genes,
            request=SwarmAnalyzeRequest(
                transcript=heldout.transcript,
                case_id=heldout.id,
                apply_genes=True,
            ),
        )
        before_status = _status(before_heldout, gl.checklist_id)
        after_status = _status(after_heldout, gl.checklist_id)

        improved = (
            before_status != gl.corrected_status
            and after_status == gl.corrected_status
            and len(after_heldout.genes_applied) > 0
        )

        return {
            "available": True,
            "before_score": before_score,
            "after_score": after_score,
            "before_status": before_status,
            "after_status": after_status,
            "improved": improved,
            "genes_applied": len(after_heldout.genes_applied) > 0,
        }


def _status(result, checklist_id: str) -> str | None:
    for item in result.checklist:
        if item.id == checklist_id:
            return item.status
    return None


def _case_score(result, scenario: Scenario) -> float:
    if result.abstained:
        return 0.0 if not scenario.golden.abstain else 1.0
    golden = scenario.golden.model_dump()
    keys = [k for k in ("threat_language", "escalation_offered", "company_disclosure", "recording_disclosure") if golden.get(k)]
    if not keys:
        return 1.0
    matches = 0
    cmap = {c.id: c.status for c in result.checklist}
    for k in keys:
        if cmap.get(k) == golden[k]:
            matches += 1
    return matches / len(keys)
