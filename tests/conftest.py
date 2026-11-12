from __future__ import annotations

from pathlib import Path

import pytest

from precedent.events import EventStore
from precedent.judge import judge_all
from precedent.judge.heuristic import HeuristicJudge
from precedent.models import Correction, JudgeOutput, Rule
from precedent.pack import Pack, load_pack
from precedent.registry import Registry


@pytest.fixture(scope="session")
def pack() -> Pack:
    return load_pack("collections-conduct")


@pytest.fixture(scope="session")
def outputs(pack: Pack) -> dict[str, JudgeOutput]:
    return judge_all(HeuristicJudge(pack), pack.cases)


@pytest.fixture(scope="session")
def rules(pack: Pack) -> dict[str, Rule]:
    return {r.key: r for r in pack.example_rules()}


@pytest.fixture()
def correction(pack: Pack) -> Correction:
    case = pack.case("CASE-019")
    return Correction(
        id="C-0001",
        pack=pack.id,
        case_id=case.id,
        case_hash=case.hash,
        item="escalation_offered",
        ai_label="needs_review",
        human_label="pass",
        reviewer="maria",
        error_type="policy_misinterpretation",
    )


@pytest.fixture()
def store(tmp_path: Path) -> EventStore:
    s = EventStore(tmp_path / "events.db")
    yield s  # type: ignore[misc]
    s.close()


@pytest.fixture()
def registry(store: EventStore) -> Registry:
    return Registry(store)
