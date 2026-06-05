#!/usr/bin/env bash
# Capture logo + Streamlit screenshots (+ optional WebM) for UCWS portal
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
OUT="${ROOT}/docs/submission"
PROFILE="live"
WITH_VIDEO=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-video) WITH_VIDEO=true; shift ;;
    --profile) PROFILE="${2:?}"; shift 2 ;;
    --profile=*) PROFILE="${1#*=}"; shift ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

mkdir -p "$OUT" reports

echo "==> Sync extras (ui, retrieval, live, submission)"
uv sync --extra dev --extra ui --extra retrieval --extra live --extra submission

echo "==> Ensure portal logo"
uv run python scripts/generate_logo.py

echo "==> Install Playwright Chromium (first run only)"
uv run playwright install chromium

echo "==> Capture Streamlit screenshots (profile=${PROFILE})"
uv run python scripts/capture_submission_assets.py --profile "${PROFILE}"

if [[ "${WITH_VIDEO}" == "true" ]]; then
  echo "==> Record demo video (WebM, profile=${PROFILE})"
  uv run python scripts/record_submission_video.py --profile "${PROFILE}"
fi

echo ""
echo "Done. Upload from docs/submission/:"
ls -lh "${OUT}"/logo-512.png "${OUT}"/screenshot-*.png 2>/dev/null || true
[[ -f "${OUT}/conductgene-demo.webm" ]] && ls -lh "${OUT}/conductgene-demo.webm"
echo ""
echo "Next: upload conductgene-demo.webm → docs/submission/youtube-upload.md"
