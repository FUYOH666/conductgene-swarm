#!/usr/bin/env python3
"""Probe BGE, Qdrant, and optional LLM services."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from conductgene.config import Settings
from conductgene.services.discovery import discover_services, format_service_table


def main() -> int:
    settings = Settings()
    settings.resolve_paths(ROOT)
    results = discover_services(settings)
    print(format_service_table(results))
    errors = sum(1 for r in results if r.status == "error")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
