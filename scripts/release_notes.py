"""Print release notes: the CHANGELOG section for a tag, plus the evidence-log anchor.

The sample evidence packs in docs/evidence/ come from a committed event log.
Writing its head hash into the release notes anchors that log outside itself:
`precedent audit verify --db docs/evidence/demo/demo.db --anchor <head>`.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from precedent.events import EventStore

ROOT = Path(__file__).resolve().parents[1]


def main(tag: str) -> int:
    version = tag.removeprefix("v")
    text = (ROOT / "CHANGELOG.md").read_text()
    match = re.search(rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|\Z)", text, re.M | re.S)
    if not match:
        print(f"no CHANGELOG section for {version}", file=sys.stderr)
        return 1
    print(match.group(1).strip())
    db = ROOT / "docs" / "evidence" / "demo" / "demo.db"
    if db.exists():
        with EventStore(db) as store:
            result = store.verify()
        print(
            "\n### Evidence log anchor\n\n"
            f"The sample evidence packs in `docs/evidence/` were cut from an event log of "
            f"{result.count} events whose head is:\n\n```\n{result.head}\n```\n\n"
            "Check it with `precedent audit verify --db docs/evidence/demo/demo.db "
            f"--anchor {result.head}`."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
