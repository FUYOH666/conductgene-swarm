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
from precedent.report import gate_markdown, print_gate, rule_summary

console = Console(highlight=False)


def _judge(pack: Pack, spec: str, db: Path | None) -> Judge:
    record_to = (db.parent / "judgements") if db is not None else None
    return make_judge(pack, spec, record_to=record_to)


def _outputs(pack: Pack, spec: str, db: Path | None) -> dict[str, JudgeOutput]:
    return judge_all(_judge(pack, spec, db), pack.cases)


def cmd_demo(args: argparse.Namespace) -> int:
    from precedent.demo import run_demo

    return run_demo(console, Path(args.out), args.judge)


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


def cmd_approve(args: argparse.Namespace) -> int:
    with EventStore(Path(args.db)) as store:
        rule = Registry(store).approve(args.actor, args.rule_key)
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


def cmd_audit(args: argparse.Namespace) -> int:
    with EventStore(Path(args.db)) as store:
        if args.action == "verify":
            result = store.verify()
            if result.ok:
                console.print(
                    f"[green]✓[/] {result.count} events, chain intact, head {result.head}"
                )
                return 0
            console.print(f"[red]✗ event {result.first_bad_seq}: {result.reason}[/]")
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

    p = sub.add_parser("approve", help="approve a rule that passed the gate")
    p.add_argument("rule_key")
    p.add_argument("--db", required=True)
    p.add_argument("--actor", required=True)
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

    p = sub.add_parser("audit", help="verify or print the event log")
    p.add_argument("action", choices=["verify", "log"])
    p.add_argument("--db", required=True)
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
