# ConductGene Swarm

**Human-approved AI conduct QA that remembers supervisor corrections safely.**

Multi-agent conduct QA for regulated industries. Prosecutor, Defender, and Arbiter agents review call transcripts with evidence-grounded citations. When a supervisor corrects the verdict, the system stores a **supervisor-approved Policy Gene** — auditable, rollbackable institutional memory.

Built for [UCWS Singapore 2026](https://luma.com/UCWS2026) AGENT track. Built on prior RAG, citation, and evaluation patterns from my portfolio.

[![CI](https://github.com/FUYOH666/conductgene-swarm/actions/workflows/ci.yml/badge.svg)](https://github.com/FUYOH666/conductgene-swarm/actions/workflows/ci.yml)

## Problem → Solution

| Problem | Solution |
|---------|----------|
| QA teams repeat the same corrections | Policy Genes preserve approved patterns |
| LLMs hallucinate policy | Evidence-grounded citations + abstain |
| Regulators need accountability | Supervisor approval, audit trail, rollback |

## Eval metrics (mock mode, synthetic suite)

| Metric | Value |
|--------|-------|
| Scenario pass rate | 16/16 (100%) |
| Citation coverage | 100% |
| Abstain rate | ~6.7% (CASE-007) |
| Gene learning (CASE-002 → CASE-005) | `escalation_offered`: needs_review → pass |

Run `./scripts/verify_all.sh` to reproduce locally.

## Demo cycle

1. Transcript → 2. Evidence → 3. Prosecutor → 4. Defender → 5. Arbiter verdict → 6. Supervisor override → 7. Policy Gene stored → 8. Better result on similar case

```bash
cp .env.example .env
uv sync --extra dev --extra ui
./scripts/verify_all.sh    # full virtual verification
./scripts/demo.sh          # 90-second demo path
uv run conductgene-ui     # 5-panel Streamlit demo
```

**Docker (optional):**

```bash
docker compose up --build
```

## API

```bash
uv run conductgene-serve   # http://127.0.0.1:8090/docs
```

| Endpoint | Description |
|----------|-------------|
| `GET /healthz` | Liveness |
| `GET /readyz` | Readiness |
| `POST /swarm/analyze` | Swarm review + audit record |
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
uv run conductgene analyze --file data/scenarios/collections/case_002.json
```

## Docs

- [Product spec](docs/product-spec.md)
- [90-second demo script](docs/demo-script.md)
- [Demo video guide](docs/demo-video-guide.md)
- [Pitch deck](docs/pitch-deck.md)
- [UCWS registration](docs/UCWS_REGISTRATION.md)
- [Governance (IMDA MGF)](docs/governance.md)
- [Architecture](docs/architecture.md)

## License

MIT — see [LICENSE](LICENSE).
