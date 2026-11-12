"""Evidence packs: the document an auditor takes away for one rule change.

``build_evidence`` collects everything from the event log, the pack and the
judge outputs into one JSON document; ``render_html`` turns it into a single
self-contained page. The JSON carries its own hash, the chain head it was cut
from, and the command that re-performs the gate, so a reader can verify it
offline without trusting the page.
"""

from __future__ import annotations

import difflib
from datetime import UTC, datetime
from html import escape
from typing import Any

from precedent import __version__
from precedent.events import EventStore
from precedent.hashing import canonical_json, sha256_hex
from precedent.models import JudgeOutput
from precedent.pack import Pack, dump_rule
from precedent.registry import Registry, RegistryError
from precedent.report import rule_summary
from precedent.theme import DARK, LIGHT, MONO, SANS, SERIF, css_variables

FORMAT = "precedent-evidence/1"
IDENTITY = "unauthenticated CLI name (no identity provider is attached in this deployment)"


def _excerpt(text: str, limit: int = 700) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def build_evidence(
    pack: Pack,
    store: EventStore,
    rule_key: str,
    outputs: dict[str, JudgeOutput],
    *,
    anchor_receipt: str | None = None,
) -> dict[str, Any]:
    registry = Registry(store)
    state = registry.state()
    record = state.rules.get(rule_key)
    if record is None:
        raise RegistryError(f"unknown rule {rule_key}")
    rule = record.rule
    report = record.gate_report
    if report is None:
        raise RegistryError(f"{rule_key} has not been gated; nothing to evidence")

    events = store.events()
    corrections = {c.id: c for c in state.corrections.values()}
    corr_seq = {e.payload["correction"]["id"]: e for e in events if e.type == "correction.recorded"}
    related = [
        e
        for e in events
        if e.payload.get("rule_key") == rule_key
        or (e.type == "rule.proposed" and e.payload.get("rule", {}).get("id") == rule.id)
        or (
            e.type == "correction.recorded"
            and e.payload["correction"]["id"] in rule.source_corrections
        )
    ]
    when = {e.type: e.ts for e in related if e.payload.get("rule_key", "") in ("", rule_key)}

    why = []
    for cid in rule.source_corrections:
        corr = corrections[cid]
        case = pack.case(corr.case_id)
        out = outputs.get(case.id)
        quotes = []
        if out is not None:
            for cond in rule.when:
                ans = out.predicates.get(cond.predicate)
                if ans is not None and ans.quote is not None:
                    quotes.append(
                        {"predicate": cond.predicate, "value": ans.value, "quote": ans.quote.text}
                    )
        why.append(
            {
                **corr.model_dump(mode="json"),
                "recorded_at": corr_seq[cid].ts if cid in corr_seq else None,
                "case_excerpt": _excerpt(case.text),
                "evidence_quotes": quotes,
            }
        )

    clause_ids = list(dict.fromkeys(rule.clause_refs))
    clauses = [c.model_dump(mode="json") for c in pack.clauses if c.id in clause_ids]
    if not clauses:  # cite the policy section the judge relied on for this item
        for corr_view in why:
            out = outputs.get(corr_view["case_id"])
            verdict = out.items.get(rule.item) if out else None
            for cid in verdict.clause_ids if verdict else []:
                clause = next((c for c in pack.clauses if c.id == cid), None)
                if clause and clause.model_dump(mode="json") not in clauses:
                    clauses.append(clause.model_dump(mode="json"))

    previous = [
        r.rule
        for r in state.rules.values()
        if r.rule.id == rule.id and r.rule.version < rule.version
    ]
    prev = max(previous, key=lambda r: r.version) if previous else None
    diff = (
        "".join(
            difflib.unified_diff(
                dump_rule(prev).splitlines(keepends=True),
                dump_rule(rule).splitlines(keepends=True),
                fromfile=prev.key,
                tofile=rule.key,
            )
        )
        if prev
        else ""
    )

    flips = []
    for f in report.flips:
        out = outputs.get(f.case_id)
        flip_quotes: list[str] = []
        if out is not None:
            for cond in rule.when:
                ans = out.predicates.get(cond.predicate)
                if ans is not None and ans.quote is not None:
                    flip_quotes.append(ans.quote.text)
        flips.append({**f.model_dump(mode="json"), "quotes": flip_quotes})

    verify = store.verify()
    doc: dict[str, Any] = {
        "format": FORMAT,
        "generated_at": datetime.now(tz=UTC).isoformat(timespec="seconds"),
        "precedent_version": __version__,
        "summary": {
            "rule": rule.key,
            "title": rule.title,
            "plain": rule_summary(rule),
            "item": rule.item,
            "status": record.status,
            "gate_decision": record.gate_decision,
            "owner": record.proposed_by,
            "proposed_at": when.get("rule.proposed"),
            "gated_at": when.get("rule.gated"),
            "approved_at": when.get("rule.approved"),
        },
        "why": {
            "corrections": why,
            "rationale": rule.rationale,
            "policy_clauses": clauses,
            "predicates": [
                pack.predicate(c.predicate).model_dump(
                    mode="json", include={"id", "question", "note"}
                )
                for c in rule.when
            ],
        },  # fmt: skip
        "change": {
            "rule_yaml": dump_rule(rule),
            "rule_hash": rule.content_hash(),
            "previous_version": prev.key if prev else None,
            "diff": diff,
            "active_before": report.ruleset_before,
            "active_after": report.ruleset_after,
        },
        "testing": {
            "report": report.model_dump(mode="json"),
            "report_hash": record.gate_report_hash,
            "flips": flips,
            "pack": pack.id,
            "dataset_hash": report.dataset_hash,
            "judge_id": report.judge_id,
            "cases": len(pack.cases),
            "heldout_cases": sum(c.split == "heldout" for c in pack.cases),
            "reproduce": (
                f"precedent gate {rule.key} --db <log> --pack {pack.id} --judge <same judge>"
                "  # must reproduce report_hash"
            ),
        },
        "signoffs": {
            "author": record.proposed_by,
            "gate_runner": record.gated_by,
            "approver": record.approved_by,
            "approval_rationale": record.approval_rationale,
            "identity": IDENTITY,
            "segregation": {
                "author_is_not_gate_runner": record.gated_by is not None
                and record.gated_by != record.proposed_by,
                "author_is_not_approver": record.approved_by is not None
                and record.approved_by != record.proposed_by,
            },
        },
        "limitations": [
            f"Tested on {len(pack.cases)} labelled cases in pack {pack.id}; see the pack's LABELING.md.",
            f"The result holds for judge {report.judge_id} only; a new judge needs a new gate run.",
            "A verified quote proves the words are in the case, not that they support the claim.",
            "Actor names are not authenticated; see 'identity'.",
        ],
        "history": [
            {"seq": e.seq, "ts": e.ts, "actor": e.actor, "type": e.type, "hash": e.hash}
            for e in related
        ],
        "integrity": {
            "chain_ok": verify.ok,
            "events": verify.count,
            "head": verify.head,
            "anchor_receipt": anchor_receipt,
            "verify": "precedent audit verify --db <log> --anchor <head>",
        },
    }
    doc["evidence_hash"] = sha256_hex(canonical_json(doc))
    return doc


