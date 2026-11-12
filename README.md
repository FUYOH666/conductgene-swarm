<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/banner-dark.svg">
    <img alt="precedent: pull requests for AI judgment" src="docs/assets/banner-light.svg" width="100%">
  </picture>
</p>

<p align="center">
  <a href="#quickstart">Quickstart</a> ·
  <a href="docs/how-it-works.md">How it works</a> ·
  <a href="https://fuyoh666.github.io/precedent/">Evidence packs</a> ·
  <a href="#results">Results</a> ·
  <a href="docs/essay.md">Essay</a> ·
  <a href="docs/what-v1-got-wrong.md">What v1 got wrong</a>
</p>

**Our first version learned a rule from one supervisor's correction. It broke three calls it had
been getting right, and our own evaluation reported `improved: True`.**

Precedent makes that change impossible to ship. It is an open-source Python library and CLI that
treats a correction to an LLM judge like a code change. The correction becomes a rule that states its
reason, and a gate tests it against every case the system has ever been checked on. A second person
approves it, one command reverts it, and every step lands in a hash-chained log an auditor can verify
offline.

```bash
uvx --from git+https://github.com/FUYOH666/precedent precedent demo      # offline, under a second
```

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/flips-dark.svg">
    <img alt="Flip map: for each of 28 calls, which verdicts each rule fixes (green) or breaks (red). The v1 keyword rule breaks 3 calls on the keyword judge and 4 on Gemma 4 and is blocked; the reason-based rule breaks none and passes." src="docs/assets/flips-light.svg" width="100%">
  </picture>
</p>

