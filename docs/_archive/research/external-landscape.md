# External Landscape — Agent Ecosystem (June 2026)

Research for UCWS Singapore 2026 AGENT track: autonomous learning + collaboration.

---

## Top 15 Borrow Targets

| # | Repository | Stars (approx.) | What to reuse |
|---|------------|-----------------|---------------|
| 1 | [OpenHands/OpenHands](https://github.com/OpenHands/OpenHands) | 75K+ | Event-sourced agent SDK, sandboxed execution, production task loops |
| 2 | [bytedance/deer-flow](https://github.com/bytedance/deer-flow) | 70K+ | Long-horizon SuperAgent: sandboxes, memory, subagents |
| 3 | [crewAIInc/crewAI](https://github.com/crewAIInc/crewAI) | 52K+ | Role-based crews; fast demo scaffolding (avoid without domain) |
| 4 | [microsoft/autogen](https://github.com/microsoft/autogen) | 58K+ | Group chat orchestration, human-in-the-loop |
| 5 | [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) | 33K+ | Graph state machines, checkpointing, auditable workflows |
| 6 | [a2aproject/A2A](https://github.com/a2aproject/A2A) | 24K+ | Agent2Agent protocol — Agent Cards, federated tasks |
| 7 | [langchain-ai/deepagents](https://github.com/langchain-ai/deepagents) | 23K+ | Batteries-included agent harness |
| 8 | [rohitg00/agentmemory](https://github.com/rohitg00/agentmemory) | 20K+ | Persistent memory via MCP + REST |
| 9 | [SWE-agent/SWE-agent](https://github.com/SWE-agent/SWE-agent) | 19K+ | Minimal issue→fix loop; [mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent) for lean design |
| 10 | [lsdefine/GenericAgent](https://github.com/lsdefine/GenericAgent) | 12K+ | **Skill crystallization** — successful runs → reusable skills |
| 11 | [MemTensor/MemOS](https://github.com/MemTensor/MemOS) | 9K+ | Layered memory L1 traces → L3 world model |
| 12 | [EvoMap/evolver](https://github.com/EvoMap/evolver) | 7K+ | **Auditable evolution** — Genes/Capsules/Events (GEP) |
| 13 | [HKUDS/ClawTeam](https://github.com/HKUDS/ClawTeam) | 5K+ | Shell-native multi-agent coordination |
| 14 | [HKUDS/OpenSpace](https://github.com/HKUDS/OpenSpace) | 6K+ | Self-evolving low-cost agent community |
| 15 | [modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers) | 86K+ | MCP server reference implementations |

**ConductGene Swarm borrow decisions:**

- **GenericAgent + Evolver** → PolicyGene crystallization with provenance
- **LangGraph concepts** → explicit agent handoff (not full dependency for 48h MVP)
- **A2A** → Agent Card in `docs/a2a-agent-card.json` (Demo Day polish)
- **ConductLens (own)** → evidence-first RAG, not reinventing retrieval

---

## Anti-Patterns (Do Not Build)

1. **CEO + Researcher + Writer CrewAI clone** — no domain, no learning metrics
2. **RAG chatbot labeled "agent"** — upload PDF, ask questions, no tool use or collaboration
3. **Multi-agent debate theater** — infinite loops, no termination, no measurable outcome
4. **Unbounded autonomous agent** — full shell/filesystem without audit log or kill switch
5. **Personal assistant with amnesia** — no persistent learning or skill reuse

---

## SEA Trends (June 2026 — Judge-Relevant)

### 1. Auditable self-evolution

Judges expect **evidence of learning**, not claims:

- Before/after accuracy on held-out cases
- Provenance for every learned rule (PolicyGene)
- Rollback capability

References: GenericAgent skill trees, Evolver GEP protocol.

### 2. Governance-by-design (Singapore edge)

[IMDA Model AI Governance Framework for Agentic AI v1.5](https://www.imda.gov.sg/-/media/imda/files/about/emerging-tech-and-research/artificial-intelligence/mgf-for-agentic-ai.pdf) (May 2026):

- Risk bounding and scoped tool access
- Semantic human approval gates
- End-user transparency

Aligning demo with IMDA MGF signals maturity in SEA market.

### 3. Skills-over-MCP federation

Ecosystem convergence:

- Agent Skills (`SKILL.md`) via MCP ([SEP-2640](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2640))
- A2A for cross-framework agent tasks
- Portable skills that survive runtime changes

Relevant for Idea C (Skill Federation Protocol); ConductGene uses gene→skill export as post-MVP.

---

## Singapore Application Angles

| Domain | Signal | Agent opportunity |
|--------|--------|-------------------|
| Fintech / conduct | MAS market conduct, collections QA | ConductGene Swarm (selected) |
| Public sector | GovTech Agentic AI Primer | Policy analysis with human escalation |
| Healthcare | Healthier SG pilots | Care-plan multi-agent with clinician veto |
| Trade / logistics | SG trade hub | TradePath Collective (Idea B) |
| SME adoption | High agent deployment intent | Low-cost governed agents |

---

## Hackathon Context

- **Event:** [UCWS Singapore 2026](https://luma.com/UCWS2026)
- **Online phase:** May 1 – June 3, 2026
- **Demo Day:** June 13, 2026, Singapore
- **Top 20:** Round-trip airfare to present
- **Format:** Open-source, ruleless global hackathon
- **AGENT track:** Autonomous learning + collaboration

---

## Recommended Stack for 48h MVP

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Orchestration | Custom swarm (3 agents) | Faster than LangGraph setup; clear demo narrative |
| Retrieval | In-memory mock + optional BGE/Qdrant | CI-friendly; live mode via env |
| Learning | PolicyGene JSONL store | Evolver-inspired, auditable |
| API | FastAPI + pydantic-settings | Matches portfolio conventions |
| Tests | pytest + mock mode | Happy path + abstain + evolution |
| Governance | `docs/governance.md` | IMDA alignment doc for judges |
