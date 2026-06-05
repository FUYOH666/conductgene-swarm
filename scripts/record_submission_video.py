#!/usr/bin/env python3
"""Record UCWS demo video (WebM) — slideshow from step screenshots (reliable)."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from capture_ui_common import (
    ROOT,
    TIMEOUTS,
    build_slideshow_webm,
    build_streamlit_env,
    parse_profile_args,
    run_demo_flow,
    start_streamlit,
    stop_streamlit,
    wait_for_server,
)

OUT_DIR = ROOT / "docs" / "submission"
SLIDES_DIR = OUT_DIR / "video-slides"


def main() -> int:
    args = parse_profile_args("Record UCWS demo video via Playwright + ffmpeg")
    profile = args.profile
    timeouts = TIMEOUTS[profile]

    if shutil.which("ffmpeg") is None:
        raise SystemExit("ffmpeg not found — install via: brew install ffmpeg")

    from playwright.sync_api import sync_playwright

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if SLIDES_DIR.exists():
        for old in SLIDES_DIR.glob("*.png"):
            old.unlink()
    SLIDES_DIR.mkdir(parents=True, exist_ok=True)

    env = build_streamlit_env(profile, prefix="video")
    proc = start_streamlit(env)
    try:
        wait_for_server()
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1200})
            slides = run_demo_flow(page, timeouts, profile, SLIDES_DIR)
            browser.close()

        dest = OUT_DIR / "conductgene-demo.webm"
        build_slideshow_webm(slides, dest, seconds_per_slide=4.0)
        print(f"Recorded demo video: {dest} ({len(slides)} slides, profile={profile})")
        print("Upload to YouTube (unlisted) — see docs/submission/youtube-upload.md")
        return 0
    finally:
        stop_streamlit(proc)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
