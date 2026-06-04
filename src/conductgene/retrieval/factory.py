"""Retrieval factory — memory, Qdrant, Qdrant + reranker."""

from __future__ import annotations

from conductgene.config import Settings
from conductgene.kb.memory import MemoryKnowledgeBase
from conductgene.logutil import get_logger
from conductgene.retrieval.bge_client import BgeClient
from conductgene.retrieval.memory import retrieve_from_memory
from conductgene.schemas import EvidenceSnippet

logger = get_logger(__name__)


def retrieve_evidence(
    settings: Settings,
    kb: MemoryKnowledgeBase,
    query: str,
    *,
    top_n: int = 8,
    min_score: float = 0.35,
) -> tuple[list[EvidenceSnippet], float | None]:
    """Retrieve policy evidence; degrades to memory when configured."""
    mode = settings.retrieval_mode
    if mode == "memory":
        return retrieve_from_memory(kb, query, top_n=top_n, min_score=min_score)

    try:
        return _retrieve_qdrant(
            settings,
            kb,
            query,
            top_n=top_n,
            min_score=min_score,
            use_reranker=mode == "qdrant_rerank",
        )
    except Exception as exc:
        if settings.retrieval_fallback_to_memory:
            logger.warning(
                "retrieval degraded to memory",
                extra={"meta": {"mode": mode, "error": str(exc)}},
            )
            return retrieve_from_memory(kb, query, top_n=top_n, min_score=min_score)
        raise


def _retrieve_qdrant(
    settings: Settings,
    kb: MemoryKnowledgeBase,
    query: str,
    *,
    top_n: int,
    min_score: float,
    use_reranker: bool,
) -> tuple[list[EvidenceSnippet], float | None]:
    if not settings.embedding_base_url or not settings.qdrant_url:
        raise RuntimeError("embedding_base_url and qdrant_url required for qdrant retrieval")

    bge = BgeClient(settings)
    query_vec = bge.embed_dense([query])[0]

    from conductgene.retrieval.qdrant_store import QdrantRetriever

    store = QdrantRetriever(settings, vector_size=len(query_vec))
    fetch_n = top_n * 3 if use_reranker and settings.enable_reranker else top_n
    evidence = store.search(query_vec, top_n=fetch_n)

    if not evidence:
        memory_ev, score = retrieve_from_memory(kb, query, top_n=top_n, min_score=min_score)
        return memory_ev, score

    if use_reranker and settings.enable_reranker and settings.reranker_base_url:
        docs = [e.text for e in evidence]
        ranked = bge.rerank(query, docs, top_n=top_n)
        evidence = [evidence[idx] for idx, score in ranked]
        for item, (_, score) in zip(evidence, ranked, strict=True):
            item.score = score

    evidence = evidence[:top_n]
    top_score = evidence[0].score if evidence else None
    return evidence, top_score
