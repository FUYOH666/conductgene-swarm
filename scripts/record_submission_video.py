#!/usr/bin/env python3
"""Record UCWS demo video (WebM) via Playwright — upload to YouTube as unlisted."""

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

OUT_DIR = ROOT / "docs" / "submission"
VIDEO_DIR = OUT_DIR / "video"
URL = "http://127.0.0.1:8501"


def main() -> int:
    args = parse_profile_args("Record UCWS demo video via Playwright")
    profile = args.profile
    timeouts = TIMEOUTS[profile]

    from playwright.sync_api import sync_playwright

    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    env = build_streamlit_env(profile, prefix="video")
    proc = start_streamlit(env)
    try:
        wait_for_server()
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1280, "height": 900},
                record_video_dir=str(VIDEO_DIR),
                record_video_size={"width": 1280, "height": 900},
            )
            page = context.new_page()
            page.goto(URL, wait_until="networkidle")
            page.wait_for_timeout(timeouts.page_load_ms)

            if profile == "live":
                assert_live_banner(page)
                page.get_by_text("Model Jury").scroll_into_view_if_needed()
                page.wait_for_timeout(timeouts.between_steps_ms)

            select_scenario(page, "CASE-002", timeouts)
            page.wait_for_timeout(timeouts.between_steps_ms)
            run_analyze(page, timeouts)
            page.get_by_text("3. Agent swarm").scroll_into_view_if_needed()
            page.wait_for_timeout(timeouts.between_steps_ms)
            page.get_by_text("4. Supervisor override").scroll_into_view_if_needed()
            approve_policy_gene(page, timeouts)
            select_scenario(page, "CASE-005", timeouts)
            page.wait_for_timeout(timeouts.between_steps_ms)
            run_analyze(page, timeouts)
            page.get_by_text("5. Policy Genes + audit").scroll_into_view_if_needed()
            page.wait_for_timeout(timeouts.between_steps_ms * 2)

            video_path = page.video.path() if page.video else None
            context.close()
            browser.close()

        if video_path:
            dest = OUT_DIR / "conductgene-demo.webm"
            Path(video_path).rename(dest)
            print(f"Recorded demo video: {dest} (profile={profile})")
            print("Upload to YouTube (unlisted) — see docs/submission/youtube-upload.md")
        return 0
    finally:
        stop_streamlit(proc)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
