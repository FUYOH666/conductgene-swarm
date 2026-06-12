# 90-Second Demo Script

**Product:** ConductGene Swarm — supervisor-approved conduct QA

## Setup

```bash
uv sync --extra dev --extra ui
uv run conductgene-ui
```

## Script (90 sec)

**0:00 — Hook (10s)**

> Regulated QA teams repeat the same supervisor corrections every week. ConductGene turns each approved correction into auditable institutional memory — not autonomous rule mutation.

**0:10 — Transcript (15s)**

Select **CASE-002** (coercive soft tone):

> Agent: This is ABC Collections. If you don't pay today, this may create serious consequences for your account. I can also connect you with a supervisor to discuss a repayment path.

Show: Prosecutor flags coercive tone as **needs_review**. Defender notes repayment path + supervisor offer.

**0:25 — Swarm (20s)**

Show 3 agent tabs + evidence citations. Arbiter: **needs_review** on threat tone, **pass** on escalation.

**0:45 — Supervisor override (20s)**

Supervisor approves: escalation is sufficient; downgrade threat to **needs_review** with coaching note.

Click **Approve Policy Gene** → GENE stored with provenance + eval 0.6 → 0.8.

**1:05 — Second transcript (15s)**

Load **CASE-005** (similar call). Gene auto-applies. Eval metrics improve. Show rollback button.

**1:20 — Close (10s)**

> Human-approved. Evidence-grounded. Rollback-ready. ConductGene Swarm.

## Primary demo pair

| Case | Role |
|------|------|
| CASE-002 | Learn gene from supervisor correction |
| CASE-005 | Held-out similar case — gene improves result |

## Backup (terminal-only)

```bash
./scripts/demo.sh
```

Mock mode — no live LLM required.

## Recording a demo video

Use any screen recorder over `conductgene-ui` following the script above; the
deterministic mock mode makes every take reproducible. For a live-LLM take,
start LM Studio and run with `CONDUCTGENE_MODE=live CONDUCTGENE_LLM_PROVIDER=lmstudio`.
