# Roadmap

## Done in v2.0.0.dev0

- Core: packs, structured LLM judge with quote verification, heuristic baseline, record/replay.
- Rules as predicate conditions; deterministic application; conflicts go to review.
- Blocking gate: source fixed, examples, counter-examples, zero regressions, conflicts, held-out with bootstrap CI.
- Lifecycle with four-eyes approval, stale-gate detection, versions, revert.
- Append-only SQLite event log with hash chain and `audit verify`.
- `collections-conduct` pack (28 calls, 9 held out) and the v1 regression as the demo.

## Next

1. **`customs-hs` pack on public data.** Product descriptions and classifications
   from U.S. CBP rulings (CROSS) and the USITC HTS, both public domain. Items such
   as "the code exists and is current", "GRI 1 and the section and chapter notes
   were applied", "the reasoning cites a source". An EAEU / TN VED adapter for
   pilots on a broker's own declarations.
2. **Benchmark.** Arms: heuristic rules; one judge; one judge with corrections as
   few-shot examples (the cheap baseline to beat); self-consistency; judge plus
   gated rules; judge plus ungated rules (how many regressions the gate prevents).
   A local model and a frontier model; cost and latency per case; numbers only
   from scripts in the repository.
3. **Model upgrades re-run the gate.** When the judge changes (new model, new
   prompt), every active rule is re-gated against the new judge's outputs before
   the switch. On the demo pack the v1 keyword rule breaks 3 verdicts on the
   heuristic judge and 5 on Gemma 4: rules are judge-specific.
4. **Second annotator** for both packs and a published human–human agreement.
5. **Rule drafting:** an LLM proposes a rule and a counter-example from a
   correction; a person edits it.
6. **Shadow mode:** a passed rule runs on new traffic without changing verdicts;
   would-flip cases go to a reviewer before approval.
7. **Evidence pack:** an HTML dossier per decision and per rule for auditors.

## Later

- Canary rollout and blast-radius queries ("which verdicts did rule X@2 change?").
- HTTP API with per-user keys and reviewer/approver roles.
- An open schema for oversight events, with adapters for tracing tools.
