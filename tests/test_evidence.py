from __future__ import annotations

import json
from pathlib import Path

import pytest

from precedent.cli import main
from precedent.evidence import FORMAT, build_evidence, render_html
from precedent.events import EventStore
from precedent.hashing import canonical_json, sha256_hex
from precedent.judge import judge_all
from precedent.judge.heuristic import HeuristicJudge
from precedent.pack import load_pack
from precedent.registry import RegistryError


@pytest.fixture()
def demo_db(tmp_path: Path) -> Path:
    assert main(["demo", "--out", str(tmp_path)]) == 0
    return tmp_path / "demo.db"


def test_evidence_pack_for_a_blocked_and_an_approved_rule(demo_db: Path) -> None:
    pack = load_pack("collections-conduct")
    outputs = judge_all(HeuristicJudge(pack), pack.cases)
    with EventStore(demo_db) as store:
        blocked = build_evidence(pack, store, "escalation-callback@1", outputs)
        approved = build_evidence(pack, store, "escalation-callback@2", outputs, anchor_receipt="r")
    assert blocked["format"] == FORMAT
    assert blocked["summary"]["gate_decision"] == "BLOCKED"
    assert {f["case_id"] for f in blocked["testing"]["flips"] if f["kind"] == "broken"} == {
        "CASE-005", "CASE-012", "CASE-023",
    }  # fmt: skip
    assert blocked["signoffs"]["segregation"]["author_is_not_gate_runner"] is True
    assert "unauthenticated" in blocked["signoffs"]["identity"]
    assert approved["signoffs"]["approver"] == "alex"
    assert approved["signoffs"]["approval_rationale"]
    assert approved["why"]["policy_clauses"], "v2 cites the escalation policy"
    assert approved["change"]["previous_version"] == "escalation-callback@1"
    assert "supervisor_callback_offered" in approved["change"]["diff"]
    assert approved["integrity"]["chain_ok"] and approved["integrity"]["anchor_receipt"] == "r"
    # the pack carries its own hash over everything else
    body = {k: v for k, v in approved.items() if k != "evidence_hash"}
    assert approved["evidence_hash"] == sha256_hex(canonical_json(body))
    html = render_html(approved, pack)
    assert html.startswith("<!doctype html>") and "Sign-offs" in html and "PASSED" in html


def test_evidence_needs_a_gated_rule(demo_db: Path) -> None:
    pack = load_pack("collections-conduct")
    with EventStore(demo_db) as store, pytest.raises(RegistryError):
        build_evidence(pack, store, "nope@1", {})


def test_cli_evidence_and_population_export(demo_db: Path, tmp_path: Path) -> None:
    out = tmp_path / "ev"
    db = str(demo_db)
    pack = ["--pack", "collections-conduct"]
    assert main(["evidence", "escalation-callback@2", "--db", db, *pack, "--out", str(out)]) == 0
    assert (out / "escalation-callback@2.html").is_file()
    export = tmp_path / "population.jsonl"
    assert main(["audit", "export", "--db", db, "--out", str(export)]) == 0
    lines = export.read_text().splitlines()
    trailer = json.loads(lines[-1])["trailer"]
    assert trailer["chain_ok"] and trailer["population"] == len(lines) - 1
