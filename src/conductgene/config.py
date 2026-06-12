"""Application settings via pydantic-settings."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CONDUCTGENE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    mode: Literal["mock", "live"] = "mock"
    llm_provider: Literal["mock", "openrouter", "lmstudio", "instruct"] = "mock"
    retrieval_mode: Literal["memory", "qdrant", "qdrant_rerank"] = "memory"
    retrieval_fallback_to_memory: bool = True

    llm_base_url: str = "http://127.0.0.1:8002/v1"
    llm_api_key: str | None = None
    llm_model: str = "default"
    llm_timeout: float = 120.0

    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_api_key: str | None = None
    openrouter_models: str = (
        "anthropic/claude-3.5-sonnet,openai/gpt-4o-mini,google/gemini-flash-1.5"
    )

    lmstudio_base_url: str = "http://127.0.0.1:1234/v1"
    lmstudio_model: str = ""

    embedding_base_url: str | None = None
    embedding_model: str = "BAAI/bge-m3"
    reranker_base_url: str | None = None
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    enable_reranker: bool = False
    service_timeout: float = 30.0

    qdrant_url: str | None = None
    qdrant_api_key: str | None = None
    qdrant_collection: str = "conductgene_policy_kb"

    host: str = "127.0.0.1"
    port: int = 8090
    # API auth: when set, all endpoints except health/readiness require X-API-Key.
    api_key: str | None = None
    # Requests per minute per client on heavy endpoints; 0 disables limiting.
    rate_limit_rpm: int = 0
    gene_store_path: Path = Field(default=Path("data/evolution/genes.jsonl"))
    audit_store_path: Path = Field(default=Path("data/audit/cases.jsonl"))
    gene_audit_store_path: Path = Field(default=Path("data/audit/gene_events.jsonl"))
    kb_dir: Path = Field(default=Path("data/synthetic/kb"))
    scenarios_dir: Path = Field(default=Path("data/scenarios"))
    rerank_min_score: float = 0.25
    rerank_top_n: int = 8
    ui_use_api: bool = False
    api_base_url: str = "http://127.0.0.1:8090"

    def resolve_paths(self, base: Path | None = None) -> None:
        root = base or Path.cwd()
        for attr in (
            "gene_store_path",
            "audit_store_path",
            "gene_audit_store_path",
            "kb_dir",
            "scenarios_dir",
        ):
            p = getattr(self, attr)
            if not p.is_absolute():
                setattr(self, attr, root / p)

    def openrouter_model_list(self) -> list[str]:
        return [m.strip() for m in self.openrouter_models.split(",") if m.strip()]
