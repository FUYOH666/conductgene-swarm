# UCWS Submission Checklist

Track submission assets for [UCWS Singapore 2026](https://luma.com/UCWS2026) AGENT track.

## Automated (done in repo)

- [x] Public GitHub repository: https://github.com/FUYOH666/conductgene-swarm
- [x] CI + Docker smoke workflows green
- [x] Release v0.2.1 with CHANGELOG
- [x] README with eval metrics, architecture, quick start
- [x] `./scripts/verify_all.sh` and `./scripts/qa_matrix.sh`
- [x] Pitch deck markdown: [pitch-deck.md](pitch-deck.md)
- [x] Architecture PNG: [assets/architecture.png](assets/architecture.png)
- [x] A2A agent card: [a2a-agent-card.json](a2a-agent-card.json)
- [x] Governance doc: [governance.md](governance.md)

## Manual (your action)

### 1. UCWS portal registration

1. Go to [evol.epicconnector.ai](https://evol.epicconnector.ai)
2. Register **ConductGene Swarm** for AGENT track
3. Submit repo URL: `https://github.com/FUYOH666/conductgene-swarm`
4. Add short description from [product-spec.md](product-spec.md)

- [ ] Registration submitted
- [ ] Confirmation email received

### 2. Demo video (90 seconds)

Follow [demo-video-guide.md](demo-video-guide.md):

```bash
uv run conductgene-ui
# Record: CASE-002 → approve gene → CASE-005
```

- [ ] Video recorded
- [ ] Uploaded (YouTube unlisted or Loom)
- [ ] URL added to README «Demo video» section

### 3. Pitch deck PDF

Export [pitch-deck.md](pitch-deck.md) to Google Slides / Keynote / PDF (10 slides).

- [ ] PDF exported for Demo Day

## Pre-Demo Day rehearsal

- [ ] `./scripts/qa_matrix.sh` — 4/4 PASS locally
- [ ] Offline demo rehearsed (mock mode, no network)
- [ ] 5-minute pitch from [pitch-deck-outline.md](pitch-deck-outline.md)
- [ ] Q&A prep (LLM? governance? gene rollback?)

## Contacts

- Epic Connector: incubator@epicconnector.ai
- Event: [UCWS Singapore 2026 on Luma](https://luma.com/UCWS2026)
