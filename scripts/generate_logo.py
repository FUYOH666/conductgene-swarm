#!/usr/bin/env python3
"""Generate 512x512 portal logo if missing."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "submission" / "logo-512.png"


def main() -> int:
    if OUT.exists():
        print(f"Logo already exists: {OUT}")
        return 0

    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise SystemExit("Pillow required: uv sync --extra ui") from exc

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (512, 512), color=(15, 23, 42))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((32, 32, 480, 480), radius=48, fill=(30, 58, 95), outline=(56, 189, 248), width=4)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 72)
        small = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 28)
    except OSError:
        font = ImageFont.load_default()
        small = font

    draw.text((96, 180), "CG", fill=(224, 242, 254), font=font)
    draw.text((72, 320), "ConductGene", fill=(186, 230, 253), font=small)
    draw.text((88, 360), "Swarm", fill=(125, 211, 252), font=small)
    img.save(OUT, format="PNG")
    print(f"Generated logo: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
