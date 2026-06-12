# ConductGene Swarm

[![CI](https://github.com/FUYOH666/conductgene-swarm/actions/workflows/ci.yml/badge.svg)](https://github.com/FUYOH666/conductgene-swarm/actions/workflows/ci.yml)
[![Docker Smoke](https://github.com/FUYOH666/conductgene-swarm/actions/workflows/docker-smoke.yml/badge.svg)](https://github.com/FUYOH666/conductgene-swarm/actions/workflows/docker-smoke.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/FUYOH666/conductgene-swarm)](https://github.com/FUYOH666/conductgene-swarm/releases)

**Human-approved AI conduct QA that remembers supervisor corrections safely.**

Multi-agent conduct QA for regulated industries (collections, debt servicing, insurance). Prosecutor, Defender, and Arbiter agents review call transcripts with evidence-grounded citations and an explicit abstain path. When a supervisor corrects a verdict, the system stores a **supervisor-approved Policy Gene** — auditable, rollbackable institutional memory that improves future reviews.

Originally built for the UCWS Singapore 2026 hackathon, now maintained as a standalone open-source project.

<p align="center">
  <a href="docs/assets/architecture.png">
    <img src="docs/assets/architecture.png" alt="ConductGene Swarm architecture" width="720"/>
  </a>
</p>

## Why

| Problem | Solution |
|---------|----------|
| QA teams repeat the same corrections | Policy Genes preserve approved patterns |
| LLMs hallucinate policy | Evidence-grounded citations + abstain |
| Regulators need accountability | Supervisor approval, audit trail, rollback, per-run traces |

Four design ideas carry the system, each transferable to other agent stacks:

1. **Adversarial review instead of a single judge** — disagreement between Prosecutor and Defender surfaces weak evidence before it becomes a wrong verdict.
2. **No citation, no verdict** — every finding cites a specific policy passage, or the system abstains to a human.
3. **Institutional memory with human sign-off** — corrections become small, auditable rules that only take effect after supervisor approval and can be rolled back at any time.
4. **Determinism as the baseline** — the whole pipeline runs offline with rule-based agents in CI; live LLMs are an opt-in layer, so behavior changes are measurable.

## Quick start

```bash
git clone https://github.com/FUYOH666/conductgene-swarm.git
cd conductgene-swarm
cp .env.example .env
uv sync --extra dev --extra ui
./scripts/verify_all.sh    # full offline gate: ruff, mypy, pytest+coverage, 16/16 eval, demo
./scripts/demo.sh          # 90-second demo path (CASE-002 → gene → CASE-005)
uv run conductgene-ui      # 5-panel Streamlit demo
```

**Docker:**

```bash
docker compose up --build
```

## Eval metrics (mock mode, synthetic suite)

| Metric | Value |
|--------|-------|
| Scenario pass rate | 16/16 (100%) |
| Citation coverage | 100% |
| Abstain rate | ~6.3% (CASE-007) |
| Gene learning (CASE-002 → CASE-005) | `escalation_offered`: needs_review → pass |

Reproduce locally with `./scripts/verify_all.sh` or `./scripts/qa_matrix.sh`.

## Live stack (BGE + Qdrant + LLM providers)

```bash
cp .env.example .env   # add CONDUCTGENE_OPENROUTER_API_KEY for cloud LLM
uv sync --extra dev --extra retrieval --extra live --extra ui

# Start Qdrant + BGE services (embedding :9001, reranker :9002)
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant
uv run python scripts/discover_services.py
uv run python scripts/synth_data.py          # optional: extend KB
uv run python scripts/ingest_qdrant.py --rebuild

# Live retrieval + mock agents (CI-safe default)
CONDUCTGENE_RETRIEVAL_MODE=qdrant_rerank CONDUCTGENE_ENABLE_RERANKER=true uv run conductgene-ui

# Full live LLM swarm (OpenRouter / LM Studio / instruct gateway)
CONDUCTGENE_MODE=live CONDUCTGENE_LLM_PROVIDER=openrouter uv run python scripts/run_live_simulation.py
uv run python scripts/bench_models.py --provider openrouter --limit 4 --max-cost-usd 1.0
```

**Docker live profile** (Qdrant in compose; BGE/LM Studio on host):

```bash
docker compose -f docker-compose.yml -f docker-compose.live.yml up --build
```

**Pre-flight scorecard:**

```bash
./scripts/run_simulation_matrix.sh                  # full scorecard → reports/simulation_matrix.md
SKIP_LIVE=true ./scripts/run_simulation_matrix.sh   # offline only (CI gate)
```

See [docs/qdrant-retrieval.md](docs/qdrant-retrieval.md) · [docs/live-simulation.md](docs/live-simulation.md)

## API

```bash
uv run conductgene-serve   # http://127.0.0.1:8090/docs
```

Production hardening (optional, off by default for local demo):

```bash
CONDUCTGENE_API_KEY=your-secret        # require X-API-Key header (health/readiness stay open)
CONDUCTGENE_RATE_LIMIT_RPM=30          # per-client limit on /swarm/analyze and /eval/run
```

| Endpoint | Description |
|----------|-------------|
| `GET /healthz` | Liveness |
| `GET /healthz/services` | BGE / Qdrant / LLM service probes |
| `GET /readyz` | Readiness |
| `POST /swarm/analyze` | Swarm review + audit record (returns `trace_id`) |
| `POST /genes/learn` | Store supervisor-approved Policy Gene |
| `GET /genes` | List genes |
| `POST /genes/{id}/rollback` | Deactivate gene (rollback) |
| `POST /eval/run` | Run synthetic scenario suite |
| `GET /audit/{case_id}` | Case provenance |
| `GET /audit/export` | Export case + gene audit trails |
| `GET /metrics/evolution` | Learning + quality metrics (cached eval) |

## CLI

```bash
uv run conductgene demo
uv run conductgene eval --suite all
uv run conductgene analyze --file data/scenarios/collections/case_002_coercive_soft.json
uv run conductgene audit export --out reports/audit_export.json
uv run conductgene genes export-skill --out reports/skill   # Policy Genes → portable SKILL.md
```

## MCP

Expose learned Policy Genes to MCP-capable agent runtimes:

```bash
uv sync --extra mcp
uv run conductgene-mcp     # stdio MCP server: list_genes, export_skill
```

## Observability

Every swarm run emits structured stage traces correlated by `trace_id` (also stored in the audit record):

```
swarm_stage trace_id=0d10a721f2664b42 stage=retrieval duration_ms=0.2 case_id=CASE-005 ...
swarm_stage trace_id=0d10a721f2664b42 stage=verdict duration_ms=0.4 abstained=False ...
```

## Docs

- [Architecture](docs/architecture.md)
- [Product spec](docs/product-spec.md)
- [Demo script](docs/demo-script.md)
- [Roadmap](docs/ROADMAP.md)
- [Qdrant retrieval setup](docs/qdrant-retrieval.md)
- [Live simulation guide](docs/live-simulation.md)
- [Governance (IMDA MGF)](docs/governance.md)
- [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [Releases](https://github.com/FUYOH666/conductgene-swarm/releases)
- Hackathon-era material: [docs/_archive/hackathon/](docs/_archive/hackathon/)

## License

MIT — see [LICENSE](LICENSE).
