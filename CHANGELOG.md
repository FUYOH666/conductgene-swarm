# Changelog

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

- GitHub community files (SECURITY, CONTRIBUTING, CODE_OF_CONDUCT)
- Issue and PR templates, Dependabot
- Release v0.2.1, social preview asset
- `scripts/qa_matrix.sh` integration scorecard
- CLI `conductgene audit export`
- Streamlit optional API mode (`CONDUCTGENE_UI_USE_API`)

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
