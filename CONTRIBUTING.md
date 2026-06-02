# Contributing to ConductGene Swarm

Thank you for your interest in contributing. This project is built for the UCWS Singapore 2026 AGENT track and welcomes improvements to governance, eval coverage, and agent collaboration.

## Development setup

```bash
git clone https://github.com/FUYOH666/conductgene-swarm.git
cd conductgene-swarm
cp .env.example .env
uv sync --extra dev --extra ui
```

## Before submitting a PR

1. Run the full verification gate:

   ```bash
   ./scripts/verify_all.sh
   ```

2. For broader QA (optional):

   ```bash
   ./scripts/qa_matrix.sh
   ```

3. Update [`CHANGELOG.md`](CHANGELOG.md) under `[Unreleased]` or the current version section.

4. Keep **mock mode** as the default — demos and CI must not depend on external LLM services.

## Code conventions

- Python 3.12+, managed with **uv** (not pip)
- Structured logging via `conductgene.logutil` — no bare `print` in library code
- Pydantic schemas in `src/conductgene/schemas.py`
- Positioning: **supervisor-approved institutional memory** — avoid "autonomous self-evolution" in public-facing copy

## Pull request checklist

- [ ] `./scripts/verify_all.sh` passes locally
- [ ] New behavior has pytest coverage where meaningful
- [ ] CHANGELOG updated
- [ ] No secrets, IPs, or `.env` files committed

## Questions

Open a [Discussion](https://github.com/FUYOH666/conductgene-swarm/discussions) or an issue with the `question` label.
