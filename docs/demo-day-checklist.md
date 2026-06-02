# Demo Day Checklist — June 13, 2026, Singapore

## Pre-submission (by June 3)

- [x] Open-source repo scaffold
- [x] README with architecture, env vars, commands, eval metrics
- [x] CHANGELOG.md
- [x] CI green (pytest + ruff + eval)
- [x] `./scripts/demo.sh` works
- [x] Streamlit 5-panel UI (`uv run conductgene-ui`)
- [x] Single product narrative (Idea B/C archived in `docs/_archive/`)
- [ ] Push to GitHub `FUYOH666/conductgene-swarm`
- [ ] Register project on [evol.epicconnector.ai](https://evol.epicconnector.ai)

## Polish (June 4–12)

### P0 — Must have

- [ ] Demo video (90s–3 min) — see [demo-video-guide.md](demo-video-guide.md)
- [ ] Pitch deck (10 slides) — see [pitch-deck.md](pitch-deck.md)
- [ ] Evolution metrics in README (eval table)
- [ ] Architecture diagram — [assets/architecture.mmd](assets/architecture.mmd)

### P1 — Should have

- [x] Streamlit UI with Deterministic Demo Mode label
- [x] Gene audit events (learn + rollback)
- [x] `GET /audit/export`
- [x] A2A Agent Card — [a2a-agent-card.json](a2a-agent-card.json)
- [x] Error path tests (404 rollback, invalid citations)
- [x] Docker one-liner

### P2 — Nice to have

- [ ] GitHub Pages landing
- [ ] Live LLM mode (beyond stub)
- [ ] BGE + Qdrant retrieval port

## Demo Day logistics

- [ ] Confirm top-20 status / travel
- [ ] Prepare offline demo (mock mode, no Tailscale dependency)
- [ ] 5-min pitch rehearsed
- [ ] Q&A prep — see pitch-deck-outline.md

## Evolution metrics dashboard

```bash
curl -s http://127.0.0.1:8090/metrics/evolution | jq .
curl -s http://127.0.0.1:8090/audit/export | jq .
```

Target numbers for compelling narrative:

| Metric | Target |
|--------|--------|
| `active_genes` | ≥ 1 after demo |
| Held-out improvement | CASE-005 escalation pass after gene |
| Demo cases | 16 synthetic transcripts |

## Contacts

- Epic Connector: incubator@epicconnector.ai
- Event: [UCWS Singapore 2026](https://luma.com/UCWS2026)
