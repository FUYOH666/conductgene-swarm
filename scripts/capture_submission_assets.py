#!/usr/bin/env python3
"""Capture Streamlit UI screenshots for UCWS portal submission."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from capture_ui_common import (
    ROOT,
    TIMEOUTS,
    build_streamlit_env,
    parse_profile_args,
    run_demo_flow,
    start_streamlit,
    stop_streamlit,
    wait_for_server,
)

OUT = ROOT / "docs" / "submission"


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
            slides = run_demo_flow(page, timeouts, profile, OUT / ".capture-slides")
            browser.close()

        mapping = {
            "04_case002_results.png": "screenshot-1-swarm.png",
            "05_agent_swarm.png": "screenshot-2-agents.png",
            "09_gene_learning.png": "screenshot-3-gene-learning.png",
        }
        for src_name, dest_name in mapping.items():
            src = OUT / ".capture-slides" / src_name
            if src.exists():
                shutil.copy2(src, OUT / dest_name)

        print(f"Captured 3 screenshots in {OUT} (profile={profile})")
        return 0
    finally:
        stop_streamlit(proc)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
