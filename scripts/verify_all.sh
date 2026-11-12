#!/usr/bin/env bash
# Offline verification gate: everything CI runs, nothing that needs a network or a model.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> Sync"
uv sync --extra dev

echo "==> Lint"
uv run ruff check src tests scripts examples
uv run ruff format --check src tests scripts examples

echo "==> Types (mypy --strict)"
uv run mypy

echo "==> Tests (coverage gate in pyproject)"
uv run pytest -q --cov --cov-report=term

echo "==> Demo: the v1 rule must be BLOCKED, the narrow rule PASSED, the log intact"
out="$(mktemp -d)"
uv run precedent demo --out "$out" > "$out/demo.txt"
uv run precedent audit verify --db "$out/demo.db"
echo "==> All checks passed"
