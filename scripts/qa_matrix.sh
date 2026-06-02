#!/usr/bin/env bash
# Full QA matrix — component integration + scorecard
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
REPORT="${ROOT}/reports/qa_scorecard.md"
mkdir -p reports

pass=0
fail=0
rows=()

record() {
  local name="$1"
  local status="$2"
  local detail="${3:-}"
  if [[ "$status" == "PASS" ]]; then
    pass=$((pass + 1))
  else
    fail=$((fail + 1))
  fi
  rows+=("| ${name} | ${status} | ${detail} |")
}

echo "==> QA Matrix for ConductGene Swarm"
echo ""

echo "==> 1/4 verify_all.sh"
if ./scripts/verify_all.sh > /tmp/cg_verify.log 2>&1; then
  record "verify_all.sh" "PASS" "ruff + pytest + eval + demo"
else
  record "verify_all.sh" "FAIL" "see /tmp/cg_verify.log"
fi

echo "==> 2/4 conductgene demo (held-out eval line)"
export CONDUCTGENE_GENE_STORE_PATH="${ROOT}/reports/.qa_demo_genes.jsonl"
rm -f "$CONDUCTGENE_GENE_STORE_PATH"
uv run conductgene demo > /tmp/cg_demo.log 2>&1 || true
if grep -q "held-out eval" /tmp/cg_demo.log && grep -q "Escalation: pass" /tmp/cg_demo.log; then
  record "conductgene demo" "PASS" "CASE-002 → gene → CASE-005"
else
  record "conductgene demo" "FAIL" "see /tmp/cg_demo.log"
fi

echo "==> 3/4 API endpoint smoke"
export CONDUCTGENE_MODE=mock
export CONDUCTGENE_GENE_STORE_PATH="${ROOT}/reports/.qa_genes.jsonl"
export CONDUCTGENE_AUDIT_STORE_PATH="${ROOT}/reports/.qa_audit.jsonl"
export CONDUCTGENE_GENE_AUDIT_STORE_PATH="${ROOT}/reports/.qa_gene_events.jsonl"
rm -f "$CONDUCTGENE_GENE_STORE_PATH" "$CONDUCTGENE_AUDIT_STORE_PATH" "$CONDUCTGENE_GENE_AUDIT_STORE_PATH"

uv run conductgene-serve > /tmp/cg_api.log 2>&1 &
API_PID=$!

for i in $(seq 1 30); do
  if curl -sf http://127.0.0.1:8090/healthz > /dev/null 2>&1; then
    break
  fi
  sleep 1
done

api_ok=true
for path in /healthz /readyz /genes; do
  if ! curl -sf "http://127.0.0.1:8090${path}" > /dev/null; then
    api_ok=false
    break
  fi
done

if $api_ok; then
  curl -sf --max-time 120 "http://127.0.0.1:8090/metrics/evolution" > /dev/null || api_ok=false
fi
if $api_ok; then
  curl -sf "http://127.0.0.1:8090/audit/export" > /dev/null || api_ok=false
fi

ANALYZE=$(curl -sf -X POST http://127.0.0.1:8090/swarm/analyze \
  -H 'Content-Type: application/json' \
  -d '{"transcript":"Agent: ABC Collections. repayment supervisor path.","case_id":"QA-MATRIX"}')
REQ_ID=$(echo "$ANALYZE" | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['request_id'])")
curl -sf -X POST http://127.0.0.1:8090/genes/learn \
  -H 'Content-Type: application/json' \
  -d "{\"request_id\":\"${REQ_ID}\",\"checklist_id\":\"escalation_offered\",\"corrected_status\":\"pass\",\"rationale\":\"qa\",\"trigger_pattern\":\"repayment\",\"supervisor_id\":\"qa\",\"approved\":true}" > /dev/null
curl -sf -X POST http://127.0.0.1:8090/eval/run -H 'Content-Type: application/json' -d '{"suite":"all"}' > /dev/null

kill "$API_PID" 2>/dev/null || true
wait "$API_PID" 2>/dev/null || true

if $api_ok; then
  record "API smoke (9 routes)" "PASS" "healthz through eval/run"
else
  record "API smoke (9 routes)" "FAIL" "see /tmp/cg_api.log"
fi

echo "==> 4/4 CLI audit export"
OUT="${ROOT}/reports/.qa_audit_export.json"
if uv run conductgene audit export --out "$OUT" > /dev/null 2>&1; then
  record "CLI audit export" "PASS" "$OUT"
else
  record "CLI audit export" "FAIL" ""
fi

total=$((pass + fail))
score=$((pass * 100 / total))

{
  echo "# QA Scorecard"
  echo ""
  echo "Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  echo ""
  echo "| Check | Status | Detail |"
  echo "|-------|--------|--------|"
  for row in "${rows[@]}"; do
    echo "$row"
  done
  echo ""
  echo "**Score: ${pass}/${total} (${score}%)**"
} > "$REPORT"

echo ""
cat "$REPORT"

if [[ "$fail" -gt 0 ]]; then
  exit 1
fi
