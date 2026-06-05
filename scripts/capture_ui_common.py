"""Shared Playwright helpers for submission screenshots and demo video."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

ROOT = Path(__file__).resolve().parents[1]
URL = "http://127.0.0.1:8501"

if TYPE_CHECKING:
    from playwright.sync_api import Page

Profile = Literal["mock", "live"]


@dataclass(frozen=True)
class CaptureTimeouts:
    page_load_ms: int
    analyze_ms: int
    gene_approve_ms: int
    between_steps_ms: int


TIMEOUTS: dict[Profile, CaptureTimeouts] = {
    "mock": CaptureTimeouts(
        page_load_ms=2500,
        analyze_ms=8000,
        gene_approve_ms=12000,
        between_steps_ms=800,
    ),
    "live": CaptureTimeouts(
        page_load_ms=4000,
        analyze_ms=420_000,
        gene_approve_ms=300_000,
        between_steps_ms=1500,
    ),
}


def parse_profile_args(description: str) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--profile",
        choices=["mock", "live"],
        default=os.environ.get("CONDUCTGENE_CAPTURE_PROFILE", "live"),
        help="mock = deterministic CI demo; live = LM Studio + qdrant_rerank",
    )
    return parser.parse_args()


def build_streamlit_env(profile: Profile, prefix: str) -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("CONDUCTGENE_GENE_STORE_PATH", str(ROOT / "reports" / f".{prefix}_genes.jsonl"))
    env.setdefault("CONDUCTGENE_AUDIT_STORE_PATH", str(ROOT / "reports" / f".{prefix}_audit.jsonl"))
    env.setdefault(
        "CONDUCTGENE_GENE_AUDIT_STORE_PATH",
        str(ROOT / "reports" / f".{prefix}_gene_events.jsonl"),
    )
    env["CONDUCTGENE_UI_USE_API"] = "false"

    if profile == "mock":
        env["CONDUCTGENE_MODE"] = "mock"
        env["CONDUCTGENE_LLM_PROVIDER"] = "mock"
        env["CONDUCTGENE_RETRIEVAL_MODE"] = "memory"
        return env

    sys.path.insert(0, str(ROOT / "src"))
    from conductgene.config import Settings

    settings = Settings()
    settings.resolve_paths(ROOT)
    if not settings.lmstudio_model:
        raise RuntimeError(
            "CONDUCTGENE_LMSTUDIO_MODEL is empty — set in .env before live capture"
        )

    env["CONDUCTGENE_MODE"] = "live"
    env["CONDUCTGENE_LLM_PROVIDER"] = "lmstudio"
    env["CONDUCTGENE_RETRIEVAL_MODE"] = "qdrant_rerank"
    env["CONDUCTGENE_LMSTUDIO_MODEL"] = settings.lmstudio_model
    env.setdefault("CONDUCTGENE_ENABLE_RERANKER", "true")
    if settings.embedding_base_url:
        env.setdefault("CONDUCTGENE_EMBEDDING_BASE_URL", settings.embedding_base_url)
    if settings.reranker_base_url:
        env.setdefault("CONDUCTGENE_RERANKER_BASE_URL", settings.reranker_base_url)
    if settings.qdrant_url:
        env.setdefault("CONDUCTGENE_QDRANT_URL", settings.qdrant_url)
    return env


def wait_for_server(timeout: float = 60.0) -> None:
    import urllib.request

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(URL, timeout=2) as resp:
                if resp.status == 200:
                    return
        except Exception:
            time.sleep(1)
    raise RuntimeError(f"Streamlit did not start at {URL}")


def start_streamlit(env: dict[str, str]) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        ["uv", "run", "streamlit", "run", "src/conductgene/ui/app.py", "--server.headless=true"],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def stop_streamlit(proc: subprocess.Popen[bytes]) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def select_scenario(page: Page, case_id: str, timeouts: CaptureTimeouts) -> None:
    page.get_by_text("1. Transcript").scroll_into_view_if_needed()
    main = page.get_by_test_id("stMainBlockContainer")
    main.locator('[data-baseweb="select"]').first.click()
    page.wait_for_timeout(timeouts.between_steps_ms)
    page.locator(f'[role="option"]:has-text("{case_id}")').click()
    page.wait_for_timeout(timeouts.between_steps_ms)


def run_analyze(page: Page, timeouts: CaptureTimeouts) -> None:
    page.get_by_role("button", name="Run swarm analyze").click()
    page.get_by_text("No analysis yet.").wait_for(state="hidden", timeout=timeouts.analyze_ms)
    page.wait_for_timeout(timeouts.between_steps_ms)


def approve_policy_gene(page: Page, timeouts: CaptureTimeouts) -> None:
    page.get_by_text("4. Supervisor override").scroll_into_view_if_needed()
    page.wait_for_timeout(timeouts.between_steps_ms)
    page.get_by_role("button", name="Approve Policy Gene").click()
    page.get_by_text("Policy Gene stored").wait_for(state="visible", timeout=timeouts.gene_approve_ms)
    page.wait_for_timeout(timeouts.between_steps_ms)


def assert_live_banner(page: Page) -> None:
    main = page.get_by_test_id("stMainBlockContainer")
    main.get_by_text("Live Mode").wait_for(state="visible", timeout=10_000)
    main.get_by_text("lmstudio").wait_for(state="visible", timeout=10_000)
    main.get_by_text("qdrant_rerank").wait_for(state="visible", timeout=10_000)
