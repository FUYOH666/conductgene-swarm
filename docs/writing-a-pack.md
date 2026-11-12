# Writing a pack

A pack is a directory that defines one domain. Point any command at it with
`--pack path/to/pack`.

```
my-pack/
  pack.yaml        rubric items, labels, predicates, optional heuristic baseline
  policy/*.md      policy corpus; every line under a heading becomes a clause
  cases.jsonl      cases with golden labels and a dev/heldout split
  rules/*.yaml     example rules (proposals; nothing is active by default)
  judgements/      recorded judge outputs for offline replay
```

## pack.yaml

```yaml
id: my-pack
version: "1.0"
title: One line on what is being judged
review_label: needs_review      # must be a label of every item
abstain_label: abstain          # added automatically to every item

items:
  - id: escalation_offered
    question: Did the agent offer contact with a supervisor?
    labels:
      - {id: pass, meaning: a transfer, call or callback was offered}
      - {id: needs_review, meaning: no such offer}
    default_label: needs_review
    evidence_required: [pass]   # the judge must quote the case to use these

predicates:
  - id: supervisor_contact_offered
    question: Does the agent offer any contact with a supervisor, manager or team lead?
    # optional, heuristic judge only:
    speaker: Agent
    patterns: ['(supervisor|manager)\b[^.]{0,40}\bcall you back']
```

Write predicates as questions a careful person could answer from the case
alone, with a quote. They are the vocabulary rules are written in, so a good
predicate is narrow ("offered a callback from a supervisor") rather than a
restatement of a rubric item ("escalation was fine").

## Policy

Markdown. Each non-empty line under a heading is one clause with a stable
content-hash id (`sha256(doc|section|text)[:12]`). Editing a clause changes
its id, which is the point: a citation always refers to the exact words.

## Cases

One JSON object per line:

```json
{"id": "CASE-001", "text": "Agent: ...", "golden": {"escalation_offered": "pass"},
 "split": "dev", "note": "why this label", "metadata": {"origin": "v2"}}
```

Label every item on every case. Put roughly a third of the cases in
`"split": "heldout"` and do not look at them while writing rules. Record who
labelled and how in a `LABELING.md` next to the data.

## Checking a pack

```bash
precedent judge --pack my-pack --errors            # heuristic baseline
precedent judge --pack my-pack --judge llm:MODEL --db work/p.db --errors
```

The second command records the model's outputs under `work/judgements/`, so
`--judge replay:work/judgements/<file>.jsonl` reproduces them offline.
