"""Command-line interface.

precedent demo                          the v1 bug, caught (offline, ~1 s)
precedent packs                         list built-in packs
precedent judge  --pack P [--judge J]   judge every case, compare with labels
precedent eval   --pack P --db DB       agreement with the active rules applied
precedent correct --db DB --pack P --case C --item I --label L --reviewer R --error-type T
precedent propose RULE.yaml --db DB --actor A
precedent gate   RULE_KEY --db DB --pack P [--judge J] [--report FILE]
precedent approve RULE_KEY --db DB --actor A
precedent revert RULE_KEY --db DB --actor A --reason TEXT
precedent rules  --db DB
precedent audit  verify|log --db DB
"""

from __future__ import annotations

import argparse
import sys
import uuid
from collections.abc import Sequence
from pathlib import Path

from rich.console import Console
from rich.table import Table

from precedent import __version__
from precedent.engine import decide
from precedent.events import EventStore
from precedent.gate import run_gate
from precedent.judge import Judge, judge_all
from precedent.judge.factory import make_judge
from precedent.models import Correction, JudgeOutput
from precedent.pack import Pack, builtin_packs, load_pack, load_rule
from precedent.registry import Registry, RegistryError
from precedent.report import TERMINAL_THEME, gate_markdown, print_gate, rule_summary

console = Console(highlight=False)


def _judge(pack: Pack, spec: str, db: Path | None) -> Judge:
    record_to = (db.parent / "judgements") if db is not None else None
    return make_judge(pack, spec, record_to=record_to)


def _outputs(pack: Pack, spec: str, db: Path | None) -> dict[str, JudgeOutput]:
    return judge_all(_judge(pack, spec, db), pack.cases)


def cmd_demo(args: argparse.Namespace) -> int:
    from precedent.demo import run_demo

    if not args.svg:
        return run_demo(console, Path(args.out), args.judge, args.anchor_receipt)
    recorder = Console(
        record=True, width=100, force_terminal=True, color_system="truecolor", highlight=False
    )
    code = run_demo(recorder, Path(args.out), args.judge, args.anchor_receipt)
    recorder.save_svg(args.svg, title="precedent demo", theme=TERMINAL_THEME)
    console.print(f"[dim]wrote {args.svg}[/]")
    return code


def cmd_packs(_: argparse.Namespace) -> int:
    for name in builtin_packs():
        pack = load_pack(name)
        held = sum(c.split == "heldout" for c in pack.cases)
        console.print(
            f"[bold]{name}[/] v{pack.version} · {len(pack.items)} items · "
            f"{len(pack.predicates)} predicates · {len(pack.clauses)} clauses · "
            f"{len(pack.cases)} cases ({held} held out)\n  [dim]{pack.title}[/]"
        )
    return 0


def _agreement_table(pack: Pack, outputs: dict[str, JudgeOutput], rules: list) -> Table:  # type: ignore[type-arg]
    table = Table(box=None, header_style="dim")
    for col in ("item", "n", "agree", "rate"):
        table.add_column(col)
    for item in pack.items:
        pairs = [
            (decide(pack, outputs[c.id], rules)[item.id].label, c.golden[item.id])
            for c in pack.cases
            if item.id in c.golden
        ]
        agree = sum(a == b for a, b in pairs)
        rate = agree / len(pairs) if pairs else float("nan")
        table.add_row(item.id, str(len(pairs)), str(agree), f"{rate:.3f}")
    return table


def cmd_judge(args: argparse.Namespace) -> int:
    pack = load_pack(args.pack)
    db = Path(args.db) if args.db else None
    judge = _judge(pack, args.judge, db)
    outputs = judge_all(judge, pack.cases)
    console.print(f"[dim]judge {judge.judge_id} · {len(outputs)} cases[/]")
    console.print(_agreement_table(pack, outputs, []))
    if args.errors:
        for case in pack.cases:
            decisions = decide(pack, outputs[case.id], [])
            for item, label in case.golden.items():
                if decisions[item].label != label:
                    console.print(
                        f"  [red]✗[/] {case.id} {item}: judge {decisions[item].label}, "
                        f"label {label}"
                    )
    return 0