| one supervisor correction, two ways to turn it into a rule | gate | fixes | breaks |
|---|---|---|---|
| v1: "the call mentions repayment" (what the hackathon version learned) | **blocked** | 2 | 3 |
| v2: "a supervisor or team lead promised a callback" (the reviewer's actual reason) | **passed**, then a second person approves | 3 | 0 |

<sub>On the keyword judge, 28 synthetic calls with 9 held out and one annotator: a test of the
machinery, not a benchmark. The same two rules as real pull requests on this repository:
<a href="https://github.com/FUYOH666/precedent/pull/14">#14 blocked</a> ·
<a href="https://github.com/FUYOH666/precedent/pull/15">#15 passed</a>. A pre-registered 240-call benchmark is under way
(<a href="benchmarks/correction_stream/PREREGISTRATION.md">design</a>).</sub>

> **Running an LLM judge with human reviewers?** Send us a sample of the decisions they overrode.
> We run them through the gate on your hardware and show which corrections are safe rules and which
> would have broken something. → [scanovich.ai/contact](https://scanovich.ai/contact/?ref=precedent)

<details>
<summary><b>Full output of <code>precedent demo</code></b></summary>
<br>
<img alt="Terminal output of precedent demo: the v1 rule is blocked for breaking three calls; the reason-based rule passes; the author cannot approve their own rule; a second person approves; one command reverts; the log verifies." src="docs/assets/demo.svg" width="100%">
</details>

## What you bring, what Precedent does

| you bring | Precedent does |
|---|---|
| a **pack**: rubric items, yes/no predicates, policy text, labelled cases | runs your judge once per case, records the run, and verifies every quote against the case |
| a **judge**: any OpenAI-compatible model, local or hosted | applies reviewed rules on top of the judge, in code, deterministically |
| **reviewers** who correct decisions | gate · four-eyes approval · revert · hash-chained log · evidence packs |

## Quickstart

Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/FUYOH666/precedent.git && cd precedent
uv sync --extra dev
uv run precedent demo                 # the v1 bug, caught; writes evidence packs too
./scripts/verify_all.sh               # ruff, mypy --strict, tests, the demo; offline
```

The lifecycle by hand:

```bash
precedent correct --db p.db --pack collections-conduct --case CASE-019 --item escalation_offered \
                  --label pass --reviewer maria --error-type policy_misinterpretation
precedent propose rule.yaml --db p.db --actor maria
precedent gate escalation-callback@2 --db p.db --pack collections-conduct      # → PASSED / BLOCKED
precedent approve escalation-callback@2 --db p.db --pack collections-conduct --actor alex \
                  --rationale "policy: callbacks count"    # re-runs the gate; must reproduce it
precedent evidence escalation-callback@2 --db p.db --pack collections-conduct --out evidence/
precedent audit verify --db p.db
```

With a real model on any OpenAI-compatible endpoint (LM Studio, vLLM, OpenRouter):

```bash
export PRECEDENT_LLM_BASE_URL=http://127.0.0.1:1234/v1
precedent judge --pack collections-conduct --judge llm:<model> --db work/p.db --errors
```

The run is recorded under `work/judgements/`, and `--judge replay:<file>` replays it exactly, offline.

## How it works

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/lifecycle-dark.svg">
    <img alt="Lifecycle: correction, rule, gate, approval by a second person, active, revert; a blocked rule goes back as a new version; every step is an event in a hash-chained log." src="docs/assets/lifecycle-light.svg" width="100%">
  </picture>
</p>

**The model perceives, code decides.** One call per case returns a label for each rubric item, plus
yes/no answers to a library of narrow predicates such as "did the agent promise a callback from a
supervisor?". Every positive claim must quote the case verbatim (and, for a predicate about one
speaker, that speaker's lines), or it is downgraded.

**A rule names its reason in predicates, not keywords or prompt text.** Its effect is therefore
deterministic and cheap to re-check on every case:

```yaml
id: escalation-callback
version: 2
item: escalation_offered
when:
  - {predicate: supervisor_callback_offered, equals: "yes"}
then: pass
source_corrections: [C-0001]
counter_examples: [CASE-005, CASE-023, CASE-025]    # required: where it must not change anything
```

**The gate blocks** a rule if it:
- does not fix its own correction;
- changes a counter-example;
- turns *any* right verdict wrong;
- conflicts with an active rule.

Changed verdicts get an exact McNemar test and held-out agreement is reported, but one regression is
enough to block.

**Approval is bound to what the gate saw.** The approver's CLI re-performs the gate, and the recorded
report must be reproduced exactly. The binding covers:
- the rule's content;
- the cases;
- the judge;
- the corrections;
- the active rules.

The author can neither run the gate on their own rule nor approve it.

**The log is append-only SQLite with a hash chain.** Lifecycle commands verify the chain and refuse
to act on a damaged log. `audit verify --anchor` checks it against a head recorded elsewhere. Case
text never enters the log.

More: [how it works](docs/how-it-works.md) · [writing a pack](docs/writing-a-pack.md) ·
[the essay behind the design](docs/essay.md).

## What an auditor receives

`precedent evidence` writes one self-contained page and a JSON twin per rule change. They cover:
- why the change exists, with the correction, the case and the judge's own quotes;
- what changes, with the rule and its diff;
- the full gate report, case by case;
- sign-offs, with segregation-of-duties checks and an honest note on identity;
- limitations and history;
- chain integrity, with the command that re-performs the gate.

Two real ones, cut from the demo's log:

- [**Blocked**: the v1 keyword rule](https://fuyoh666.github.io/precedent/evidence/escalation-callback@1.html)
- [**Passed and approved**: the reason-based rule](https://fuyoh666.github.io/precedent/evidence/escalation-callback@2.html)

The log head they were cut from is anchored in the
[v2.0.0 release notes](https://github.com/FUYOH666/precedent/releases/tag/v2.0.0). `precedent audit
export` hands over the complete event population for sampling.

## Run the gate on pull requests

Rules are files, so a change to how your judge decides can be reviewed like any other change. The
repository's own [`rules/active/`](rules/) directory is gated this way: a pull request that adds or
edits a rule gets the gate report as a comment, fails if the rule is blocked, and the merge makes the
rule active.

See it on this repository:
- [**#14**](https://github.com/FUYOH666/precedent/pull/14), the rule v1 learned: **blocked**, left open on purpose;
- [**#15**](https://github.com/FUYOH666/precedent/pull/15), the same correction stated as its reason: **passed and merged**.

```yaml
# .github/workflows/rules.yml
on:
  pull_request:
    paths: ["rules/**"]
jobs:
  gate:
    runs-on: ubuntu-latest
    permissions: {contents: read, pull-requests: write}
    steps:
      - uses: actions/checkout@v7
      - uses: FUYOH666/precedent@v2
        with:
          pack: path/to/your-pack          # or a built-in pack name
          rules: rules/active/*.yaml         # or only the files the PR changed
          corrections: rules/corrections.yaml
          active: rules/active
          judge: replay:path/to/recorded-judge.jsonl   # recorded outputs; CI needs no model
```

Locally, the same check without an event log is `precedent check RULE.yaml --pack ... --corrections ...`.

## Results

`collections-conduct` is a deliberately small pack: 28 synthetic calls, 9 held out, one annotator.
Every number and figure here is regenerated by `scripts/results.py` and `scripts/figures.py`, and CI
fails if they drift.

| judge, no rules | agree with labels | held-out | where it is wrong |
|---|---|---|---|
| keyword heuristic (offline baseline) | 107/112 | 33/36 | misses callbacks from a team lead or manager (3), a threat without the usual keywords (1), one disputed label |
| Gemma 4 26B, local (LM Studio, MLX), recorded | 106/112 | 32/36 | gives a full verdict on an out-of-domain hotel call instead of abstaining (4), two disputed company-disclosure labels |

- **Quote verification earns its keep.** It downgraded three Gemma claims that an escalation was
  offered. One was on CASE-025, where the agent explicitly *refused* a supervisor callback.
- **A rule is only safe relative to a judge.** The v1 keyword rule breaks 3 verdicts on the keyword
  judge and 4 on Gemma, which reads "would you like to make a payment today?" as a repayment offer.
  The v2 rule fixes nothing on Gemma, which already understands callbacks, and the gate's `has_effect`
  advisory says so.
- **Local is practical.** Median 6.6 s and about 1.9k tokens per call on an Apple Silicon Mac, with
  no data leaving the machine.

All tables and every single disagreement: [docs/results/collections-conduct.md](docs/results/collections-conduct.md).

**Next: does the gate beat the alternatives?** A pre-registered benchmark is running:
- 240 calls written from fact vectors, with gold labels from a policy function;
- three model families (one writes, one checks, one judges);
- eight arms, among them "corrections as few-shot examples", retrieved examples, guidelines in the
  prompt, a placebo, and gated vs ungated rules.

Hypotheses and endpoints were hashed into an event log before the first judge call:
[PREREGISTRATION.md](benchmarks/correction_stream/PREREGISTRATION.md).

## Design principles

1. **No quote, no claim.** A finding the judge cannot quote from the case does not count.
2. **State the reason, not the trigger.** A rule names the condition that made the human right,
   and the cases where it must not apply.
3. **Nothing that was right may become wrong.** Broken verdicts are counted one by one; an average
   cannot hide them.
4. **Two people, one log, re-performable evidence.** Author, gate runner and approver differ. Every
   step is an event, and anyone can re-run the gate and get the same report.
5. **Offline by default.** Tests, the demo and the gate run without a network or a model; real
   model runs are recorded and replayed.

## Where this applies

The pattern fits any workflow where an AI makes many similar judgments, experts correct some of
them, and someone outside the team will ask "why did you decide that?":

| domain | the judgment | a correction that should become a rule |
|---|---|---|
| customs and trade compliance | tariff code for a product description | "a general-purpose part goes to its own heading, not to the vehicle's" |
| contact-centre QA | did the call follow conduct policy | "a promised callback from a team lead is an escalation offer" |
| claims and AML triage | is this claim or alert worth a human | "this transfer pattern is payroll, not structuring" |
| content moderation | does this post break policy | "quoting a slur to report it is not using it" |
| coding agents | does this change follow team rules | "migrations go in a separate PR" |

Only the pack changes: rubric, predicates, policy, labelled cases.

## Limitations

- The packs are small and labelled by one person. There is no human–human agreement figure yet, so
  there is no ceiling to measure a judge against.
- A verified quote proves the words are in the case, not that they support the claim. A prompt
  injection inside a case is itself quotable; see [SECURITY.md](SECURITY.md).
- Rules can only use predicates the judge was asked; adding a predicate means re-running the judge.
- Actors are names given to the CLI. Segregation of duties stops mistakes, not impersonation; put
  it behind your own authentication.
- The log is tamper-evident, not tamper-proof: anchor the head elsewhere (`audit verify --anchor`).
- Automated monitoring of employees' behaviour (as in call QA) is high-risk under the EU AI Act
  (Annex III, 4(b)). This tool documents oversight; it does not make a deployment compliant.

## Related work

- **Corrections fed back into the judge.** [MemAlign](https://www.databricks.com/blog/memalign-building-better-llm-judges-human-feedback-scalable-memory),
  [LangSmith Align Evals](https://blog.langchain.com/introducing-align-evals) and
  [Galileo's continuous learning with human feedback](https://galileo.ai/blog/introducing-continuous-learning-with-human-feedback)
  turn corrections into prompt context, guidelines or examples. They distil automatically and do not
  run a regression gate before a correction takes effect.
- **Graded propositions combined by code.** [Rule Based Rewards](https://arxiv.org/abs/2411.01111) is the
  closest ancestor of "the model perceives, code decides". Checklist evaluation
  ([CheckEval](https://arxiv.org/abs/2403.18771), [TICK](https://arxiv.org/abs/2410.03608)) and
  [concept-bottleneck LLMs](https://arxiv.org/abs/2412.07992) share the idea that narrow yes/no
  questions are more checkable than holistic labels.
- **Criteria drift.** In [Shankar et al., *Who Validates the Validators?*](https://arxiv.org/abs/2404.12272)
  and [SPADE](https://arxiv.org/abs/2401.03038), criteria change as people grade. Precedent records
  that drift as reviewed, reversible rule versions.
- **Model editing.** Precedent borrows the vocabulary of efficacy, generalisation and locality, and
  counts negative flips the way model-update work does.

## Who builds this

Precedent is built at [Scanovich](https://scanovich.ai), an independent applied-AI lab run by
Aleksandr Mordvinov, working with AI agents as collaborators (this repository included). We build
AI-operated workflows where a model does the reading and a person signs off:
- document intelligence;
- evidence-grounded agents;
- private inference that keeps data on your hardware.

Other open work in the same line:
- [**evidencegene-court**](https://github.com/FUYOH666/evidencegene-court): an adversarial AI court
  for digital forensics, where findings without evidence are rejected at the API boundary.
- [**Services-BGE**](https://github.com/FUYOH666/Services-BGE): local embeddings, reranking and a
  retrieval eval harness on Apple Silicon.
- [**VoiceToText**](https://github.com/FUYOH666/VoiceToText): private, local voice typing.

**Working with us.** If experts in your organisation correct an AI's decisions and those
corrections go nowhere, or you need an AI workflow that can explain itself to an auditor:
[scanovich.ai/contact](https://scanovich.ai/contact/?ref=precedent).

---

<sub>v1 of this project was "ConductGene Swarm", built for the UCWS Singapore 2026 hackathon and kept
under the tag <code>v1-ucws-2026</code>. MIT licence. Cite with <code>CITATION.cff</code>.</sub>
