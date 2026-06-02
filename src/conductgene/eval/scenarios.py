"""Scenario loading from data/scenarios."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field


class ScenarioGolden(BaseModel):
    threat_language: str | None = None
    escalation_offered: str | None = None
    company_disclosure: str | None = None
    recording_disclosure: str | None = None
    abstain: bool = False


class ScenarioGeneLearning(BaseModel):
    applies_to: str | None = None
    checklist_id: str = "escalation_offered"
    corrected_status: Literal["pass", "fail", "needs_review"] = "pass"
    trigger_pattern: str = "supervisor"
    rationale: str = "Supervisor-approved pattern"
    expected_improvement: str | None = None


class Scenario(BaseModel):
    id: str
    persona: str = "linear_qa_analyst"
    transcript: str
    golden: ScenarioGolden = Field(default_factory=ScenarioGolden)
    gene_learning: ScenarioGeneLearning | None = None
    tags: list[str] = Field(default_factory=list)


def load_manifest(manifest_path: Path) -> dict[str, Any]:
    return yaml.safe_load(manifest_path.read_text(encoding="utf-8"))


def load_scenario(path: Path) -> Scenario:
    data = json.loads(path.read_text(encoding="utf-8"))
    return Scenario.model_validate(data)


def load_all_scenarios(scenarios_dir: Path, suite: str = "all") -> list[Scenario]:
    manifest_path = scenarios_dir / "manifest.yaml"
    if not manifest_path.exists():
        return []

    manifest = load_manifest(manifest_path)
    case_entries = manifest.get("cases", [])
    if suite != "all":
        case_entries = [c for c in case_entries if c.get("suite") == suite or c.get("id")]

    scenarios: list[Scenario] = []
    for entry in case_entries:
        rel = entry["file"]
        path = scenarios_dir / rel
        if path.exists():
            scenarios.append(load_scenario(path))
    return scenarios


def get_demo_pair(scenarios_dir: Path) -> tuple[Scenario | None, Scenario | None]:
    all_s = load_all_scenarios(scenarios_dir)
    learn_case = next((s for s in all_s if s.id == "CASE-002"), None)
    heldout = next((s for s in all_s if s.id == "CASE-005"), None)
    return learn_case, heldout
