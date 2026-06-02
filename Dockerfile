FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY data ./data
COPY scripts ./scripts

RUN uv sync --extra dev --extra ui

ENV CONDUCTGENE_MODE=mock
ENV CONDUCTGENE_HOST=0.0.0.0
ENV CONDUCTGENE_PORT=8090

EXPOSE 8090 8501

CMD ["uv", "run", "conductgene-serve"]
