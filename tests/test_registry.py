from __future__ import annotations

import pytest

from precedent.events import EventStore
from precedent.gate import run_gate
from precedent.models import Correction, JudgeOutput, Rule
from precedent.pack import Pack
from precedent.registry import Registry, RegistryError


def _gate(registry: Registry, pack: Pack, outputs: dict[str, JudgeOutput], key: str) -> str:
    state = registry.state()
    rule = state.rules[key].rule
    report = run_gate(pack, outputs, state.active(pack.id), rule, list(state.corrections.values()))
    registry.record_gate("ci", report)
    return report.decision


def test_full_lifecycle(
    registry: Registry,
    pack: Pack,
    outputs: dict[str, JudgeOutput],
    rules: dict[str, Rule],
    correction: Correction,
) -> None:
    registry.record_correction("maria", correction)
    registry.propose("maria", rules["escalation-callback@1"])
    assert _gate(registry, pack, outputs, "escalation-callback@1") == "BLOCKED"
    with pytest.raises(RegistryError, match="blocked"):
        registry.approve("alex", "escalation-callback@1")

    registry.propose("maria", rules["escalation-callback@2"])
    assert _gate(registry, pack, outputs, "escalation-callback@2") == "PASSED"
    with pytest.raises(RegistryError, match="four-eyes"):
        registry.approve("maria", "escalation-callback@2")
    registry.approve("alex", "escalation-callback@2")
    assert [r.key for r in registry.active_rules(pack.id)] == ["escalation-callback@2"]

    with pytest.raises(RegistryError, match="reason"):
        registry.revert("alex", "escalation-callback@2", " ")
    registry.revert("alex", "escalation-callback@2", "rollback drill")
    assert registry.active_rules(pack.id) == []
    state = registry.state()
    assert state.rules["escalation-callback@2"].status == "reverted"
    assert state.rules["escalation-callback@1"].status == "blocked"
    assert registry.store.verify().ok


def test_approval_is_invalid_after_the_active_set_changes(
    registry: Registry,
    pack: Pack,
    outputs: dict[str, JudgeOutput],
    rules: dict[str, Rule],
    correction: Correction,
) -> None:
    registry.record_correction("maria", correction)
    other = rules["escalation-callback@2"].model_copy(update={"id": "other-rule"})
    registry.propose("maria", rules["escalation-callback@2"])
    registry.propose("maria", other)
    _gate(registry, pack, outputs, "escalation-callback@2")
    _gate(registry, pack, outputs, "other-rule@2")
    registry.approve("alex", "escalation-callback@2")
    with pytest.raises(RegistryError, match="gate again"):
        registry.approve("alex", "other-rule@2")


def test_new_version_supersedes_the_old(
    registry: Registry,
    pack: Pack,
    outputs: dict[str, JudgeOutput],
    rules: dict[str, Rule],
    correction: Correction,
) -> None:
    registry.record_correction("maria", correction)
    v2 = rules["escalation-callback@2"]
    v3 = v2.model_copy(update={"version": 3, "title": "same rule, reworded"})
    registry.propose("maria", v2)
    _gate(registry, pack, outputs, v2.key)
    registry.approve("alex", v2.key)
    registry.propose("maria", v3)
    _gate(registry, pack, outputs, v3.key)
    registry.approve("alex", v3.key)
    state = registry.state()
    assert state.rules[v2.key].status == "superseded"
    assert [r.key for r in state.active(pack.id)] == [v3.key]


def test_corrections_are_owned_by_their_reviewer(
    registry: Registry, correction: Correction
) -> None:
    with pytest.raises(RegistryError, match="reviewer"):
        registry.record_correction("alex", correction)
    registry.record_correction("maria", correction)
    with pytest.raises(RegistryError, match="already"):
        registry.record_correction("maria", correction)
    same = correction.model_copy(update={"id": "C-2", "human_label": "needs_review"})
    with pytest.raises(RegistryError, match="change the label"):
        registry.record_correction("maria", same)


def test_gate_report_must_match_the_rule(
    registry: Registry,
    pack: Pack,
    outputs: dict[str, JudgeOutput],
    rules: dict[str, Rule],
    correction: Correction,
) -> None:
    registry.record_correction("maria", correction)
    registry.propose("maria", rules["escalation-callback@2"])
    edited = rules["escalation-callback@2"].model_copy(update={"title": "edited after proposal"})
    report = run_gate(pack, outputs, [], edited, [correction])
    with pytest.raises(RegistryError, match="different rule content"):
        registry.record_gate("ci", report)


def test_duplicate_and_unknown(registry: Registry, rules: dict[str, Rule]) -> None:
    rule = rules["escalation-callback@2"]
    with pytest.raises(RegistryError, match="unknown correction"):
        registry.propose("maria", rule)
    plain = rule.model_copy(update={"source_corrections": []})
    registry.propose("maria", plain)
    with pytest.raises(RegistryError, match="already exists"):
        registry.propose("maria", plain)
    with pytest.raises(RegistryError):
        registry.approve("alex", "nope@1")
    with pytest.raises(RegistryError):
        registry.revert("alex", plain.key, "not active")
    registry.reject("alex", plain.key, "superseded by discussion")
    assert registry.state().rules[plain.key].status == "rejected"
    with pytest.raises(RegistryError):
        registry.reject("alex", plain.key, "again")