def cmd_eval(args: argparse.Namespace) -> int:
    pack = load_pack(args.pack)
    db = Path(args.db)
    with EventStore(db) as store:
        rules = Registry(store).active_rules(pack.id)
    outputs = _outputs(pack, args.judge, db)
    console.print(f"[dim]{len(rules)} active rule(s)[/]")
    console.print(_agreement_table(pack, outputs, rules))
    return 0


def cmd_correct(args: argparse.Namespace) -> int:
    pack = load_pack(args.pack)
    db = Path(args.db)
    case = pack.case(args.case)
    if args.label not in pack.item(args.item).label_ids():
        console.print(f"[red]invalid label {args.label!r} for {args.item}[/]")
        return 2
    with EventStore(db) as store:
        registry = Registry(store)
        rules = registry.active_rules(pack.id)
        output = _judge(pack, args.judge, db).judge(case)
        ai_label = decide(pack, output, rules)[args.item].label
        corr = Correction(
            id=args.id or f"C-{uuid.uuid4().hex[:6].upper()}",
            pack=pack.id,
            case_id=case.id,
            case_hash=case.hash,
            item=args.item,
            ai_label=ai_label,
            human_label=args.label,
            reviewer=args.reviewer,
            error_type=args.error_type,
            note=args.note or "",
        )
        registry.record_correction(args.reviewer, corr)
    console.print(f"recorded {corr.id}: {case.id} {args.item} {ai_label} → {args.label}")
    return 0


def cmd_propose(args: argparse.Namespace) -> int:
    rule = load_rule(args.rule)
    with EventStore(Path(args.db)) as store:
        rule = Registry(store).propose(args.actor, rule)
    console.print(f"proposed [cyan]{rule.key}[/]: {rule_summary(rule)}")
    return 0


def cmd_gate(args: argparse.Namespace) -> int:
    pack = load_pack(args.pack)
    db = Path(args.db)
    with EventStore(db) as store:
        registry = Registry(store)
        state = registry.state()
        record = state.rules.get(args.rule_key)
        if record is None:
            console.print(f"[red]unknown rule {args.rule_key}[/]")
            return 2
        outputs = _outputs(pack, args.judge, db)
        report = run_gate(
            pack,
            outputs,
            state.active(pack.id),
            record.rule,
            [c for c in state.corrections.values() if c.pack == pack.id],
        )
        registry.record_gate(args.actor, report)
    console.print(f"[cyan]{record.rule.key}[/] {rule_summary(record.rule)}")
    print_gate(console, report)
    if args.report:
        Path(args.report).write_text(gate_markdown(report, record.rule), encoding="utf-8")
        console.print(f"[dim]report written to {args.report}[/]")
    return 0 if report.decision == "PASSED" else 1


def _load_corrections(pack: Pack, path: str | None) -> list[Correction]:
    if not path:
        return []
    import yaml

    rows = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or []
    out = []
    for row in rows:
        if "case_hash" not in row:
            row = {**row, "case_hash": pack.case(row["case_id"]).hash}
        out.append(Correction.model_validate({"pack": pack.id, **row}))
    return out


def cmd_check(args: argparse.Namespace) -> int:
    """Stateless gate for CI: rule files in, verdicts and a Markdown summary out."""
    pack = load_pack(args.pack)
    outputs = _outputs(pack, args.judge, None)
    corrections = _load_corrections(pack, args.corrections)
    active = [load_rule(p) for p in sorted(Path(args.active).glob("*.yaml"))] if args.active else []
    blocked = 0
    sections = []
    for path in args.rules:
        rule = load_rule(path)
        report = run_gate(pack, outputs, [r for r in active if r.id != rule.id], rule, corrections)
        console.print(f"[cyan]{rule.key}[/] {rule_summary(rule)}  [dim]({path})[/]")
        print_gate(console, report)
        blocked += report.decision == "BLOCKED"
        sections.append(gate_markdown(report, rule))
    if args.summary:
        with Path(args.summary).open("a", encoding="utf-8") as fh:
            fh.write("\n\n---\n\n".join(sections) + "\n")
    return 1 if blocked else 0


