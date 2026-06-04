# Live Simulation (roadmap)

End-to-end flow for judges and enterprise demos:

```
Transcript → policy retrieval → multi-agent review → supervisor correction
→ Policy Gene → held-out re-evaluation → metrics → audit export
```

## Today (v0.3) — retrieval only

Agents remain **deterministic mock**; retrieval can use BGE + Qdrant.

```bash
./scripts/discover_services.py
uv run python scripts/ingest_qdrant.py
CONDUCTGENE_RETRIEVAL_MODE=qdrant_rerank ./scripts/demo.sh
```

## Tomorrow checklist (MacBook + services)

See [ROADMAP.md](ROADMAP.md) v0.3.0 «Tomorrow» section.

## Future (v0.4–v0.5)

| Step | Command (planned) |
|------|-------------------|
| Service discovery | `./scripts/discover_services.py` |
| Ingest KB | `uv run python scripts/ingest_qdrant.py` |
| Live LLM swarm | `CONDUCTGENE_LLM_PROVIDER=openrouter uv run python scripts/run_live_simulation.py` |
| Model benchmark | `uv run python scripts/bench_models.py` |
| Judge report | `outputs/demo/live_simulation_report.md` |

## Judge demo path (target v0.5)

1. Start Services-BGE + Qdrant
2. Add OpenRouter key to `.env` (optional for LLM)
3. `discover_services.py` — all green or explicit degraded status
4. `ingest_qdrant.py`
5. `run_live_simulation.py` — CASE-002 → gene → CASE-005
6. Open benchmark summary + audit export

Until v0.5 ships, use `./scripts/demo.sh` and Streamlit UI with mock agents.
