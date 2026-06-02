#!/usr/bin/env python3
"""Record UCWS demo video (WebM) via Playwright — upload to YouTube as unlisted."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "submission"
VIDEO_DIR = OUT_DIR / "video"
URL = "http://127.0.0.1:8501"


def _wait_for_server(timeout: float = 45.0) -> None:
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


def main() -> int:
    from playwright.sync_api import sync_playwright

    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["CONDUCTGENE_MODE"] = "mock"
    env.setdefault("CONDUCTGENE_GENE_STORE_PATH", str(ROOT / "reports" / ".video_genes.jsonl"))
    env.setdefault("CONDUCTGENE_AUDIT_STORE_PATH", str(ROOT / "reports" / ".video_audit.jsonl"))
    env.setdefault("CONDUCTGENE_GENE_AUDIT_STORE_PATH", str(ROOT / "reports" / ".video_gene_events.jsonl"))

    proc = subprocess.Popen(
        ["uv", "run", "streamlit", "run", "src/conductgene/ui/app.py", "--server.headless=true"],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_for_server()
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1280, "height": 900},
                record_video_dir=str(VIDEO_DIR),
                record_video_size={"width": 1280, "height": 900},
            )
            page = context.new_page()
            page.goto(URL, wait_until="networkidle")
            page.wait_for_timeout(2500)

            def select_scenario(case_id: str) -> None:
                page.get_by_text("1. Transcript").scroll_into_view_if_needed()
                page.locator('[data-baseweb="select"]').first.click()
                page.wait_for_timeout(700)
                page.locator(f'[role="option"]:has-text("{case_id}")').click()
                page.wait_for_timeout(700)

            select_scenario("CASE-002")
            page.wait_for_timeout(1500)
            page.get_by_role("button", name="Run swarm analyze").click()
            page.wait_for_timeout(3500)
            page.get_by_text("3. Agent swarm").scroll_into_view_if_needed()
            page.wait_for_timeout(2000)
            page.get_by_text("4. Supervisor override").scroll_into_view_if_needed()
            page.wait_for_timeout(1500)
            page.get_by_role("button", name="Approve Policy Gene").click()
            page.wait_for_timeout(4500)
            select_scenario("CASE-005")
            page.wait_for_timeout(1000)
            page.get_by_role("button", name="Run swarm analyze").click()
            page.wait_for_timeout(3500)
            page.get_by_text("5. Policy Genes + audit").scroll_into_view_if_needed()
            page.wait_for_timeout(2500)

            video_path = page.video.path() if page.video else None
            context.close()
            browser.close()

        if video_path:
            dest = OUT_DIR / "conductgene-demo.webm"
            Path(video_path).rename(dest)
            print(f"Recorded demo video: {dest}")
            print("Upload to YouTube (unlisted) — see docs/submission/youtube-upload.md")
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    sys.exit(main())
