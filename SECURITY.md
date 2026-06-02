# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.2.x   | Yes       |
| < 0.2   | No        |

## Reporting a vulnerability

Please **do not** open a public issue for security-sensitive reports.

1. Open a [private security advisory](https://github.com/FUYOH666/conductgene-swarm/security/advisories/new) on GitHub, or
2. Email the maintainer via GitHub profile contact.

We aim to acknowledge reports within 72 hours.

## Design notes (hackathon / demo scope)

- **No authentication** on the API — intentional for local demo. Do not expose `conductgene-serve` to the public internet without adding auth.
- **Synthetic data only** — scenario corpus and KB contain no real PII.
- **Local JSONL stores** — gene and audit files are append-only on disk; production deployments need encryption, access control, and retention policies.
- **Mock mode default** — deterministic agents; live LLM mode requires your own gateway credentials via `.env`.

## Dependency updates

Dependabot is enabled for GitHub Actions. Python dependencies are managed via `uv` and `uv.lock`.
