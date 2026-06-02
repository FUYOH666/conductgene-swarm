# Architecture

## One cycle

```
Transcript → Evidence → Prosecutor + Defender → Arbiter → Supervisor approval → Policy Gene → Improved re-review
```

## Components

| Module | Responsibility |
|--------|----------------|
| `agents/roles.py` | Prosecutor, Defender, Arbiter (deterministic demo mode) |
| `agents/live.py` | Live mode stub (OpenAI-compatible gateway hooks) |
| `retrieval.py` | In-memory KB evidence ranking |
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

- **mock** (default): deterministic agents, no external LLM — labeled "Deterministic Demo Mode" in UI
- **live**: stub hooks in `agents/live.py`; install with `uv sync --extra live`

## API notes

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
