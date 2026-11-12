"""Rule lifecycle on top of the event log.

States are derived by replaying events, never stored separately, so the log
is the single source of truth::

    proposed ──gate──▶ passed ──approve (another person)──▶ active ──revert──▶ reverted
        │                 │                                    │
        └──gate──▶ blocked └──reject──▶ rejected                └─ newer version ─▶ superseded

An approval is valid only against the active rule set the gate saw; if
anything was activated or reverted since, the gate must run again.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from precedent.events import EventStore
from precedent.models import Correction, GateReport, Rule, ruleset_hash

Status = Literal["proposed", "blocked", "passed", "active", "superseded", "reverted", "rejected"]


class RegistryError(RuntimeError):
    pass


@dataclass
class RuleRecord:
    rule: Rule
    status: Status = "proposed"
    proposed_by: str = ""
    gate_decision: str | None = None
    gate_report_hash: str | None = None
    gated_against: str | None = None
    approved_by: str | None = None
    history: list[str] = field(default_factory=list)


@dataclass
class State:
    rules: dict[str, RuleRecord] = field(default_factory=dict)
    corrections: dict[str, Correction] = field(default_factory=dict)

    def active(self, pack: str | None = None) -> list[Rule]:
        return [
            r.rule
            for r in self.rules.values()
            if r.status == "active" and (pack is None or r.rule.pack == pack)
        ]


class Registry:
    def __init__(self, store: EventStore) -> None:
        self.store = store

    # --- projection ----------------------------------------------------------
    def state(self) -> State:
        st = State()
        for ev in self.store.events():
            p = ev.payload
            if ev.type == "correction.recorded":
                corr = Correction.model_validate(p["correction"])
                st.corrections[corr.id] = corr
            elif ev.type == "rule.proposed":
                rule = Rule.model_validate(p["rule"])
                st.rules[rule.key] = RuleRecord(rule=rule, proposed_by=ev.actor)
            elif ev.type == "rule.gated":
                rec = st.rules[p["rule_key"]]
                rec.gate_decision = p["decision"]
                rec.gate_report_hash = p["report_hash"]
                rec.gated_against = p["ruleset_before"]
                if rec.status in ("proposed", "blocked", "passed"):
                    rec.status = "passed" if p["decision"] == "PASSED" else "blocked"
            elif ev.type == "rule.approved":
                rec = st.rules[p["rule_key"]]
                for other in st.rules.values():
                    if other.rule.id == rec.rule.id and other.status == "active":
                        other.status = "superseded"
                        other.history.append(f"superseded by {rec.rule.key} (seq {ev.seq})")
                rec.status = "active"
                rec.approved_by = ev.actor
            elif ev.type == "rule.reverted":
                st.rules[p["rule_key"]].status = "reverted"
            elif ev.type == "rule.rejected":
                st.rules[p["rule_key"]].status = "rejected"
            if "rule_key" in p and p["rule_key"] in st.rules:
                st.rules[p["rule_key"]].history.append(f"{ev.type} by {ev.actor} (seq {ev.seq})")
        return st

    def active_rules(self, pack: str) -> list[Rule]:
        return self.state().active(pack)

    def corrections(self, pack: str) -> list[Correction]:
        return [c for c in self.state().corrections.values() if c.pack == pack]

    # --- commands --------------------------------------------------------------
    def record_correction(self, actor: str, correction: Correction) -> Correction:
        st = self.state()
        if correction.id in st.corrections:
            raise RegistryError(f"correction {correction.id} already recorded")
        if actor != correction.reviewer:
            raise RegistryError("a correction is recorded by the reviewer who made it")
        if correction.ai_label == correction.human_label:
            raise RegistryError("a correction must change the label")
        self.store.append(actor, "correction.recorded", {"correction": correction.model_dump()})
        return correction

    def propose(self, actor: str, rule: Rule) -> Rule:
        st = self.state()
        rule = rule.model_copy(update={"author": actor})
        if rule.key in st.rules:
            raise RegistryError(f"{rule.key} already exists; bump the version")
        for cid in rule.source_corrections:
            if cid not in st.corrections:
                raise RegistryError(f"unknown correction {cid}")
        self.store.append(actor, "rule.proposed", {"rule": rule.model_dump(mode="json")})
        return rule

    def record_gate(self, actor: str, report: GateReport) -> None:
        st = self.state()
        rec = st.rules.get(report.rule_key)
        if rec is None:
            raise RegistryError(f"unknown rule {report.rule_key}")
        if rec.rule.content_hash() != report.rule_hash:
            raise RegistryError("gate report was produced for different rule content")
        if rec.status not in ("proposed", "blocked", "passed"):
            raise RegistryError(f"{report.rule_key} is {rec.status}; nothing to gate")
        self.store.append(
            actor,
            "rule.gated",
            {
                "rule_key": report.rule_key,
                "decision": report.decision,
                "report_hash": report.content_hash(),
                "ruleset_before": report.ruleset_before,
                "dataset_hash": report.dataset_hash,
                "judge_id": report.judge_id,
                "failed": [c.name for c in report.blocking_failures],
            },
        )

    def approve(self, actor: str, rule_key: str) -> Rule:
        st = self.state()
        rec = st.rules.get(rule_key)
        if rec is None:
            raise RegistryError(f"unknown rule {rule_key}")
        if rec.status != "passed":
            raise RegistryError(f"{rule_key} is {rec.status}; only a rule that passed the gate")
        if actor == rec.proposed_by:
            raise RegistryError(
                f"four-eyes: {actor} proposed {rule_key} and cannot also approve it"
            )
        current = ruleset_hash(st.active(rec.rule.pack))
        if rec.gated_against != current:
            raise RegistryError(
                "active rules changed since this rule was gated; run the gate again"
            )
        self.store.append(actor, "rule.approved", {"rule_key": rule_key, "ruleset_before": current})
        return rec.rule

    def revert(self, actor: str, rule_key: str, reason: str) -> None:
        st = self.state()
        rec = st.rules.get(rule_key)
        if rec is None or rec.status != "active":
            raise RegistryError(f"{rule_key} is not active")
        if not reason.strip():
            raise RegistryError("a revert needs a reason")
        self.store.append(actor, "rule.reverted", {"rule_key": rule_key, "reason": reason})

    def reject(self, actor: str, rule_key: str, reason: str) -> None:
        st = self.state()
        rec = st.rules.get(rule_key)
        if rec is None or rec.status in ("active", "superseded", "reverted", "rejected"):
            raise RegistryError(f"{rule_key} cannot be rejected")
        self.store.append(actor, "rule.rejected", {"rule_key": rule_key, "reason": reason})
