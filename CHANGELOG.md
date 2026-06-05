# Changelog

## [0.5.1] - 2026-06-05

### Added

- `scripts/run_simulation_matrix.sh` — Singapore pre-flight scorecard (S1–S10)
- [`docs/singapore-demo-runbook.md`](docs/singapore-demo-runbook.md) — 90s LM Studio booth script
- QA matrix step 5/5: optional live service discovery

### Fixed

- `bench_models.py` — `ScenarioGolden` comparison via `model_dump()`
- `eval/scenarios.py` — suite filter for `synth` cases
- `providers/llm.py` — `response_format` only for OpenRouter; LM Studio/instruct compatible
- `agents/dispatch.py` — unified live/mock guard; abstain skips LLM calls
- `docker-compose.live.yml` — in-process UI (`UI_USE_API=false`) for Model Jury
- Staff review findings: architecture + demo-day docs updated

### Validated (Singapore pre-flight)

- LM Studio live: `run_live_simulation` CASE-005 escalation pass
- OpenRouter live: `claude-sonnet-4` simulation pass (~47s)
- Offline CI: 48 tests, 16/16 mock eval

## [0.5.0] - 2026-06-05

### Added

- `providers/llm.py` — OpenAI-compatible client for OpenRouter, LM Studio, instruct gateway
- `agents/prompts.py`, `agents/dispatch.py` — live LLM agent prompts and swarm dispatch
- CLI flags: `conductgene analyze --provider`, `--model`, `--mode`
- `scripts/synth_data.py` — extended policy KB (15 docs) + synth scenarios (CASE-017/018)
- `scripts/run_live_simulation.py` — end-to-end judge path report
- `scripts/bench_models.py` — model benchmark JSON/CSV/MD outputs
- Streamlit **Model Jury** sidebar (provider, mode, retrieval, service probe)
- `docker-compose.live.yml` — Qdrant + live retrieval via `host.docker.internal`
- Discovery probes: instruct gateway, always-on LM Studio probe
- Tests: `test_llm_provider.py`, `test_swarm_live.py`, BGE `dense_embedding` / rerank `relevance_score`

### Fixed

- BGE client: `dense_embedding` and `relevance_score` field aliases (Services-BGE API)
- Qdrant: UUID point IDs, `query_points` API (qdrant-client 1.18+)
- `verify_all.sh` forces offline env overrides (CI-safe with local `.env`)

### Changed

- `pipeline/swarm.py` dispatches live agents when `CONDUCTGENE_MODE=live` and provider != mock
- Dockerfile includes `retrieval` + `live` extras
- Version 0.5.0

## [0.3.0] - 2026-06-03

### Added

- Live retrieval scaffolding: `retrieval/` package (memory, BGE client, Qdrant store, factory)
- `scripts/discover_services.py` and `GET /healthz/services` for service probes
- `scripts/ingest_qdrant.py` for BGE → Qdrant policy KB ingest
- Extended settings: `llm_provider`, `retrieval_mode`, OpenRouter/LM Studio/Qdrant env vars
- Optional `[retrieval]` extra (`qdrant-client`)
- Docs: [ROADMAP.md](docs/ROADMAP.md), [qdrant-retrieval.md](docs/qdrant-retrieval.md), [live-simulation.md](docs/live-simulation.md)
- Tests: config, retrieval fallback, discovery mocks

### Changed

- `retrieve_evidence()` now accepts `Settings`; qdrant modes degrade to memory when configured
- Version 0.3.0

## [0.2.2] - 2026-06-01

### Added

- UCWS dual-track portal copy (one entry: AGENT ConductGene + APPLICATION AttestRWA)
- [docs/UCWS_DUAL_TRACK.md](docs/UCWS_DUAL_TRACK.md) — single submission, two repos
- [docs/submission/resubmit-checklist.md](docs/submission/resubmit-checklist.md) — post-rejection resubmit steps

### Changed

- [docs/submission/portal-copy.md](docs/submission/portal-copy.md) — unified Description with TRACK 1 / TRACK 2 blocks; explicit no MiroMind API
- [docs/UCWS_REGISTRATION.md](docs/UCWS_REGISTRATION.md), [docs/SUBMISSION.md](docs/SUBMISSION.md) — dual-track model
- README — dual-track UCWS links; ConductGene demo https://youtu.be/5wIBi-HkK9Y

## [0.2.1] - 2026-06-02

### Added

- Gene audit store (`audit/gene_events.py`) for learn + rollback events
- `GET /audit/export` — combined case + gene audit export
- `compute_learn_eval_delta` — real held-out eval scores on gene learn (no hardcoded +0.2)
- CASE-016 rollback_operator persona scenario
- Streamlit Deterministic Demo Mode label + real eval delta display
- Thin HTTP client (`ui/client.py`) for API-backed demos
- Docker + docker-compose one-liner
- Pitch deck, demo video guide, UCWS registration doc
- Architecture mermaid diagram (`docs/assets/architecture.mmd`)

### Changed

- `/metrics/evolution` caches eval result; use `?refresh=true` to re-run
- `citation_ok` validates cited chunk IDs against evidence pool
- A2A agent card v0.2.0 — institutional memory positioning
- `openai` moved to optional `[live]` extra
- Live mode stub in `agents/live.py`

### Tests

- Rollback integration test (gene apply → rollback → revert)
- Gene learn audit event test
- Invalid citation ID test
- Persona matrix parametrized test (5 personas)
- Streamlit import smoke test
- Harmony tests (version sync, manifest, doc consistency)
- Docker smoke CI workflow

### Repository

- `docs/submission/` portal assets (logo, screenshots, demo WebM, portal-copy)
- Playwright capture scripts for screenshots and demo video
- Optional `[submission]` extra with playwright

## [0.2.0] - 2026-06-01

### Added

- Audit store (`GET /audit/{case_id}`) with append-only case provenance
- Eval harness (`POST /eval/run`) with 15 synthetic scenarios
- Explicit rollback endpoint (`POST /genes/{id}/rollback`)
- Supervisor approval fields on Policy Genes (`supervisor_id`, `created_from`, `eval_detail`)
- Streamlit 5-panel UI (`uv run conductgene-ui`)
- `./scripts/verify_all.sh` — full virtual verification
- Scenario corpus under `data/scenarios/` with persona matrix
- Repositioned copy: supervisor-approved institutional memory

### Changed

- README and docs minimalism — single product narrative
- Internal research/ideas archived to `docs/_archive/`
- Prosecutor detects coercive soft tone as `needs_review` (not fail)
- Demo path uses CASE-002 → Policy Gene → CASE-005 held-out

## [0.1.0] - 2026-06-01

### Added

- Initial ConductGene Swarm MVP for UCWS Singapore 2026
