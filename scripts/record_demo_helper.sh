#!/usr/bin/env bash
# Helper for demo video recording — pauses between steps for screen capture
set -euo pipefail

pause() {
  echo ""
  echo ">>> $1"
  echo "    (pause 5s for recording...)"
  sleep 5
}

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

pause "Terminal demo: CASE-002 → Policy Gene → CASE-005"
export CONDUCTGENE_GENE_STORE_PATH="${ROOT}/reports/.video_demo_genes.jsonl"
rm -f "$CONDUCTGENE_GENE_STORE_PATH"
uv run conductgene demo

pause "Full verification gate (optional B-roll)"
./scripts/verify_all.sh

echo ""
echo "Done. For Streamlit recording run: uv run conductgene-ui"
echo "Guide: docs/demo-video-guide.md"
