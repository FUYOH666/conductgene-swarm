#!/usr/bin/env bash
# Export pitch deck markdown to PDF (requires pandoc)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${ROOT}/docs/pitch-deck.md"
OUT="${ROOT}/docs/pitch-deck.pdf"
HTML="${ROOT}/docs/pitch-deck.html"

if ! command -v pandoc >/dev/null 2>&1; then
  echo "Install pandoc: brew install pandoc"
  echo "Or copy docs/pitch-deck.md into Google Slides manually."
  exit 1
fi

if pandoc "$SRC" -o "$OUT" --pdf-engine=pdflatex 2>/dev/null; then
  echo "Wrote $OUT"
elif pandoc "$SRC" -o "$HTML" --standalone; then
  echo "Wrote $HTML (open in browser → Print to PDF)"
else
  echo "Export failed — use docs/pitch-deck.md in Google Slides"
  exit 1
fi
