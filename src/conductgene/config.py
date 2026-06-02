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
    llm_base_url: str = "http://127.0.0.1:8002/v1"
    llm_api_key: str | None = None
    llm_model: str = "default"
    llm_timeout: float = 120.0
    embedding_base_url: str | None = None
    reranker_base_url: str | None = None
    host: str = "127.0.0.1"
    port: int = 8090
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
        for attr in ("gene_store_path", "audit_store_path", "gene_audit_store_path", "kb_dir", "scenarios_dir"):
            p = getattr(self, attr)
            if not p.is_absolute():
                setattr(self, attr, root / p)
