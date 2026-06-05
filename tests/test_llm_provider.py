"""Tests for LLM provider resolution and JSON parsing."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from conductgene.config import Settings
from conductgene.providers.llm import chat_completion_json, resolve_llm_config
from conductgene.schemas import AgentOpinion


def test_resolve_openrouter_config():
    s = Settings(
        _env_file=None,
        llm_provider="openrouter",
        openrouter_api_key="sk-test",
        openrouter_models="openai/gpt-4o-mini",
    )
    cfg = resolve_llm_config(s)
    assert cfg.provider == "openrouter"
    assert cfg.model == "openai/gpt-4o-mini"
    assert cfg.api_key == "sk-test"


def test_resolve_lmstudio_requires_model():
    s = Settings(_env_file=None, llm_provider="lmstudio", lmstudio_model="")
    with pytest.raises(ValueError, match="LMSTUDIO_MODEL"):
        resolve_llm_config(s)


def test_resolve_instruct_config():
    s = Settings(
        _env_file=None,
        llm_provider="instruct",
        llm_base_url="http://127.0.0.1:8002/v1",
        llm_model="test-model",
    )
    cfg = resolve_llm_config(s)
    assert cfg.provider == "instruct"
    assert cfg.model == "test-model"


@pytest.mark.asyncio
async def test_chat_completion_json_parses_agent_opinion():
    payload = {
        "role": "prosecutor",
        "checklist": [
            {
                "id": "threat_language",
                "status": "pass",
                "rationale": "No threats detected.",
                "cited_chunk_ids": ["abc"],
            }
        ],
        "summary": "Clean transcript.",
    }
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content=json.dumps(payload)))]

    settings = Settings(
        _env_file=None,
        llm_provider="openrouter",
        mode="live",
        openrouter_api_key="sk-test",
        openrouter_models="openai/gpt-4o-mini",
    )

    with patch("conductgene.providers.llm.AsyncOpenAI") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        opinion = await chat_completion_json(
            settings,
            [{"role": "user", "content": "test"}],
            expected_role="prosecutor",
        )

    assert isinstance(opinion, AgentOpinion)
    assert opinion.role == "prosecutor"
    assert opinion.checklist[0].id == "threat_language"
