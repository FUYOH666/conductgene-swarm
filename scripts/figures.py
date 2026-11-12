"""Draw the README figures as SVG, in a light and a dark variant.

    uv run --with "fonttools[woff]==4.68.0" python scripts/figures.py

Fonts (Instrument Serif, Geist, Geist Mono; SIL OFL, docs/assets/fonts) are
subset to the glyphs each figure uses and embedded as WOFF2, because SVGs shown
through <img> on GitHub cannot load web fonts.

Writes docs/assets/{banner,lifecycle,flips,benchmark}-{light,dark}.svg. The flip
map is computed from the pack and the recorded judge runs, and the benchmark
chart from benchmarks/correction_stream/results, so neither can drift from the
numbers in the docs.
"""

from __future__ import annotations

import base64
import io
import json
import logging
import re
from html import escape, unescape
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
FONTS = {
    "Instrument Serif": ("InstrumentSerif-Regular.ttf", "400"),
    "Geist": ("Geist.ttf", "100 900"),
    "Geist Mono": ("GeistMono.ttf", "100 900"),
}
_USED: dict[str, set[str]] = {}


def _family(stack: str) -> str:
    return stack.split(",")[0].strip().strip("'\"")


def font_faces(used: dict[str, set[str]]) -> str:
    """@font-face rules with each font subset to the characters it renders."""
    from fontTools import subset

    logging.getLogger("fontTools").setLevel(logging.ERROR)
    rules = []
    for family, chars in sorted(used.items()):
        if family not in FONTS or not chars:
            continue
        file, weight = FONTS[family]
        options = subset.Options()
        options.flavor = "woff2"
        options.layout_features = ["kern", "liga", "calt"]
        options.name_IDs = [0, 1, 2]
        font = subset.load_font(str(ASSETS / "fonts" / file), options)
        subsetter = subset.Subsetter(options)
        subsetter.populate(text="".join(sorted(chars | {" "})))
        subsetter.subset(font)
        buf = io.BytesIO()
        subset.save_font(font, buf, options)
        data = base64.b64encode(buf.getvalue()).decode()
        rules.append(
            f"@font-face{{font-family:'{family}';font-weight:{weight};"
            f"src:url(data:font/woff2;base64,{data}) format('woff2')}}"
        )
    return "".join(rules)


def svg(width: int, height: int, body: str, p: Palette, title: str) -> str:
    faces = font_faces(_USED)
    _USED.clear()
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">\n'
        f"<title>{escape(title)}</title>\n<defs><style>{faces}</style></defs>\n"
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
    _USED.setdefault(_family(font), set()).update(s)
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
    b += text(140, 124, "precedent", size=84, fill=p.ink, font=SERIF, weight=400, spacing=-1)
    b += text(66, 190, "Pull requests for AI judgment", size=38, fill=p.ink, weight=500)
    b += text(
        66,
        232,
        "A human correction to an LLM judge becomes a scoped rule.",
        size=23,
        fill=p.muted,
    )
    b += text(
        66,
        268,
        "Tested on every case, approved by a second person, reversible.",
        size=23,
        fill=p.muted,
    )
    b += text(66, 336, "gate · four-eyes · hash-chained log · offline", size=18,
              fill=p.faint, font=MONO)  # fmt: skip

    # the story in two lines
    cx, cy, cw, ch = 742, 64, 484, 276
    b += (
        f'<rect x="{cx}" y="{cy}" width="{cw}" height="{ch}" rx="14" fill="{p.panel}" '
        f'stroke="{p.line}"/>\n'
    )
    b += text(cx + 26, cy + 42, "one correction, two rules", size=17, fill=p.faint, font=MONO)
    rows = [
        ("v1", "when mentions_repayment", False, "fixes 2 · breaks 3"),
        ("v2", "when supervisor_callback", True, "fixes 3 · breaks 0"),
    ]
    for i, (ver, cond, ok, stats) in enumerate(rows):
        y = cy + 100 + i * 100
        b += text(cx + 26, y, ver, size=19, fill=p.accent, font=MONO, weight=700)
        b += text(cx + 66, y, cond, size=19, fill=p.ink, font=MONO)
        b += text(cx + 66, y + 34, "→ escalation = pass", size=19, fill=p.muted, font=MONO)
        b += badge(cx + cw - 26 - 14 * 6.4, y, ok, p, size=14)
        b += text(cx + cw - 26, y + 34, stats, size=15, fill=p.faint, font=MONO, anchor="end")
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


# --- benchmark ----------------------------------------------------------------

BENCH = (
    ROOT / "benchmarks" / "correction_stream" / "results" / "gemma-4-26b-a4b-it" / "results.json"
)
BENCH_ROWS = [
    ("A0-rerun", "same judge, re-run unchanged", ""),
    ("P@30", "placebo paragraph in the prompt", ""),
    ("A1@30", "all corrections as few-shot examples", ""),
    ("A3@30", "reasons as prompt guidelines", ""),
    ("A3g@30", "guidelines, kept only if dev holds", "every batch rejected"),
    ("A2@30", "5 most similar corrections retrieved", ""),
    ("B2@30", "rules through the Precedent gate", "0 broken in all 3 orders"),
]


