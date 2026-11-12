# Pre-registration: correction-stream benchmark

Written on 2026-11-12, before any judge output on this data existed. The sha256
of this file is appended to `prereg.db`, a Precedent event log, before the first
judge call. The analysis follows this document; any deviation is reported as a
deviation.

## Question

When people correct an LLM judge one decision at a time, which way of
feeding those corrections back changes the fewest verdicts that were already
right, without giving up accuracy?

## Data

- `bench-conduct`: 240 synthetic call transcripts written by a GPT-family model
  (via Codex) from fact vectors sampled from a factorial design (`spec.py`).
- Gold labels are a deterministic function of the facts and the written policy
  (`spec.py::gold`, `pack/policy/`). They are never produced by a model.
- 30% of the cases are minimal contrast pairs that differ in one fact.
- Fact realisation is checked by a Qwen-family model (`verify.py`).
  Mismatches are adjudicated by Claude (a third family), and the adjudications
  are published. No human has audited the data yet.
- Splits are assigned per contrast group: 80 **pool** (source of corrections),
  80 **dev** (what gates may see), 80 **test** (sealed; read only at the
  checkpoints below).
- The policy text and the 15-predicate library were frozen before any judge
  output was seen (`pack/`).

## Judge

Gemma 4 26B (MLX, via LM Studio), temperature 0, the Precedent structured judge
prompt. Base run = arm A0.

## The correction stream

- **Source.** A0's wrong verdicts on the pool split. The list is shuffled with
  seed 7, round-robin over items, capped at 30 (fewer if fewer exist).
- **Content.** Each correction carries the case, the item, the wrong label, the
  right label, and a reason sentence. The reason is generated from the fact that
  determines the label (`run.py::REASONS`), so every arm receives the same
  information.
- **Checkpoints:** after 15 and after 30 corrections.

## Arms

| arm | what happens to corrections | judge calls |
|---|---|---|
| A0 | nothing (baseline) | base run |
| A1 | every correction so far as a few-shot example in the prompt | test, at both checkpoints |
| A2 | top-5 most similar corrected cases (bge-m3 + bge-reranker-v2-m3) as examples, with reasons | test, at both checkpoints |
| A3 | reasons appended to the prompt as guidelines | test, at both checkpoints |
| A3g | as A3, in two batches of 15; a batch is kept only if re-judging dev shows zero right→wrong flips | dev and test |
| P | a placebo paragraph of the same length as A3's guidelines | test, at both checkpoints |
| B1 | each correction becomes a predicate rule drafted by a Qwen-family model from the frozen library; every rule applied | none (rules read A0's predicate answers) |
| B2 | as B1, but each rule must pass the Precedent gate on dev plus earlier corrections; one revision allowed after gate feedback | none |

- B arms run in 3 random correction orders (seeds 1, 2, 3); reported as mean and range.
- A0 is re-run once on test to measure judge instability. This is the noise floor.

## Endpoints (sealed test, 80 cases × 4 items = 320 verdicts)

- **Primary.** Negative flips after 30 corrections: verdicts right under A0 and
  wrong under the arm.
- **Secondary:**
  - verdict accuracy with Wilson 95% CIs;
  - case-level accuracy (all four items right);
  - positive flips;
  - exact McNemar against A0;
  - per-item accuracy;
  - generalisation: test verdicts that were wrong under A0 and share the
    corrected fact value, and became right;
  - locality: contrast pairs in test where one side flips the wrong way;
  - coverage: share of corrections that became an accepted rule (B2);
  - LLM calls per correction.

## Hypotheses

- **H1.** B2 has fewer negative flips than each of A1, A2 and A3 after 30
  corrections. Paired exact McNemar per comparison, Holm-corrected over the three.
- **H2.** B2 is non-inferior to the best of A1, A2 and A3 on verdict accuracy,
  with a margin of 2 percentage points.
- **H3.** Gating reduces negative flips within each family: B2 < B1 and A3g < A3.
- **H4.** Prompt arms flip more verdicts than the placebo P. If they do not, the
  difference is prompt noise, not learning.

## What would count against us

If B2 does not have fewer negative flips than the prompt arms, or loses more
than 2 points of accuracy to the best of them, the README says so in the same
place it would have said the opposite.
