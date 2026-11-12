"""Draw the README figures as SVG, in a light and a dark variant.

    uv run python scripts/figures.py

Writes docs/assets/{banner,lifecycle,flips}-{light,dark}.svg. The flip map is
computed from the pack and the recorded judge runs, so it cannot drift from
the numbers in docs/results.
"""

from __future__ import annotations

from html import escape
from pathlib import Path

from precedent.gate import run_gate
from precedent.judge import Judge, judge_all
from precedent.judge.cassette import ReplayJudge
from precedent.judge.heuristic import HeuristicJudge
from precedent.models import Correction, GateReport
from precedent.pack import load_pack
from precedent.theme import DARK, LIGHT, MONO, SANS, SERIF, Palette

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "assets"


def svg(width: int, height: int, body: str, p: Palette, title: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">\n'
        f"<title>{escape(title)}</title>\n"
        f'<rect width="{width}" height="{height}" fill="{p.bg}"/>\n{body}</svg>\n'
    )


def text(
    x: float,
    y: float,
    s: str,
    *,
    size: float,
    fill: str,
    font: str = SANS,
    weight: int = 400,
    anchor: str = "start",
    spacing: float = 0,
) -> str:
    ls = f' letter-spacing="{spacing}"' if spacing else ""
    return (
        f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" font-weight="{weight}" '
        f'fill="{fill}" text-anchor="{anchor}"{ls}>{escape(s)}</text>\n'
    )


def mark(x: float, y: float, s: float, p: Palette) -> str:
    """The logo: a two-line diff. One line removed, one added."""
    h = s * 0.42
    return (
        f'<rect x="{x}" y="{y}" width="{s}" height="{h}" rx="{h * 0.28}" fill="{p.red_bg}" '
        f'stroke="{p.red}" stroke-width="{s * 0.04}"/>\n'
        f'<rect x="{x + s * 0.14}" y="{y + h / 2 - s * 0.03}" width="{s * 0.2}" height="{s * 0.06}" '
        f'rx="{s * 0.03}" fill="{p.red}"/>\n'
        f'<rect x="{x}" y="{y + h + s * 0.16}" width="{s}" height="{h}" rx="{h * 0.28}" '
        f'fill="{p.green_bg}" stroke="{p.green}" stroke-width="{s * 0.04}"/>\n'
        f'<rect x="{x + s * 0.14}" y="{y + h + s * 0.16 + h / 2 - s * 0.03}" width="{s * 0.2}" '
        f'height="{s * 0.06}" rx="{s * 0.03}" fill="{p.green}"/>\n'
        f'<rect x="{x + s * 0.21}" y="{y + h + s * 0.16 + h / 2 - s * 0.1}" width="{s * 0.06}" '
        f'height="{s * 0.2}" rx="{s * 0.03}" fill="{p.green}"/>\n'
    )


def badge(x: float, y: float, ok: bool, p: Palette, size: float = 13) -> str:
    label = "✓ PASSED" if ok else "✗ BLOCKED"
    w = size * 6.4
    fg, bg = (p.green, p.green_bg) if ok else (p.red, p.red_bg)
    return (
        f'<rect x="{x}" y="{y - size * 1.15}" width="{w}" height="{size * 1.7}" rx="{size * 0.85}" '
        f'fill="{bg}" stroke="{fg}" stroke-width="1"/>\n'
        + text(x + w / 2, y, label, size=size, fill=fg, font=MONO, weight=700, anchor="middle")
    )


# --- banner -------------------------------------------------------------------


def banner(p: Palette, width: int = 1280, height: int = 400) -> str:
    b = mark(64, 74, 56, p)
    b += text(140, 122, "precedent", size=76, fill=p.ink, font=SERIF, weight=400, spacing=-1)
    b += text(66, 186, "Pull requests for AI judgment", size=32, fill=p.ink, weight=500)
    b += text(
        66,
        232,
        "A human correction to an LLM judge becomes a scoped rule.",
        size=20,
        fill=p.muted,
    )
    b += text(
        66,
        262,
        "It is tested on every case, approved by a second person, and reversible.",
        size=20,
        fill=p.muted,
    )
    b += text(66, 330, "gate · four-eyes · hash-chained log · offline", size=15,
              fill=p.faint, font=MONO)  # fmt: skip

    # the story in two lines
    cx, cy, cw, ch = 760, 70, 456, 260
    b += (
        f'<rect x="{cx}" y="{cy}" width="{cw}" height="{ch}" rx="14" fill="{p.panel}" '
        f'stroke="{p.line}"/>\n'
    )
    b += text(cx + 24, cy + 40, "one correction, two rules", size=14, fill=p.faint, font=MONO)
    rows = [
        ("v1", "when mentions_repayment", False, "fixes 2 · breaks 3"),
        ("v2", "when supervisor_callback", True, "fixes 3 · breaks 0"),
    ]
    for i, (ver, cond, ok, stats) in enumerate(rows):
        y = cy + 92 + i * 92
        b += text(cx + 24, y, ver, size=16, fill=p.accent, font=MONO, weight=700)
        b += text(cx + 64, y, cond, size=16, fill=p.ink, font=MONO)
        b += text(cx + 64, y + 30, "→ escalation = pass", size=16, fill=p.muted, font=MONO)
        b += badge(cx + cw - 128, y + 2, ok, p, size=13)
        b += text(cx + cw - 24, y + 30, stats, size=13, fill=p.faint, font=MONO, anchor="end")
    return svg(width, height, b, p, "precedent — pull requests for AI judgment")


