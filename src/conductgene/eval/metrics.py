"""Quality metrics for eval runs."""

from __future__ import annotations

from conductgene.schemas import ChecklistItem, EvalCaseResult, SwarmAnalyzeResult


GOLDEN_KEYS = (
    "threat_language",
    "escalation_offered",
    "company_disclosure",
    "recording_disclosure",
)


def checklist_map(items: list[ChecklistItem]) -> dict[str, str]:
    return {item.id: item.status for item in items}


def citation_ok(result: SwarmAnalyzeResult) -> bool:
    if result.abstained:
        return True
    if not result.evidence:
        return False
    valid_chunk_ids = {ev.chunk_id for ev in result.evidence}
    for item in result.checklist:
        if not item.cited_chunk_ids:
            if item.id in GOLDEN_KEYS:
                return False
            continue
        if not all(cid in valid_chunk_ids for cid in item.cited_chunk_ids):
            return False
    return True


def match_golden(
    result: SwarmAnalyzeResult,
    golden: dict[str, str | None],
    *,
    expect_abstain: bool,
) -> tuple[bool, dict[str, str | None], dict[str, str | None], str | None]:
    actual: dict[str, str | None] = {}
    expected: dict[str, str | None] = {}

    if expect_abstain:
        expected["abstain"] = "true"
        actual["abstain"] = str(result.abstained).lower()
        if not result.abstained:
            return False, expected, actual, "expected abstain but got verdict"
        return True, expected, actual, None

    if result.abstained:
        return False, expected, actual, "unexpected abstain"

    cmap = checklist_map(result.checklist)
    for key in GOLDEN_KEYS:
        exp = golden.get(key)
        if exp is None:
            continue
        expected[key] = exp
        actual[key] = cmap.get(key)
        if actual[key] != exp:
            return False, expected, actual, f"{key}: expected {exp}, got {actual[key]}"

    if not citation_ok(result):
        return False, expected, actual, "missing citations on checklist items"

    return True, expected, actual, None


def build_case_result(
    case_id: str,
    passed: bool,
    expected: dict[str, str | None],
    actual: dict[str, str | None],
    result: SwarmAnalyzeResult,
    detail: str | None,
) -> EvalCaseResult:
    return EvalCaseResult(
        case_id=case_id,
        passed=passed,
        expected=expected,
        actual=actual,
        abstained=result.abstained,
        citation_ok=citation_ok(result),
        detail=detail,
    )


def aggregate_metrics(results: list[EvalCaseResult]) -> tuple[float, float, float]:
    if not results:
        return 0.0, 0.0, 0.0
    passed = sum(1 for r in results if r.passed)
    score = passed / len(results)
    citation_cov = sum(1 for r in results if r.citation_ok) / len(results)
    abstain_rate = sum(1 for r in results if r.abstained) / len(results)
    return score, citation_cov, abstain_rate
