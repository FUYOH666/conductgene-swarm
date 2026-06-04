# Qdrant + BGE Retrieval

Optional live retrieval for ConductGene Swarm. **Default remains in-memory keyword search** (`CONDUCTGENE_RETRIEVAL_MODE=memory`).

## Prerequisites (MacBook)

1. [Services-BGE](https://github.com/FUYOH666/Services-BGE) running:
   - Embedding: `http://127.0.0.1:9001` (`GET /readyz`)
   - Reranker: `http://127.0.0.1:9002` (`GET /readyz`)
2. Qdrant: `http://127.0.0.1:6333` (Docker example below)
3. Install extras: `uv sync --extra dev --extra retrieval`

## Quick setup

```bash
# Qdrant (one-time)
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 qdrant/qdrant

cp .env.example .env
# Set CONDUCTGENE_RETRIEVAL_MODE=qdrant_rerank
# Set CONDUCTGENE_ENABLE_RERANKER=true
# Set embedding/reranker URLs if not localhost

uv run python scripts/discover_services.py
uv run python scripts/ingest_qdrant.py
```

## Ingestion

`scripts/ingest_qdrant.py`:

- Reads `data/synthetic/kb/*.md`
- Embeds via BGE-M3 (`POST /v1/embeddings`, dense vectors)
- Upserts into `CONDUCTGENE_QDRANT_COLLECTION` (default `conductgene_policy_kb`)
- Payload: `document_id`, `source_type`, `text`, `doc_id`, `section`, `version`, `tags`

## Retrieval modes

| Mode | Behavior |
|------|----------|
| `memory` | Keyword overlap on in-memory KB (CI default) |
| `qdrant` | Vector search only |
| `qdrant_rerank` | Vector search + BGE reranker top-N |

If Qdrant or BGE is unavailable and `CONDUCTGENE_RETRIEVAL_FALLBACK_TO_MEMORY=true` (default), the system logs a warning and uses memory mode.

## Verify

```bash
CONDUCTGENE_RETRIEVAL_MODE=qdrant_rerank uv run conductgene analyze \
  --file data/scenarios/collections/case_002_coercive_soft.json
```

Check evidence scores in output — Qdrant hits typically differ from keyword-only scores.

## API

`GET /healthz/services` — service discovery table (embedding, reranker, qdrant, llm providers).
