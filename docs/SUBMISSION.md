# UCWS Submission Checklist

Track submission assets for [UCWS Singapore 2026](https://luma.com/UCWS2026) AGENT track.

## Portal assets (ready to upload)

All files in [`submission/`](submission/):

| Asset | File | Status |
|-------|------|--------|
| Logo 512×512 | [logo-512.png](submission/logo-512.png) | Ready |
| Screenshot 1 | [screenshot-1-swarm.png](submission/screenshot-1-swarm.png) | Ready |
| Screenshot 2 | [screenshot-2-agents.png](submission/screenshot-2-agents.png) | Ready |
| Screenshot 3 | [screenshot-3-gene-learning.png](submission/screenshot-3-gene-learning.png) | Ready |
| Demo video (WebM) | [conductgene-demo.webm](submission/conductgene-demo.webm) | Ready — upload to YouTube |
| Form copy-paste | [portal-copy.md](submission/portal-copy.md) | Ready |
| Video end card | [video-end-card.png](submission/video-end-card.png) | Optional overlay |

Regenerate: `./scripts/capture_submission_assets.sh --with-video`

## Automated (done in repo)

- [x] Public GitHub repository: https://github.com/FUYOH666/conductgene-swarm
- [x] CI + Docker smoke workflows green
- [x] Release v0.2.1 with CHANGELOG
- [x] README with eval metrics, architecture, quick start
- [x] `./scripts/verify_all.sh` and `./scripts/qa_matrix.sh`
- [x] Pitch deck markdown: [pitch-deck.md](pitch-deck.md)
- [x] Portal submission folder with logo + 3 screenshots + demo WebM
- [x] [portal-copy.md](submission/portal-copy.md) for all text fields

## Manual (your action — ~30 min)

### 1. YouTube upload → Demo URL

1. Upload [conductgene-demo.webm](submission/conductgene-demo.webm) to YouTube (**Unlisted**)
2. Follow [youtube-upload.md](submission/youtube-upload.md)
3. Paste URL into [portal-copy.md](submission/portal-copy.md) and README

- [x] Video recorded (WebM in repo)
- [ ] Uploaded to YouTube (unlisted)
- [ ] URL in README and portal form

### 2. UCWS portal registration

1. Go to [evol.epicconnector.ai](https://evol.epicconnector.ai)
2. Copy fields from [portal-copy.md](submission/portal-copy.md)
3. Upload logo + 3 screenshots from `docs/submission/`

- [ ] Registration submitted
- [ ] Confirmation email received

### 3. Pitch deck PDF (optional for portal)

```bash
./scripts/export_pitch_deck.sh
```

- [ ] PDF or Google Slides link in Demo File Link field

## Pre-Demo Day rehearsal

- [ ] `./scripts/qa_matrix.sh` — 4/4 PASS locally
- [ ] Offline demo rehearsed (mock mode, no network)
- [ ] 5-minute pitch from [pitch-deck-outline.md](pitch-deck-outline.md)
- [ ] Ask 5+ people to vote (Community Vote 40%)

## Contacts

- Epic Connector: incubator@epicconnector.ai
- Event: [UCWS Singapore 2026 on Luma](https://luma.com/UCWS2026)
