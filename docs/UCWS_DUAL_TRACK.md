# UCWS Singapore 2026 — Dual Track (One Portal Entry)

Single submission on [evol.epicconnector.ai](https://evol.epicconnector.ai) covering **two tracks** and **two repositories**.

## Model

| Track | Project | Repository | Demo |
|-------|---------|------------|------|
| **AGENT** | ConductGene Swarm | [conductgene-swarm](https://github.com/FUYOH666/conductgene-swarm) | [youtu.be/5wIBi-HkK9Y](https://youtu.be/5wIBi-HkK9Y) — primary **Demo URL** on portal |
| **APPLICATION** | AttestRWA | [attestrwa](https://github.com/FUYOH666/attestrwa) | [YouTube Shorts](https://youtube.com/shorts/BipB2qPzZz0) — link in portal **Description** |

**Not submitted:** Deep Research track (requires [MiroMind Responses API](https://platform.miromind.ai/docs/responses-api); neither project uses it).

## Shared narrative

Both projects address **governed compliance** in regulated finance for SEA:

- **ConductGene** — multi-agent QA that learns from supervisor corrections with eval proof (Policy Genes).
- **AttestRWA** — application that gates stablecoin settlement on verifiable EAS attestations and escrow rules.

Same author, different layers: agent collaboration vs end-user settlement application.

## Portal field limits

The portal accepts **one** repo URL and **one** demo URL per project entry. We use:

- **Repo field** → ConductGene (AGENT primary; rejection was about this project)
- **Demo field** → ConductGene video
- **Description** → full text for both tracks with AttestRWA repo + demo links

Copy-paste text: [submission/portal-copy.md](submission/portal-copy.md)

## Quick verify (for judges)

**ConductGene (AGENT):**

```bash
git clone https://github.com/FUYOH666/conductgene-swarm.git
cd conductgene-swarm && uv sync --extra dev --extra ui
./scripts/verify_all.sh
```

**AttestRWA (APPLICATION):**

```bash
git clone https://github.com/FUYOH666/attestrwa.git
cd attestrwa && ./scripts/demo-mode.sh
```

## Related docs

- [UCWS registration steps](UCWS_REGISTRATION.md)
- [Submission checklist](SUBMISSION.md)
- [Resubmit checklist](submission/resubmit-checklist.md)
- Event: [UCWS Singapore 2026 on Luma](https://luma.com/UCWS2026)
