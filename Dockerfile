# Precedent: offline image. Runs the demo by default; mount a volume at /work
# to keep an event log between runs.
FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.8.15 /uv /bin/
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-install-project --no-editable
COPY src ./src
RUN uv sync --frozen --no-editable

FROM python:3.12-slim
RUN useradd --create-home --uid 1000 precedent
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
WORKDIR /work
RUN chown precedent:precedent /work
USER precedent
ENTRYPOINT ["precedent"]
CMD ["demo", "--out", "/work/demo"]