def cmd_approve(args: argparse.Namespace) -> int:
    pack = load_pack(args.pack)
    db = Path(args.db)
    judge = _judge(pack, args.judge, db)
    with EventStore(db) as store:
        registry = Registry(store)
        state = registry.state()
        record = state.rules.get(args.rule_key)
        if record is None:
            console.print(f"[red]unknown rule {args.rule_key}[/]")
            return 2
        # The approver re-performs the gate; the recorded report must be reproduced.
        rerun = run_gate(
            pack,
            judge_all(judge, pack.cases),
            state.active(pack.id),
            record.rule,
            [c for c in state.corrections.values() if c.pack == pack.id],
        )
        rule = registry.approve(
            args.actor,
            args.rule_key,
            dataset_hash=pack.dataset_hash(),
            judge_id=judge.judge_id,
            rationale=args.rationale or "",
            rerun=rerun,
        )
    console.print(f"[green]✓[/] {rule.key} is active")
    return 0


def cmd_revert(args: argparse.Namespace) -> int:
    with EventStore(Path(args.db)) as store:
        Registry(store).revert(args.actor, args.rule_key, args.reason)
    console.print(f"{args.rule_key} reverted")
    return 0


def cmd_rules(args: argparse.Namespace) -> int:
    with EventStore(Path(args.db)) as store:
        state = Registry(store).state()
    table = Table(box=None, header_style="dim")
    for col in ("rule", "status", "gate", "proposed by", "approved by", "rule"):
        table.add_column(col)
    for key, rec in state.rules.items():
        table.add_row(
            key,
            rec.status,
            rec.gate_decision or "—",
            rec.proposed_by,
            rec.approved_by or "—",
            rule_summary(rec.rule),
        )
    console.print(table)
    return 0


