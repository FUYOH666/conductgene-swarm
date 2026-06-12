# --- Build stage: resolve and install dependencies into a self-contained venv ---
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.8.15 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Dependency layer (cached unless lock changes); project installed non-editable
# so the venv is portable into the runtime stage.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-install-project --no-editable --extra ui --extra retrieval --extra live

COPY src ./src
RUN uv sync --frozen --no-editable --extra ui --extra retrieval --extra live

# --- Runtime stage: no uv, no dev tools, non-root ---
FROM python:3.12-slim

RUN useradd --create-home --uid 1000 conductgene

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --chown=conductgene:conductgene src ./src
COPY --chown=conductgene:conductgene data ./data
COPY --chown=conductgene:conductgene scripts ./scripts

# Runtime store dirs must exist and be writable before volumes mount over them
# (a fresh git checkout has no data/evolution or data/audit — contents are gitignored).
RUN mkdir -p data/evolution data/audit && chown -R conductgene:conductgene data

# Package is installed non-editable (site-packages), so data paths must be
# absolute — they cannot be derived from the package location.
ENV PATH="/app/.venv/bin:$PATH" \
    CONDUCTGENE_MODE=mock \
    CONDUCTGENE_HOST=0.0.0.0 \
    CONDUCTGENE_PORT=8090 \
    CONDUCTGENE_KB_DIR=/app/data/synthetic/kb \
    CONDUCTGENE_SCENARIOS_DIR=/app/data/scenarios \
    CONDUCTGENE_GENE_STORE_PATH=/app/data/evolution/genes.jsonl \
    CONDUCTGENE_AUDIT_STORE_PATH=/app/data/audit/cases.jsonl \
    CONDUCTGENE_GENE_AUDIT_STORE_PATH=/app/data/audit/gene_events.jsonl

USER conductgene

EXPOSE 8090 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8090/healthz', timeout=4)"]

CMD ["conductgene-serve"]
