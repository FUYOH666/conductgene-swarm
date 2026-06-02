# Governance — IMDA Agentic AI MGF v1.5

Reference: [IMDA Model AI Governance Framework for Agentic AI v1.5](https://www.imda.gov.sg/-/media/imda/files/about/emerging-tech-and-research/artificial-intelligence/mgf-for-agentic-ai.pdf) (May 2026)

ConductGene implements governance-by-design for regulated conduct QA.

| MGF dimension | ConductGene control |
|---------------|---------------------|
| **Assess & bound risks** | Read-only agents; no shell/tools; abstain on weak evidence |
| **Human accountability** | Policy Genes require supervisor approval; agents recommend, humans decide |
| **Technical controls** | Citations (chunk_ids), case audit trail, eval scores, rollback |
| **End-user responsibility** | Coaching tips; clear abstain reasons; exportable audit reports |

## Key principles

1. **Not autonomous rule mutation** — supervisors approve reusable patterns
2. **Multi-agent specialization** — Prosecutor / Defender / Arbiter reduce single-model bias
3. **Traceability** — every verdict links to evidence chunks and case_id
4. **Rollback** — any active gene can be deactivated without data loss

## Pitch language

**Use:** supervisor-approved institutional memory, auditable Policy Gene, rollback-ready

**Avoid:** self-evolving without control, AI rewrites regulation
