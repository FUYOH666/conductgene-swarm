#!/usr/bin/env bash
# Singapore simulation matrix — offline + live scorecard
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
REPORT="${ROOT}/reports/simulation_matrix.md"
mkdir -p reports outputs/demo outputs/benchmarks

SKIP_LIVE="${SKIP_LIVE:-false}"
SKIP_OPENROUTER="${SKIP_OPENROUTER:-false}"
SKIP_DOCKER="${SKIP_DOCKER:-true}"

pass=0
fail=0
skip=0
rows=()

record() {
  local id="$1"
  local name="$2"
  local status="$3"
  local detail="${4:-}"
  case "$status" in
    PASS) pass=$((pass + 1)) ;;
    FAIL) fail=$((fail + 1)) ;;
    SKIP) skip=$((skip + 1)) ;;
  esac
  rows+=("| ${id} | ${name} | ${status} | ${detail} |")
}

echo "==> Simulation Matrix — ConductGene Swarm"
echo ""

# S1 — Offline CI
echo "==> S1 verify_all.sh"
if ./scripts/verify_all.sh > /tmp/cg_sim_s1.log 2>&1; then
  record "S1" "Offline CI gate" "PASS" "ruff + pytest + 16/16 eval"
else
  record "S1" "Offline CI gate" "FAIL" "/tmp/cg_sim_s1.log"
fi

# S2 — QA matrix
echo "==> S2 qa_matrix.sh"
if ./scripts/qa_matrix.sh > /tmp/cg_sim_s2.log 2>&1; then
  record "S2" "QA integration" "PASS" "4/4 scorecard"
else
  record "S2" "QA integration" "FAIL" "/tmp/cg_sim_s2.log"
fi

if [[ "$SKIP_LIVE" == "true" ]]; then
  for id in S3 S4 S5 S6 S7 S8; do
    record "$id" "Live stack" "SKIP" "SKIP_LIVE=true"
  done
else
  docker start qdrant >/dev/null 2>&1 || docker run -d --name qdrant -p 6333:6333 qdrant/qdrant >/dev/null 2>&1 || true

  # S3 — Discovery
  echo "==> S3 discover_services"
  if uv run python scripts/discover_services.py > /tmp/cg_sim_s3.log 2>&1; then
    record "S3" "Service preflight" "PASS" "discover exit 0"
  else
    detail=$(grep -E "embedding|qdrant|lmstudio|openrouter" /tmp/cg_sim_s3.log | head -3 | tr '\n' '; ')
    record "S3" "Service preflight" "FAIL" "${detail:-/tmp/cg_sim_s3.log}"
  fi

  # S4 — Retrieval ingest + analyze
  echo "==> S4 retrieval smoke"
  if uv run python scripts/ingest_qdrant.py --rebuild > /tmp/cg_sim_s4.log 2>&1 \
    && uv run conductgene analyze -f data/scenarios/collections/case_002_coercive_soft.json \
      > /tmp/cg_sim_s4_analyze.json 2>&1; then
    if grep -q '"score"' /tmp/cg_sim_s4_analyze.json; then
      record "S4" "Retrieval smoke" "PASS" "ingest + CASE-002 vector evidence"
    else
      record "S4" "Retrieval smoke" "FAIL" "no evidence scores"
    fi
  else
    record "S4" "Retrieval smoke" "FAIL" "/tmp/cg_sim_s4.log"
  fi

  # S5 — LM Studio live simulation
  echo "==> S5 LM Studio live simulation"
  export CONDUCTGENE_MODE=live
  export CONDUCTGENE_LLM_PROVIDER=lmstudio
  if uv run python scripts/run_live_simulation.py > /tmp/cg_sim_s5.log 2>&1; then
    if grep -q "Escalation: pass" /tmp/cg_sim_s5.log; then
      record "S5" "LM Studio live swarm" "PASS" "CASE-005 escalation pass"
    else
      record "S5" "LM Studio live swarm" "FAIL" "CASE-005 not pass"
    fi
  else
    record "S5" "LM Studio live swarm" "FAIL" "/tmp/cg_sim_s5.log"
  fi

  # S6 — LM Studio bench
  echo "==> S6 LM Studio bench"
  if uv run python scripts/bench_models.py --provider lmstudio --limit 4 \
    > /tmp/cg_sim_s6.log 2>&1; then
    record "S6" "LM Studio bench" "PASS" "outputs/benchmarks/"
  else
    record "S6" "LM Studio bench" "FAIL" "/tmp/cg_sim_s6.log"
  fi

  if [[ "$SKIP_OPENROUTER" == "true" ]]; then
    record "S7" "OpenRouter live" "SKIP" "SKIP_OPENROUTER=true"
    record "S8" "OpenRouter bench" "SKIP" "SKIP_OPENROUTER=true"
  else
    # S7 — OpenRouter live
    echo "==> S7 OpenRouter live simulation"
    export CONDUCTGENE_LLM_PROVIDER=openrouter
    if uv run python scripts/run_live_simulation.py > /tmp/cg_sim_s7.log 2>&1; then
      record "S7" "OpenRouter live" "PASS" "run_live_simulation OK"
    else
      record "S7" "OpenRouter live" "FAIL" "/tmp/cg_sim_s7.log"
    fi

    # S8 — OpenRouter bench
    echo "==> S8 OpenRouter bench"
    if uv run python scripts/bench_models.py --provider openrouter \
      --models anthropic/claude-sonnet-4 openai/gpt-4.1-mini --limit 4 \
      > /tmp/cg_sim_s8.log 2>&1; then
      record "S8" "OpenRouter bench" "PASS" "claude-sonnet-4 + gpt-4.1-mini"
    else
      record "S8" "OpenRouter bench" "FAIL" "/tmp/cg_sim_s8.log"
    fi
  fi
fi

# S9 — Streamlit manual
record "S9" "Streamlit Model Jury" "SKIP" "manual: uv run conductgene-ui"

# S10 — Docker live (optional)
if [[ "$SKIP_DOCKER" == "true" ]]; then
  record "S10" "Docker live profile" "SKIP" "SKIP_DOCKER=true"
else
  echo "==> S10 Docker live"
  if docker compose -f docker-compose.yml -f docker-compose.live.yml up -d --build \
    > /tmp/cg_sim_s10.log 2>&1; then
    sleep 8
    if curl -sf http://127.0.0.1:8090/healthz/services > /dev/null; then
      record "S10" "Docker live profile" "PASS" "/healthz/services OK"
    else
      record "S10" "Docker live profile" "FAIL" "healthz/services"
    fi
    docker compose -f docker-compose.yml -f docker-compose.live.yml down >> /tmp/cg_sim_s10.log 2>&1 || true
  else
    record "S10" "Docker live profile" "FAIL" "/tmp/cg_sim_s10.log"
  fi
fi

total=$((pass + fail + skip))
{
  echo "# Simulation Matrix"
  echo ""
  echo "Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  echo ""
  echo "| ID | Scenario | Status | Detail |"
  echo "|----|----------|--------|--------|"
  for row in "${rows[@]}"; do
    echo "$row"
  done
  echo ""
  echo "**PASS: ${pass} | FAIL: ${fail} | SKIP: ${skip} (total ${total})**"
} > "$REPORT"

echo ""
cat "$REPORT"

if [[ "$fail" -gt 0 ]]; then
  exit 1
fi
