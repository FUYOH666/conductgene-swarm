from __future__ import annotations

import httpx
import respx

from precedent.similarity import SimilarityClient, cosine

EMBED = "http://embed.test/v1"
RERANK = "http://rerank.test/v1"
VECTORS = {"query": [1.0, 0.0], "near": [0.9, 0.1], "far": [0.0, 1.0], "mid": [0.6, 0.4]}


def _embeddings(request: httpx.Request) -> httpx.Response:
    texts = __import__("json").loads(request.content)["input"]
    data = [{"index": i, "embedding": VECTORS[t]} for i, t in enumerate(texts)]
    return httpx.Response(200, json={"data": data})


@respx.mock
def test_nearest_uses_embeddings_then_reranker() -> None:
    respx.post(f"{EMBED}/embeddings").mock(side_effect=_embeddings)
    respx.post(f"{RERANK}/rerank").mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {"index": 0, "relevance_score": 0.2},
                    {"index": 1, "relevance_score": 0.9},
                ]
            },
        )
    )
    client = SimilarityClient(embed_url=EMBED, rerank_url=RERANK)
    out = client.nearest("query", {"a": "near", "b": "mid", "c": "far"}, k=2, shortlist=2)
    # embeddings shortlist a, b; the reranker reorders them
    assert [n.case_id for n in out] == ["b", "a"]
    assert client.embed(["near"]) == [VECTORS["near"]]  # cached, no second request needed


@respx.mock
def test_nearest_without_reranker() -> None:
    respx.post(f"{EMBED}/embeddings").mock(side_effect=_embeddings)
    client = SimilarityClient(embed_url=EMBED, rerank_url="")
    out = client.nearest("query", {"a": "far", "b": "near"}, k=1)
    assert [n.case_id for n in out] == ["b"]
    assert client.rerank("q", ["x"]) == [0.0]
    assert client.nearest("query", {}) == []
    assert cosine([0.0], [0.0]) == 0.0
