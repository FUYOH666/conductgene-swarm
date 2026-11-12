from __future__ import annotations

from pathlib import Path

import pytest

from precedent.cli import main
from precedent.pack import builtin_packs_root

RULES = builtin_packs_root() / "collections-conduct" / "rules"


def test_demo_tells_the_whole_story(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["demo", "--out", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "BLOCKED" in out and "PASSED" in out and "four-eyes" in out
    assert (tmp_path / "reports" / "escalation-callback@1.md").is_file()
    assert main(["audit", "verify", "--db", str(tmp_path / "demo.db")]) == 0


def test_cli_lifecycle(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    db = str(tmp_path / "p.db")
    pack = ["--pack", "collections-conduct"]
    assert main(["packs"]) == 0
    assert main(["judge", *pack, "--errors"]) == 0
    assert "CASE-019" in capsys.readouterr().out

    assert (
        main(
            [
                "correct", "--db", db, *pack, "--case", "CASE-019",
                "--item", "escalation_offered", "--label", "pass",
                "--reviewer", "maria", "--error-type", "policy_misinterpretation",
                "--id", "C-0001",
            ]
        )
        == 0
    )  # fmt: skip
    assert (
        main(
            ["propose", str(RULES / "escalation-callback.v1.yaml"), "--db", db, "--actor", "maria"]
        )
        == 0
    )
    report = tmp_path / "gate.md"
    assert main(["gate", "escalation-callback@1", "--db", db, *pack, "--report", str(report)]) == 1
    assert "BLOCKED" in report.read_text()

    assert (
        main(
            ["propose", str(RULES / "escalation-callback.v2.yaml"), "--db", db, "--actor", "maria"]
        )
        == 0
    )
    assert main(["gate", "escalation-callback@2", "--db", db, *pack]) == 0
    assert main(["approve", "escalation-callback@2", "--db", db, *pack, "--actor", "maria"]) == 2
    assert main(["approve", "escalation-callback@2", "--db", db, *pack, "--actor", "alex"]) == 0
    assert main(["rules", "--db", db]) == 0
    assert main(["eval", *pack, "--db", db]) == 0
    assert (
        main(
            ["revert", "escalation-callback@2", "--db", db, "--actor", "alex", "--reason", "drill"]
        )
        == 0
    )
    assert main(["audit", "log", "--db", db]) == 0
    assert main(["audit", "verify", "--db", db]) == 0
    out = capsys.readouterr().out
    assert "chain intact" in out


def test_cli_errors(tmp_path: Path) -> None:
    db = str(tmp_path / "p.db")
    assert main(["gate", "nope@1", "--db", db, "--pack", "collections-conduct"]) == 2
    assert main(["judge", "--pack", "no-such-pack"]) == 2
    assert (
        main(
            [
                "correct", "--db", db, "--pack", "collections-conduct", "--case", "CASE-001",
                "--item", "escalation_offered", "--label", "maybe",
                "--reviewer", "maria", "--error-type", "misread",
            ]
        )
        == 2
    )  # fmt: skip


def test_demo_exports_a_terminal_svg(tmp_path: Path) -> None:
    svg = tmp_path / "demo.svg"
    assert main(["demo", "--out", str(tmp_path / "d"), "--svg", str(svg)]) == 0
    body = svg.read_text()
    assert body.startswith("<svg") and "BLOCKED" in body and "PASSED" in body
