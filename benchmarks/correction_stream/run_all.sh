#!/usr/bin/env bash
# Run every phase against a hosted OpenAI-compatible endpoint (default OpenRouter).
# The key is read from the environment (PRECEDENT_LLM_API_KEY); nothing is printed.
# JUDGE_MODEL picks the judge; each judge writes to results/<model>/.
set -euo pipefail
cd "$(dirname "$0")/../.."
phases=("$@")
[ ${#phases[@]} -eq 0 ] && phases=(build base prompts gated draft rules stability analyze)
for phase in "${phases[@]}"; do
  echo "== $phase $(date -u +%H:%M:%S)"
  uv run python benchmarks/correction_stream/run.py "$phase"
done
