"""Deterministic baseline judge.

Regex predicates with a short negation window, plus per-item decision lists
from the pack. It exists for three reasons: offline CI, a reproducible demo,
and the "keyword rules" arm of the benchmark. It is deliberately imperfect;
its blind spots are what the human corrections in the demo are about.
"""

from __future__ import annotations

import re

from precedent.engine import rule_fires
from precedent.models import (
    Case,
    Condition,
    ItemVerdict,
    JudgeOutput,
    PredicateAnswer,
    Rule,
    Span,
)
from precedent.pack import Pack, PredicateDef

NEGATIONS = frozenset(
    {"not", "never", "no", "nobody", "won't", "wont", "don't", "dont", "cannot", "can't", "isn't"}
)
_TOKEN = re.compile(r"[a-z']+")
_SENTENCE_BREAK = re.compile(r"[.!?;\n]")


def _tokens(text: str) -> list[str]:
    return _TOKEN.findall(text.lower().replace("’", "'"))


def _negated(text: str, start: int, end: int, window: int = 5) -> bool:
    """True if the match, or one of the ``window`` tokens before it in the same
    sentence, contains a negation ("nobody is going to arrest you",
    "a supervisor will not call you back")."""
    left = text[:start]
    breaks = list(_SENTENCE_BREAK.finditer(left))
    if breaks:
        left = left[breaks[-1].end() :]
    before = _tokens(left)[-window:]
    inside = _tokens(text[start:end])
    return any(t in NEGATIONS for t in (*before, *inside))


def _speaker_lines(text: str, speaker: str | None) -> list[tuple[int, str]]:
    lines: list[tuple[int, str]] = []
    offset = 0
    for line in text.splitlines(keepends=True):
        if speaker is None or line.lstrip().lower().startswith(speaker.lower() + ":"):
            lines.append((offset, line))
        offset += len(line)
    return lines


def eval_predicate(pred: PredicateDef, text: str) -> PredicateAnswer:
    if not pred.patterns:
        return PredicateAnswer(predicate_id=pred.id, value="unknown")
    regexes = [re.compile(p, re.IGNORECASE) for p in pred.patterns]
    for offset, line in _speaker_lines(text, pred.speaker):
        for rx in regexes:
            for m in rx.finditer(line):
                if pred.negation and _negated(line, m.start(), m.end()):
                    continue
                start, end = offset + m.start(), offset + m.end()
                return PredicateAnswer(
                    predicate_id=pred.id,
                    value="yes",
                    quote=Span(start=start, end=end, text=text[start:end]),
                )
    return PredicateAnswer(predicate_id=pred.id, value="no")


class HeuristicJudge:
    def __init__(self, pack: Pack) -> None:
        if pack.heuristic is None:
            raise ValueError(f"pack {pack.id} defines no heuristic baseline")
        self.pack = pack
        self.spec = pack.heuristic

    @property
    def judge_id(self) -> str:
        return f"heuristic:{self.pack.id}@{self.pack.version}"

    def judge(self, case: Case) -> JudgeOutput:
        answers = {p.id: eval_predicate(p, case.text) for p in self.pack.predicates}
        probe = JudgeOutput(
            case_id=case.id,
            case_hash=case.hash,
            judge_id=self.judge_id,
            items={},
            predicates=answers,
        )
        if self.spec.abstain_when and _all_match(self.spec.abstain_when, probe):
            return probe.model_copy(
                update={"abstained": True, "abstain_reason": "out of domain (heuristic)"}
            )
        items: dict[str, ItemVerdict] = {}
        for item in self.pack.items:
            label, quote = item.default_label, None
            for branch in self.spec.items.get(item.id, []):
                if not branch.when or _all_match(branch.when, probe):
                    label = branch.then
                    if branch.when:
                        quote = answers[branch.when[0].predicate].quote
                    break
            items[item.id] = ItemVerdict(item_id=item.id, label=label, quote=quote)
        return probe.model_copy(update={"items": items})


def _all_match(conditions: list[Condition], output: JudgeOutput) -> bool:
    probe_rule = Rule(
        id="probe", pack="", item="", title="", rationale="", when=conditions, then=""
    )
    return rule_fires(probe_rule, output)
