# UCWS Submission Assets

Assets for the hackathon portal form — **one entry**, tracks **AGENT + APPLICATION**.

Master copy: [portal-copy.md](portal-copy.md) · Resubmit: [resubmit-checklist.md](resubmit-checklist.md) · Overview: [../UCWS_DUAL_TRACK.md](../UCWS_DUAL_TRACK.md)

## Quick workflow

```bash
uv sync --extra dev --extra ui --extra retrieval --extra live --extra submission
./scripts/capture_submission_assets.sh --with-video --profile live   # Singapore path
# Upload conductgene-demo.webm to YouTube → paste URL into portal-copy.md
# AttestRWA demo already live: https://youtube.com/shorts/BipB2qPzZz0 (link in Description only)
```

## Files

| File | Purpose |
|------|---------|
| [portal-copy.md](portal-copy.md) | Unified text fields (both tracks) |
| [resubmit-checklist.md](resubmit-checklist.md) | After Deep Research rejection |
| [logo-512.png](logo-512.png) | Project logo (512×512) |
| [screenshot-1-swarm.png](screenshot-1-swarm.png) | Portal screenshot #1 |
| [screenshot-2-agents.png](screenshot-2-agents.png) | Portal screenshot #2 |
| [screenshot-3-gene-learning.png](screenshot-3-gene-learning.png) | Portal screenshot #3 |
| [youtube-upload.md](youtube-upload.md) | ConductGene YouTube checklist |
| [video-end-card.png](video-end-card.png) | Optional end card for demo video |

AttestRWA screenshots: [attestrwa repo](https://github.com/FUYOH666/attestrwa).

## Portal requirements

- Logo: square, max 5MB, JPEG/PNG/WebP/GIF
- Screenshots: up to 3, 200–4096px, max 5MB each
- Tracks: AGENT + APPLICATION (not Deep Research without MiroMind API)
