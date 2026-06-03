# UCWS Portal — Copy-Paste Fields (Dual Track)

**One portal entry**, tracks **AGENT + APPLICATION**. Fill [evol.epicconnector.ai](https://evol.epicconnector.ai).

ConductGene demo: https://youtu.be/5wIBi-HkK9Y

---

## Tracks (checkboxes)

- [x] **AGENT**
- [x] **APPLICATION**
- [ ] Deep Research — **do not select** (requires MiroMind API; we do not use it)

---

## Project Name (max 100)

**Recommended** (both products visible to reviewers):

```
ConductGene Swarm & AttestRWA
```

Alternative (ConductGene-only title; AttestRWA only in Description):

```
ConductGene Swarm
```

---

## Tagline (max 200)

```
Dual-track UCWS submission: multi-agent conduct QA (AGENT) + RWA settlement attestation app (APPLICATION). Open source, reproducible demos.
```

Character count: ~115

---

## Description (max 2000)

```
UCWS Singapore 2026 — dual-track submission: AGENT + APPLICATION.
This submission does NOT use the MiroMind Deep Research API.

Two open-source projects, one compliance portfolio for regulated finance in SEA:

━━━ TRACK 1: AGENT — ConductGene Swarm ━━━
Multi-agent conduct QA with supervisor-approved Policy Genes. Prosecutor, Defender, and Arbiter agents review call transcripts with evidence citations. Human corrections become auditable, rollbackable institutional memory with held-out eval proof (16/16 scenarios, 100% citation coverage). Reproducible demo — no API key required.
• Repo: https://github.com/FUYOH666/conductgene-swarm
• Demo: https://youtu.be/5wIBi-HkK9Y
• Run: ./scripts/verify_all.sh

━━━ TRACK 2: APPLICATION — AttestRWA ━━━
Settlement Attestation Layer for RWA — on-chain compliance bridge for stablecoin real-world-asset settlements. EAS attestations on Base Sepolia + programmable escrow: USDC releases only when the attester validates developer feed, payee authority, and RAG-assisted evidence. Happy-path release and payee-mismatch reject demos included.
• Repo: https://github.com/FUYOH666/attestrwa
• Demo: https://youtube.com/shorts/BipB2qPzZz0
• Run: ./scripts/demo-mode.sh

Shared theme: accountable AI and compliance infrastructure — agents that collaborate and learn with proof (ConductGene), and applications that enforce verification before money moves (AttestRWA).

Author: Aleksandr Mordvinov · Open source (MIT / Apache-2.0)
```

Character count: ~1,464 / 2000

### ASCII-safe variant (paste if Unicode dividers break in the form)

```
UCWS Singapore 2026 — dual-track submission: AGENT + APPLICATION.
This submission does NOT use the MiroMind Deep Research API.

Two open-source projects, one compliance portfolio for regulated finance in SEA:

--- TRACK 1: AGENT — ConductGene Swarm ---
Multi-agent conduct QA with supervisor-approved Policy Genes. Prosecutor, Defender, and Arbiter agents review call transcripts with evidence citations. Human corrections become auditable, rollbackable institutional memory with held-out eval proof (16/16 scenarios, 100% citation coverage). Reproducible demo — no API key required.
• Repo: https://github.com/FUYOH666/conductgene-swarm
• Demo: https://youtu.be/5wIBi-HkK9Y
• Run: ./scripts/verify_all.sh

--- TRACK 2: APPLICATION — AttestRWA ---
Settlement Attestation Layer for RWA — on-chain compliance bridge for stablecoin real-world-asset settlements. EAS attestations on Base Sepolia + programmable escrow: USDC releases only when the attester validates developer feed, payee authority, and RAG-assisted evidence. Happy-path release and payee-mismatch reject demos included.
• Repo: https://github.com/FUYOH666/attestrwa
• Demo: https://youtube.com/shorts/BipB2qPzZz0
• Run: ./scripts/demo-mode.sh

Shared theme: accountable AI and compliance infrastructure — agents that collaborate and learn with proof (ConductGene), and applications that enforce verification before money moves (AttestRWA).

Author: Aleksandr Mordvinov · Open source (MIT / Apache-2.0)
```

---

## Field mapping (single-form limits)

| Portal field | Value | Notes |
|--------------|-------|-------|
| Tracks | AGENT + APPLICATION | Not Deep Research |
| Repo URL | `https://github.com/FUYOH666/conductgene-swarm` | Primary repo field |
| Demo URL | `https://youtu.be/5wIBi-HkK9Y` | Primary demo (ConductGene) |
| AttestRWA repo + demo | In Description only | Second GitHub / YouTube links in body |
| Logo + screenshots | ConductGene assets below | AttestRWA UI in attestrwa README |

---

## Demo URL (primary — ConductGene)

```
https://youtu.be/5wIBi-HkK9Y
```

AttestRWA demo (in Description only): `https://youtube.com/shorts/BipB2qPzZz0`

Upload guide: [youtube-upload.md](youtube-upload.md)

---

## Repo URL (primary — ConductGene)

```
https://github.com/FUYOH666/conductgene-swarm
```

AttestRWA: `https://github.com/FUYOH666/attestrwa` (in Description)

---

## Tech Stack (comma-separated, both projects)

```
Python, FastAPI, Streamlit, Pydantic, uv, pytest, multi-agent systems, Policy Genes, governance, audit trail, Solidity, Foundry, EAS, Base Sepolia, Next.js, RAG, Qdrant, stablecoin escrow, Docker
```

---

## Project Logo

Upload: [`logo-512.png`](logo-512.png) (512×512 PNG)

---

## Project Screenshots (up to 3)

1. [`screenshot-1-swarm.png`](screenshot-1-swarm.png) — transcript + evidence + analyze
2. [`screenshot-2-agents.png`](screenshot-2-agents.png) — Prosecutor / Defender / Arbiter tabs
3. [`screenshot-3-gene-learning.png`](screenshot-3-gene-learning.png) — Policy Gene + CASE-005 improvement

Generate with: `./scripts/capture_submission_assets.sh`

AttestRWA UI screenshots: see [attestrwa README](https://github.com/FUYOH666/attestrwa).

---

## Demo File Link (optional)

Google Slides or PDF from [`../pitch-deck.md`](../pitch-deck.md):

```
https://docs.google.com/presentation/d/YOUR_SLIDES_ID
```

Or export: `./scripts/export_pitch_deck.sh`

---

## LinkedIn URL (optional)

```
https://linkedin.com/in/YOUR_PROFILE
```

---

## Resubmit after rejection

If rejected for Deep Research track mismatch:

1. Tracks: **AGENT + APPLICATION** only (remove Deep Research)
2. Description: first lines must state dual-track + **no MiroMind API**
3. Save → **Resubmit for review**

Full checklist: [resubmit-checklist.md](resubmit-checklist.md)
