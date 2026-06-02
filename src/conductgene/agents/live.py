"""Live LLM agent mode — OpenAI-compatible instruct gateway."""

from __future__ import annotations

from conductgene.config import Settings
from conductgene.logutil import get_logger
from conductgene.schemas import AgentOpinion, EvidenceSnippet, PolicyGene

logger = get_logger(__name__)


def ensure_live_mode(settings: Settings) -> None:
    if settings.mode != "live":
        raise RuntimeError("Live mode requested but CONDUCTGENE_MODE is not 'live'")


async def run_prosecutor_live(
    settings: Settings,
    transcript: str,
    evidence: list[EvidenceSnippet],
) -> AgentOpinion:
    ensure_live_mode(settings)
    logger.warning(
        "live mode prosecutor not yet wired; falling back to mock agents",
        extra={"meta": {"llm_base_url": settings.llm_base_url}},
    )
    from conductgene.agents.roles import run_prosecutor

    return run_prosecutor(transcript, evidence)


async def run_defender_live(
    settings: Settings,
    transcript: str,
    evidence: list[EvidenceSnippet],
) -> AgentOpinion:
    ensure_live_mode(settings)
    from conductgene.agents.roles import run_defender

    return run_defender(transcript, evidence)


async def run_arbiter_live(
    settings: Settings,
    transcript: str,
    prosecutor: AgentOpinion,
    defender: AgentOpinion,
    evidence: list[EvidenceSnippet],
    genes: list[PolicyGene],
) -> AgentOpinion:
    ensure_live_mode(settings)
    from conductgene.agents.roles import run_arbiter

    return run_arbiter(transcript, prosecutor, defender, evidence, genes)
