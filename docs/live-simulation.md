# Live Simulation

End-to-end flow for judges and enterprise demos:

```
Transcript → policy retrieval → multi-agent review → supervisor correction
→ Policy Gene → held-out re-evaluation → metrics → audit export
```

## Quick start (v0.5)

```bash
cp .env.example .env
# Set CONDUCTGENE_OPENROUTER_API_KEY for cloud LLM (optional for retrieval-only)

uv sync --extra dev --extra retrieval --extra live
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant

uv run python scripts/discover_services.py
uv run python scripts/synth_data.py
uv run python scripts/ingest_qdrant.py --rebuild

# Retrieval + mock agents
CONDUCTGENE_RETRIEVAL_MODE=qdrant_rerank CONDUCTGENE_ENABLE_RERANKER=true \
  uv run python scripts/run_live_simulation.py

# Full live LLM (OpenRouter)
CONDUCTGENE_MODE=live CONDUCTGENE_LLM_PROVIDER=openrouter \
  uv run python scripts/run_live_simulation.py

# LM Studio (local :1234)
CONDUCTGENE_MODE=live CONDUCTGENE_LLM_PROVIDER=lmstudio \
  CONDUCTGENE_LMSTUDIO_MODEL=<your-loaded-model> \
  uv run conductgene analyze --file data/scenarios/collections/case_002_coercive_soft.json

# Model benchmark
uv run python scripts/bench_models.py --provider openrouter --limit 4
```

## Outputs

| Artifact | Path |
|----------|------|
| Judge report | `outputs/demo/live_simulation_report.md` |
| Audit export | `reports/audit_export.json` |
| Benchmarks | `outputs/benchmarks/bench_*.json` |

## Judge demo path

1. Start Services-BGE + Qdrant (+ LM Studio or OpenRouter key)
2. `discover_services.py` — embedding/reranker/qdrant green (LLM optional)
3. `ingest_qdrant.py --rebuild`
4. `run_live_simulation.py` — CASE-002 → gene → CASE-005
5. Open benchmark summary + Streamlit Model Jury panel (`uv run conductgene-ui`)

CI regression remains offline: `./scripts/verify_all.sh` (16/16 mock).
