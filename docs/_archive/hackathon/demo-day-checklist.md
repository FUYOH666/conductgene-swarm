# Demo Day Checklist — June 13, 2026, Singapore

## Pre-submission (by June 3)

- [x] Open-source repo scaffold
- [x] README with architecture, env vars, commands, eval metrics
- [x] CHANGELOG.md
- [x] CI green (pytest + ruff + eval)
- [x] `./scripts/demo.sh` works
- [x] Streamlit 5-panel UI (`uv run conductgene-ui`)
- [x] Single product narrative (Idea B/C archived in `docs/_archive/`)
- [x] Push to GitHub [FUYOH666/conductgene-swarm](https://github.com/FUYOH666/conductgene-swarm)
- [x] GitHub About: description, topics, community files, release v0.2.1
- [ ] Dual-track resubmit on [evol.epicconnector.ai](https://evol.epicconnector.ai) (AGENT + APPLICATION) — see [resubmit-checklist.md](submission/resubmit-checklist.md)

## Polish (June 4–12)

### P0 — Must have

- [x] Demo video — [youtu.be/5wIBi-HkK9Y](https://youtu.be/5wIBi-HkK9Y) (AttestRWA: [Shorts](https://youtube.com/shorts/BipB2qPzZz0))
- [x] Pitch deck (10 slides) — see [pitch-deck.md](pitch-deck.md) (export PDF manually)
- [x] Evolution metrics in README (eval table)
- [x] Architecture diagram — [assets/architecture.png](assets/architecture.png)

### P1 — Should have

- [x] Streamlit UI with Deterministic Demo Mode label
- [x] Gene audit events (learn + rollback)
- [x] `GET /audit/export` + CLI `conductgene audit export`
- [x] A2A Agent Card — [a2a-agent-card.json](a2a-agent-card.json)
- [x] Error path tests (404 rollback, invalid citations)
- [x] Docker one-liner + docker-smoke CI
- [x] `./scripts/qa_matrix.sh` integration scorecard

### P2 — Nice to have

- [ ] GitHub Pages landing
- [x] Live LLM mode — `providers/llm.py`, LM Studio + OpenRouter (v0.5)
- [x] BGE + Qdrant retrieval — validated MacBook; `ingest_qdrant.py --rebuild`

### Singapore live rehearsal (June 4–12)

- [x] `./scripts/run_simulation_matrix.sh` — S1–S8 PASS (LM Studio + OpenRouter validation)
- [x] Live demo WebM — `./scripts/capture_submission_assets.sh --with-video --profile live`
- [ ] Re-upload YouTube from `docs/submission/conductgene-demo.webm` (replace youtu.be/5wIBi-HkK9Y)
- [ ] Rehearse 90s path — [singapore-demo-runbook.md](singapore-demo-runbook.md)
- [x] `discover_services` green: embedding, reranker, qdrant, lmstudio
- [x] Streamlit Model Jury: `MODE=live`, `LLM_PROVIDER=lmstudio`, `qdrant_rerank`

## Demo Day logistics

- [ ] Confirm top-20 status / travel
- [x] Prepare offline demo — LM Studio + qdrant_rerank (no cloud required)
- [ ] 5-min pitch rehearsed
- [ ] Q&A prep — see pitch-deck-outline.md

## Evolution metrics dashboard

```bash
curl -s http://127.0.0.1:8090/metrics/evolution | jq .
curl -s http://127.0.0.1:8090/audit/export | jq .
./scripts/qa_matrix.sh
```

Target numbers for compelling narrative:

| Metric | Target |
|--------|--------|
| `active_genes` | ≥ 1 after demo |
| Held-out improvement | CASE-005 escalation pass after gene |
| Demo cases | 16 synthetic transcripts |
| QA scorecard | 5/5 PASS |

## Contacts

- Epic Connector: incubator@epicconnector.ai
- Event: [UCWS Singapore 2026](https://luma.com/UCWS2026)
