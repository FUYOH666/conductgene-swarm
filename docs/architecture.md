# Architecture

## One cycle

```
Transcript → Evidence → Prosecutor + Defender → Arbiter → Supervisor approval → Policy Gene → Improved re-review
```

## Components

| Module | Responsibility |
|--------|----------------|
| `agents/roles.py` | Prosecutor, Defender, Arbiter (deterministic mock mode) |
| `agents/dispatch.py` | Routes mock vs live LLM per `mode` + `llm_provider` |
| `agents/live.py` | Live agent entrypoints |
| `agents/prompts.py` | Evidence-grounded LLM prompts + JSON schema hints |
| `providers/llm.py` | OpenAI-compatible client (OpenRouter, LM Studio, instruct) |
| `retrieval/` | memory, BGE, Qdrant retrieval factory |
| `services/discovery.py` | Service health probes (BGE, Qdrant, LLM providers) |
| `pipeline/swarm.py` | Orchestration + audit persistence |
| `evolution/genes.py` | Supervisor-approved Policy Gene store |
| `audit/store.py` | Append-only case provenance |
| `audit/gene_events.py` | Gene learn + rollback audit events |
| `eval/harness.py` | Synthetic scenario verification + held-out eval |
| `api/app.py` | REST spine + cached metrics |
| `ui/app.py` | Streamlit 5-panel demo + Model Jury sidebar |
| `ui/client.py` | Thin HTTP client for API-backed demos |

## Data

| Path | Content |
|------|---------|
| `data/synthetic/kb/` | Policy knowledge base (15+ docs) |
| `data/scenarios/` | 16 golden CI cases + synth suite (CASE-017/018) |
| `data/evolution/genes.jsonl` | Active Policy Genes |
| `data/audit/cases.jsonl` | Case audit trail |
| `data/audit/gene_events.jsonl` | Gene lifecycle audit |

## Modes

| `MODE` | `LLM_PROVIDER` | Agents | Use case |
|--------|----------------|--------|----------|
| `mock` | `mock` | Rule-based | CI, offline fallback |
| `mock` | any | Rule-based (warn if provider≠mock) | Misconfiguration guard |
| `live` | `lmstudio` | Local LLM | **Singapore primary offline** |
| `live` | `openrouter` | Cloud LLM | Pre-flight validation / bench |
| `live` | `instruct` | Remote gateway | Optional (TailScale) |

## Retrieval

| Mode | Description |
|------|-------------|
| `memory` | Keyword overlap on KB (CI default) |
| `qdrant` | BGE embeddings + Qdrant vector search |
| `qdrant_rerank` | Qdrant + BGE reranker when `ENABLE_RERANKER=true` |

Explicit fallback to memory when BGE/Qdrant unavailable (logged).

## API notes

- `GET /healthz/services` — probe embedding, reranker, qdrant, openrouter, lmstudio, instruct
- `GET /metrics/evolution` — cached eval; `?refresh=true` to re-run
- `GET /audit/export` — case + gene audit for compliance review
- No auth — intentional for local hackathon demo

**Streamlit Model Jury:** sidebar overrides apply in **in-process** mode (`CONDUCTGENE_UI_USE_API=false`). Docker live profile uses in-process UI for Singapore demos.

## Verification

```bash
./scripts/verify_all.sh              # offline CI gate (16/16)
./scripts/qa_matrix.sh                 # integration scorecard
./scripts/run_simulation_matrix.sh     # Singapore pre-flight (S1–S8)
```

See [singapore-demo-runbook.md](singapore-demo-runbook.md) · [qdrant-retrieval.md](qdrant-retrieval.md) · [ROADMAP.md](ROADMAP.md)

## Diagram

See [assets/architecture.mmd](assets/architecture.mmd). Export PNG:

```bash
./scripts/export_architecture.sh
```
