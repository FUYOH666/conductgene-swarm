# 90-Second Demo Video Guide

Record a screen capture following this script. Upload unlisted to YouTube/Loom and add the link to README.

## Setup

```bash
uv sync --extra dev --extra ui
uv run conductgene-ui
```

Open browser at `http://localhost:8501`.

## Shot list (90 seconds)

| Time | Action | Voiceover |
|------|--------|-----------|
| 0:00 | Title card or Streamlit header | "ConductGene Swarm — supervisor-approved institutional memory for AI conduct QA." |
| 0:10 | Select CASE-002, click Run swarm analyze | "Multi-agent swarm reviews a collections call with evidence citations." |
| 0:25 | Show Evidence + Prosecutor/Defender tabs | "Prosecutor and Defender disagree on coercive tone — Arbiter synthesizes." |
| 0:35 | Supervisor form: approve gene, trigger `repayment` | "Supervisor approves a correction — held-out eval runs before we store the gene." |
| 0:50 | Show success with eval delta | "Policy Gene stored with measurable held-out improvement." |
| 0:55 | Select CASE-005, Run analyze | "Similar held-out case now passes escalation — gene applied." |
| 1:05 | Open Gene audit events expander | "Every learn and rollback is auditable." |
| 1:15 | Terminal: `./scripts/verify_all.sh` (optional B-roll) | "Sixteen scenarios, full CI verification — reproducible without external LLM." |
| 1:25 | End card: GitHub URL | "Open source — github.com/FUYOH666/conductgene-swarm" |

## Alternative: terminal-only

```bash
./scripts/demo.sh
```

Uses CASE-002 → gene learn → CASE-005 with printed JSON output.

## Recording tips

- Use **Deterministic Demo Mode** banner visible (mock mode default)
- Zoom browser to 125% for readability
- Keep mouse movements slow; pause 2s on key results
