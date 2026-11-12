from __future__ import annotations

import math
from pathlib import Path

import pytest
import yaml

from precedent.pack import Pack, builtin_packs, dump_rule, load_pack, load_rule, parse_policy
from precedent.stats import agreement, cohen_kappa, mcnemar_exact, wilson


def test_builtin_pack_is_complete(pack: Pack) -> None:
    assert "collections-conduct" in builtin_packs()
    assert len(pack.cases) == 28
    assert sum(c.split == "heldout" for c in pack.cases) == 9
    for case in pack.cases:
        assert set(case.golden) == {i.id for i in pack.items}, case.id


def test_clause_ids_are_content_hashes() -> None:
    a = parse_policy("doc", "## S\n- Rule one.\n- Rule two.\n")
    b = parse_policy("doc", "## S\n\n- Rule one.\n")
    assert a[0].id == b[0].id
    assert a[0].id != a[1].id
    assert a[0].section == "S"


def test_hashes_are_stable(pack: Pack) -> None:
    again = load_pack("collections-conduct")
    assert pack.dataset_hash() == again.dataset_hash()
    assert pack.definition_hash() == again.definition_hash()
    assert pack.case("CASE-001").hash == again.case("CASE-001").hash


def test_invalid_golden_label_is_rejected(tmp_path: Path, pack: Pack) -> None:
    src = pack.root
    assert src is not None
    spec = yaml.safe_load((src / "pack.yaml").read_text())
    (tmp_path / "pack.yaml").write_text(yaml.safe_dump(spec))
    (tmp_path / "cases.jsonl").write_text(
        '{"id": "A", "text": "Agent: hi", "golden": {"threat_language": "maybe"}}\n'
    )
    with pytest.raises(ValueError, match="invalid golden"):
        load_pack(tmp_path)


def test_unknown_pack() -> None:
    with pytest.raises(FileNotFoundError):
        load_pack("no-such-pack")


def test_rule_roundtrip(tmp_path: Path, pack: Pack) -> None:
    rule = pack.example_rules()[0]
    path = tmp_path / "r.yaml"
    path.write_text(dump_rule(rule))
    assert load_rule(path) == rule


def test_stats() -> None:
    pairs = [("a", "a"), ("a", "b"), ("b", "b"), ("b", "b")]
    assert agreement(pairs) == 0.75
    kappa = cohen_kappa(pairs)
    assert kappa is not None and math.isclose(kappa, 0.5)
    assert cohen_kappa([("a", "a")]) is None
    assert cohen_kappa([]) is None
    assert math.isnan(agreement([]))
    lo, hi = wilson(33, 36)  # the advisor's worked example: 92%, 95% CI 78–97%
    assert round(lo, 2) == 0.78 and round(hi, 2) == 0.97
    assert wilson(0, 0) == (0.0, 1.0)
    assert mcnemar_exact(0, 0) == 1.0
    assert mcnemar_exact(3, 0) == 0.25
    assert math.isclose(mcnemar_exact(2, 3), 1.0)
    assert mcnemar_exact(10, 0) < 0.01
