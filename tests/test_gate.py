from __future__ import annotations

from precedent.engine import decide, rule_fires
from precedent.gate import run_gate, validate_rule
from precedent.models import Condition, Correction, JudgeOutput, PredicateAnswer, Rule
from precedent.pack import Pack


def _checks(report: object) -> dict[str, bool]:
    return {c.name: c.passed for c in report.checks}  # type: ignore[attr-defined]


def test_v1_keyword_rule_is_blocked(
    pack: Pack,
    outputs: dict[str, JudgeOutput],
    rules: dict[str, Rule],
    correction: Correction,
) -> None:
    report = run_gate(pack, outputs, [], rules["escalation-callback@1"], [correction])
    assert report.decision == "BLOCKED"
    checks = _checks(report)
    assert checks["source_fixed"] is True  # it does fix the call it came from...
    assert checks["no_regressions"] is False  # ...and breaks three others
    broken = sorted(f.case_id for f in report.flips if f.kind == "broken")
    assert broken == ["CASE-005", "CASE-012", "CASE-023"]
    assert report.labelled is not None and (report.labelled.fixes, report.labelled.breaks) == (2, 3)
    assert report.heldout is not None and (report.heldout.fixes, report.heldout.breaks) == (1, 2)


def test_narrow_rule_passes(
    pack: Pack,
    outputs: dict[str, JudgeOutput],
    rules: dict[str, Rule],
    correction: Correction,
) -> None:
    report = run_gate(pack, outputs, [], rules["escalation-callback@2"], [correction])
    assert report.decision == "PASSED", report.blocking_failures
    assert sorted(f.case_id for f in report.flips if f.kind == "fixed") == [
        "CASE-019",
        "CASE-024",
        "CASE-028",
    ]
    assert not [f for f in report.flips if f.kind == "broken"]
    assert report.heldout is not None and (report.heldout.fixes, report.heldout.breaks) == (2, 0)
    assert report.labelled is not None and report.labelled.mcnemar_p == 0.25  # 3 fixes, 0 breaks
    assert next(c for c in report.checks if c.name == "has_effect").passed
    esc = next(m for m in report.metrics if m.item == "escalation_offered")
    assert esc.agreement_after > esc.agreement_before


def test_conflicting_rule_is_blocked(
    pack: Pack,
    outputs: dict[str, JudgeOutput],
    rules: dict[str, Rule],
    correction: Correction,
) -> None:
    active = [rules["escalation-callback@2"]]
    conflicting = Rule(
        id="repayment-needs-review",
        pack=pack.id,
        item="escalation_offered",
        title="Any repayment talk goes to review",
        rationale="test",
        when=[Condition(predicate="mentions_repayment")],
        then="needs_review",
        examples=["CASE-005"],
        counter_examples=["CASE-001"],
    )
    report = run_gate(pack, outputs, active, conflicting, [correction])
    assert report.decision == "BLOCKED"
    assert _checks(report)["no_conflicts"] is False
    after = decide(pack, outputs["CASE-019"], [*active, conflicting])
    assert after["escalation_offered"].source == "conflict"
    assert after["escalation_offered"].label == "needs_review"


def test_rule_needs_a_counter_example_and_known_predicates(
    pack: Pack, correction: Correction
) -> None:
    rule = Rule(
        id="r",
        pack=pack.id,
        item="escalation_offered",
        title="t",
        rationale="r",
        when=[Condition(predicate="mood_is_good")],
        then="pass",
        source_corrections=[correction.id],
    )
    problems = validate_rule(pack, rule, [correction])
    assert any("counter-example" in p for p in problems)
    assert any("mood_is_good" in p for p in problems)


def test_a_misread_does_not_justify_a_rule(
    pack: Pack, outputs: dict[str, JudgeOutput], rules: dict[str, Rule], correction: Correction
) -> None:
    misread = correction.model_copy(update={"error_type": "misread"})
    report = run_gate(pack, outputs, [], rules["escalation-callback@2"], [misread])
    assert report.decision == "BLOCKED"
    assert "test case" in report.checks[0].detail


