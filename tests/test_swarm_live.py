"""Tests for swarm live LLM dispatch."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from conductgene.agents.dispatch import uses_live_llm
from conductgene.config import Settings
from conductgene.evolution.genes import GeneStore
from conductgene.kb.memory import MemoryKnowledgeBase
from conductgene.pipeline.swarm import swarm_analyze
from conductgene.schemas import SwarmAnalyzeRequest


def test_uses_live_llm_false_for_mock():
    s = Settings(_env_file=None, llm_provider="mock")
    assert uses_live_llm(s) is False


def test_uses_live_llm_true_for_openrouter():
    s = Settings(_env_file=None, llm_provider="openrouter")
    assert uses_live_llm(s) is True


@pytest.mark.asyncio
async def test_swarm_mock_provider_unchanged(tmp_path):
    settings = Settings(
        _env_file=None,
        llm_provider="mock",
        mode="mock",
        retrieval_mode="memory",
        kb_dir=tmp_path / "kb",
        gene_store_path=tmp_path / "genes.jsonl",
        audit_store_path=tmp_path / "audit.jsonl",
        gene_audit_store_path=tmp_path / "gene_events.jsonl",
    )
    settings.resolve_paths()
    (tmp_path / "kb").mkdir()
    (tmp_path / "kb" / "policy.md").write_text(
        "## Threat policy\nNo arrest language allowed.\n",
        encoding="utf-8",
    )
    kb = MemoryKnowledgeBase(settings.kb_dir)
    genes = GeneStore(settings.gene_store_path)

    result = await swarm_analyze(
        settings=settings,
        kb=kb,
        gene_store=genes,
        request=SwarmAnalyzeRequest(
            transcript="Agent: This is ABC Collections. No threats here.",
            case_id="TEST-001",
            abstain_when_low_evidence=False,
        ),
    )
    assert result.abstained is False
    assert result.prosecutor.role == "prosecutor"


@pytest.mark.asyncio
async def test_swarm_live_dispatch_calls_llm(tmp_path):
    prosecutor_json = {
        "role": "prosecutor",
        "checklist": [
            {
                "id": "threat_language",
                "status": "pass",
                "rationale": "OK",
                "cited_chunk_ids": [],
            }
        ],
        "summary": "ok",
    }
    defender_json = {
        "role": "defender",
        "checklist": [
            {
                "id": "escalation_offered",
                "status": "pass",
                "rationale": "OK",
                "cited_chunk_ids": [],
            }
        ],
        "summary": "ok",
    }
    arbiter_json = {
        "role": "arbiter",
        "checklist": prosecutor_json["checklist"] + defender_json["checklist"],
        "summary": "merged",
    }

    async def fake_chat(settings, messages, *, expected_role, model_override=None):
        from conductgene.schemas import AgentOpinion

        data = {"prosecutor": prosecutor_json, "defender": defender_json, "arbiter": arbiter_json}[
            expected_role
        ]
        return AgentOpinion.model_validate(data)

    settings = Settings(
        _env_file=None,
        llm_provider="openrouter",
        mode="live",
        retrieval_mode="memory",
        openrouter_api_key="sk-test",
        openrouter_models="openai/gpt-4o-mini",
        kb_dir=tmp_path / "kb",
        gene_store_path=tmp_path / "genes.jsonl",
        audit_store_path=tmp_path / "audit.jsonl",
        gene_audit_store_path=tmp_path / "gene_events.jsonl",
    )
    settings.resolve_paths()
    (tmp_path / "kb").mkdir()
    (tmp_path / "kb" / "policy.md").write_text(
        "## Policy\nCompany identification and escalation required.\n",
        encoding="utf-8",
    )
    kb = MemoryKnowledgeBase(settings.kb_dir)
    genes = GeneStore(settings.gene_store_path)

    with patch(
        "conductgene.agents.live.chat_completion_json",
        new=AsyncMock(side_effect=fake_chat),
    ):
        result = await swarm_analyze(
            settings=settings,
            kb=kb,
            gene_store=genes,
            request=SwarmAnalyzeRequest(
                transcript="Agent: This is ABC Collections calling about your account.",
                case_id="TEST-LIVE",
                abstain_when_low_evidence=False,
            ),
        )

    assert result.prosecutor.summary == "ok"
    assert result.arbiter.role == "arbiter"
