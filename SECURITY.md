# Security policy

Report vulnerabilities through a [private security advisory](https://github.com/FUYOH666/precedent/security/advisories/new),
not a public issue. Expect an acknowledgement within 72 hours.

## What the design does and does not protect

- **The event log is tamper-evident, not tamper-proof.** Triggers refuse
  UPDATE and DELETE and `precedent audit verify` detects edits, but anyone
  with write access to the SQLite file can replace the whole chain. Anchor
  the head hash somewhere you do not control alone (a ticket, a signed
  commit, a timestamping service) and check with
  `precedent audit verify --anchor <hash>`; that also detects a cut-off tail.
- **Lifecycle commands fail closed.** They verify the chain before acting and
  run read-check-append in one SQLite write transaction.
- **Gate results are recorded by whoever runs the gate.** A report whose
  decision contradicts its own checks is refused, and the gate is
  deterministic given recorded judge outputs, so anyone can re-run it; but a
  fully fabricated report is only caught by re-running it.
- **Actors are names, not identities.** The CLI records whatever `--actor`
  says. Four-eyes approval stops honest mistakes, not impersonation. Put the
  CLI behind your own authentication before relying on it for sign-off.
- **Case text stays out of the log**, but packs and cassettes contain it.
  Keep real data out of public repositories.
- **LLM judges see the case text.** Use a local endpoint for confidential
  material; the default endpoint is a local LM Studio server.
