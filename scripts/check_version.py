"""Fail unless the release tag, pyproject.toml and CITATION.cff name the same version."""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(tag: str) -> int:
    want = tag.removeprefix("v")
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    match = re.search(r"^version:\s*\"?([^\"\n]+)\"?", (ROOT / "CITATION.cff").read_text(), re.M)
    citation = match.group(1).strip() if match else ""
    found = {"tag": want, "pyproject.toml": pyproject, "CITATION.cff": citation}
    if len(set(found.values())) != 1:
        print(f"version mismatch: {found}", file=sys.stderr)
        return 1
    print(f"version {want} consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
