# Pitch Deck Outline — Demo Day June 13, 2026

**Product:** ConductGene Swarm  
**Event:** UCWS Singapore 2026  
**Duration:** 5–7 min pitch + 3 min demo + Q&A

---

## Slide 1 — Title

- ConductGene Swarm
- Supervisor-approved institutional memory for AI conduct QA
- Aleksandr Mordvinov · UCWS AGENT track · Open source

## Slide 2 — Problem

- Regulated industries (fintech, collections, insurance) scale QA with AI
- Static rules miss nuance; pure LLM hallucinates policy
- Human corrections are lost — supervisors repeat themselves
- IMDA Agentic AI MGF v1.5 (May 2026) demands accountability

## Slide 3 — Insight

- Agents must **collaborate** (not solo chatbot)
- Agents must **learn** with **proof** (not magic)
- Governance is a **feature**, not paperwork

## Slide 4 — Solution

- Prosecutor ↔ Defender ↔ Arbiter swarm
- Shared evidence pool with citations + abstain
- Human override → **Policy Gene** crystallization
- Before/after held-out eval metrics, rollback, audit log

## Slide 5 — Architecture

- Diagram from `docs/assets/architecture.mmd`
- Deterministic demo mode (CI) vs live mode (LLM hooks)

## Slide 6 — Live Demo

- 3-min script from `docs/demo-script.md`
- Show gene learn + re-analyze CASE-005

## Slide 7 — Traction / Portfolio

- Prior RAG + citation + eval patterns from portfolio
- 16/16 synthetic eval, 100% citation coverage
- Reproducible `./scripts/verify_all.sh`

## Slide 8 — Market

- SEA fintech conduct QA
- Call center QA ($XB market)
- Expand: insurance, healthcare

## Slide 9 — Business model

- SaaS per seat / per analyzed hour
- On-prem for regulated enterprises
- Policy Gene export as SKILL.md (roadmap)

## Slide 10 — Ask

- Top 20 → Demo Day Singapore
- Partners: collections agencies, fintech QA teams
- Open source: github.com/FUYOH666/conductgene-swarm

---

## Demo video checklist (90s–3 min)

- [ ] Record Streamlit: CASE-002 → approve gene → CASE-005
- [ ] Record terminal: `./scripts/demo.sh`
- [ ] Voiceover using `docs/demo-video-guide.md`
- [ ] Upload to YouTube (unlisted) + link in README

## Q&A prep

| Question | Answer |
|----------|--------|
| How is this different from CrewAI? | Domain + evidence grounding + auditable genes + IMDA alignment |
| Does it work without cloud LLM? | Yes — deterministic demo mode; live hooks via OpenAI-compatible gateway |
| Can genes go wrong? | Yes — supervisor approval + rollback + audit events |
| Is eval real? | Held-out CASE-005 before/after gene; full 16-case suite in CI |
