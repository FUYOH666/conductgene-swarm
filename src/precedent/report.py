"""Render gate reports for the terminal and as Markdown (the reviewable artifact)."""

from __future__ import annotations

from rich.console import Console
from rich.padding import Padding
from rich.table import Table
from rich.terminal_theme import TerminalTheme
from rich.text import Text

from precedent.models import GateReport, Rule

#: Palette for exported terminal SVGs; matches docs/assets (GitHub dark).
TERMINAL_THEME = TerminalTheme(
    (13, 17, 23),
    (230, 237, 243),
    [
        (22, 27, 34),
        (248, 81, 73),
        (63, 185, 80),
        (210, 153, 34),
        (121, 192, 255),
        (190, 150, 255),
        (139, 148, 255),
        (201, 209, 217),
    ],
    [
        (110, 118, 129),
        (255, 123, 114),
        (86, 211, 100),
        (227, 179, 65),
        (165, 214, 255),
        (210, 168, 255),
        (165, 172, 255),
        (240, 246, 252),
    ],
)


def rule_summary(rule: Rule) -> str:
    cond = " and ".join(
        c.predicate if c.equals == "yes" else f"not {c.predicate}" for c in rule.when
    )
    return f"when {cond} → {rule.item} = {rule.then}"


def decision_text(report: GateReport) -> Text:
    style = "bold green" if report.decision == "PASSED" else "bold red"
    mark = "✓" if report.decision == "PASSED" else "✗"
    return Text(f"{mark} {report.decision}", style=style)


def print_gate(
    console: Console, report: GateReport, *, flips: bool = True, compact: bool = False
) -> None:
    line = Text("   gate ")
    line.append_text(decision_text(report))
    if report.heldout is not None:
        h = report.heldout
        line.append(f"   held-out {h.right_before}/{h.n} → {h.right_after}/{h.n}", style="dim")
    console.print(line)
    if compact and report.decision == "PASSED":
        n_blocking = sum(c.blocking for c in report.checks)
        fixed = sum(f.kind == "fixed" for f in report.flips)
        broken = sum(f.kind == "broken" for f in report.flips)
        console.print(
            f"     [green]✓[/] all {n_blocking} blocking checks pass "
            f"[dim]· fixes {fixed} · breaks {broken}[/]"
        )
    checks = [] if compact and report.decision == "PASSED" else report.checks
    for check in checks:
        if check.passed:
            mark, style = "✓", "green"
        elif check.blocking:
            mark, style = "✗", "red"
        else:
            mark, style = "!", "yellow"
        console.print(f"     [{style}]{mark}[/] {check.name:<22} [dim]{check.detail}[/]")
    if flips and report.flips:
        table = Table(
            box=None, padding=(0, 1), show_header=True, header_style="dim", pad_edge=False
        )
        for col in ("case", "split", "item", "before", "after", "golden", ""):
            table.add_column(col)
        for f in report.flips:
            kind_style = {"fixed": "green", "broken": "red"}.get(f.kind, "yellow")
            table.add_row(
                f.case_id,
                f.split,
                f.item,
                f.before,
                f.after,
                f.golden or "—",
                f"[{kind_style}]{f.kind}[/]",
            )
        console.print(Padding(table, (0, 0, 0, 5)))


def gate_markdown(report: GateReport, rule: Rule) -> str:
    lines = [
        f"# Gate report: `{report.rule_key}` — **{report.decision}**",
        "",
        f"> {rule.title}",
        "",
        f"`{rule_summary(rule)}`",
        "",
        "| | |",
        "|---|---|",
        f"| pack | `{report.pack}` (dataset `{report.dataset_hash[:12]}`) |",
        f"| judge | `{report.judge_id}` |",
        f"| rule content | `{report.rule_hash[:12]}` |",
        f"| active rules before → after | `{report.ruleset_before[:12]}` → "
        f"`{report.ruleset_after[:12]}` |",
        f"| fires on | {report.fires_on} case(s) |",
        "",
        "## Checks",
        "",
        "| check | result | detail |",
        "|---|---|---|",
    ]
    for c in report.checks:
        result = "pass" if c.passed else ("FAIL" if c.blocking else "warn")
        lines.append(f"| {c.name} | {result} | {c.detail} |")
    lines += ["", "## Verdicts that change", ""]
    if report.flips:
        lines += [
            "| case | split | item | before | after | golden | effect |",
            "|---|---|---|---|---|---|---|",
        ]
        for f in report.flips:
            lines.append(
                f"| {f.case_id} | {f.split} | {f.item} | {f.before} | {f.after} "
                f"| {f.golden or '—'} | {f.kind} |"
            )
    else:
        lines.append("None.")
    lines += [
        "",
        "## Agreement with labels, per item",
        "",
        "| item | n | before | after | κ before | κ after |",
        "|---|---|---|---|---|---|",
    ]
    for m in report.metrics:
        kb = "—" if m.kappa_before is None else f"{m.kappa_before:.3f}"
        ka = "—" if m.kappa_after is None else f"{m.kappa_after:.3f}"
        before, after = f"{m.agreement_before:.3f}", f"{m.agreement_after:.3f}"
        lines.append(f"| {m.item} | {m.n} | {before} | {after} | {kb} | {ka} |")
    lines += ["", f"Report hash: `{report.content_hash()}`", ""]
    return "\n".join(lines)
