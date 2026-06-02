# Idea Selection — UCWS Singapore 2026

**Date:** 2026-06-01  
**Decision:** **ConductGene Swarm** (Idea A)

---

## Scoring matrix

| Criterion | A ConductGene | B TradePath | C SFP |
|-----------|:-------------:|:-----------:|:-----:|
| Demo impact 48h | ★★★★ | ★★★ | ★★★★ |
| Uniqueness | ★★★★★ | ★★★★ | ★★★★★ |
| Your expertise | ★★★★ | ★★★★★ | ★★★★★ |
| SEA relevance | ★★★★★ | ★★★★ | ★★★ |
| Open-source clarity | ★★★★ | ★★★ | ★★★★★ |
| **Weighted total** | **23** | **19** | **21** |

---

## Rationale

1. **Demo Day in Singapore (June 13)** — IMDA MGF governance narrative + conduct QA is immediately legible to SEA judges and VCs
2. **48h skeleton deadline (June 3)** — ConductLens pipeline already exists locally; porting patterns is low-risk
3. **Visible learning loop** — PolicyGene crystallization satisfies AGENT track "autonomous learning" with measurable before/after
4. **Multi-agent collaboration** — Prosecutor ↔ Defender ↔ Arbiter is clearer than four customs agents for a 3-minute demo
5. **Portfolio moat** — builds on shipped SCB_hackaton + attestrwa, not a generic framework wrapper

---

## Deferred ideas (post-hackathon)

| Idea | When to pursue |
|------|----------------|
| **TradePath Collective** | Product line #1 per million-dollar-bets; reuse PolicyGene engine as TradeSkill |
| **Skill Federation Protocol** | Export PolicyGenes as SKILL.md; hybrid narrative for Demo Day polish |

---

## Implementation name

- **Repo:** `conductgene-swarm` (package: `conductgene`)
- **Workspace:** `evol hackaton/`
- **Public GitHub:** to be created as `FUYOH666/conductgene-swarm`

---

## Success criteria (June 3)

- [ ] Open-source repo with MIT license, CI green
- [ ] `/healthz` + swarm analyze API
- [ ] 3 agents collaborate on synthetic transcript
- [ ] One PolicyGene created from human correction
- [ ] `scripts/demo.sh` runs end-to-end in mock mode
- [ ] `docs/demo-script.md` for 3-minute pitch

## Success criteria (June 13)

- [ ] Demo video (2–3 min)
- [ ] Pitch deck
- [ ] Evolution metrics in README
- [ ] A2A Agent Card (optional)
- [ ] Live BGE/Qdrant mode documented
