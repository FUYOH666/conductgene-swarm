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
- [ ] Register project on [evol.epicconnector.ai](https://evol.epicconnector.ai) — see [SUBMISSION.md](SUBMISSION.md)

## Polish (June 4–12)

### P0 — Must have

- [ ] Demo video (90s–3 min) — see [demo-video-guide.md](demo-video-guide.md)
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
- [ ] Live LLM mode (beyond stub)
- [ ] BGE + Qdrant retrieval port

## Demo Day logistics

- [ ] Confirm top-20 status / travel
- [x] Prepare offline demo (mock mode, no Tailscale dependency)
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
| QA scorecard | 4/4 PASS |

## Contacts

- Epic Connector: incubator@epicconnector.ai
- Event: [UCWS Singapore 2026](https://luma.com/UCWS2026)
