"""Check the pre-registration record: chain, document and pack hashes, and that specs regenerate."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from precedent.events import EventStore
from precedent.hashing import sha256_hex

HERE = Path(__file__).resolve().parent


def main() -> int:
    with EventStore(HERE / "prereg.db") as store:
        chain_ok = store.verify().ok
        record = store.events()[0].payload
    pack = "".join(
        p.read_text() for p in sorted((HERE / "pack").rglob("*")) if p.is_file() and p.name != "cases.jsonl"
    )
    sys.path.insert(0, str(HERE))
    import spec

    regen = "".join(json.dumps(r) + "\n" for r in spec.build())
    checks = {
        "event log chain intact": chain_ok,
        "PREREGISTRATION.md matches its recorded hash": sha256_hex((HERE / "PREREGISTRATION.md").read_text()) == record["prereg_sha256"],
        "frozen pack (policy + pack.yaml) matches its recorded hash": sha256_hex(pack) == record["pack_sha256"],
        "specs.jsonl regenerates byte for byte from spec.py": regen == (HERE / "specs.jsonl").read_text(),
    }
    for name, ok in checks.items():
        print(("✓ " if ok else "✗ ") + name)
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
