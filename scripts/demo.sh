#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export CONDUCTGENE_MODE=mock
export CONDUCTGENE_GENE_STORE_PATH="${ROOT}/data/evolution/demo_genes.jsonl"
rm -f "$CONDUCTGENE_GENE_STORE_PATH"
uv sync --extra dev --quiet
uv run pytest -q
uv run conductgene demo