def test_stale_correction_does_not_count(
    pack: Pack, outputs: dict[str, JudgeOutput], rules: dict[str, Rule], correction: Correction
) -> None:
    stale = correction.model_copy(update={"case_hash": "0" * 64})
    report = run_gate(pack, outputs, [], rules["escalation-callback@2"], [stale])
    assert report.decision == "BLOCKED"
    assert "changed since it was corrected" in report.checks[0].detail


def test_outputs_must_belong_to_their_cases(
    pack: Pack, outputs: dict[str, JudgeOutput], rules: dict[str, Rule], correction: Correction
) -> None:
    """Codex review: swapping in another case's output made the v1 rule pass."""
    forged = dict(outputs)
    for cid in ("CASE-005", "CASE-012", "CASE-023"):
        forged[cid] = outputs["CASE-001"]
    report = run_gate(pack, forged, [], rules["escalation-callback@1"], [correction])
    assert report.decision == "BLOCKED"
    assert "do not belong to their case" in report.checks[0].detail


def test_corrections_stay_tests_even_if_their_case_is_removed(
    pack: Pack, outputs: dict[str, JudgeOutput], rules: dict[str, Rule], correction: Correction
) -> None:
    orphan = correction.model_copy(update={"id": "C-0002", "case_id": "CASE-999"})
    report = run_gate(pack, outputs, [], rules["escalation-callback@2"], [correction, orphan])
    assert report.decision == "BLOCKED"
    assert "no longer in the pack" in report.checks[0].detail


def test_counter_examples_must_not_change_at_all(
    pack: Pack, outputs: dict[str, JudgeOutput], rules: dict[str, Rule], correction: Correction
) -> None:
    """A counter-example is "must not change", even when the change would be right."""
    rule = rules["escalation-callback@2"].model_copy(update={"counter_examples": ["CASE-024"]})
    report = run_gate(pack, outputs, [], rule, [correction])
    assert report.decision == "BLOCKED"
    assert _checks(report)["counter_examples_hold"] is False


def test_missing_judge_outputs_block(
    pack: Pack, outputs: dict[str, JudgeOutput], rules: dict[str, Rule], correction: Correction
) -> None:
    partial = dict(list(outputs.items())[:5])
    report = run_gate(pack, partial, [], rules["escalation-callback@2"], [correction])
    assert report.decision == "BLOCKED"
    assert "no judge output" in report.checks[0].detail


def test_unknown_never_fires_a_rule(
    outputs: dict[str, JudgeOutput], rules: dict[str, Rule]
) -> None:
    out = outputs["CASE-019"]
    rule = rules["escalation-callback@2"]
    assert rule_fires(rule, out)
    unknown = out.model_copy(
        update={
            "predicates": {
                **out.predicates,
                "supervisor_callback_offered": PredicateAnswer(
                    predicate_id="supervisor_callback_offered", value="unknown"
                ),
            }
        }
    )
    assert not rule_fires(rule, unknown)


def test_report_hash_is_stable(
    pack: Pack, outputs: dict[str, JudgeOutput], rules: dict[str, Rule], correction: Correction
) -> None:
    a = run_gate(pack, outputs, [], rules["escalation-callback@2"], [correction])
    b = run_gate(pack, outputs, [], rules["escalation-callback@2"], [correction])
    assert a.content_hash() == b.content_hash()


def test_rules_are_judge_specific(
    pack: Pack, rules: dict[str, Rule], correction: Correction
) -> None:
    """The v1 rule breaks 3 verdicts on the heuristic judge and 4 on Gemma 4."""
    from precedent.judge import judge_all
    from precedent.judge.cassette import ReplayJudge

    jdir = pack.judgements_dir()
    assert jdir is not None
    (cassette,) = sorted(jdir.glob("llm_gemma*.jsonl"))
    gemma = judge_all(ReplayJudge(cassette), pack.cases)
    v1 = run_gate(pack, gemma, [], rules["escalation-callback@1"], [correction])
    v2 = run_gate(pack, gemma, [], rules["escalation-callback@2"], [correction])
    assert v1.decision == "BLOCKED"
    assert sum(f.kind == "broken" for f in v1.flips) == 4
    assert v2.decision == "PASSED"
    assert v1.judge_id.startswith("llm:gemma")  # the model, not the transport
