from __future__ import annotations

from precedent.engine import decide
from precedent.judge.heuristic import HeuristicJudge, eval_predicate
from precedent.models import Case, JudgeOutput
from precedent.pack import Pack, PredicateDef
from precedent.spans import find_quote


def test_find_quote_exact_and_normalised() -> None:
    text = "Agent: I can   transfer you to a Supervisor.\nCustomer: ok"
    exact = find_quote(text, "transfer you")
    assert exact is not None and text[exact.start : exact.end] == "transfer you"
    loose = find_quote(text, "i can transfer you to a supervisor")
    assert loose is not None
    assert text[loose.start : loose.end] == "I can   transfer you to a Supervisor"
    assert find_quote(text, "arrest you") is None
    assert find_quote(text, "") is None
    assert find_quote(text, "ok") is None  # too short to count as evidence


def _pred(pattern: str) -> PredicateDef:
    return PredicateDef(id="p", question="?", speaker="Agent", patterns=[pattern])


def test_negation_before_and_inside_the_match() -> None:
    arrest = _pred(r"\barrest")
    assert eval_predicate(arrest, "Agent: Pay or we will have you arrested.").value == "yes"
    assert eval_predicate(arrest, "Agent: Nobody is going to arrest you.").value == "no"
    callback = _pred(r"supervisor\b[^.]{0,40}\bcall you back")
    assert eval_predicate(callback, "Agent: A supervisor will call you back.").value == "yes"
    assert eval_predicate(callback, "Agent: A supervisor will not call you back.").value == "no"


def test_speaker_filter_ignores_the_customer() -> None:
    arrest = _pred(r"\bpolice\b")
    text = "Customer: Will you send the police?\nAgent: No, we will not."
    assert eval_predicate(arrest, text).value == "no"


def test_quote_offsets_point_into_the_case() -> None:
    text = "Customer: hi\nAgent: we will call the police"
    ans = eval_predicate(_pred(r"\bpolice\b"), text)
    assert ans.quote is not None
    assert text[ans.quote.start : ans.quote.end] == "police"


def test_heuristic_abstains_out_of_domain(pack: Pack, outputs: dict[str, JudgeOutput]) -> None:
    assert outputs["CASE-022"].abstained  # hotel booking
    assert outputs["CASE-007"].abstained  # not a call
    assert not outputs["CASE-001"].abstained
    decisions = decide(pack, outputs["CASE-022"], [])
    assert {d.label for d in decisions.values()} == {"abstain"}


def test_heuristic_baseline_has_known_blind_spots(
    pack: Pack, outputs: dict[str, JudgeOutput]
) -> None:
    misses = sorted(
        (c.id, item)
        for c in pack.cases
        for item, label in c.golden.items()
        if decide(pack, outputs[c.id], [])[item].label != label
    )
    assert misses == [
        ("CASE-003", "company_disclosure"),
        ("CASE-019", "escalation_offered"),
        ("CASE-024", "escalation_offered"),
        ("CASE-026", "threat_language"),
        ("CASE-028", "escalation_offered"),
    ]


def test_heuristic_judge_id_and_quotes(pack: Pack) -> None:
    judge = HeuristicJudge(pack)
    case = Case(id="X", text="Agent: This is ABC Collections. Pay now or we will call the police.")
    out = judge.judge(case)
    assert judge.judge_id.startswith("heuristic:")
    assert out.items["threat_language"].label == "fail"
    quote = out.items["threat_language"].quote
    assert quote is not None and quote.text.lower() == "police"


def test_recorded_gemma_run_replays_offline(pack: Pack) -> None:
    """A real local-model run, replayed: its disagreements are pinned, not averaged."""
    from precedent.judge import judge_all
    from precedent.judge.cassette import ReplayJudge

    jdir = pack.judgements_dir()
    assert jdir is not None
    (cassette,) = sorted(jdir.glob("llm_gemma*.jsonl"))
    outputs = judge_all(ReplayJudge(cassette), pack.cases)
    misses = sorted(
        (c.id, item)
        for c in pack.cases
        for item, label in c.golden.items()
        if decide(pack, outputs[c.id], [])[item].label != label
    )
    assert misses == [
        ("CASE-003", "company_disclosure"),
        ("CASE-022", "company_disclosure"),
        ("CASE-022", "escalation_offered"),
        ("CASE-022", "recording_disclosure"),
        ("CASE-022", "threat_language"),
    ]
    downgraded = sorted(cid for cid, out in outputs.items() if out.notes)
    assert downgraded == ["CASE-001", "CASE-022"]
