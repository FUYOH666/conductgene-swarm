# Contributing

## Setup

```bash
git clone https://github.com/FUYOH666/conductgene-swarm.git
cd conductgene-swarm
uv sync --extra dev
./scripts/verify_all.sh
```

`verify_all.sh` is what CI runs: ruff, mypy `--strict`, pytest with a coverage
gate, and the demo. It needs no network and no model.

## Ground rules

- **No number without a script.** Any figure in the README or docs must be
  reproducible from a command in this repository, with the data it ran on.
- **Pin judge errors, not just rates.** If you change a judge or a pack, update
  the exact list of disagreements in the tests; an aggregate can hide a swap.
- **Offline by default.** Tests and the demo must not call a model. Use the
  heuristic judge or a recorded cassette.
- **Packs document their labels.** Who labelled, against which policy, what changed.

## Pull requests

- [ ] `./scripts/verify_all.sh` passes
- [ ] New behaviour has a test that would fail without it
- [ ] CHANGELOG updated
- [ ] No secrets, `.env` files, addresses or personal data