# --- lifecycle -------------------------------------------------------------------


def lifecycle(p: Palette, width: int = 1280, height: int = 446) -> str:
    nodes = [
        ("correction", "a reviewer disagrees", "C-0001"),
        ("rule", "a reason, as predicates", "when … then …"),
        ("gate", "tested on every case", "0 regressions"),
        ("approval", "a second person", "author ≠ approver"),
        ("active", "until reverted", "revert = 1 event"),
    ]
    nw, nh, gap, x0, y0 = 214, 126, 42, 26, 64
    b = ""
    centers = []
    for i, (title, sub, mono) in enumerate(nodes):
        x = x0 + i * (nw + gap)
        is_gate = title == "gate"
        stroke = p.accent if is_gate else p.line
        sw = 2 if is_gate else 1
        b += (
            f'<rect x="{x}" y="{y0}" width="{nw}" height="{nh}" rx="12" fill="{p.panel}" '
            f'stroke="{stroke}" stroke-width="{sw}"/>\n'
        )
        b += text(x + 18, y0 + 40, title, size=26, fill=p.ink, weight=700)
        b += text(x + 18, y0 + 74, sub, size=17, fill=p.muted)
        b += text(x + 18, y0 + 104, mono, size=15, fill=p.accent if is_gate else p.faint, font=MONO)
        centers.append(x + nw / 2)
        if i < len(nodes) - 1:
            ax, ay = x + nw + 8, y0 + nh / 2
            b += (
                f'<line x1="{ax}" y1="{ay}" x2="{ax + gap - 18}" y2="{ay}" stroke="{p.muted}" '
                f'stroke-width="2"/>\n'
                f'<path d="M{ax + gap - 18} {ay - 6} L{ax + gap - 8} {ay} L{ax + gap - 18} {ay + 6} Z" '
                f'fill="{p.muted}"/>\n'
            )

    # BLOCKED loop: gate back to rule
    gx, rx = centers[2], centers[1]
    ly = y0 + nh
    b += (
        f'<path d="M{gx} {ly + 6} C{gx} {ly + 70}, {rx} {ly + 70}, {rx} {ly + 12}" fill="none" '
        f'stroke="{p.red}" stroke-width="2" stroke-dasharray="6 5"/>\n'
        f'<path d="M{rx - 6} {ly + 20} L{rx} {ly + 8} L{rx + 6} {ly + 20} Z" fill="{p.red}"/>\n'
    )
    b += text((gx + rx) / 2, ly + 80, "BLOCKED → new version", size=17, fill=p.red, font=MONO,
              anchor="middle", weight=700)  # fmt: skip

    # event log band
    by = 318
    b += text(x0, by - 14, "hash-chained event log", size=16, fill=p.faint, font=MONO)
    b += (
        f'<rect x="{x0}" y="{by}" width="{width - 2 * x0}" height="66" rx="10" fill="none" '
        f'stroke="{p.line}"/>\n'
        f'<line x1="{centers[0]}" y1="{by + 22}" x2="{centers[-1]}" y2="{by + 22}" '
        f'stroke="{p.faint}" stroke-width="1"/>\n'
    )
    labels = [
        "correction.recorded",
        "rule.proposed",
        "rule.gated",
        "rule.approved",
        "rule.reverted",
    ]
    for cx, lab in zip(centers, labels, strict=True):
        b += (
            f'<line x1="{cx}" y1="{y0 + nh}" x2="{cx}" y2="{by + 16}" stroke="{p.line}" '
            f'stroke-dasharray="2 4"/>\n'
        )
        b += f'<circle cx="{cx}" cy="{by + 22}" r="5.5" fill="{p.accent}"/>\n'
        b += text(cx, by + 50, lab, size=15, fill=p.muted, font=MONO, anchor="middle")
    b += text(x0, by + 94, "sha256(prev ‖ event) · UPDATE/DELETE refused · audit verify recomputes the chain",
              size=15, fill=p.faint, font=MONO)  # fmt: skip
    return svg(width, height, b, p, "Rule lifecycle: correction, rule, gate, approval, active")


