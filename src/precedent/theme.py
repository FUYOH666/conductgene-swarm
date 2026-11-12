"""Design tokens shared by every rendered artifact.

Figures, the social card, evidence packs and the Pages site read colours and
type from here, so the project has one visual identity. The palette follows the
lab's site (scanovich.ai): paper, ink, one pen colour; red and green appear only
where the gate blocks or passes.
"""

from __future__ import annotations

from dataclasses import dataclass

SERIF = "'Instrument Serif', 'Iowan Old Style', 'Palatino Linotype', Palatino, Georgia, serif"
SANS = "Geist, -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif"
MONO = "'Geist Mono', ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace"


@dataclass(frozen=True)
class Palette:
    name: str
    bg: str
    panel: str
    ink: str
    muted: str
    faint: str
    line: str
    accent: str
    green: str
    green_bg: str
    red: str
    red_bg: str


LIGHT = Palette(
    name="light",
    bg="#f5f3ee",
    panel="#ece9e1",
    ink="#16181d",
    muted="#585d66",
    faint="#8a8f98",
    line="#d6d2c7",
    accent="#1c3f9e",
    green="#1a7f37",
    green_bg="#dcefdc",
    red="#c4262e",
    red_bg="#f6dcd8",
)

DARK = Palette(
    name="dark",
    bg="#0f1115",
    panel="#171a20",
    ink="#e9e6df",
    muted="#a3a7af",
    faint="#6f747d",
    line="#2a2e36",
    accent="#8fb0ff",
    green="#4cc26a",
    green_bg="#14261a",
    red="#ff6b62",
    red_bg="#2c1513",
)


def css_variables(p: Palette) -> str:
    return "".join(f"--{k.replace('_', '-')}:{v};" for k, v in p.__dict__.items() if k != "name")
