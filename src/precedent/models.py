"""Core data model.

Vocabulary:

- A **pack** defines a domain: rubric items, the labels each item can take,
  a library of yes/no *predicates* about a case, and a policy corpus.
- A **judge** reads a case and returns a label per item plus an answer per
  predicate. Every positive answer must carry a quote that exists verbatim in
  the case text.
- A **correction** records that a human disagreed with the judge on one item.
- A **rule** is the reviewable change a correction turns into:
  ``when <predicates> then <item> = <label>``. Rules are applied by code on top
  of the judge's predicate answers, so a rule's effect is deterministic and
  auditable.
- The **gate** decides whether a rule may become active.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from precedent.hashing import canonical_json, sha256_hex

TriState = Literal["yes", "no", "unknown"]
ErrorType = Literal[
    "policy_misinterpretation",
    "rubric_ambiguity",
    "missing_context",
    "misread",
    "judge_noise",
]
#: Only these error types can justify a rule; the others become test cases.
RULE_WORTHY_ERRORS: frozenset[str] = frozenset({"policy_misinterpretation", "rubric_ambiguity"})


class Span(BaseModel):
    """A verified quote: ``text == case.text[start:end]``."""

    start: int
    end: int
    text: str


class Case(BaseModel):
    id: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    golden: dict[str, str] = Field(default_factory=dict)
    split: Literal["dev", "heldout"] = "dev"
    note: str = ""

    @property
    def hash(self) -> str:
        return sha256_hex(canonical_json({"id": self.id, "text": self.text, "meta": self.metadata}))


class ItemVerdict(BaseModel):
    item_id: str
    label: str
    quote: Span | None = None
    clause_ids: list[str] = Field(default_factory=list)
    rationale: str = ""


class PredicateAnswer(BaseModel):
    predicate_id: str
    value: TriState
    quote: Span | None = None


class JudgeOutput(BaseModel):
    case_id: str
    case_hash: str
    judge_id: str
    items: dict[str, ItemVerdict]
    predicates: dict[str, PredicateAnswer]
    abstained: bool = False
    abstain_reason: str | None = None
    notes: list[str] = Field(default_factory=list)
    #: Latency, token usage and similar run facts; never case content.
    meta: dict[str, Any] = Field(default_factory=dict)


class Condition(BaseModel):
    predicate: str
    equals: Literal["yes", "no"] = "yes"


class Rule(BaseModel):
    """A reviewable change to how one rubric item is decided."""

    id: str
    version: int = 1
    pack: str
    item: str
    title: str
    rationale: str
    when: list[Condition] = Field(min_length=1)
    then: str
    clause_refs: list[str] = Field(default_factory=list)
    source_corrections: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    counter_examples: list[str] = Field(default_factory=list)
    author: str = ""

    @field_validator("id")
    @classmethod
    def _id_has_no_at(cls, v: str) -> str:
        if "@" in v or not v.strip():
            raise ValueError("rule id must be non-empty and must not contain '@'")
        return v

    @property
    def key(self) -> str:
        return f"{self.id}@{self.version}"

    def content_hash(self) -> str:
        return sha256_hex(canonical_json(self.model_dump(mode="json")))


class Correction(BaseModel):
    """A reviewer disagreed with the judge on one item of one case.

    Only ids, hashes and labels are stored; the case text stays out of the log.
    """

    id: str
    pack: str
    case_id: str
    case_hash: str
    item: str
    ai_label: str
    human_label: str
    reviewer: str
    error_type: ErrorType
    note: str = ""


class GateCheck(BaseModel):
    name: str
    passed: bool
    blocking: bool = True
    detail: str = ""


class Flip(BaseModel):
    case_id: str
    item: str
    before: str
    after: str
    golden: str | None
    kind: Literal["fixed", "broken", "changed", "unlabeled"]
    split: str = "dev"


class ItemMetrics(BaseModel):
    item: str
    n: int
    agreement_before: float
    agreement_after: float
    kappa_before: float | None
    kappa_after: float | None


class Tally(BaseModel):
    """Before/after comparison against the labels over a set of verdicts."""

    n: int
    right_before: int
    right_after: int
    fixes: int
    breaks: int
    cases_fixed: int
    cases_broken: int
    mcnemar_p: float
    after_ci: tuple[float, float]


class GateReport(BaseModel):
    rule_key: str
    rule_hash: str
    pack: str
    judge_id: str
    dataset_hash: str
    ruleset_before: str
    ruleset_after: str
    decision: Literal["PASSED", "BLOCKED"]
    checks: list[GateCheck]
    flips: list[Flip]
    metrics: list[ItemMetrics]
    labelled: Tally | None = None
    heldout: Tally | None = None
    fires_on: int = 0

    @property
    def blocking_failures(self) -> list[GateCheck]:
        return [c for c in self.checks if c.blocking and not c.passed]

    def content_hash(self) -> str:
        return sha256_hex(canonical_json(self.model_dump(mode="json")))


def ruleset_hash(rules: list[Rule]) -> str:
    """Identity of an active rule set; a gate result is only valid against it."""
    return sha256_hex(canonical_json(sorted(r.content_hash() for r in rules)))
