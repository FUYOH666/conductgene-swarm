"""Gate a rule from Python, using only the public API.

uv run python examples/01_gate_a_rule.py
"""

from precedent import Condition, Correction, Rule, judge_all, load_pack, make_judge, run_gate

pack = load_pack("collections-conduct")
outputs = judge_all(make_judge(pack, "heuristic"), pack.cases)  # or "llm:<model>"

case = pack.case("CASE-019")
correction = Correction(
    id="C-1",
    pack=pack.id,
    case_id=case.id,
    case_hash=case.hash,
    item="escalation_offered",
    ai_label="needs_review",
    human_label="pass",
    reviewer="maria",
    error_type="policy_misinterpretation",
)

for trigger in ("mentions_repayment", "supervisor_callback_offered"):
    rule = Rule(
        id="callback",
        pack=pack.id,
        item="escalation_offered",
        title=f"{trigger} counts as an escalation offer",
        rationale="example",
        when=[Condition(predicate=trigger)],
        then="pass",
        source_corrections=[correction.id],
        counter_examples=["CASE-005"],
    )
    report = run_gate(pack, outputs, [], rule, [correction])
    assert report.labelled is not None
    print(
        f"{trigger:<28} {report.decision:<8} "
        f"fixes {report.labelled.fixes}  breaks {report.labelled.breaks}"
    )
