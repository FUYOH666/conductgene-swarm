#!/usr/bin/env python3
"""Capture Streamlit UI screenshots for UCWS portal submission."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "submission"
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

    OUT.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["CONDUCTGENE_MODE"] = "mock"
    env.setdefault("CONDUCTGENE_GENE_STORE_PATH", str(ROOT / "reports" / ".capture_genes.jsonl"))
    env.setdefault("CONDUCTGENE_AUDIT_STORE_PATH", str(ROOT / "reports" / ".capture_audit.jsonl"))
    env.setdefault("CONDUCTGENE_GENE_AUDIT_STORE_PATH", str(ROOT / "reports" / ".capture_gene_events.jsonl"))

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
            page = browser.new_page(viewport={"width": 1440, "height": 1200})
            page.goto(URL, wait_until="networkidle")
            page.wait_for_timeout(2000)

            def select_scenario(case_id: str) -> None:
                page.get_by_text("1. Transcript").scroll_into_view_if_needed()
                page.locator('[data-baseweb="select"]').first.click()
                page.wait_for_timeout(800)
                page.locator(f'[role="option"]:has-text("{case_id}")').click()
                page.wait_for_timeout(800)

            # Screenshot 1: CASE-002 analyze
            select_scenario("CASE-002")
            page.get_by_role("button", name="Run swarm analyze").click()
            page.wait_for_timeout(3500)
            page.screenshot(path=str(OUT / "screenshot-1-swarm.png"), full_page=True)

            # Screenshot 2: agent swarm section
            page.get_by_text("3. Agent swarm").scroll_into_view_if_needed()
            page.wait_for_timeout(800)
            page.screenshot(path=str(OUT / "screenshot-2-agents.png"), full_page=True)

            # Approve Policy Gene
            page.get_by_text("4. Supervisor override").scroll_into_view_if_needed()
            page.get_by_role("button", name="Approve Policy Gene").click()
            page.wait_for_timeout(5000)

            # CASE-005 held-out
            select_scenario("CASE-005")
            page.get_by_role("button", name="Run swarm analyze").click()
            page.wait_for_timeout(4000)
            page.get_by_text("5. Policy Genes + audit").scroll_into_view_if_needed()
            page.wait_for_timeout(500)
            page.screenshot(path=str(OUT / "screenshot-3-gene-learning.png"), full_page=True)

            browser.close()
        print(f"Captured 3 screenshots in {OUT}")
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    sys.exit(main())
