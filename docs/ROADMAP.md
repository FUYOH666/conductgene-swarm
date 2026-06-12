# ConductGene Swarm — Roadmap

Supervisor-approved policy memory for regulated AI conduct QA.

**Baseline (always):** deterministic mock mode, 16/16 eval, no external services — `./scripts/verify_all.sh`

---

## v0.2.2 — Done (2026-06-01)

- UCWS dual-track portal submission (AGENT ConductGene + APPLICATION AttestRWA)
- Unified portal copy, resubmit checklist, demo URLs
- Docs: [_archive/hackathon/UCWS_DUAL_TRACK.md](_archive/hackathon/UCWS_DUAL_TRACK.md)

---

## v0.3.0 — Live retrieval scaffolding — Done (2026-06-05)

**Goal:** BGE + Qdrant retrieval path without breaking mock CI.

| Item | Status | Notes |
|------|--------|-------|
| Extended `Settings` (retrieval_mode, llm_provider, Qdrant, OpenRouter) | Done | [`config.py`](../src/conductgene/config.py) |
| `scripts/discover_services.py` | Done | BGE :9001/:9002, Qdrant, LLM probes |
| `GET /healthz/services` | Done | JSON service table |
| `retrieval/` package (memory, BGE, Qdrant) | Done | Factory + explicit fallback |
| `scripts/ingest_qdrant.py` | Done | `--rebuild` flag; BGE + Qdrant |
| Tests (mock HTTP, fallback) | Done | CI stays offline |
| [`docs/qdrant-retrieval.md`](qdrant-retrieval.md) | Done | MacBook setup validated |

---

## v0.4.0 — LLM providers — Done (2026-06-05)

| Item | Status |
|------|--------|
| `providers/llm.py` | Done — openrouter, lmstudio, instruct |
| Wire `pipeline/swarm.py` | Done — `agents/dispatch.py` |
| Structured JSON output | Done — Pydantic `AgentOpinion` + retry |
| CLI flags | Done — `--provider`, `--model`, `--mode` |
| Tests | Done — `test_llm_provider.py`, `test_swarm_live.py` |

Env: `CONDUCTGENE_MODE=live`, `CONDUCTGENE_LLM_PROVIDER=openrouter|lmstudio|instruct`

---

## v0.5.0 — Benchmark + live simulation — Done (2026-06-05)

| Script | Status |
|--------|--------|
| `scripts/synth_data.py` | Done — 15 KB docs, CASE-017/018 (suite: synth) |
| `scripts/bench_models.py` | Done — `outputs/benchmarks/*` |
| `scripts/run_live_simulation.py` | Done — `outputs/demo/live_simulation_report.md` |
| Streamlit «Model Jury» panel | Done — sidebar provider/retrieval/probe |
| `docker-compose.live.yml` | Done — Qdrant + host BGE/LM Studio |

---

## v0.6.0 — Production hardening — Done (2026-06-12)

| Item | Status | Notes |
|------|--------|-------|
| API authentication for non-local deploys | Done | `CONDUCTGENE_API_KEY` → `X-API-Key`; health/readiness stay open |
| Rate limits + cost caps on OpenRouter bench | Done | `CONDUCTGENE_RATE_LIMIT_RPM`; `bench_models.py --max-requests / --max-cost-usd` |
| Observability (structured traces per swarm run) | Done | `trace_id` + per-stage duration logs; stdlib logging, no OTel dependency yet |
| Policy Gene export as SKILL.md | Done | `conductgene genes export-skill --out <dir>` |
| Type-check + coverage CI | Done | mypy + pytest-cov in `verify_all.sh` (coverage ratchet from 72%) |

---

## v1.0.0 — Final open-source release — Done (2026-06-12)

| Item | Status | Notes |
|------|--------|-------|
| Docs overhaul | Done | Hackathon material archived to `_archive/hackathon/`; product docs refreshed |
| Docker hardening | Done | Multi-stage build, non-root user, no dev extras in runtime, `HEALTHCHECK` |
| Live-stack CI (Qdrant) | Done | Integration tests against real Qdrant service container (stub embedder, no BGE in CI) |
| Policy Gene MCP stub | Done | `conductgene-mcp` stdio server (`list_genes`, `export_skill`), optional `mcp` extra |
| CLI test coverage | Done | `tests/test_cli.py` drives the dispatch path; coverage ratchet raised |

The LM Studio live path stays a manual verification (`./scripts/run_simulation_matrix.sh`) by design — a local desktop LLM cannot run in hosted CI.

---

## Future (no committed date)

- OpenTelemetry trace export (current: structured stdlib logging with `trace_id`)
- Optional EAS attestation bridge (AttestRWA integration — external dependency)
- Postgres / object-store backends for gene and audit stores (current: append-only JSONL)

---

## Mode matrix

| Profile | `MODE` | `RETRIEVAL_MODE` | `LLM_PROVIDER` | Use case |
|---------|--------|------------------|----------------|----------|
| CI / offline demo | mock | memory | mock | Default, offline |
| Local RAG | mock | qdrant_rerank | mock | Evidence via BGE+Qdrant, agents still rules |
| Live LLM | live | qdrant_rerank | openrouter | Full simulation |
| Local LLM | live | qdrant_rerank | lmstudio | LM Studio on :1234 |
| Instruct gateway | live | qdrant_rerank | instruct | Self-hosted OpenAI-compatible gateway |
| Degraded | mock | qdrant | mock | Qdrant down → memory fallback (logged) |

---

## Related docs

- [Architecture](architecture.md)
- [Qdrant retrieval setup](qdrant-retrieval.md)
- [Live simulation guide](live-simulation.md)
- [Demo script](demo-script.md)
