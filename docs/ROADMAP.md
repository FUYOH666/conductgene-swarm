# ConductGene Swarm — Roadmap

Supervisor-approved policy memory for regulated AI conduct QA.

**Baseline (always):** deterministic mock mode, 16/16 eval, no external services — `./scripts/verify_all.sh`

---

## v0.2.2 — Done (2026-06-01)

- UCWS dual-track portal submission (AGENT ConductGene + APPLICATION AttestRWA)
- Unified portal copy, resubmit checklist, demo URLs
- Docs: [UCWS_DUAL_TRACK.md](UCWS_DUAL_TRACK.md)

---

## v0.3.0 — Live retrieval scaffolding (in progress)

**Goal:** BGE + Qdrant retrieval path without breaking mock CI.

| Item | Status | Notes |
|------|--------|-------|
| Extended `Settings` (retrieval_mode, llm_provider, Qdrant, OpenRouter) | Done | [`config.py`](../src/conductgene/config.py) |
| `scripts/discover_services.py` | Done | BGE :9001/:9002, Qdrant, optional LLM |
| `GET /healthz/services` | Done | JSON service table |
| `retrieval/` package (memory, BGE, Qdrant) | Done | Factory + explicit fallback |
| `scripts/ingest_qdrant.py` | Done | Requires live BGE + Qdrant |
| Tests (mock HTTP, fallback) | Done | CI stays offline |
| [`docs/qdrant-retrieval.md`](qdrant-retrieval.md) | Done | Setup for MacBook |

**Tomorrow (MacBook with Services-BGE running):**

1. `~/development/Services-BGE/scripts/service.sh start`
2. `docker run -p 6333:6333 qdrant/qdrant` (or local Qdrant)
3. `uv sync --extra dev --extra retrieval`
4. `uv run python scripts/discover_services.py`
5. `uv run python scripts/ingest_qdrant.py`
6. `CONDUCTGENE_RETRIEVAL_MODE=qdrant_rerank CONDUCTGENE_ENABLE_RERANKER=true uv run conductgene-ui`

---

## v0.4.0 — LLM providers (planned)

| Item | Description |
|------|-------------|
| `providers/llm.py` | mock, openrouter, lmstudio, instruct (TailScale :8002) |
| Wire `pipeline/swarm.py` | Dispatch live agents when `llm_provider != mock` |
| Structured JSON output | Pydantic `AgentOpinion` from LLM |
| CLI flags | `--provider`, `--model` |
| Tests | respx mocks only in CI |

Env: `CONDUCTGENE_LLM_PROVIDER=openrouter`, `CONDUCTGENE_OPENROUTER_API_KEY=...`

---

## v0.5.0 — Benchmark + live simulation (planned)

| Script | Output |
|--------|--------|
| `scripts/synth_data.py` | Extended synthetic scenarios (fintech, insurance, …) |
| `scripts/bench_models.py` | `outputs/benchmarks/*` JSON/CSV/MD |
| `scripts/run_live_simulation.py` | `outputs/demo/live_simulation_report.md` |
| Streamlit «Model Jury» panel | Provider, retrieval, before/after gene eval |

Metrics: pass_rate, citation_coverage, latency, cost_estimate, gene_delta.

---

## v1.0 — Production hardening (planned)

- API authentication for non-local deploys
- Rate limits + cost caps on OpenRouter bench
- Observability (structured traces per swarm run)
- Policy Gene export as SKILL.md / MCP stub
- Optional EAS attestation bridge (AttestRWA integration)

---

## Mode matrix

| Profile | `MODE` | `RETRIEVAL_MODE` | `LLM_PROVIDER` | Use case |
|---------|--------|------------------|----------------|----------|
| CI / hackathon demo | mock | memory | mock | Default, offline |
| MacBook RAG | mock | qdrant_rerank | mock | Evidence via BGE+Qdrant, agents still rules |
| Live LLM | live | qdrant_rerank | openrouter | Full simulation |
| Degraded | mock | qdrant | mock | Qdrant down → memory fallback (logged) |

---

## Related docs

- [Architecture](architecture.md)
- [Qdrant retrieval setup](qdrant-retrieval.md)
- [Live simulation (judge path)](live-simulation.md)
- [UCWS dual-track](UCWS_DUAL_TRACK.md)
