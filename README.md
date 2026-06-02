# ConductGene Swarm

[![CI](https://github.com/FUYOH666/conductgene-swarm/actions/workflows/ci.yml/badge.svg)](https://github.com/FUYOH666/conductgene-swarm/actions/workflows/ci.yml)
[![Docker Smoke](https://github.com/FUYOH666/conductgene-swarm/actions/workflows/docker-smoke.yml/badge.svg)](https://github.com/FUYOH666/conductgene-swarm/actions/workflows/docker-smoke.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/FUYOH666/conductgene-swarm)](https://github.com/FUYOH666/conductgene-swarm/releases)

**Human-approved AI conduct QA that remembers supervisor corrections safely.**

Multi-agent conduct QA for regulated industries. Prosecutor, Defender, and Arbiter agents review call transcripts with evidence-grounded citations. When a supervisor corrects the verdict, the system stores a **supervisor-approved Policy Gene** — auditable, rollbackable institutional memory.

Built for [UCWS Singapore 2026](https://luma.com/UCWS2026) AGENT track.

<p align="center">
  <a href="docs/assets/architecture.png">
    <img src="docs/assets/architecture.png" alt="ConductGene Swarm architecture" width="720"/>
  </a>
</p>

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
| Abstain rate | ~6.3% (CASE-007) |
| Gene learning (CASE-002 → CASE-005) | `escalation_offered`: needs_review → pass |

Run `./scripts/verify_all.sh` or `./scripts/qa_matrix.sh` to reproduce locally.

## Quick start

```bash
git clone https://github.com/FUYOH666/conductgene-swarm.git
cd conductgene-swarm
cp .env.example .env
uv sync --extra dev --extra ui
./scripts/verify_all.sh    # full virtual verification
./scripts/demo.sh          # 90-second demo path
uv run conductgene-ui     # 5-panel Streamlit demo
```

**Docker:**

```bash
docker compose up --build
```

## Demo video

<!-- Add YouTube/Loom URL after recording — see docs/demo-video-guide.md -->
Recording guide: [docs/demo-video-guide.md](docs/demo-video-guide.md)

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
uv run conductgene audit export --out reports/audit_export.json
```

## Docs

- [Product spec](docs/product-spec.md)
- [90-second demo script](docs/demo-script.md)
- [Demo video guide](docs/demo-video-guide.md)
- [Pitch deck](docs/pitch-deck.md)
- [UCWS registration](docs/UCWS_REGISTRATION.md)
- [Submission checklist](docs/SUBMISSION.md)
- [Governance (IMDA MGF)](docs/governance.md)
- [Architecture](docs/architecture.md)
- [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [Releases](https://github.com/FUYOH666/conductgene-swarm/releases)

## License

MIT — see [LICENSE](LICENSE).
