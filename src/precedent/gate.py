"""The gate: may this rule change verdicts?

A candidate rule is evaluated together with every rule that is already active,
against every labelled case the pack has, plus the cases behind accepted
corrections. It is BLOCKED if it breaks a single case that was right before,
if it does not fix the correction it came from, if it changes a declared
counter-example, if it conflicts with another rule, or if held-out agreement
goes down. Judge outputs are computed once; rules are applied by code, so the
gate is cheap enough to run on every proposal.
"""

from __future__ import annotations

from typing import Any, Literal

from precedent.engine import decide, rule_fires
from precedent.models import (
    RULE_WORTHY_ERRORS,
    Correction,
    Flip,
    GateCheck,
    GateReport,
    ItemMetrics,
    JudgeOutput,
    Rule,
    ruleset_hash,
)
from precedent.pack import Pack
from precedent.stats import agreement, cohen_kappa, paired_bootstrap_delta


def validate_rule(pack: Pack, rule: Rule, corrections: list[Correction]) -> list[str]:
    problems: list[str] = []
    if rule.pack != pack.id:
        problems.append(f"rule is for pack {rule.pack!r}, not {pack.id!r}")
        return problems
    try:
        item = pack.item(rule.item)
    except KeyError:
        return [f"unknown item {rule.item!r}"]
    if rule.then not in item.label_ids():
        problems.append(f"label {rule.then!r} is not valid for {rule.item}")
    for cond in rule.when:
        try:
            pack.predicate(cond.predicate)
        except KeyError:
            problems.append(
                f"predicate {cond.predicate!r} is not in the pack library; add it to pack.yaml "
                "and re-run the judge so it is evaluated on every case"
            )
    case_ids = {c.id for c in pack.cases}
    if not rule.counter_examples:
        problems.append("at least one counter-example is required: a case the rule must not change")
    for cid in [*rule.examples, *rule.counter_examples]:
        if cid not in case_ids:
            problems.append(f"unknown case {cid!r}")
    if not rule.source_corrections and not rule.examples:
        problems.append("a rule needs a source correction or at least one example")
    by_id = {c.id: c for c in corrections}
    for cid in rule.source_corrections:
        corr = by_id.get(cid)
        if corr is None:
            problems.append(f"unknown correction {cid!r}")
            continue
        if corr.item != rule.item:
            problems.append(f"correction {cid} is about {corr.item}, not {rule.item}")
        if corr.error_type not in RULE_WORTHY_ERRORS:
            problems.append(
                f"correction {cid} is a {corr.error_type!r}; keep it as a test case, "
                "it does not justify a rule"
            )
    return problems


def _golden(pack: Pack, corrections: list[Correction]) -> dict[tuple[str, str], str]:
    golden = {(c.id, item): label for c in pack.cases for item, label in c.golden.items()}
    for corr in corrections:
        golden[(corr.case_id, corr.item)] = corr.human_label
    return golden


