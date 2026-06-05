# 90-Second Demo Video Guide

Record a screen capture following this script. Upload unlisted to YouTube/Loom and add the link to README.

## Setup

**Automated (recommended):**

```bash
uv sync --extra dev --extra ui --extra retrieval --extra live --extra submission
uv run python scripts/discover_services.py
uv run python scripts/ingest_qdrant.py --rebuild
./scripts/capture_submission_assets.sh --with-video --profile live
```

Output: `docs/submission/conductgene-demo.webm` + 3 portal screenshots.

**Manual:**

```bash
uv sync --extra dev --extra ui
CONDUCTGENE_MODE=live CONDUCTGENE_LLM_PROVIDER=lmstudio CONDUCTGENE_RETRIEVAL_MODE=qdrant_rerank uv run conductgene-ui
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

## Live LM Studio shot list (Singapore primary)

| Time | Action | Voiceover |
|------|--------|-----------|
| 0:00 | Model Jury sidebar: live / lmstudio / qdrant_rerank | "Offline live stack — local LLM and vector retrieval." |
| 0:10 | CASE-002 analyze | "Evidence from BGE rerank over Qdrant policy KB." |
| 0:40 | Agent swarm tabs | "Prosecutor and Defender with structured JSON opinions." |
| 1:00 | Approve Policy Gene | "Supervisor correction with held-out eval gate." |
| 1:30 | CASE-005 held-out | "Gene applied — escalation passes on similar case." |
| 2:00 | Policy Genes + audit | "Auditable institutional memory." |

## Recording tips

- **Live Mode** banner + Model Jury visible for Singapore demo; use mock profile for deterministic fallback
- Zoom browser to 125% for readability
- Keep mouse movements slow; pause 2s on key results