def cmd_evidence(args: argparse.Namespace) -> int:
    import json

    from precedent.evidence import build_evidence, render_html

    pack = load_pack(args.pack)
    db = Path(args.db)
    outputs = _outputs(pack, args.judge, db)
    with EventStore(db) as store:
        doc = build_evidence(
            pack, store, args.rule_key, outputs, anchor_receipt=args.anchor_receipt
        )
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{args.rule_key}.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    (out / f"{args.rule_key}.html").write_text(render_html(doc, pack))
    console.print(
        f"wrote {out / args.rule_key}.html and .json · sha256 {doc['evidence_hash'][:16]}…"
    )
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    with EventStore(Path(args.db)) as store:
        if args.action == "export":
            import json

            result = store.verify(anchor=args.anchor)
            lines = [
                json.dumps(
                    {
                        "seq": e.seq,
                        "ts": e.ts,
                        "actor": e.actor,
                        "type": e.type,
                        "payload": e.payload,
                        "prev_hash": e.prev_hash,
                        "hash": e.hash,
                    },
                    ensure_ascii=False,
                )  # fmt: skip
                for e in store.events()
            ]
            trailer = {"population": result.count, "head": result.head, "chain_ok": result.ok}
            lines.append(json.dumps({"trailer": trailer}))
            text = "\n".join(lines) + "\n"
            if args.out:
                Path(args.out).write_text(text, encoding="utf-8")
                console.print(f"exported {result.count} events to {args.out}, head {result.head}")
            else:
                sys.stdout.write(text)
            return 0 if result.ok else 1
        if args.action == "verify":
            result = store.verify(anchor=args.anchor)
            if result.ok:
                console.print(
                    f"[green]✓[/] {result.count} events, chain intact, head {result.head}"
                )
                return 0
            where = f"event {result.first_bad_seq}: " if result.first_bad_seq else ""
            console.print(f"[red]✗ {where}{result.reason}[/]")
            return 1
        for ev in store.events():
            console.print(
                f"{ev.seq:>4} {ev.ts} {ev.actor:<10} {ev.type:<20} [dim]{ev.hash[:16]}[/]"
            )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="precedent", description="Pull requests for AI judgment.")
    parser.add_argument("--version", action="version", version=f"precedent {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    def judge_opt(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--judge",
            default="heuristic",
            help="heuristic (default), replay:PATH, llm or llm:MODEL",
        )

    p = sub.add_parser("demo", help="the v1 bug, caught by the gate")
    p.add_argument("--out", default="precedent-demo")
    p.add_argument("--svg", help="also export the run as a terminal SVG")
    p.add_argument("--anchor-receipt", help="where the log head will be recorded (evidence packs)")
    judge_opt(p)
    p.set_defaults(func=cmd_demo)

    p = sub.add_parser("packs", help="list built-in packs")
    p.set_defaults(func=cmd_packs)

    p = sub.add_parser("judge", help="judge all cases of a pack and compare with labels")
    p.add_argument("--pack", required=True)
    p.add_argument("--db", help="record LLM outputs next to this event log")
    p.add_argument("--errors", action="store_true", help="list disagreements")
    judge_opt(p)
    p.set_defaults(func=cmd_judge)

    p = sub.add_parser("eval", help="agreement with active rules applied")
    p.add_argument("--pack", required=True)
    p.add_argument("--db", required=True)
    judge_opt(p)
    p.set_defaults(func=cmd_eval)

    p = sub.add_parser("correct", help="record a reviewer correction")
    p.add_argument("--db", required=True)
    p.add_argument("--pack", required=True)
    p.add_argument("--case", required=True)
    p.add_argument("--item", required=True)
    p.add_argument("--label", required=True)
    p.add_argument("--reviewer", required=True)
    p.add_argument(
        "--error-type",
        required=True,
        choices=[
            "policy_misinterpretation",
            "rubric_ambiguity",
            "missing_context",
            "misread",
            "judge_noise",
        ],
    )
    p.add_argument("--note")
    p.add_argument("--id")
    judge_opt(p)
    p.set_defaults(func=cmd_correct)

    p = sub.add_parser("propose", help="propose a rule from a YAML file")
    p.add_argument("rule")
    p.add_argument("--db", required=True)
    p.add_argument("--actor", required=True)
    p.set_defaults(func=cmd_propose)

    p = sub.add_parser("gate", help="run the gate for a proposed rule")
    p.add_argument("rule_key")
    p.add_argument("--db", required=True)
    p.add_argument("--pack", required=True)
    p.add_argument("--actor", default="ci")
    p.add_argument("--report", help="write the Markdown gate report here")
    judge_opt(p)
    p.set_defaults(func=cmd_gate)

    p = sub.add_parser("check", help="gate rule files without an event log (for CI)")
    p.add_argument("rules", nargs="+", help="rule YAML files")
    p.add_argument("--pack", required=True)
    p.add_argument("--corrections", help="YAML list of corrections the rules may cite")
    p.add_argument("--active", help="directory of rules already in force")
    p.add_argument("--summary", help="append the Markdown gate reports here")
    judge_opt(p)
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("approve", help="re-run the gate and approve a rule that passed it")
    p.add_argument("rule_key")
    p.add_argument("--db", required=True)
    p.add_argument("--pack", required=True)
    p.add_argument("--actor", required=True)
    p.add_argument("--rationale", help="why the approver accepts this change (kept in the log)")
    judge_opt(p)
    p.set_defaults(func=cmd_approve)

    p = sub.add_parser("revert", help="deactivate an active rule")
    p.add_argument("rule_key")
    p.add_argument("--db", required=True)
    p.add_argument("--actor", required=True)
    p.add_argument("--reason", required=True)
    p.set_defaults(func=cmd_revert)

    p = sub.add_parser("rules", help="list rules and their status")
    p.add_argument("--db", required=True)
    p.set_defaults(func=cmd_rules)

    p = sub.add_parser("evidence", help="write an evidence pack (HTML + JSON) for one rule")
    p.add_argument("rule_key")
    p.add_argument("--db", required=True)
    p.add_argument("--pack", required=True)
    p.add_argument("--out", default="evidence")
    p.add_argument("--anchor-receipt", help="where the chain head was recorded outside the log")
    judge_opt(p)
    p.set_defaults(func=cmd_evidence)

    p = sub.add_parser("audit", help="verify, print or export the event log")
    p.add_argument("action", choices=["verify", "log", "export"])
    p.add_argument("--out", help="export: write the population here instead of stdout")
    p.add_argument("--db", required=True)
    p.add_argument("--anchor", help="a head hash recorded earlier outside the log")
    p.set_defaults(func=cmd_audit)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except (RegistryError, KeyError, ValueError, FileNotFoundError) as exc:
        console.print(f"[red]error:[/] {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
