# Correction-stream benchmark

**Question.** When people correct an LLM judge one decision at a time, which way of feeding the corrections
back changes the fewest verdicts that were already right, without giving up accuracy?

**Method.**
- Design, arms and hypotheses: [PREREGISTRATION.md](PREREGISTRATION.md). Its hash went into `prereg.db` before
  any judge output existed.
- Deviations from that plan: [DEVIATIONS.md](DEVIATIONS.md).
- `uv run python benchmarks/correction_stream/check_prereg.py` re-checks the recorded hashes.

## Results

| judge | baseline | corrections in the stream | tables |
|---|---|---|---|
| Gemma 4 26B (`google/gemma-4-26b-a4b-it`, the pre-registered judge) | 876/960 verdicts right | 20 | [RESULTS.md](results/gemma-4-26b-a4b-it/RESULTS.md) |
| DeepSeek V4.1 Flash (`deepseek/deepseek-v4.1-flash-1017`) | 960/960 | 0: nothing to correct | [RESULTS.md](results/deepseek-v4.1-flash-1017/RESULTS.md) |

**Pre-registered hypotheses, Gemma judge.** The final checkpoint is the whole stream of 20 corrections.

| hypothesis | result | evidence |
|---|---|---|
| H1: gated rules break fewer right verdicts than each prompt method | **partly supported** | rules 0 vs few-shot 19 and retrieval 10 (significant); vs guidelines 5 (not significant, p = 0.062) |
| H2: gated rules are within 2 points of the best prompt method's accuracy | **not supported** | rules 91.6% vs retrieved examples 95.0% |
| H3: gating reduces broken verdicts within each family | **partly supported** | rules: 0 → 0, the gate blocked no drafted rule. Guidelines: 5 → 0, but only because the gate rejected every batch. |
| H4: prompt methods break more than a placebo paragraph | **partly supported** | placebo 9; few-shot 19 and retrieval 10 are above it, guidelines 5 is below |

**Main exploratory finding.** 7 of the 20 corrections could not be expressed as a rule. In all 7, the judge said
the agent had stated the purpose of the call, and the agent had not.
- In 5, the judge's quote was the customer's guess ("I assume this is about the overdue debt").
- In the other 2, it took the company's name ("… Debt Collection") for a purpose.

These are perception errors. A rule built on the judge's own answers cannot fix them.

## How it was built

| step | by |
|---|---|
| fact vectors and gold labels (`spec.py`, 240 cases, 80/80/80 pool/dev/test) | code; gold is a function of the facts |
| policy and frozen 15-predicate library (`pack/`) | written before any judge output |
| transcripts (`transcripts.jsonl`) | GPT family, via Codex |
| fact verification (`verify.py` → `verification.jsonl`) | Qwen family (`qwen/qwen3.8-27b`): 18 of 240 disagreements |
| adjudication of those disagreements (`adjudication.jsonl`) | Claude, blind to judge outputs; all 18 kept as specified |
| judge runs (`results/<model>/runs/`, one cassette per arm) | Gemma 4 26B and DeepSeek V4.1 Flash, via OpenRouter |
| rule drafting for the B arms (`drafts.json`) | Qwen family |

## Reproduce

Rebuild every table from the recorded cassettes. No model call is made, and CI runs this and fails on drift:

```bash
JUDGE_MODEL=google/gemma-4-26b-a4b-it uv run python benchmarks/correction_stream/run.py analyze
```

Re-run from scratch. This needs an OpenAI-compatible endpoint (default OpenRouter) with
`PRECEDENT_LLM_API_KEY` set, plus local bge-m3 and bge-reranker for arm A2:

```bash
JUDGE_MODEL=google/gemma-4-26b-a4b-it ./benchmarks/correction_stream/run_all.sh
```

The recorded Gemma judge calls cost $0.31 on OpenRouter.
