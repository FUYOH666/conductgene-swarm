"""Apply active rules to a judge output.

The judge perceives (labels and predicate answers, each backed by a quote);
code decides. A rule fires only when every condition matches a definite
predicate answer; ``unknown`` never satisfies a condition. If two firing rules
disagree on a label, the item goes to human review instead of "last one wins".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from precedent.models import JudgeOutput, Rule
from precedent.pack import Pack

Source = Literal["judge", "rule", "conflict", "abstain"]


@dataclass(frozen=True)
class Decision:
    item: str
    label: str
    source: Source
    rules: tuple[str, ...] = field(default_factory=tuple)


def rule_fires(rule: Rule, output: JudgeOutput) -> bool:
    if output.abstained:
        return False
    for cond in rule.when:
        answer = output.predicates.get(cond.predicate)
        if answer is None or answer.value != cond.equals:
            return False
    return True


def decide(pack: Pack, output: JudgeOutput, rules: list[Rule]) -> dict[str, Decision]:
    decisions: dict[str, Decision] = {}
    for item in pack.items:
        if output.abstained:
            decisions[item.id] = Decision(item.id, pack.abstain_label, "abstain")
            continue
        verdict = output.items.get(item.id)
        base = verdict.label if verdict else pack.review_label
        fired = [r for r in rules if r.item == item.id and rule_fires(r, output)]
        labels = {r.then for r in fired}
        keys = tuple(sorted(r.key for r in fired))
        if len(labels) == 1:
            decisions[item.id] = Decision(item.id, next(iter(labels)), "rule", keys)
        elif len(labels) > 1:
            decisions[item.id] = Decision(item.id, pack.review_label, "conflict", keys)
        else:
            decisions[item.id] = Decision(item.id, base, "judge")
    return decisions
