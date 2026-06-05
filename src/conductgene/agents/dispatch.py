"""Agent dispatch — mock rules vs live LLM."""

from __future__ import annotations

from conductgene.agents.live import (
    run_arbiter_live,
    run_defender_live,
    run_prosecutor_live,
)
from conductgene.agents.roles import run_arbiter, run_defender, run_prosecutor
from conductgene.config import Settings
from conductgene.logutil import get_logger
from conductgene.schemas import AgentOpinion, EvidenceSnippet, PolicyGene

logger = get_logger(__name__)


def uses_live_llm(settings: Settings) -> bool:
    return settings.llm_provider != "mock"


def _live_active(settings: Settings) -> bool:
    return uses_live_llm(settings) and settings.mode == "live"


def _warn_mock_fallback(settings: Settings) -> None:
    if uses_live_llm(settings) and settings.mode != "live":
        logger.warning(
            "llm_provider=%s but mode=%s; set CONDUCTGENE_MODE=live for LLM agents",
            settings.llm_provider,
            settings.mode,
        )


async def run_prosecutor_agent(
    settings: Settings,
    transcript: str,
    evidence: list[EvidenceSnippet],
) -> AgentOpinion:
    if not _live_active(settings):
        _warn_mock_fallback(settings)
        return run_prosecutor(transcript, evidence)
    return await run_prosecutor_live(settings, transcript, evidence)


async def run_defender_agent(
    settings: Settings,
    transcript: str,
    evidence: list[EvidenceSnippet],
) -> AgentOpinion:
    if not _live_active(settings):
        _warn_mock_fallback(settings)
        return run_defender(transcript, evidence)
    return await run_defender_live(settings, transcript, evidence)


async def run_arbiter_agent(
    settings: Settings,
    transcript: str,
    prosecutor: AgentOpinion,
    defender: AgentOpinion,
    evidence: list[EvidenceSnippet],
    genes: list[PolicyGene],
) -> AgentOpinion:
    if not _live_active(settings):
        _warn_mock_fallback(settings)
        return run_arbiter(prosecutor, defender, evidence)
    return await run_arbiter_live(
        settings, transcript, prosecutor, defender, evidence, genes
    )
