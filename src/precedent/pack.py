"""Domain packs: rubric, predicate library, policy clauses, labelled cases.

A pack is a directory::

    pack.yaml        rubric items, labels, predicates, heuristic baseline
    policy/*.md      policy corpus; every line under a heading is a clause
    cases.jsonl      cases with golden labels and a dev/heldout split
    rules/*.yaml     example rules (proposals, not active by default)
    judgements/      recorded judge outputs (cassettes) for offline replay
"""

from __future__ import annotations

import json
import re
from importlib import resources
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, model_validator

from precedent.hashing import canonical_json, content_id, sha256_hex
from precedent.models import Case, Condition, Rule


class LabelDef(BaseModel):
    id: str
    meaning: str


class RubricItem(BaseModel):
    id: str
    question: str
    labels: list[LabelDef]
    default_label: str
    #: Labels that are only valid with a verified quote from the case.
    evidence_required: list[str] = Field(default_factory=list)

    def label_ids(self) -> list[str]:
        return [label.id for label in self.labels]


class PredicateDef(BaseModel):
    id: str
    question: str
    #: Heuristic baseline only: regexes searched in lines from this speaker.
    speaker: str | None = None
    patterns: list[str] = Field(default_factory=list)
    negation: bool = True
    note: str = ""


class HeuristicBranch(BaseModel):
    when: list[Condition] = Field(default_factory=list)
    then: str


class HeuristicSpec(BaseModel):
    """Deterministic baseline judge: a test double and benchmark arm, not the product."""

    abstain_when: list[Condition] = Field(default_factory=list)
    items: dict[str, list[HeuristicBranch]]


class Clause(BaseModel):
    id: str
    doc: str
    section: str
    text: str


class Pack(BaseModel):
    id: str
    version: str
    title: str
    description: str = ""
    abstain_label: str = "abstain"
    review_label: str = "needs_review"
    items: list[RubricItem]
    predicates: list[PredicateDef]
    heuristic: HeuristicSpec | None = None
    clauses: list[Clause] = Field(default_factory=list)
    cases: list[Case] = Field(default_factory=list)
    root: Path | None = None

    @model_validator(mode="after")
    def _consistent(self) -> Pack:
        item_ids = {i.id for i in self.items}
        pred_ids = {p.id for p in self.predicates}
        for item in self.items:
            labels = set(item.label_ids())
            if item.default_label not in labels:
                raise ValueError(f"{item.id}: default_label {item.default_label!r} not in labels")
            if self.review_label not in labels:
                raise ValueError(f"{item.id}: review label {self.review_label!r} missing")
        if self.heuristic:
            for cond in self.heuristic.abstain_when:
                if cond.predicate not in pred_ids:
                    raise ValueError(f"heuristic abstain_when: unknown predicate {cond.predicate}")
            for item_id, branches in self.heuristic.items.items():
                if item_id not in item_ids:
                    raise ValueError(f"heuristic: unknown item {item_id}")
                for b in branches:
                    if b.then not in self.labels_for(item_id):
                        raise ValueError(f"heuristic {item_id}: invalid label {b.then}")
                    for cond in b.when:
                        if cond.predicate not in pred_ids:
                            raise ValueError(f"heuristic {item_id}: unknown predicate")
        seen: set[str] = set()
        for case in self.cases:
            if case.id in seen:
                raise ValueError(f"duplicate case id {case.id}")
            seen.add(case.id)
            for item_id, label in case.golden.items():
                if item_id not in item_ids:
                    raise ValueError(f"{case.id}: golden for unknown item {item_id}")
                if label not in self.labels_for(item_id):
                    raise ValueError(f"{case.id}: invalid golden label {label!r} for {item_id}")
        return self

    # --- lookups -----------------------------------------------------------
    def item(self, item_id: str) -> RubricItem:
        for item in self.items:
            if item.id == item_id:
                return item
        raise KeyError(f"unknown item {item_id!r} in pack {self.id}")

    def predicate(self, predicate_id: str) -> PredicateDef:
        for p in self.predicates:
            if p.id == predicate_id:
                return p
        raise KeyError(f"unknown predicate {predicate_id!r} in pack {self.id}")

    def labels_for(self, item_id: str) -> list[str]:
        return [*self.item(item_id).label_ids(), self.abstain_label]

    def case(self, case_id: str) -> Case:
        for c in self.cases:
            if c.id == case_id:
                return c
        raise KeyError(f"unknown case {case_id!r} in pack {self.id}")

    def clause_ids(self) -> set[str]:
        return {c.id for c in self.clauses}

    def dataset_hash(self) -> str:
        rows = [c.model_dump(mode="json") for c in sorted(self.cases, key=lambda c: c.id)]
        return sha256_hex(canonical_json(rows))

    def definition_hash(self) -> str:
        """Identity of what the judge is asked; part of every LLM prompt hash."""
        body = {
            "items": [i.model_dump(mode="json") for i in self.items],
            "predicates": [{"id": p.id, "question": p.question} for p in self.predicates],
            "clauses": sorted(c.id for c in self.clauses),
        }
        return sha256_hex(canonical_json(body))

    def example_rules(self) -> list[Rule]:
        if self.root is None:
            return []
        rules_dir = self.root / "rules"
        if not rules_dir.is_dir():
            return []
        return [load_rule(p) for p in sorted(rules_dir.glob("*.yaml"))]

    def judgements_dir(self) -> Path | None:
        return None if self.root is None else self.root / "judgements"


