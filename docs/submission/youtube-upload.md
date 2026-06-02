# YouTube Demo Upload Checklist

## Before recording

**Option A — use pre-recorded WebM (fastest):**

Upload [`conductgene-demo.webm`](conductgene-demo.webm) directly to YouTube.

**Option B — re-record:**

```bash
./scripts/capture_submission_assets.sh --with-video
```

**Option C — manual screen capture:**

```bash
uv run conductgene-ui   # http://localhost:8501
```

Follow [demo-video-guide.md](../demo-video-guide.md). Optional end card: [video-end-card.png](video-end-card.png).

## Recording (Mac)

QuickTime → File → New Screen Recording → select window → Record.

## Upload settings

| Field | Value |
|-------|--------|
| Title | `ConductGene Swarm — UCWS 2026 Demo` |
| Visibility | **Unlisted** |
| Description | See below |

### Description template

```
ConductGene Swarm — supervisor-approved institutional memory for AI conduct QA.

Multi-agent conduct review (Prosecutor, Defender, Arbiter) with evidence citations and Policy Genes. Deterministic demo mode — no API key required.

GitHub: https://github.com/FUYOH666/conductgene-swarm
UCWS Singapore 2026 AGENT track

Clone and verify:
git clone https://github.com/FUYOH666/conductgene-swarm.git
./scripts/verify_all.sh
```

## After upload

1. Copy watch URL: `https://www.youtube.com/watch?v=XXXXXXXX`
2. Update [portal-copy.md](portal-copy.md) Demo URL
3. Update README «Demo video» section
4. Test link in incognito window
5. Submit portal form

## Portal Demo URL field

Paste the full YouTube watch URL (not youtu.be unless form accepts it).