def run_gate(
    pack: Pack,
    outputs: dict[str, JudgeOutput],
    active: list[Rule],
    candidate: Rule,
    corrections: list[Correction],
) -> GateReport:
    before_rules = [r for r in active if r.pack == pack.id]
    after_rules = [r for r in before_rules if r.id != candidate.id] + [candidate]
    judge_ids = sorted({o.judge_id for o in outputs.values()})
    base: dict[str, Any] = {
        "rule_key": candidate.key,
        "rule_hash": candidate.content_hash(),
        "pack": pack.id,
        "judge_id": ",".join(judge_ids) or "none",
        "dataset_hash": pack.dataset_hash(),
        "ruleset_before": ruleset_hash(before_rules),
        "ruleset_after": ruleset_hash(after_rules),
    }

    checks: list[GateCheck] = []
    problems = validate_rule(pack, candidate, corrections)
    missing = [c.id for c in pack.cases if c.id not in outputs]
    if missing:
        problems.append(f"no judge output for {len(missing)} case(s): {', '.join(missing[:5])}")
    hashes = {c.id: c.hash for c in pack.cases}
    foreign = [
        cid
        for cid, out in outputs.items()
        if hashes.get(cid) != out.case_hash or out.case_id != cid
    ]
    if foreign:
        problems.append(
            f"{len(foreign)} judge output(s) do not belong to their case: {', '.join(foreign[:5])}"
        )
    if len(judge_ids) > 1:
        problems.append(f"outputs come from more than one judge: {judge_ids}")
    # every accepted correction stays a test: its case must still exist, unchanged
    for corr in corrections:
        if corr.pack != pack.id:
            continue
        if corr.case_id not in hashes:
            problems.append(f"correction {corr.id}: case {corr.case_id} is no longer in the pack")
        elif hashes[corr.case_id] != corr.case_hash:
            problems.append(
                f"correction {corr.id}: case {corr.case_id} changed since it was corrected; "
                "re-confirm the correction"
            )
    not_asked = sorted(
        {
            cond.predicate
            for out in outputs.values()
            for cond in candidate.when
            if not out.abstained and cond.predicate not in out.predicates
        }
    )
    if not_asked:
        problems.append(f"judge was never asked {not_asked}; re-run the judge first")
    checks.append(GateCheck(name="well_formed", passed=not problems, detail="; ".join(problems)))
    if problems:
        return GateReport(**base, decision="BLOCKED", checks=checks, flips=[], metrics=[])

    golden = _golden(pack, corrections)
    split = {c.id: c.split for c in pack.cases}
    before = {cid: decide(pack, out, before_rules) for cid, out in outputs.items()}
    after = {cid: decide(pack, out, after_rules) for cid, out in outputs.items()}

    flips: list[Flip] = []
    for cid in sorted(outputs):
        for item in pack.items:
            b, a = before[cid][item.id].label, after[cid][item.id].label
            if a == b:
                continue
            g = golden.get((cid, item.id))
            kind: Literal["fixed", "broken", "changed", "unlabeled"]
            if g is None:
                kind = "unlabeled"
            elif a == g:
                kind = "fixed"
            elif b == g:
                kind = "broken"
            else:
                kind = "changed"
            flips.append(
                Flip(
                    case_id=cid,
                    item=item.id,
                    before=b,
                    after=a,
                    golden=g,
                    kind=kind,
                    split=split.get(cid, "dev"),
                )
            )

    # 1. the correction the rule came from is fixed
    by_id = {c.id: c for c in corrections}
    unfixed: list[str] = []
    for corr_id in candidate.source_corrections:
        corr = by_id[corr_id]
        case = pack.case(corr.case_id)
        if case.hash != corr.case_hash:
            unfixed.append(f"{corr_id}: case {case.id} changed since the correction")
        elif after[case.id][corr.item].label != corr.human_label:
            unfixed.append(f"{corr_id}: {case.id} is {after[case.id][corr.item].label}")
    checks.append(
        GateCheck(
            name="source_fixed",
            passed=not unfixed,
            detail="; ".join(unfixed) or f"{len(candidate.source_corrections)} correction(s) fixed",
        )
    )

    # 2. declared examples fire
    silent = [cid for cid in candidate.examples if not rule_fires(candidate, outputs[cid])]
    checks.append(
        GateCheck(
            name="examples_fire",
            passed=not silent,
            detail=f"does not fire on {', '.join(silent)}" if silent else "fires on all examples",
        )
    )

    # 3. declared counter-examples must not change at all (right or wrong)
    moved: list[str] = []
    for cid in candidate.counter_examples:
        was, now = before[cid][candidate.item].label, after[cid][candidate.item].label
        if now != was:
            moved.append(f"{cid}: {was} → {now}")
    checks.append(
        GateCheck(
            name="counter_examples_hold",
            passed=not moved,
            detail="; ".join(moved) or f"{len(candidate.counter_examples)} unchanged",
        )
    )

    # 4. nothing that was right becomes wrong
    broken = [f for f in flips if f.kind == "broken"]
    fixed = [f for f in flips if f.kind == "fixed"]
    checks.append(
        GateCheck(
            name="no_regressions",
            passed=not broken,
            detail=(
                f"breaks {len(broken)}: " + ", ".join(sorted({f.case_id for f in broken})[:8])
                if broken
                else f"fixes {len(fixed)}, breaks 0"
            ),
        )
    )

    # 5. no disagreement with an active rule
    conflicts = [
        cid
        for cid, decisions in after.items()
        for d in decisions.values()
        if d.source == "conflict" and candidate.key in d.rules
    ]
    checks.append(
        GateCheck(
            name="no_conflicts",
            passed=not conflicts,
            detail=f"conflicts on {', '.join(sorted(set(conflicts)))}" if conflicts else "none",
        )
    )

    # 6. held-out agreement does not go down
    heldout_keys = [
        (cid, item) for (cid, item) in golden if split.get(cid) == "heldout" and cid in outputs
    ]
    delta: float | None = None
    ci: tuple[float, float] | None = None
    if heldout_keys:
        b_ok = [before[cid][item].label == golden[(cid, item)] for cid, item in heldout_keys]
        a_ok = [after[cid][item].label == golden[(cid, item)] for cid, item in heldout_keys]
        delta, ci = paired_bootstrap_delta(b_ok, a_ok)
        checks.append(
            GateCheck(
                name="heldout_not_worse",
                passed=delta >= 0,
                detail=(
                    f"{sum(b_ok)}/{len(b_ok)} → {sum(a_ok)}/{len(a_ok)} "
                    f"(Δ {delta:+.3f}, 95% CI [{ci[0]:+.3f}, {ci[1]:+.3f}])"
                ),
            )
        )
    else:
        checks.append(
            GateCheck(
                name="heldout_not_worse",
                passed=True,
                blocking=False,
                detail="no held-out labels in this pack",
            )  # fmt: skip
        )

    # Advisory: does the rule generalise at all, and where could it not decide?
    known = set(candidate.examples) | {by_id[c].case_id for c in candidate.source_corrections}
    fires = [cid for cid, out in outputs.items() if rule_fires(candidate, out)]
    beyond = [cid for cid in fires if cid not in known]
    checks.append(
        GateCheck(
            name="generalises",
            passed=bool(beyond),
            blocking=False,
            detail=(
                f"fires on {len(fires)} case(s), {len(beyond)} beyond its sources"
                if beyond
                else "fires only on its own sources: a narrow rule, consider a test case instead"
            ),
        )
    )
    undecided = [
        cid
        for cid, out in outputs.items()
        if any(
            (ans := out.predicates.get(c.predicate)) is not None and ans.value == "unknown"
            for c in candidate.when
        )
    ]
    if undecided:
        checks.append(
            GateCheck(
                name="undecided_predicates",
                passed=False,
                blocking=False,
                detail=f"judge answered 'unknown' on {len(undecided)} case(s); rule cannot fire",
            )
        )

    metrics: list[ItemMetrics] = []
    for item in pack.items:
        keys = [(cid, it) for (cid, it) in golden if it == item.id and cid in outputs]
        bp = [(before[cid][item.id].label, golden[(cid, item.id)]) for cid, _ in keys]
        ap = [(after[cid][item.id].label, golden[(cid, item.id)]) for cid, _ in keys]
        metrics.append(
            ItemMetrics(
                item=item.id,
                n=len(keys),
                agreement_before=agreement(bp),
                agreement_after=agreement(ap),
                kappa_before=cohen_kappa(bp),
                kappa_after=cohen_kappa(ap),
            )
        )

    decision: Literal["PASSED", "BLOCKED"] = (
        "BLOCKED" if any(c.blocking and not c.passed for c in checks) else "PASSED"
    )
    return GateReport(
        **base,
        decision=decision,
        checks=checks,
        flips=flips,
        metrics=metrics,
        heldout_delta=delta,
        heldout_ci=ci,
        fires_on=len(fires),
    )