# --- loading ---------------------------------------------------------------

_HEADING = re.compile(r"^#{1,6}\s+(.*)$")


def parse_policy(doc: str, markdown: str) -> list[Clause]:
    """Every non-empty line under a heading becomes a clause with a content-hash id."""
    clauses: list[Clause] = []
    section = ""
    for raw in markdown.splitlines():
        line = raw.strip()
        if not line:
            continue
        heading = _HEADING.match(line)
        if heading:
            section = heading.group(1).strip()
            continue
        text = line.lstrip("-* ").strip()
        if text:
            clauses.append(
                Clause(id=content_id(doc, section, text), doc=doc, section=section, text=text)
            )
    return clauses


def builtin_packs_root() -> Path:
    return Path(str(resources.files("precedent") / "packs"))


def builtin_packs() -> list[str]:
    root = builtin_packs_root()
    return sorted(p.name for p in root.iterdir() if (p / "pack.yaml").is_file())


def resolve_pack_path(name_or_path: str | Path) -> Path:
    path = Path(name_or_path)
    if (path / "pack.yaml").is_file():
        return path
    builtin = builtin_packs_root() / str(name_or_path)
    if (builtin / "pack.yaml").is_file():
        return builtin
    raise FileNotFoundError(
        f"no pack at {name_or_path!r}; built-in packs: {', '.join(builtin_packs())}"
    )


def load_pack(name_or_path: str | Path) -> Pack:
    root = resolve_pack_path(name_or_path)
    spec: dict[str, Any] = yaml.safe_load((root / "pack.yaml").read_text(encoding="utf-8"))
    clauses: list[Clause] = []
    policy_dir = root / "policy"
    if policy_dir.is_dir():
        for md in sorted(policy_dir.glob("*.md")):
            clauses.extend(parse_policy(md.stem, md.read_text(encoding="utf-8")))
    cases: list[Case] = []
    cases_file = root / "cases.jsonl"
    if cases_file.is_file():
        for line in cases_file.read_text(encoding="utf-8").splitlines():
            if line.strip():
                cases.append(Case.model_validate(json.loads(line)))
    return Pack.model_validate({**spec, "clauses": clauses, "cases": cases, "root": root})


def load_rule(path: Path | str) -> Rule:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return Rule.model_validate(data)


def dump_rule(rule: Rule) -> str:
    data = rule.model_dump(mode="json", exclude_defaults=False)
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
