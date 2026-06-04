# Architecture

## One cycle

```
Transcript → Evidence → Prosecutor + Defender → Arbiter → Supervisor approval → Policy Gene → Improved re-review
```

## Components

| Module | Responsibility |
|--------|----------------|
| `agents/roles.py` | Prosecutor, Defender, Arbiter (deterministic demo mode) |
| `agents/live.py` | Live LLM hooks (v0.4+) |
| `retrieval/` | memory, BGE, Qdrant retrieval factory |
| `services/discovery.py` | Service health probes |
| `pipeline/swarm.py` | Orchestration + audit persistence |
| `evolution/genes.py` | Supervisor-approved Policy Gene store |
| `audit/store.py` | Append-only case provenance |
| `audit/gene_events.py` | Gene learn + rollback audit events |
| `eval/harness.py` | Synthetic scenario verification + held-out eval |
| `api/app.py` | REST spine + cached metrics |
| `ui/app.py` | Streamlit 5-panel demo |
| `ui/client.py` | Thin HTTP client for API-backed demos |

## Data

| Path | Content |
|------|---------|
| `data/synthetic/kb/` | Policy knowledge base |
| `data/scenarios/` | 16 golden test cases |
| `data/evolution/genes.jsonl` | Active Policy Genes |
| `data/audit/cases.jsonl` | Case audit trail |
| `data/audit/gene_events.jsonl` | Gene lifecycle audit |

## Modes

- **mock** (default): deterministic agents, in-memory retrieval — labeled "Deterministic Demo Mode" in UI
- **live** (v0.4+): LLM providers via `CONDUCTGENE_LLM_PROVIDER` — stub hooks in [`agents/live.py`](../src/conductgene/agents/live.py)

## Retrieval (v0.3+)

| Mode | Description |
|------|-------------|
| `memory` | Keyword overlap on `data/synthetic/kb` (CI default) |
| `qdrant` | BGE embeddings + Qdrant vector search |
| `qdrant_rerank` | Qdrant + BGE reranker when `ENABLE_RERANKER=true` |

Modules: [`retrieval/`](../src/conductgene/retrieval/) · [`services/discovery.py`](../src/conductgene/services/discovery.py)

See [qdrant-retrieval.md](qdrant-retrieval.md) and [ROADMAP.md](ROADMAP.md).

## API notes

- `GET /healthz/services` — probe BGE, Qdrant, optional LLM endpoints

- `GET /metrics/evolution` uses cached eval result; pass `?refresh=true` to re-run suite
- `GET /audit/export` returns case records + gene events for compliance review
- No auth on API — intentional for local hackathon demo

## Verification

```bash
./scripts/verify_all.sh
```

Runs ruff, pytest (16+ tests), eval suite (16/16), and demo path CASE-002 → CASE-005.

## Diagram

See [assets/architecture.mmd](assets/architecture.mmd). Export PNG:

```bash
./scripts/export_architecture.sh   # requires npx @mermaid-js/mermaid-cli
```