# --- HTML ---------------------------------------------------------------------------

_CSS = """
:root{%LIGHT%}
@media (prefers-color-scheme: dark){:root{%DARK%}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 %SANS%}
main{max-width:960px;margin:0 auto;padding:48px 24px 80px}
h1{font:400 44px/1.1 %SERIF%;margin:8px 0 4px;letter-spacing:-.5px}
h2{font:400 28px/1.2 %SERIF%;margin:44px 0 12px;padding-top:16px;border-top:1px solid var(--line)}
h2 small{font:500 12px %MONO%;color:var(--faint);letter-spacing:.08em;margin-right:10px;text-transform:uppercase}
.kicker{font:500 12px %MONO%;color:var(--accent);letter-spacing:.12em;text-transform:uppercase}
.muted{color:var(--muted)}.faint{color:var(--faint)}
code,pre,.mono{font-family:%MONO%;font-size:13.5px}
pre{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 16px;overflow:auto}
table{border-collapse:collapse;width:100%;font-size:14px;margin:8px 0}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{font:500 12px %MONO%;color:var(--faint);text-transform:uppercase;letter-spacing:.06em}
.badge{display:inline-block;font:700 13px %MONO%;padding:3px 12px;border-radius:999px;border:1px solid}
.pass{color:var(--green);background:var(--green-bg)}.block{color:var(--red);background:var(--red-bg)}
.ok{color:var(--green)}.bad{color:var(--red)}.warn{color:var(--muted)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:16px 0}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.card b{display:block;font:400 26px %SERIF%}
blockquote{margin:8px 0;padding:6px 14px;border-left:3px solid var(--accent);color:var(--muted)}
.strip{display:flex;flex-wrap:wrap;gap:3px;margin:10px 0}
.cell{width:16px;height:16px;border-radius:3px;border:1px solid var(--line)}
.cell.fixed{background:var(--green);border-color:var(--green)}
.cell.broken{background:var(--red);border-color:var(--red)}
footer{margin-top:56px;font:12px %MONO%;color:var(--faint)}
"""


