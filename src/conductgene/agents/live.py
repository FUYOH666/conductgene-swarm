"""Live LLM agent mode — OpenAI-compatible providers."""

from __future__ import annotations

from conductgene.agents.prompts import (
    arbiter_messages,
    defender_messages,
    prosecutor_messages,
)
from conductgene.config import Settings
from conductgene.providers.llm import chat_completion_json
from conductgene.schemas import AgentOpinion, EvidenceSnippet, PolicyGene


def ensure_live_mode(settings: Settings) -> None:
    if settings.mode != "live":
        raise RuntimeError("Live mode requested but CONDUCTGENE_MODE is not 'live'")
    if settings.llm_provider == "mock":
        raise RuntimeError("Live agents require CONDUCTGENE_LLM_PROVIDER != mock")


async def run_prosecutor_live(
    settings: Settings,
    transcript: str,
    evidence: list[EvidenceSnippet],
) -> AgentOpinion:
    ensure_live_mode(settings)
    return await chat_completion_json(
        settings,
        prosecutor_messages(transcript, evidence),
        expected_role="prosecutor",
    )


async def run_defender_live(
    settings: Settings,
    transcript: str,
    evidence: list[EvidenceSnippet],
) -> AgentOpinion:
    ensure_live_mode(settings)
    return await chat_completion_json(
        settings,
        defender_messages(transcript, evidence),
        expected_role="defender",
    )


async def run_arbiter_live(
    settings: Settings,
    transcript: str,
    prosecutor: AgentOpinion,
    defender: AgentOpinion,
    evidence: list[EvidenceSnippet],
    genes: list[PolicyGene],
) -> AgentOpinion:
    ensure_live_mode(settings)
    return await chat_completion_json(
        settings,
        arbiter_messages(transcript, prosecutor, defender, evidence, genes),
        expected_role="arbiter",
    )
