# ConductGene Swarm — Pitch Deck (10 slides)

Copy into Google Slides / Keynote. See also [pitch-deck-outline.md](pitch-deck-outline.md).

---

## Slide 1 — Title

**ConductGene Swarm**  
Supervisor-approved institutional memory for AI conduct QA

Aleksandr Mordvinov · UCWS AGENT track · MIT · github.com/FUYOH666/conductgene-swarm

---

## Slide 2 — Problem

- Regulated QA teams (fintech, collections, insurance) need AI at scale
- Static rules miss nuance; solo LLMs hallucinate policy
- Supervisor corrections are lost — same mistakes repeat
- IMDA Agentic AI MGF v1.5 (May 2026) requires accountability

---

## Slide 3 — Insight

1. **Collaboration** beats single chatbot (Prosecutor vs Defender debate)
2. **Learning with proof** beats magic (held-out eval before/after gene)
3. **Governance** is a product feature (approval, abstain, rollback, audit)

---

## Slide 4 — Solution

```
Transcript → Evidence → Swarm → Supervisor → Policy Gene → Better re-review
```

- Multi-agent swarm with evidence citations
- Abstain when evidence is insufficient (CASE-007)
- Supervisor approves → Policy Gene stored with eval delta
- Rollback + full audit export

---

## Slide 5 — Architecture

![Architecture](assets/architecture.png)

| Mode | Purpose |
|------|---------|
| **Deterministic demo** | CI, judges, offline Demo Day |
| **Live** | OpenAI-compatible LLM hooks (roadmap) |

Modules: agents, retrieval, pipeline, genes, audit, eval harness, API, Streamlit UI

---

## Slide 6 — Live Demo

**CASE-002** (coercive soft tone) → supervisor approves gene  
**CASE-005** (held-out) → `escalation_offered` improves needs_review → pass

```bash
./scripts/demo.sh
uv run conductgene-ui
```

---

## Slide 7 — Proof

| Metric | Result |
|--------|--------|
| Synthetic scenarios | 16/16 pass |
| Citation coverage | 100% |
| Gene learning | CASE-002 → CASE-005 improved |
| CI | `./scripts/verify_all.sh` green |

---

## Slide 8 — Governance (IMDA MGF)

- Human-in-the-loop approval for every Policy Gene
- Append-only case + gene audit trails
- Rollback operator persona (CASE-016)
- Abstain path when retrieval confidence is low

---

## Slide 9 — Open Source & Reproducibility

- MIT license
- Mock mode — no Tailscale / LLM required for demo
- Docker one-liner: `docker compose up`
- A2A-inspired agent card published

---

## Slide 10 — Ask & Roadmap

**Ask:** Top 20 → Demo Day Singapore · QA/fintech pilot partners

**Roadmap:**
- Live LLM mode (instruct gateway)
- BGE + Qdrant retrieval
- Policy Gene export as SKILL.md

**Repo:** github.com/FUYOH666/conductgene-swarm
