"""OpenAI-compatible LLM provider (OpenRouter, LM Studio, instruct gateway)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal

from openai import AsyncOpenAI
from pydantic import ValidationError

from conductgene.config import Settings
from conductgene.logutil import get_logger
from conductgene.schemas import AgentOpinion

logger = get_logger(__name__)

LlmProviderName = Literal["openrouter", "lmstudio", "instruct"]
MAX_JSON_RETRIES = 2


@dataclass(frozen=True)
class LlmConfig:
    provider: LlmProviderName
    base_url: str
    api_key: str | None
    model: str
    timeout: float


def resolve_llm_config(settings: Settings, model_override: str | None = None) -> LlmConfig:
    provider = settings.llm_provider
    if provider == "mock":
        raise ValueError("resolve_llm_config called with mock provider")

    if provider == "openrouter":
        if not settings.openrouter_api_key:
            raise ValueError("CONDUCTGENE_OPENROUTER_API_KEY required for openrouter provider")
        models = settings.openrouter_model_list()
        model = model_override or (models[0] if models else "openai/gpt-4o-mini")
        return LlmConfig(
            provider="openrouter",
            base_url=settings.openrouter_base_url.rstrip("/"),
            api_key=settings.openrouter_api_key,
            model=model,
            timeout=settings.llm_timeout,
        )

    if provider == "lmstudio":
        model = model_override or settings.lmstudio_model
        if not model:
            raise ValueError(
                "CONDUCTGENE_LMSTUDIO_MODEL required (or pass --model); "
                "check LM Studio /v1/models"
            )
        return LlmConfig(
            provider="lmstudio",
            base_url=settings.lmstudio_base_url.rstrip("/"),
            api_key="lm-studio",
            model=model,
            timeout=settings.llm_timeout,
        )

    if provider == "instruct":
        model = model_override or settings.llm_model
        return LlmConfig(
            provider="instruct",
            base_url=settings.llm_base_url.rstrip("/"),
            api_key=settings.llm_api_key or "instruct-local",
            model=model,
            timeout=settings.llm_timeout,
        )

    raise ValueError(f"Unsupported LLM provider: {provider}")


def _client(cfg: LlmConfig) -> AsyncOpenAI:
    return AsyncOpenAI(
        base_url=cfg.base_url,
        api_key=cfg.api_key,
        timeout=cfg.timeout,
    )


def _extra_headers(cfg: LlmConfig) -> dict[str, str]:
    if cfg.provider == "openrouter":
        return {
            "HTTP-Referer": "https://github.com/FUYOH666/conductgene-swarm",
            "X-Title": "ConductGene Swarm",
        }
    return {}


async def chat_completion_json(
    settings: Settings,
    messages: list[dict[str, str]],
    *,
    expected_role: str,
    model_override: str | None = None,
) -> AgentOpinion:
    """Call chat completion and parse structured AgentOpinion JSON."""
    cfg = resolve_llm_config(settings, model_override=model_override)
    client = _client(cfg)
    headers = _extra_headers(cfg)
    last_error: str | None = None

    for attempt in range(MAX_JSON_RETRIES + 1):
        retry_hint = ""
        if attempt > 0 and last_error:
            retry_hint = (
                f"\n\nPrevious response failed validation: {last_error}. "
                "Return valid JSON only matching AgentOpinion schema."
            )
        req_messages = list(messages)
        if retry_hint:
            req_messages = req_messages + [{"role": "user", "content": retry_hint}]

        logger.info(
            "llm chat request",
            extra={
                "meta": {
                    "provider": cfg.provider,
                    "model": cfg.model,
                    "attempt": attempt,
                }
            },
        )

        create_kwargs: dict = {
            "model": cfg.model,
            "messages": req_messages,
            "temperature": 0.1,
            "extra_headers": headers or None,
        }
        if cfg.provider == "openrouter":
            create_kwargs["response_format"] = {"type": "json_object"}
        try:
            resp = await client.chat.completions.create(**create_kwargs)
        except Exception as exc:
            if cfg.provider != "openrouter" and "response_format" in str(exc).lower():
                resp = await client.chat.completions.create(
                    model=cfg.model,
                    messages=req_messages,
                    temperature=0.1,
                    extra_headers=headers or None,
                )
            else:
                raise
        if not resp.choices:
            last_error = "empty choices from LLM"
            continue
        raw = (resp.choices[0].message.content or "").strip()
        try:
            data = json.loads(raw)
            opinion = AgentOpinion.model_validate(data)
            if opinion.role != expected_role:
                opinion = opinion.model_copy(update={"role": expected_role})  # type: ignore[arg-type]
            return opinion
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = str(exc)
            logger.warning(
                "llm json parse failed",
                extra={"meta": {"attempt": attempt, "error": last_error[:200]}},
            )

    raise RuntimeError(f"LLM returned invalid JSON after retries: {last_error}")
