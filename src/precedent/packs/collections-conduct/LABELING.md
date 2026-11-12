# collections-conduct: how the labels were made

- **Source.** 18 transcripts come from the v1 hackathon suite (CASE-001…018);
  10 were written for v2 (CASE-019…028) to cover what v1 never tested:
  negation, a standard recording disclosure, an out-of-domain call, callbacks
  from a team lead or manager, a refused callback, and a threat phrased
  without the usual keywords.
- **Who labelled.** One author, against the policy in `policy/`. There is no
  second annotator yet, so there is no human–human agreement figure. Treat
  every number from this pack as a smoke test, not a benchmark.
- **Complete labels.** Every case has a label for every item. v1 left items
  unlabelled when the rules did not cover them.
- **Split.** 9 cases are held out (`split: heldout`). The gate reports
  held-out agreement separately; nothing is tuned on them.

## Labels changed from v1

| Case | Item | v1 | v2 | Why |
|---|---|---|---|---|
| CASE-009 | recording_disclosure | needs_review | pass | "This call is being record[ed] for quality purposes" is a disclosure with a typo, not a missing one. The v1 label matched the v1 rule, not the policy. |
| CASE-011 | recording_disclosure | — | pass | Clear disclosure; v1 had no label. |
| CASE-003 | company_disclosure | — | needs_review | Company named, purpose never stated before the threat. Strict reading. Both the heuristic judge and Gemma 4 disagree, so this label is the first candidate for a second annotator. |

## Known judge blind spots (by design)

The heuristic judge counts only explicit transfers as escalation offers and
does not know the word "sheriff". Five of 112 verdicts disagree with the
labels; `tests/test_judges.py` pins the exact list so a change to the judge
cannot hide behind an aggregate number.
