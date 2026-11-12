"""The offline demo: the v1 bug, caught.

In the hackathon version a supervisor correction was stored as a keyword rule
("repayment" → escalation passes). It fixed the call it came from, quietly
broke three others, and the eval reported ``improved: True``. Here the same
correction goes through the gate.
"""

from __future__ import annotations

import json
from pathlib import Path

from rich.console import Console

from precedent.engine import decide
from precedent.events import EventStore
from precedent.evidence import build_evidence, render_html
from precedent.gate import run_gate
from precedent.judge import judge_all
from precedent.judge.factory import make_judge
from precedent.models import Correction, JudgeOutput, Rule
from precedent.pack import Pack, load_pack
from precedent.registry import Registry, RegistryError
from precedent.report import gate_markdown, print_gate, rule_summary

PACK = "collections-conduct"
CASE = "CASE-019"
ITEM = "escalation_offered"


def _agreement(pack: Pack, outputs: dict[str, JudgeOutput], rules: list[Rule]) -> tuple[int, int]:
    ok = total = 0
    for case in pack.cases:
        decisions = decide(pack, outputs[case.id], rules)
        for item, label in case.golden.items():
            total += 1
            ok += decisions[item].label == label
    return ok, total


def _fresh_db(path: Path) -> None:
    for suffix in ("", "-wal", "-shm"):
        p = path.with_name(path.name + suffix)
        if p.exists():
            p.unlink()


def run_demo(
    console: Console,
    out_dir: Path,
    judge_spec: str = "heuristic",
    anchor_receipt: str | None = None,
) -> int:
    pack = load_pack(PACK)
    judge = make_judge(pack, judge_spec)
    out_dir.mkdir(parents=True, exist_ok=True)
    db = out_dir / "demo.db"
    _fresh_db(db)
    reports_dir = out_dir / "reports"
    reports_dir.mkdir(exist_ok=True)

    store = EventStore(db)
    registry = Registry(store)
    rules = {r.key: r for r in pack.example_rules()}
    n_held = sum(c.split == "heldout" for c in pack.cases)

    console.print(
        f"[bold]precedent[/] [dim]·[/] pull requests for AI judgment\n"
        f"[dim]{pack.id}: {len(pack.cases)} calls, {n_held} held out · "
        f"judge {judge.judge_id}[/]\n"
    )

    outputs = judge_all(judge, pack.cases)
    ok, total = _agreement(pack, outputs, [])
    console.print(
        f"[bold]1[/]  The judge agrees with the labels on [bold]{ok}/{total}[/] verdicts."
    )

    case = pack.case(CASE)
    ai_label = decide(pack, outputs[CASE], [])[ITEM].label
    quote = outputs[CASE].predicates["supervisor_callback_offered"].quote
    correction = Correction(
        id="C-0001",
        pack=pack.id,
        case_id=CASE,
        case_hash=case.hash,
        item=ITEM,
        ai_label=ai_label,
        human_label="pass",
        reviewer="maria",
        error_type="policy_misinterpretation",
        note="A team-lead callback is an escalation offer.",
    )
    registry.record_correction("maria", correction)
    console.print(
        f"[bold]2[/]  maria corrects {CASE}: {ITEM} [red]{ai_label}[/] → [green]pass[/]"
        + (f'\n   [dim]"…{quote.text}…"[/]' if quote else "")
    )

    console.print(
        "\n[bold]3[/]  She turns it into a rule the way v1 did "
        "[dim](v1 shipped this rule and reported improved: True)[/]"
    )
    v1 = registry.propose("maria", rules["escalation-callback@1"])
    console.print(f"   [cyan]{v1.key}[/]  [green]+[/] {rule_summary(v1)}")
    report1 = run_gate(pack, outputs, registry.active_rules(pack.id), v1, [correction])
    registry.record_gate("ci", report1)
    print_gate(console, report1)
    (reports_dir / "escalation-callback@1.md").write_text(gate_markdown(report1, v1))

    console.print("\n[bold]4[/]  She states the real reason instead")
    v2 = registry.propose("maria", rules["escalation-callback@2"])
    console.print(f"   [cyan]{v2.key}[/]  [green]+[/] {rule_summary(v2)}")
    report2 = run_gate(pack, outputs, registry.active_rules(pack.id), v2, [correction])
    registry.record_gate("ci", report2)
    print_gate(console, report2, compact=True)
    (reports_dir / "escalation-callback@2.md").write_text(gate_markdown(report2, v2))

    console.print("\n[bold]5[/]  Approval needs a second person")
    data_hash, judge_id = pack.dataset_hash(), judge.judge_id
    try:
        registry.approve("maria", v2.key, dataset_hash=data_hash, judge_id=judge_id)
    except RegistryError as exc:
        console.print(f"   [red]✗[/] maria: {exc}")
    rerun = run_gate(
        pack, outputs, registry.active_rules(pack.id), v2, registry.corrections(pack.id)
    )
    registry.approve(
        "alex",
        v2.key,
        dataset_hash=data_hash,
        judge_id=judge_id,
        rerun=rerun,
        rationale="Policy (escalation): a scheduled callback from a team lead is an offer.",
    )
    ok2, _ = _agreement(pack, outputs, registry.active_rules(pack.id))
    console.print(
        f"   [green]✓[/] alex approves {v2.key}: agreement {ok}/{total} → [bold]{ok2}/{total}[/]"
    )

    evidence_dir = out_dir / "evidence"
    evidence_dir.mkdir(exist_ok=True)
    for key in (v1.key, v2.key):
        doc = build_evidence(pack, store, key, outputs, anchor_receipt=anchor_receipt)
        (evidence_dir / f"{key}.json").write_text(
            json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
        )
        (evidence_dir / f"{key}.html").write_text(render_html(doc, pack))
    console.print(f"   [dim]evidence packs: {evidence_dir}[/]")

    registry.revert("alex", v2.key, "demo: show that one command undoes it")
    ok3, _ = _agreement(pack, outputs, registry.active_rules(pack.id))
    console.print(
        f"\n[bold]6[/]  alex reverts it with one command: agreement back to {ok3}/{total}"
    )

    result = store.verify()
    status = "[green]✓ intact[/]" if result.ok else f"[red]✗ {result.reason}[/]"
    console.print(
        f"[bold]7[/]  Audit log: {result.count} hash-chained events, {status}, "
        f"head [dim]{result.head[:16]}[/]"
    )
    console.print(f"\n[dim]Gate reports: {reports_dir} · event log: {db}[/]")
    store.close()
    return (
        0 if (report1.decision, report2.decision, result.ok) == ("BLOCKED", "PASSED", True) else 1
    )
