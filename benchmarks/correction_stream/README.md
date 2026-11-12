# Correction-stream benchmark (in progress)

Question: when people correct an LLM judge one decision at a time, which way of
feeding the corrections back changes the fewest verdicts that were already right,
without giving up accuracy? Design, arms and hypotheses: [PREREGISTRATION.md](PREREGISTRATION.md).
Its hash went into `prereg.db` before any judge output existed. Deviations are
logged in [DEVIATIONS.md](DEVIATIONS.md).

| step | status |
|---|---|
| fact vectors and gold labels (`spec.py`, 240 cases, 80/80/80) | done |
| policy and frozen predicate library (`pack/`) | done |
| transcripts written by a GPT-family model via Codex (`transcripts.jsonl`) | done, 240/240 |
| fact verification by a Qwen-family model (`verify.py`) | waiting for a hosted endpoint |
| judge runs and arms (`run.py`) | waiting |

Reproduce: `uv run python benchmarks/correction_stream/run.py build base prompts gated draft rules stability analyze`
with `PRECEDENT_LLM_API_KEY` set for an OpenAI-compatible endpoint (default OpenRouter).
