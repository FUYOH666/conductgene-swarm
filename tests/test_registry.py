from __future__ import annotations

import pytest

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
