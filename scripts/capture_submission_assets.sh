#!/usr/bin/env bash
# Capture logo check + Streamlit screenshots for UCWS portal
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
OUT="${ROOT}/docs/submission"
mkdir -p "$OUT" reports

echo "==> Sync submission extras (playwright)"
uv sync --extra dev --extra ui --extra submission

if [[ ! -f "${OUT}/logo-512.png" ]]; then
  echo "Missing ${OUT}/logo-512.png — generate or copy manually"
  exit 1
fi

echo "==> Install Playwright Chromium (first run only)"
uv run playwright install chromium

echo "==> Capture Streamlit screenshots"
uv run python scripts/capture_submission_assets.py

if [[ "${1:-}" == "--with-video" ]]; then
  echo "==> Record demo video (WebM)"
  uv run python scripts/record_submission_video.py
fi

echo ""
echo "Done. Upload from docs/submission/:"
ls -lh "${OUT}"/logo-512.png "${OUT}"/screenshot-*.png 2>/dev/null || true
echo ""
echo "Next: record demo video → docs/submission/youtube-upload.md"
