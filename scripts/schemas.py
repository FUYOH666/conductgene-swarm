"""Write JSON Schemas for rule and pack YAML files (editor autocompletion, validation).

    uv run python scripts/schemas.py

CI regenerates them and fails if the committed copies drift from the models.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from precedent.models import Rule
from precedent.pack import Pack

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "src" / "precedent" / "schemas"
BASE = "https://raw.githubusercontent.com/FUYOH666/precedent/main/src/precedent/schemas"


def _write(name: str, schema: dict[str, Any], title: str) -> None:
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"{BASE}/{name}",
        "title": title,
        **{k: v for k, v in schema.items() if k != "title"},
    }
    (OUT / name).write_text(json.dumps(schema, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    print(f"{(OUT / name).relative_to(ROOT)}")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    _write("rule.schema.json", Rule.model_json_schema(), "Precedent rule")
    pack = Pack.model_json_schema()
    for key in ("clauses", "cases", "root"):
        pack["properties"].pop(key, None)
    for key in ("Clause", "Case"):
        pack.get("$defs", {}).pop(key, None)
    _write("pack.schema.json", pack, "Precedent pack (pack.yaml)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