# --- flip map ---------------------------------------------------------------------


def gate_reports() -> list[tuple[str, str, GateReport]]:
    pack = load_pack("collections-conduct")
    case = pack.case("CASE-019")
    corr = Correction(
        id="C-0001",
        pack=pack.id,
        case_id=case.id,
        case_hash=case.hash,
        item="escalation_offered",
        ai_label="needs_review",
        human_label="pass",
        reviewer="maria",
        error_type="policy_misinterpretation",
    )
    judges: list[tuple[str, Judge]] = [("keyword heuristic", HeuristicJudge(pack))]
    jdir = pack.judgements_dir()
    if jdir:
        for path in sorted(jdir.glob("llm_gemma*.jsonl")):
            judges.append(("Gemma 4 26B (local)", ReplayJudge(path)))
    rules = {r.key: r for r in pack.example_rules()}
    out = []
    for jname, judge in judges:
        outputs = judge_all(judge, pack.cases)
        for key, label in (("escalation-callback@1", "v1 mentions_repayment"),
                           ("escalation-callback@2", "v2 supervisor_callback")):  # fmt: skip
            out.append((jname, label, run_gate(pack, outputs, [], rules[key], [corr])))
    return out


def flips(p: Palette, reports: list[tuple[str, str, GateReport]]) -> str:
    pack = load_pack("collections-conduct")
    cases = pack.cases
    cell, pitch, x0, y0 = 20, 25, 300, 128
    row, group_gap = 44, 40
    width = x0 + len(cases) * pitch + 150
    b = text(40, 48, "What each rule changes, case by case", size=30, fill=p.ink, weight=700)
    b += text(
        40,
        78,
        "28 calls · ▾ held out · each judge gated separately",
        size=18,
        fill=p.muted,
    )
    for j, case in enumerate(cases):
        cx = x0 + j * pitch + cell / 2
        b += text(cx, y0 - 10, case.id[-2:], size=12, fill=p.faint, font=MONO, anchor="middle")
        if case.split == "heldout":
            b += text(cx, y0 - 28, "▾", size=14, fill=p.accent, font=MONO, anchor="middle")
    y = y0
    last_judge = None
    for jname, rlabel, rep in reports:
        if jname != last_judge:
            if last_judge is not None:
                b += f'<line x1="40" y1="{y + 6}" x2="{width - 40}" y2="{y + 6}" stroke="{p.line}"/>\n'
                y += 12
            b += text(40, y + 22, jname, size=18, fill=p.ink, weight=700)
            y += group_gap
            last_judge = jname
        b += text(40, y + 16, rlabel, size=16, fill=p.muted, font=MONO)
        kinds = {f.case_id: f.kind for f in rep.flips}
        for j, case in enumerate(cases):
            x = x0 + j * pitch
            kind = kinds.get(case.id)
            if kind == "fixed":
                fill, stroke = p.green, p.green
            elif kind == "broken":
                fill, stroke = p.red, p.red
            else:
                fill, stroke = "none", p.line
            b += (
                f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="4" fill="{fill}" '
                f'stroke="{stroke}"/>\n'
            )
        b += badge(x0 + len(cases) * pitch + 18, y + 16, rep.decision == "PASSED", p, size=13)
        y += row
    ly = y + 30
    items = [(p.green, p.green, "fixed: was wrong, now right"),
             (p.red, p.red, "broken: was right, now wrong"),
             ("none", p.line, "unchanged")]  # fmt: skip
    lx = 40
    for fill, stroke, lab in items:
        b += f'<rect x="{lx}" y="{ly - 15}" width="18" height="18" rx="4" fill="{fill}" stroke="{stroke}"/>\n'
        b += text(lx + 28, ly, lab, size=17, fill=p.muted)
        lx += 28 + len(lab) * 9.2 + 40
    b += text(40, ly + 40, "Generated by scripts/figures.py from the pack and recorded judge runs.",
              size=14, fill=p.faint, font=MONO)  # fmt: skip
    return svg(width, ly + 64, b, p, "Flip map: cases each rule fixes or breaks, per judge")


def main() -> int:
    ASSETS.mkdir(parents=True, exist_ok=True)
    reports = gate_reports()
    for p in (LIGHT, DARK):
        (ASSETS / f"banner-{p.name}.svg").write_text(banner(p), encoding="utf-8")
        (ASSETS / f"lifecycle-{p.name}.svg").write_text(lifecycle(p), encoding="utf-8")
        (ASSETS / f"flips-{p.name}.svg").write_text(flips(p, reports), encoding="utf-8")
    for f in sorted(ASSETS.glob("*.svg")):
        print(f"{f.relative_to(ROOT)}  {f.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
