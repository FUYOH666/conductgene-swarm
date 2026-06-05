#!/usr/bin/env python3
"""Capture Streamlit UI screenshots for UCWS portal submission."""

from __future__ import annotations

import sys
from pathlib import Path

from capture_ui_common import (
    ROOT,
    TIMEOUTS,
    approve_policy_gene,
    assert_live_banner,
    build_streamlit_env,
    parse_profile_args,
    run_analyze,
    select_scenario,
    start_streamlit,
    stop_streamlit,
    wait_for_server,
)

OUT = ROOT / "docs" / "submission"
URL = "http://127.0.0.1:8501"


def main() -> int:
    args = parse_profile_args("Capture Streamlit screenshots for UCWS portal")
    profile = args.profile
    timeouts = TIMEOUTS[profile]

    from playwright.sync_api import sync_playwright

    OUT.mkdir(parents=True, exist_ok=True)
    env = build_streamlit_env(profile, prefix="capture")
    proc = start_streamlit(env)
    try:
        wait_for_server()
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1200})
            page.goto(URL, wait_until="networkidle")
            page.wait_for_timeout(timeouts.page_load_ms)

            if profile == "live":
                assert_live_banner(page)

            select_scenario(page, "CASE-002", timeouts)
            run_analyze(page, timeouts)
            page.screenshot(path=str(OUT / "screenshot-1-swarm.png"), full_page=True)

            page.get_by_text("3. Agent swarm").scroll_into_view_if_needed()
            page.wait_for_timeout(timeouts.between_steps_ms)
            page.screenshot(path=str(OUT / "screenshot-2-agents.png"), full_page=True)

            approve_policy_gene(page, timeouts)

            select_scenario(page, "CASE-005", timeouts)
            run_analyze(page, timeouts)
            page.get_by_text("5. Policy Genes + audit").scroll_into_view_if_needed()
            page.wait_for_timeout(timeouts.between_steps_ms)
            page.screenshot(path=str(OUT / "screenshot-3-gene-learning.png"), full_page=True)

            browser.close()
        print(f"Captured 3 screenshots in {OUT} (profile={profile})")
        return 0
    finally:
        stop_streamlit(proc)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
