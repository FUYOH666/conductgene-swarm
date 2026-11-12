from __future__ import annotations

import runpy
from pathlib import Path

import pytest

EXAMPLES = sorted((Path(__file__).resolve().parents[1] / "examples").glob("*.py"))


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.name)
def test_example_runs(path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runpy.run_path(str(path), run_name="__main__")
    assert capsys.readouterr().out.strip()


def test_first_example_shows_the_story(capsys: pytest.CaptureFixture[str]) -> None:
    runpy.run_path(str(EXAMPLES[0]), run_name="__main__")
    out = capsys.readouterr().out
    assert "mentions_repayment" in out and "BLOCKED" in out and "PASSED" in out
