# Repository Inventory — FUYOH666

Audit date: 2026-06-01  
Purpose: UCWS Singapore 2026 (AGENT track) — reuse matrix for hackathon build.

## Summary

| Tier | Count | Hackathon value |
|------|-------|-----------------|
| Public OSS | 19+ | Demo-ready modules, CI patterns, licenses |
| Private high-value | 15+ | Domain patterns, synthetic data templates (no secrets in OSS) |
| Prior hackathons | 3 | ConductLens, AttestRWA, GPThub archive |

**Selected build path:** ConductGene Swarm — extracts ConductLens pipeline + AttestRWA audit patterns + Plague evolution log.

---

## Reuse Matrix

| Module | Source repo | License | Reuse as | Extract effort | Demo value |
|--------|-------------|---------|----------|----------------|------------|
| Evidence-first RAG pipeline | SCB_hackaton (ConductLens) | MIT (local) | Core analyze + abstain + citations | Low — patterns ported | ★★★★★ |
| Synthetic conduct KB | SCB_hackaton `data/synthetic/kb/` | MIT | Demo dataset | Trivial — copy | ★★★★★ |
| Compliance DSL + attestation | attestrwa / bankable | MIT | Gene provenance / audit trail | Medium — concept only for MVP | ★★★★ |
| Self-evolution log | Plague-InGG `evolution/log.jsonl` | MIT | PolicyGene store pattern | Low | ★★★★★ |
| BGE embed + rerank clients | Services-BGE + ConductLens | MIT | Optional live retrieval | Low — httpx clients | ★★★★ |
| Model routing + traces | GPT-hub v4 | MIT | Future: cheap/strong route | Medium | ★★★ |
| Cursor skills sync | cursor-skills-config (private) | Private | Dev velocity, remote AI mesh | N/A in OSS | ★★★ |
| Hybrid customs search | DT-xml (private) | Private | TradePath idea only | High | ★★★★ |
| TN VED classification | TN-ved-AI (private) | Private | TradePath idea only | High | ★★★★ |
| Multi-channel agent | hermes-agent, CoPaw, deer-flow | Apache/MIT forks | Runtime alternatives | High | ★★★ |
| Call analytics pipeline | Scanovich.ai-audio-call | MIT | Voice-in conduct QA (post-MVP) | Medium | ★★★★ |
| Voice-to-text client | VoiceToText | MIT | ASR integration | Low | ★★★ |
| MCP reference | Cleaner-OS | MIT | Skill Federation idea (Idea C) | Medium | ★★★ |
| Real estate multi-tenant agent | realestate-agent-platform | MIT | Tenant isolation patterns | Medium | ★★★ |
| LocalScript trust loop | LocalScript | MIT | Sandboxed tool execution | Medium | ★★★ |

---

## Public Repositories (GitHub)

| Repo | Language | Maturity | Hackathon relevance |
|------|----------|----------|---------------------|
| [attestrwa](https://github.com/FUYOH666/attestrwa) | Python/Solidity | High — SEA Blockchain Week 2026 | Compliance attestation, audit trail |
| [Plague-InGG](https://github.com/FUYOH666/Plague-InGG) | Python | Medium — experimental | Evolution kernel, skill crystallization |
| [GPT-hub](https://github.com/FUYOH666/GPT-hub) | Python/Docker | Medium–High | Model routing, hackathon archive |
| [Cleaner-OS](https://github.com/FUYOH666/Cleaner-OS) | Python | High | MCP server pattern |
| [VoiceToText](https://github.com/FUYOH666/VoiceToText) | Python | High | ASR client |
| [Services-BGE](https://github.com/FUYOH666/Services-BGE) | Python | High | Embedding/rerank microservices |
| [hermes-agent](https://github.com/FUYOH666/hermes-agent) | Python | High (fork) | Full agent harness |
| [CoPaw](https://github.com/FUYOH666/CoPaw) | Python | High (fork) | Multi-channel assistant |
| [deer-flow](https://github.com/FUYOH666/deer-flow) | Python | High (fork) | SuperAgent harness |
| [Scanovich.ai-audio-call](https://github.com/FUYOH666/Scanovich.ai-audio-call) | Python | Medium–High | Call analytics |
| [realestate-agent-platform](https://github.com/FUYOH666/realestate-agent-platform) | Python | Medium | Multi-tenant agents |
| [ai-agent-tts](https://github.com/FUYOH666/ai-agent-tts) | Python | Medium | Voice agent FSM |
| [LocalScript](https://github.com/FUYOH666/LocalScript) | Python | Medium | Local trust loop |
| [retail-crm-analytics-demo](https://github.com/FUYOH666/retail-crm-analytics-demo) | TypeScript | Medium | Full-stack demo pattern |
| [linux-defender](https://github.com/FUYOH666/linux-defender) | Python | Medium | Security audit |

---

## Private Repositories (patterns only — not committed to OSS)

| Repo | Domain | Extract for hackathon |
|------|--------|----------------------|
| DT-xml | EAEU customs semantic search | Hybrid retrieval architecture (Idea B) |
| TN-ved-AI | HS code classification | Classifier agent pattern (Idea B) |
| cursor-skills-config | Local AI mesh + skills | `.env.example` placeholders, skill layout |
| YM-AI | Marketplace analytics | Structured report agents |
| Books-RAS | Telegram RAG | RAG + bot pattern |
| positioning-hub | GTM strategy | million-dollar-bets ranking |
| excel-customs-eaeu | Customs Excel automation | Synthetic workflow (Idea B) |

---

## Prior Hackathon Assets

### SCB_hackaton → ConductLens (primary extract)

- **Pipeline:** segment → embed → Qdrant → rerank → grounded LLM → citations + abstain
- **Tests:** happy path, low-score abstain, citation validation
- **Synthetic KB:** `fair_treatment_en.md`, `disclosures_en.md`, `disclosures_th_mix.md`

### bankable / attestrwa (SEA Blockchain Week 2026)

- Compliance DSL evaluator
- EAS attestation for audit trail (optional post-MVP on-chain gene commits)

### GPThub archive

- `docs/archive/hackathon/` — pitch templates, team sync, demo scripts

---

## Gaps (addressed in ConductGene Swarm)

| Gap | Solution in this repo |
|-----|----------------------|
| No multi-agent orchestration | Prosecutor ↔ Defender ↔ Arbiter swarm |
| No evolution proof | PolicyGene store + before/after metrics |
| No unified eval harness | `tests/test_evolution.py` + gene eval scores |
| No governance narrative | `docs/governance.md` (IMDA MGF alignment) |

---

## Extraction Policy (OSS safety)

- No Tailscale IPs, API keys, or private customer data in commits
- Synthetic KB only from SCB_hackaton
- Private repo logic reimplemented as patterns, not copied wholesale
- All secrets via `.env` (gitignored); `.env.example` uses placeholders
