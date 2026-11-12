# Roadmap

## Done

- **v2.0.0.** The core:
  - packs; a structured LLM judge with quote verification; a heuristic baseline; record and replay;
  - rules as predicate conditions, applied by code;
  - the blocking gate, four-eyes approval, revert;
  - the hash-chained event log, evidence packs and audit export;
  - the `collections-conduct` pack with the v1 regression as the demo.
- **v2.1.0.** A GitHub Action and `precedent check`: rule changes are gated in pull requests.
- **v2.2.0.** A pre-registered correction-stream benchmark (240 calls, seven ways to use 20 corrections).
  Rules broke no right verdict, but retrieved examples were 3.4 points more accurate, largely because 7 of the 20
  corrections were perception errors that a rule cannot express. [Results](../README.md#benchmark-20-corrections-seven-ways-to-use-them).

## Next

1. **Route each correction to the remedy that fits it.** The benchmark shows two kinds of correction.
   - A misapplied policy (the judge saw the facts and drew the wrong conclusion) becomes a rule.
   - A misread fact (the judge says the agent stated the call's purpose, quoting the customer's guess)
     becomes a gated example.
     It is retrieved for similar cases, and it is accepted only if re-judging the regression set
     breaks nothing.

   The router reads the judge's own predicate answers. If they contradict the reviewer's reason, the
   error is perception. A pre-registered follow-up compares routed corrections with retrieved examples.
2. **Speaker-bound predicates by default.** A predicate about what the agent said accepts only a quote
   from an agent line. The library supports this today (`speaker: Agent`); packs should not be able to
   forget it.
3. **`customs-hs` pack on public data.**
   - Product descriptions and classifications from U.S. CBP rulings (CROSS) and the USITC HTS, both
     public domain.
   - Items such as "the code exists and is current", "GRI 1 and the section and chapter notes were
     applied", "the reasoning cites a source".
   - An EAEU / TN VED adapter for pilots on a broker's own declarations.
4. **Model upgrades re-run the gate.** When the judge changes (new model, new prompt), every active rule
   is re-gated against the new judge's outputs before the switch. Rules are judge-specific. On the demo
   pack the v1 keyword rule breaks 3 verdicts on the heuristic judge and 4 on Gemma 4.
5. **Second annotator** for both packs and a published human–human agreement.
6. **Rule drafting in the CLI.** An LLM proposes a rule and a counter-example from a correction, and a
   person edits it. The benchmark harness already does this with a Qwen-family drafter. In 13 of 13
   expressible cases the draft passed the gate on the first attempt.
7. **Shadow mode.** A passed rule runs on new traffic without changing verdicts, and would-flip cases go
   to a reviewer before approval.

## Later

- Canary rollout and blast-radius queries ("which verdicts did rule X@2 change?").
- HTTP API with per-user keys and reviewer/approver roles.
- An open schema for oversight events, with adapters for tracing tools.
