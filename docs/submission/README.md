# UCWS Submission Assets

Assets for the hackathon portal form.

## Quick workflow (~2 hours)

```bash
uv sync --extra dev --extra ui --extra submission
./scripts/capture_submission_assets.sh   # logo check + 3 screenshots
# Record video manually (see youtube-upload.md), then:
# Paste YouTube URL into portal-copy.md and README
```

## Files

| File | Purpose |
|------|---------|
| [portal-copy.md](portal-copy.md) | All text fields for the form |
| [logo-512.png](logo-512.png) | Project logo (512×512) |
| [screenshot-1-swarm.png](screenshot-1-swarm.png) | Portal screenshot #1 |
| [screenshot-2-agents.png](screenshot-2-agents.png) | Portal screenshot #2 |
| [screenshot-3-gene-learning.png](screenshot-3-gene-learning.png) | Portal screenshot #3 |
| [youtube-upload.md](youtube-upload.md) | YouTube upload checklist |
| [video-end-card.png](video-end-card.png) | Optional end card for demo video |

## Manual screenshot fallback (Mac)

1. `uv run conductgene-ui` → http://localhost:8501
2. Browser zoom 125%
3. Follow shot list in [../demo-video-guide.md](../demo-video-guide.md)
4. Cmd+Shift+4 → window capture → save as `screenshot-N-*.png` here

## Portal requirements

- Logo: square, max 5MB, JPEG/PNG/WebP/GIF
- Screenshots: up to 3, 200–4096px, max 5MB each
