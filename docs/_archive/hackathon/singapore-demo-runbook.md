# Singapore Demo Runbook — UCWS 2026

**Primary path:** LM Studio (offline) + BGE + Qdrant + `qdrant_rerank`.  
**Backup:** deterministic mock (no external services).

## Pre-demo (30 min before)

```bash
cd conductgene-swarm
uv sync --extra dev --extra retrieval --extra live --extra ui

# Services
~/development/Services-BGE/scripts/service.sh start   # or status
docker start qdrant || docker run -d --name qdrant -p 6333:6333 qdrant/qdrant
# LM Studio: load model, enable Local Server :1234

cp .env.example .env   # if fresh — set LMSTUDIO_MODEL from discovery
uv run python scripts/discover_services.py
uv run python scripts/ingest_qdrant.py --rebuild
```

Expected discovery: `embedding`, `reranker`, `qdrant`, `lmstudio` = **ok**.

## Environment (Singapore booth)

```bash
CONDUCTGENE_MODE=live
CONDUCTGENE_LLM_PROVIDER=lmstudio
CONDUCTGENE_LMSTUDIO_MODEL=<your-loaded-model>
CONDUCTGENE_RETRIEVAL_MODE=qdrant_rerank
CONDUCTGENE_ENABLE_RERANKER=true
CONDUCTGENE_UI_USE_API=false
```

## 90-second judge script

| Step | Action | Talking point |
|------|--------|---------------|
| 1 | Show `discover_services` table | "Live stack: BGE retrieval + local LLM, no cloud dependency" |
| 2 | `uv run conductgene-ui` → Model Jury sidebar | Provider=lmstudio, Mode=live, Retrieval=qdrant_rerank |
| 3 | Load **CASE-002** → Run analyze | Multi-agent swarm with evidence citations |
| 4 | Supervisor tab → approve Policy Gene | Human-in-the-loop institutional memory |
| 5 | Load **CASE-005** → Run analyze | Held-out: gene fixes `escalation_offered` |
| 6 | `conductgene audit export` or API `/audit/export` | Regulator-ready provenance |

## CLI equivalent (if UI fails)

```bash
CONDUCTGENE_MODE=live CONDUCTGENE_LLM_PROVIDER=lmstudio \
  uv run python scripts/run_live_simulation.py
```

Success: `Escalation: pass` on CASE-005.

## Fallback (30 seconds)

```bash
CONDUCTGENE_MODE=mock CONDUCTGENE_RETRIEVAL_MODE=memory ./scripts/demo.sh
```

Still shows CASE-002 → gene → CASE-005 with 16/16 eval story.

## Pre-flight scorecard

```bash
./scripts/run_simulation_matrix.sh
# or offline only:
SKIP_LIVE=true ./scripts/run_simulation_matrix.sh
```

Report: `reports/simulation_matrix.md`

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Qdrant connection refused | `docker start qdrant` |
| LM Studio JSON parse fail | Retry; check model supports chat; reduce temperature |
| Retrieval fallback warning | Re-run `ingest_qdrant.py --rebuild` |
| UI shows mock despite live | Set `CONDUCTGENE_UI_USE_API=false` |

## OpenRouter (optional, not for booth)

Use for pre-flight validation only when online:

```bash
CONDUCTGENE_MODE=live CONDUCTGENE_LLM_PROVIDER=openrouter \
  uv run python scripts/bench_models.py --provider openrouter --limit 4
```