def test_approval_is_refused_if_data_or_judge_changed(
    registry: Registry,
    pack: Pack,
    outputs: dict[str, JudgeOutput],
    rules: dict[str, Rule],
    correction: Correction,
) -> None:
    registry.record_correction("maria", correction)
    registry.propose("maria", rules["escalation-callback@2"])
    _gate(registry, pack, outputs, "escalation-callback@2")
    key = "escalation-callback@2"
    judge = next(iter(outputs.values())).judge_id
    with pytest.raises(RegistryError, match="labelled cases changed"):
        registry.approve("alex", key, dataset_hash="0" * 64, judge_id=judge)
    with pytest.raises(RegistryError, match="judge changed"):
        registry.approve("alex", key, dataset_hash=pack.dataset_hash(), judge_id="llm:other:1")
    # replaying the same model's recording counts as the same judge
    registry.approve("alex", key, dataset_hash=pack.dataset_hash(), judge_id=f"replay:{judge}")
    assert [r.key for r in registry.active_rules(pack.id)] == [key]


def test_a_relabelled_blocked_report_is_refused(
    registry: Registry,
    pack: Pack,
    outputs: dict[str, JudgeOutput],
    rules: dict[str, Rule],
    correction: Correction,
) -> None:
    """Codex review: a BLOCKED report edited to say PASSED used to be accepted."""
    registry.record_correction("maria", correction)
    registry.propose("maria", rules["escalation-callback@1"])
    report = run_gate(pack, outputs, [], rules["escalation-callback@1"], [correction])
    forged = report.model_copy(update={"decision": "PASSED"})
    with pytest.raises(RegistryError, match="blocking checks"):
        registry.record_gate("mallory", forged)


def test_new_corrections_invalidate_a_passed_gate(
    registry: Registry,
    pack: Pack,
    outputs: dict[str, JudgeOutput],
    rules: dict[str, Rule],
    correction: Correction,
) -> None:
    registry.record_correction("maria", correction)
    registry.propose("maria", rules["escalation-callback@2"])
    _gate(registry, pack, outputs, "escalation-callback@2")
    case = pack.case("CASE-026")
    registry.record_correction(
        "lena",
        Correction(
            id="C-0002", pack=pack.id, case_id=case.id, case_hash=case.hash,
            item="threat_language", ai_label="pass", human_label="fail",
            reviewer="lena", error_type="missing_context",
        ),
    )  # fmt: skip
    with pytest.raises(RegistryError, match="corrections were recorded"):
        registry.approve("alex", "escalation-callback@2")


def test_a_damaged_log_stops_all_changes(
    store: EventStore, registry: Registry, rules: dict[str, Rule], correction: Correction
) -> None:
    import sqlite3

    registry.record_correction("maria", correction)
    conn = sqlite3.connect(store.path)
    conn.execute("DROP TRIGGER events_no_update")
    conn.execute("UPDATE events SET actor = 'mallory' WHERE seq = 1")
    conn.commit()
    conn.close()
    with pytest.raises(RegistryError, match="failed verification"):
        registry.propose("maria", rules["escalation-callback@2"])


def test_the_author_cannot_record_the_gate(
    registry: Registry,
    pack: Pack,
    outputs: dict[str, JudgeOutput],
    rules: dict[str, Rule],
    correction: Correction,
) -> None:
    registry.record_correction("maria", correction)
    stored = registry.propose("maria", rules["escalation-callback@2"])
    report = run_gate(pack, outputs, [], stored, [correction])
    with pytest.raises(RegistryError, match="segregation of duties"):
        registry.record_gate("maria", report)


def test_approval_reproduces_the_gate_and_keeps_the_evidence(
    registry: Registry,
    pack: Pack,
    outputs: dict[str, JudgeOutput],
    rules: dict[str, Rule],
    correction: Correction,
) -> None:
    registry.record_correction("maria", correction)
    rule = registry.propose("maria", rules["escalation-callback@2"])
    _gate(registry, pack, outputs, rule.key)
    record = registry.state().rules[rule.key]
    assert record.gate_report is not None  # the full report is in the log, not just its hash
    assert record.gate_report.content_hash() == record.gate_report_hash

    tampered = dict(outputs)
    tampered["CASE-024"] = outputs["CASE-001"].model_copy(
        update={"case_id": "CASE-024", "case_hash": pack.case("CASE-024").hash}
    )
    different = run_gate(pack, tampered, [], rule, [correction])
    with pytest.raises(RegistryError, match="does not reproduce"):
        registry.approve("alex", rule.key, rerun=different)

    same = run_gate(pack, outputs, [], rule, [correction])
    registry.approve("alex", rule.key, rerun=same, rationale="policy says callbacks count")
    record = registry.state().rules[rule.key]
    assert record.status == "active" and record.approval_rationale == "policy says callbacks count"
    approved = [e for e in registry.store.events() if e.type == "rule.approved"][-1]
    assert approved.payload["reproduced"] is True
    assert approved.payload["report_hash"] == record.gate_report_hash
