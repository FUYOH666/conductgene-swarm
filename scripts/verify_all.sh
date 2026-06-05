#!/usr/bin/env bash
# Full virtual verification for ConductGene Swarm
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export CONDUCTGENE_MODE=mock
export CONDUCTGENE_LLM_PROVIDER=mock
export CONDUCTGENE_RETRIEVAL_MODE=memory
export CONDUCTGENE_EMBEDDING_BASE_URL=
export CONDUCTGENE_RERANKER_BASE_URL=
export CONDUCTGENE_QDRANT_URL=
export CONDUCTGENE_ENABLE_RERANKER=false
export CONDUCTGENE_GENE_STORE_PATH="${ROOT}/reports/.verify_genes.jsonl"
export CONDUCTGENE_AUDIT_STORE_PATH="${ROOT}/reports/.verify_audit.jsonl"
export CONDUCTGENE_GENE_AUDIT_STORE_PATH="${ROOT}/reports/.verify_gene_events.jsonl"

rm -f "$CONDUCTGENE_GENE_STORE_PATH" "$CONDUCTGENE_AUDIT_STORE_PATH" "$CONDUCTGENE_GENE_AUDIT_STORE_PATH"
mkdir -p reports

echo "==> Sync dependencies"
uv sync --extra dev --extra ui --extra retrieval --extra live

echo ""
echo "==> Ruff"
uv run ruff check src tests

echo ""
echo "==> Pytest"
uv run pytest -q

echo ""
echo "==> Eval suite"
uv run conductgene eval --suite all --out reports/eval_latest.json

echo ""
echo "==> Demo path (CASE-002 → gene → CASE-005)"
uv run conductgene demo

echo ""
echo "==> Verification complete — see reports/eval_latest.json"
