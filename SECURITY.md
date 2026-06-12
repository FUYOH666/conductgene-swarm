# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | Yes       |
| < 1.0   | No        |

## Reporting a vulnerability

Please **do not** open a public issue for security-sensitive reports.

1. Open a [private security advisory](https://github.com/FUYOH666/conductgene-swarm/security/advisories/new) on GitHub, or
2. Email the maintainer via GitHub profile contact.

We aim to acknowledge reports within 72 hours.

## Design notes (hackathon / demo scope)

- **API authentication is opt-in** — set `CONDUCTGENE_API_KEY` to require an `X-API-Key` header on all endpoints except `/healthz*` and `/readyz`. When unset, the server logs an explicit "auth disabled" warning at startup (local demo mode). Do not expose `conductgene-serve` to the public internet without setting a key.
- **Rate limiting is opt-in** — set `CONDUCTGENE_RATE_LIMIT_RPM` (requests/minute per client) to throttle `/swarm/analyze` and `/eval/run`; `0` (default) disables it.
- **Synthetic data only** — scenario corpus and KB contain no real PII.
- **Local JSONL stores** — gene and audit files are append-only on disk; production deployments need encryption, access control, and retention policies.
- **Mock mode default** — deterministic agents; live LLM mode requires your own gateway credentials via `.env`.

## Dependency updates

Dependabot is enabled for GitHub Actions. Python dependencies are managed via `uv` and `uv.lock`.
