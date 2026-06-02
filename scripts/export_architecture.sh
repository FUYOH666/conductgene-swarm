#!/usr/bin/env bash
# Export architecture diagram to PNG (requires mermaid-cli)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${ROOT}/docs/assets/architecture.png"
SRC="${ROOT}/docs/assets/architecture.mmd"

if ! command -v npx >/dev/null 2>&1; then
  echo "npx not found — install Node.js or open architecture.mmd in https://mermaid.live"
  exit 1
fi

npx --yes @mermaid-js/mermaid-cli -i "$SRC" -o "$OUT"
echo "Wrote $OUT"
