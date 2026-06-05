"""Tests for extended settings."""

from __future__ import annotations

from conductgene.config import Settings


def test_default_retrieval_and_llm_provider():
    s = Settings(
        _env_file=None,
        mode="mock",
        llm_provider="mock",
        retrieval_mode="memory",
    )
    assert s.mode == "mock"
    assert s.llm_provider == "mock"
    assert s.retrieval_mode == "memory"
    assert s.retrieval_fallback_to_memory is True


def test_openrouter_model_list():
    s = Settings(openrouter_models="a/b,c/d")
    assert s.openrouter_model_list() == ["a/b", "c/d"]
