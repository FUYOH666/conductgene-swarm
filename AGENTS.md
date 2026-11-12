# Notes for coding agents (and people)

- **One gate:** `./scripts/verify_all.sh` must pass. It runs ruff (lint and
  format), mypy `--strict`, pytest with a coverage floor, and the demo. Run it
  before you hand anything back.
- **Offline only in tests.** No test may call a network service or a model. Use
  the heuristic judge or a recorded cassette (`replay:`).
- **No number without a script.** README and docs numbers come from
  `scripts/results.py`. Figures come from `scripts/figures.py`, schemas from
  `scripts/schemas.py`. CI regenerates them and fails on drift, so regenerate
  and commit them with your change.
- **Pin errors, not rates.** If you change a judge or a pack, update the exact
  lists of disagreements pinned in `tests/test_judges.py`.
- **Public API** is `precedent.__all__`. Examples in `examples/` use only that
  surface and run in CI.
- **Never weaken the gate to make a test pass.** If a rule is blocked, the rule
  is wrong, or the test's labels are.
- **Event log:** never write SQL against it directly. Go through `EventStore`
  and `Registry`.
