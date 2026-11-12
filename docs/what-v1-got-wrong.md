# What v1 got wrong

v1 of this project ("ConductGene Swarm") was built in June 2026 for a
hackathon. Its headline feature was learning from supervisor corrections: when
a supervisor overrode a verdict, the system stored a "Policy Gene" and applied
it to similar calls. The README said the learning was measured on a held-out
case. This page records what a review in November 2026 found, because the
failure is the reason v2 exists.

## The learning demo learned the wrong rule

- The correction came from CASE-002, a call where the agent offered "a
  supervisor to discuss a repayment path". The stored gene had a trigger
  pattern of `"repayment"` and set `escalation_offered = pass` on any call
  containing that word.
- The held-out case, CASE-005, offers a repayment path and **no**
  supervisor. Its label is `needs_review`, and the project's own policy said
  a repayment plan counts only *together with* a supervisor offer.
- The gene flipped CASE-005 from right to wrong. The held-out score went from
  **1.0 to 0.67**. The evaluation harness returned **`improved: True`**,
  because it defined improvement as "the status changed to the corrected
  status", not "the answer got closer to the label".
- A test asserted the regression as success. The demo script said the score
  rose from 0.6 to 0.8. The held-out set was one case, and its file name
  contained the trigger word.

## Why it went unnoticed

- **The metric measured the change, not the outcome.** Nothing compared the
  new answer with the label.
- **One held-out case.** A rule that fixes one call and breaks three others
  cannot be seen on one call.
- **No counter-examples.** Nobody had to say where the rule must *not* apply.
- **Keyword trigger.** "Repayment" was a correlate of the correction, not its
  reason. The reason was "a supervisor was offered".
- **100% everywhere.** The rules and the 16 test transcripts were written by
  the same person; "16/16 passed" and "citation coverage 100%" held by
  construction and hid the one number that mattered.

## Other findings from the same review

- "Citation coverage" checked that a cited id existed, not that it supported
  the claim; the mock agents cited the first snippet when nothing matched,
  and clause ids changed on every restart.
- The prosecutor and defender agents checked disjoint items, so the arbiter
  never saw a disagreement on any of the 18 cases.
- Abstention never fired on real text: a hotel booking call got a full
  verdict with citations.
- "Supervisor-approved" was a request flag that defaulted to `true`.
- The audit trail was a JSONL file rewritten in place on rollback, with no
  hash chain and raw transcripts in the clear.

## What v2 changes

| v1 | v2 |
|---|---|
| Substring trigger | Named predicates the judge answers with a verbatim quote |
| One held-out case | Every labelled case, accepted corrections as permanent tests, held-out reported separately with a bootstrap CI |
| "Improved" = status changed | Blocked if any case that was right becomes wrong |
| No counter-examples | At least one required; checked on every run |
| `approved: true` by default | A second person must approve; the author cannot |
| JSONL rewritten on rollback | Append-only SQLite with a hash chain; revert is an event |
| 100% on synthetic data | Pinned list of known judge errors; numbers labelled as smoke tests |

Run `precedent demo` to watch the v1 rule go through the v2 gate. It is
blocked with three broken cases. The same correction, stated as its real
reason, passes.
