# ConductGene Swarm — Product Spec

**One-liner:** ConductGene turns every supervisor correction into an auditable, rollbackable policy pattern that improves future AI conduct reviews.

**Subtitle:** Human-approved AI QA that remembers supervisor corrections safely.

## Problem

Regulated QA teams (collections, fintech, insurance) repeat the same supervisor corrections. Static rules miss nuance; pure LLM QA hallucinates policy.

## Solution

Three evidence-grounded agents review each transcript. When a supervisor approves a correction, the system stores it as a **Policy Gene** — institutional memory with provenance, eval score, and rollback.

| Agent | Role |
|-------|------|
| Prosecutor | Flag potential violations (with citations) |
| Defender | Surface mitigating compliance signals |
| Arbiter | Synthesize recommendation (not final regulatory decision) |

## Demo cycle (8 steps)

1. Transcript uploaded
2. Evidence retrieved from policy KB
3. Prosecutor flags issues with citations
4. Defender finds mitigating context
5. Arbiter delivers verdict
6. Supervisor overrides / approves correction
7. Policy Gene stored (supervisor-approved)
8. Similar transcript — gene applied, eval improves

## Governance (IMDA Agentic AI MGF v1.5)

- Scoped agents (read-only, no shell/tools)
- Human accountability (supervisor approval for genes)
- Traceability (chunk_ids, case audit trail)
- Abstain on weak evidence
- Rollback any active gene

## Out of scope (MVP)

- Autonomous rule mutation without supervisor
- Live LLM as demo dependency (mock mode default)
- On-chain attestation

Built on prior RAG, citation, and evaluation patterns from my portfolio.
