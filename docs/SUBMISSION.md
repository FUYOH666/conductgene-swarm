# UCWS Submission Checklist

[UCWS Singapore 2026](https://luma.com/UCWS2026) — **one portal entry**, tracks **AGENT + APPLICATION**.

Overview: [UCWS_DUAL_TRACK.md](UCWS_DUAL_TRACK.md)

## Portal assets (ConductGene — upload to form)

Files in [`submission/`](submission/):

| Asset | File | Status |
|-------|------|--------|
| Logo 512×512 | [logo-512.png](submission/logo-512.png) | Ready |
| Screenshot 1 | [screenshot-1-swarm.png](submission/screenshot-1-swarm.png) | Ready |
| Screenshot 2 | [screenshot-2-agents.png](submission/screenshot-2-agents.png) | Ready |
| Screenshot 3 | [screenshot-3-gene-learning.png](submission/screenshot-3-gene-learning.png) | Ready |
| Demo video (WebM) | [conductgene-demo.webm](submission/conductgene-demo.webm) | Ready — upload to YouTube |
| Unified form copy | [portal-copy.md](submission/portal-copy.md) | Ready |
| Resubmit steps | [resubmit-checklist.md](submission/resubmit-checklist.md) | Ready |

Regenerate ConductGene assets: `./scripts/capture_submission_assets.sh --with-video`

## Agent track — ConductGene Swarm

- [x] Public repo: https://github.com/FUYOH666/conductgene-swarm
- [x] CI + Docker smoke green
- [x] Release v0.2.1
- [x] `./scripts/verify_all.sh` and `./scripts/qa_matrix.sh`
- [x] YouTube demo: https://youtu.be/5wIBi-HkK9Y → primary **Demo URL** on portal
- [ ] Listed as **TRACK 1: AGENT** in portal Description

## Application track — AttestRWA

- [x] Public repo: https://github.com/FUYOH666/attestrwa
- [x] Demo video: https://youtube.com/shorts/BipB2qPzZz0
- [x] One-command demo: `./scripts/demo-mode.sh`
- [ ] Listed as **TRACK 2: APPLICATION** in portal Description (same form)

## Portal registration (manual)

1. [evol.epicconnector.ai](https://evol.epicconnector.ai) → Edit project
2. Tracks: **AGENT** + **APPLICATION** (not Deep Research)
3. Paste from [portal-copy.md](submission/portal-copy.md)
4. Upload logo + 3 screenshots
5. **Resubmit for review**

- [ ] Registration / resubmit complete
- [ ] Organizer approval pending

## Pre-Demo Day rehearsal

- [ ] `./scripts/qa_matrix.sh` — 4/4 PASS locally
- [ ] ConductGene offline demo (mock mode)
- [ ] AttestRWA `./scripts/e2e_rwa_flow.sh` (optional second demo path)
- [ ] 5-minute pitch from [pitch-deck-outline.md](pitch-deck-outline.md)
- [ ] Community vote outreach (40% of score)

## Contacts

- Epic Connector: incubator@epicconnector.ai
- Event: [UCWS Singapore 2026 on Luma](https://luma.com/UCWS2026)