def _css() -> str:
    return (
        _CSS.replace("%LIGHT%", css_variables(LIGHT))
        .replace("%DARK%", css_variables(DARK))
        .replace("%SANS%", SANS)
        .replace("%SERIF%", SERIF)
        .replace("%MONO%", MONO)
    )


def _row(*cells: str) -> str:
    return "<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"


def render_html(doc: dict[str, Any], pack: Pack) -> str:
    e = escape
    s, why, ch, t, so, integ = (
        doc["summary"], doc["why"], doc["change"], doc["testing"], doc["signoffs"], doc["integrity"]
    )  # fmt: skip
    rep = t["report"]
    passed = s["gate_decision"] == "PASSED"
    badge = (
        '<span class="badge pass">✓ PASSED</span>'
        if passed
        else '<span class="badge block">✗ BLOCKED</span>'
    )
    lab = rep.get("labelled") or {}
    held = rep.get("heldout")

    parts = [
        f"<main><div class='kicker'>Evidence pack · {e(doc['format'])}</div>",
        f"<h1>{e(s['title'])}</h1>",
        f"<p class='muted mono'>{e(s['rule'])} · {e(s['plain'])}</p>",
        f"<p>{badge} &nbsp; status <b>{e(s['status'])}</b> · owner {e(s['owner'] or '—')} · "
        f"pack <code>{e(t['pack'])}</code></p>",
        "<div class='grid'>",
        f"<div class='card'><span class='faint mono'>fixes</span><b class='ok'>{lab.get('fixes', 0)}</b></div>",
        f"<div class='card'><span class='faint mono'>breaks</span><b class='{'bad' if lab.get('breaks') else 'ok'}'>{lab.get('breaks', 0)}</b></div>",
        f"<div class='card'><span class='faint mono'>labelled verdicts</span><b>{lab.get('right_before', 0)} → {lab.get('right_after', 0)} / {lab.get('n', 0)}</b></div>",
    ]
    if held:
        parts.append(
            f"<div class='card'><span class='faint mono'>held-out</span><b>{held['right_before']} → {held['right_after']} / {held['n']}</b></div>"
        )
    parts.append("</div>")

    # 1 why
    parts.append("<h2><small>1</small>Why this change exists</h2>")
    for c in why["corrections"]:
        parts.append(
            f"<p><b>{e(c['id'])}</b> · reviewer <b>{e(c['reviewer'])}</b> · {e(c.get('recorded_at') or '')}<br>"
            f"<code>{e(c['case_id'])}</code> <span class='faint mono'>sha256 {e(c['case_hash'][:16])}…</span> · "
            f"<code>{e(c['item'])}</code>: <span class='bad'>{e(c['ai_label'])}</span> → "
            f"<span class='ok'>{e(c['human_label'])}</span> · error type <code>{e(c['error_type'])}</code></p>"
        )
        if c.get("note"):
            parts.append(f"<blockquote>{e(c['note'])}</blockquote>")
        parts.append(f"<pre>{e(c['case_excerpt'])}</pre>")
        for q in c["evidence_quotes"]:
            parts.append(
                f"<p class='muted'>Judge, <code>{e(q['predicate'])}</code> = {e(q['value'])}: “{e(q['quote'])}”</p>"
            )
    parts.append(f"<p><b>Rationale.</b> {e(why['rationale'])}</p>")
    for p in why["predicates"]:
        parts.append(
            f"<p class='muted'><code>{e(p['id'])}</code>: {e(p['question'])} {e(p.get('note') or '')}</p>"
        )
    if why["policy_clauses"]:
        parts.append("<table><tr><th>clause</th><th>policy text</th></tr>")
        for cl in why["policy_clauses"]:
            parts.append(
                _row(
                    f"<code>{e(cl['id'])}</code><br><span class='faint'>{e(cl['doc'])} / {e(cl['section'])}</span>",
                    e(cl["text"]),
                )
            )
        parts.append("</table>")

    # 2 what changed
    parts.append("<h2><small>2</small>What changes</h2>")
    parts.append(f"<pre>{e(ch['rule_yaml'])}</pre>")
    if ch["diff"]:
        parts.append(
            f"<p class='muted'>Against the previous version {e(ch['previous_version'])}:</p><pre>{e(ch['diff'])}</pre>"
        )
    parts.append(
        f"<p class='faint mono'>rule content sha256 {e(ch['rule_hash'])}<br>active rules before {e(ch['active_before'][:16])}… → after {e(ch['active_after'][:16])}…</p>"
    )

    # 3 testing
    parts.append("<h2><small>3</small>Testing: the gate</h2>")
    parts.append("<table><tr><th>check</th><th>result</th><th>detail</th></tr>")
    for c in rep["checks"]:
        res = "pass" if c["passed"] else ("FAIL" if c["blocking"] else "advisory")
        cls = "ok" if c["passed"] else ("bad" if c["blocking"] else "warn")
        parts.append(
            _row(f"<code>{e(c['name'])}</code>", f"<b class='{cls}'>{res}</b>", e(c["detail"]))
        )
    parts.append("</table>")
    kinds = {f["case_id"]: f["kind"] for f in t["flips"]}
    parts.append(
        "<p class='muted'>Every labelled case, in order; filled cells changed.</p><div class='strip'>"
    )
    for case in pack.cases:
        kind = kinds.get(case.id, "")
        parts.append(
            f"<span class='cell {kind}' title='{e(case.id)} {e(kind or 'unchanged')}'></span>"
        )
    parts.append("</div>")
    if t["flips"]:
        parts.append(
            "<table><tr><th>case</th><th>split</th><th>before → after</th><th>label</th><th>effect</th><th>judge quote</th></tr>"
        )
        for f in t["flips"]:
            cls = {"fixed": "ok", "broken": "bad"}.get(f["kind"], "warn")
            parts.append(
                _row(
                    f"<code>{e(f['case_id'])}</code>",
                    e(f["split"]),
                    f"{e(f['before'])} → {e(f['after'])}",
                    e(f["golden"] or "—"),
                    f"<b class='{cls}'>{e(f['kind'])}</b>",
                    "<br>".join(f"“{e(q)}”" for q in f["quotes"]) or "—",
                )  # fmt: skip
            )
        parts.append("</table>")
    if lab:
        lo, hi = lab["after_ci"]
        parts.append(
            f"<p class='muted'>All labelled verdicts: {lab['right_before']} → {lab['right_after']} of {lab['n']} correct "
            f"(95% Wilson CI after: {lo:.2f}–{hi:.2f}); fixes {lab['fixes']}, breaks {lab['breaks']}, "
            f"exact McNemar p = {lab['mcnemar_p']:.2f}."
            + (
                f" Held-out: {held['right_before']} → {held['right_after']} of {held['n']}."
                if held
                else ""
            )
            + " Threshold: zero verdicts may go from right to wrong.</p>"
        )
    parts.append(
        f"<p class='faint mono'>judge {e(t['judge_id'])}<br>dataset sha256 {e(t['dataset_hash'])}<br>"
        f"report sha256 {e(t['report_hash'] or '')}<br>re-perform: {e(t['reproduce'])}</p>"
    )

    # 4 sign-offs
    parts.append("<h2><small>4</small>Sign-offs</h2><table>")
    seg = so["segregation"]
    parts.append(_row("author", e(so["author"] or "—")))
    parts.append(_row("gate run by", e(so["gate_runner"] or "—")))
    parts.append(_row("approved by", e(so["approver"] or "— (not approved)")))
    if so["approval_rationale"]:
        parts.append(_row("approver's rationale", e(so["approval_rationale"])))
    parts.append(
        _row(
            "author ≠ gate runner",
            "<b class='ok'>yes</b>"
            if seg["author_is_not_gate_runner"]
            else "<b class='bad'>no</b>",
        )
    )
    if so["approver"]:
        parts.append(
            _row(
                "author ≠ approver",
                "<b class='ok'>yes</b>"
                if seg["author_is_not_approver"]
                else "<b class='bad'>no</b>",
            )
        )
    parts.append(_row("identity", e(so["identity"])))
    parts.append("</table>")

    # 5 limitations, 6 history, 7 integrity
    parts.append("<h2><small>5</small>Limitations</h2><ul>")
    parts += [f"<li>{e(x)}</li>" for x in doc["limitations"]]
    parts.append(
        "</ul><h2><small>6</small>History</h2><table><tr><th>seq</th><th>time (UTC)</th><th>actor</th><th>event</th><th>hash</th></tr>"
    )
    for h in doc["history"]:
        parts.append(
            _row(
                str(h["seq"]),
                e(h["ts"]),
                e(h["actor"]),
                f"<code>{e(h['type'])}</code>",
                f"<span class='mono faint'>{e(h['hash'][:16])}…</span>",
            )
        )
    parts.append("</table><h2><small>7</small>Integrity</h2>")
    parts.append(
        f"<p>Hash chain {'<b class=ok>verifies</b>' if integ['chain_ok'] else '<b class=bad>FAILS</b>'} over "
        f"{integ['events']} events. Head:</p><pre>{e(integ['head'])}</pre>"
    )
    if integ["anchor_receipt"]:
        parts.append(f"<p>Head anchored outside the log: {e(integ['anchor_receipt'])}</p>")
    else:
        parts.append("<p class='bad'>Head not anchored outside the log.</p>")
    parts.append(
        f"<p class='faint mono'>{e(integ['verify'])}<br>evidence sha256 {e(doc['evidence_hash'])} "
        f"(over the JSON without this field)</p>"
    )
    parts.append(
        f"<footer>Generated {e(doc['generated_at'])} by precedent {e(doc['precedent_version'])} · "
        "github.com/FUYOH666/precedent</footer></main>"
    )
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>Evidence · {e(s['rule'])}</title><style>{_css()}</style></head><body>"
        + "\n".join(parts)
        + "</body></html>\n"
    )