def benchmark(p: Palette) -> str:
    r = json.loads(BENCH.read_text())
    arms, n = r["arms"], r["arms"]["A0"]["n"]
    width, x_label, axis, scale, x_acc = 1280, 40, 640, 9.5, 1010
    row, y0 = 46, 168
    b = text(40, 48, f"{r['corrections']} corrections, seven ways to use them", size=30,
             fill=p.ink, weight=700)  # fmt: skip
    b += text(40, 78, f"Gemma 4 26B judge · sealed test of {n} verdicts · pre-registered",
              size=18, fill=p.muted)  # fmt: skip
    b += text(axis - 12, y0 - 40, "right → wrong", size=15, fill=p.red, font=MONO, anchor="end")
    b += text(axis + 12, y0 - 40, "wrong → right", size=15, fill=p.green, font=MONO)
    b += text(x_acc, y0 - 40, "verdicts right", size=15, fill=p.muted, font=MONO)
    base = arms["A0"]
    b += text(x_label, y0 - 4, "no corrections (baseline)", size=17, fill=p.muted)
    b += text(x_acc, y0 - 4, f"{base['right']}/{n}  {base['accuracy']:.1%}", size=17,
              fill=p.muted, font=MONO)  # fmt: skip
    y = y0 + 22
    for key, label, note in BENCH_ROWS:
        a = arms[key]
        neg = float(a.get("negative_flips_mean", a["negative_flips"]))
        pos = float(a["positive_flips"])
        ours = key.startswith("B2")
        if ours:
            b += (f'<rect x="24" y="{y - 8}" width="{width - 48}" height="{row - 6}" rx="8" '
                  f'fill="{p.panel}"/>\n')  # fmt: skip
        b += text(x_label, y + 20, label, size=17, fill=p.ink if ours else p.muted,
                  weight=700 if ours else 400)  # fmt: skip
        if note:
            b += text(axis - 16 - neg * scale, y + 20, note, size=13, fill=p.faint, font=MONO,
                      anchor="end")  # fmt: skip
        if neg:
            w = neg * scale
            b += f'<rect x="{axis - w}" y="{y + 4}" width="{w}" height="22" rx="3" fill="{p.red}"/>\n'
            b += text(
                axis - w - 8, y + 21, f"{neg:.0f}", size=15, fill=p.red, font=MONO, anchor="end"
            )
        if pos:
            w = pos * scale
            b += f'<rect x="{axis}" y="{y + 4}" width="{w}" height="22" rx="3" fill="{p.green}"/>\n'
            b += text(axis + w + 8, y + 21, f"{pos:.0f}", size=15, fill=p.green, font=MONO)
        acc = float(a.get("accuracy_mean", a["accuracy"]))
        b += text(x_acc, y + 20, f"{a['right']}/{n}  {acc:.1%}", size=17,
                  fill=p.ink if ours else p.muted, font=MONO, weight=700 if ours else 400)  # fmt: skip
        y += row
    b += f'<line x1="{axis}" y1="{y0 - 28}" x2="{axis}" y2="{y}" stroke="{p.line}" stroke-width="2"/>\n'
    b += text(40, y + 34, "Rules read the judge's recorded answers; prompt methods re-judge every case "
              "and carry the judge's run-to-run noise (first row).", size=15, fill=p.muted)  # fmt: skip
    b += text(40, y + 64, "Generated by scripts/figures.py from benchmarks/correction_stream/results.",
              size=14, fill=p.faint, font=MONO)  # fmt: skip
    return svg(
        width,
        int(y + 88),
        b,
        p,
        "Correction-stream benchmark: verdicts broken and fixed per method",
    )


def embed_terminal_font(path: Path) -> None:
    """Swap the CDN font in rich's terminal SVG for embedded Geist Mono (idempotent)."""
    svg_text = path.read_text(encoding="utf-8")
    if "Fira Code" not in svg_text:
        return
    glyphs = set(unescape(re.sub(r"<[^>]+>", "", svg_text.split("</style>", 1)[1])))
    faces = font_faces({"Geist Mono": glyphs, "Geist": set("precedent demo")})
    svg_text = re.sub(r"@font-face \{.*?\}\s*", "", svg_text, flags=re.S)
    svg_text = svg_text.replace("<style>", f"<style>{faces}", 1)
    svg_text = svg_text.replace(
        "font-family: Fira Code, monospace", "font-family: 'Geist Mono', monospace"
    )
    svg_text = svg_text.replace("font-family: arial", "font-family: Geist, arial")
    path.write_text(svg_text, encoding="utf-8")


def main() -> int:
    ASSETS.mkdir(parents=True, exist_ok=True)
    if (ASSETS / "demo.svg").exists():
        embed_terminal_font(ASSETS / "demo.svg")
    reports = gate_reports()
    for p in (LIGHT, DARK):
        (ASSETS / f"banner-{p.name}.svg").write_text(banner(p), encoding="utf-8")
        (ASSETS / f"lifecycle-{p.name}.svg").write_text(lifecycle(p), encoding="utf-8")
        (ASSETS / f"flips-{p.name}.svg").write_text(flips(p, reports), encoding="utf-8")
        (ASSETS / f"benchmark-{p.name}.svg").write_text(benchmark(p), encoding="utf-8")
    for f in sorted(ASSETS.glob("*.svg")):
        print(f"{f.relative_to(ROOT)}  {f.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
