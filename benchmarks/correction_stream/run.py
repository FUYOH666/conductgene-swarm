"""Correction-stream benchmark: how should reviewer corrections reach an LLM judge?

Each judge (``JUDGE_MODEL``) writes to its own ``results/<model>/``. Phases are cached
on disk (judge cassettes under ``results/<model>/runs/``), so each can be re-run, and
``analyze`` alone rebuilds the tables from the recorded cassettes without any model call:

    uv run python benchmarks/correction_stream/run.py build      # pack/cases.jsonl
    uv run python benchmarks/correction_stream/run.py base       # A0 on all cases
    uv run python benchmarks/correction_stream/run.py prompts    # A1 A2 A3 P on test
    uv run python benchmarks/correction_stream/run.py gated      # A3g (dev gate, test)
    uv run python benchmarks/correction_stream/run.py draft      # rules drafted by Qwen
    uv run python benchmarks/correction_stream/run.py rules      # B1 B2, 3 orders
    uv run python benchmarks/correction_stream/run.py stability  # A0 re-run on test
    uv run python benchmarks/correction_stream/run.py analyze    # results.json, RESULTS.md

See PREREGISTRATION.md for the design and the hypotheses.
"""

from __future__ import annotations

import json
import os
import random
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import httpx

from precedent.engine import decide, rule_fires
from precedent.gate import run_gate
from precedent.hashing import sha256_hex
from precedent.judge.cassette import RecordingJudge
from precedent.judge.llm import LLMJudge, _spoken_by, extract_json
from precedent.models import Case, Condition, Correction, JudgeOutput, Rule
from precedent.pack import Pack, load_pack
from precedent.similarity import SimilarityClient
from precedent.stats import mcnemar_exact, wilson

HERE = Path(__file__).resolve().parent
PACK_DIR = HERE / "pack"
BASE_URL = os.environ.get("PRECEDENT_LLM_BASE_URL", "https://openrouter.ai/api/v1")
API_KEY = os.environ.get("PRECEDENT_LLM_API_KEY", "")
JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "deepseek/deepseek-v4.1-flash-1017")
DRAFT_MODEL = os.environ.get("DRAFT_MODEL", "qwen/qwen3.8-27b")
WORKERS = int(os.environ.get("BENCH_WORKERS", "8"))
# every judge gets its own results directory, so cassettes never mix across judges
OUT = HERE / "results" / JUDGE_MODEL.split("/")[-1].replace(":", "-")
RUNS = OUT / "runs"
ITEMS = ["threat_language", "escalation_offered", "company_disclosure", "recording_disclosure"]
FACT_FOR_ITEM = {
    "threat_language": "threat",
    "escalation_offered": "escalation",
    "company_disclosure": "company",
    "recording_disclosure": "recording",
}
CHECKPOINTS = (15, 30)
ORDERS = (1, 2, 3)

REASONS: dict[tuple[str, str], str] = {
    ("threat", "arrest"): "Threatening arrest, jail, police or prosecution is a threat (fail).",
    (
        "threat",
        "euphemistic",
    ): "Threatening the sheriff, 'the authorities' or seizure of property is a threat of force even without the word arrest (fail).",
    (
        "threat",
        "vague",
    ): "Warning of unspecified serious consequences is pressure that needs review (needs_review).",
    (
        "threat",
        "lawful",
    ): "Accurately stating a lawful next step such as credit reporting or a civil claim is not a threat (pass).",
    (
        "threat",
        "negated",
    ): "Mentioning arrest or police only to rule it out is not a threat (pass).",
    ("threat", "none"): "There is no threat or pressure in this call (pass).",
    (
        "escalation",
        "transfer",
    ): "Offering a live transfer to a supervisor, manager or team lead is an escalation offer (pass).",
    (
        "escalation",
        "callback_supervisor",
    ): "A promised callback from a supervisor or manager is an escalation offer (pass).",
    (
        "escalation",
        "callback_teamlead",
    ): "A promised callback from a team lead is an escalation offer (pass).",
    (
        "escalation",
        "callback_specialist",
    ): "A callback from a specialist, hardship or payments team is not an escalation offer (needs_review).",
    (
        "escalation",
        "refused",
    ): "The customer asked for a supervisor and the agent declined, so no escalation was offered (needs_review).",
    (
        "escalation",
        "none",
    ): "No contact with a supervisor, manager or team lead was offered (needs_review).",
    (
        "company",
        "full",
    ): "The agent stated both the company name and the purpose of the call (pass).",
    (
        "company",
        "name_only",
    ): "The agent named the company but never said why they were calling (needs_review).",
    ("recording", "disclosed"): "The agent clearly and early said the call may be recorded (pass).",
    (
        "recording",
        "unclear",
    ): "A vague or late reference to keeping notes of the call is not a clear recording disclosure (needs_review).",
    (
        "recording",
        "none",
    ): "Recording is never mentioned, so the requirement does not apply (not_applicable).",
    (
        "ood",
        "true",
    ): "This call is not about a debt or payment, so the rubric does not apply (abstain).",
}
PLACEBO_SENTENCES = [
    "Read the whole transcript before deciding any item.",
    "Consider each rubric item on its own terms.",
    "Quote the transcript exactly when you cite it.",
    "Prefer the label whose meaning matches the transcript most closely.",
    "Do not let the tone of the customer change the label for the agent's conduct.",
    "Check both the agent's and the customer's lines for context.",
]


# --- data ------------------------------------------------------------------------------


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return (
        [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        if path.exists()
        else []
    )


def specs() -> dict[str, dict[str, Any]]:
    return {r["id"]: r for r in _jsonl(HERE / "specs.jsonl")}


def build() -> None:
    sp = specs()
    texts = {r["id"]: r["text"] for r in _jsonl(HERE / "transcripts.jsonl")}
    adjudicated = {r["id"]: r for r in _jsonl(HERE / "adjudication.jsonl")}
    rows = []
    dropped = []
    for cid, s in sp.items():
        adj = adjudicated.get(cid, {})
        if adj.get("decision") == "drop" or cid not in texts:
            dropped.append(cid)
            continue
        text = adj.get("text", texts[cid])
        rows.append(
            {
                "id": cid,
                "text": text,
                "golden": s["golden"],
                "split": "heldout" if s["split"] == "test" else "dev",
                "metadata": {
                    "bench_split": s["split"],
                    "group": s["group"],
                    "contrast": s["contrast"],
                    "facts": s["facts"],
                },
            }  # fmt: skip
        )
    (PACK_DIR / "cases.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    )
    print(f"cases {len(rows)}, dropped {dropped}")


def pack() -> Pack:
    return load_pack(PACK_DIR)


def split_of(case: Case) -> str:
    return str(case.metadata["bench_split"])


# --- judges ----------------------------------------------------------------------------


class GuidedJudge(LLMJudge):
    """The structured judge plus extra guidance; the guidance is part of its id."""

    def __init__(
        self, p: Pack, tag: str, guidance: str = "", per_case: dict[str, str] | None = None
    ) -> None:
        super().__init__(
            p, base_url=BASE_URL, model=JUDGE_MODEL, api_key=API_KEY or None, timeout=600
        )
        self.tag = tag
        self.guidance = guidance
        self.per_case = per_case or {}
        self._id = f"{tag}:{JUDGE_MODEL}:{sha256_hex(self.prompt_hash + guidance + json.dumps(self.per_case, sort_keys=True))[:10]}"

    @property
    def judge_id(self) -> str:
        return self._id

    def messages(self, case: Case) -> list[dict[str, str]]:
        msgs = super().messages(case)
        extra = self.guidance + self.per_case.get(case.id, "")
        if extra:
            msgs[0] = {"role": "system", "content": msgs[0]["content"] + "\n\n" + extra}
        return msgs


def run_judge(judge: LLMJudge, cases: list[Case], name: str) -> dict[str, JudgeOutput]:
    """Judge cases in parallel; every new output is appended to the run's cassette."""
    rec = RecordingJudge(judge, RUNS / f"{name}.jsonl")
    cached = {c.id for c in cases if c.hash in rec._outputs}
    todo = [c for c in cases if c.id not in cached]
    lock = threading.Lock()
    done = 0

    def one(c: Case) -> None:
        nonlocal done
        out = judge.judge(c)
        with lock:
            rec.cassette.append(out)
            rec._outputs[c.hash] = out
            done += 1
            if done % 20 == 0:
                print(f"  {name}: {done}/{len(todo)} new", flush=True)

    with ThreadPoolExecutor(WORKERS) as pool:
        list(pool.map(one, todo))
    return {c.id: rec.judge(c) for c in cases}


def load_run(name: str, p: Pack) -> dict[str, JudgeOutput]:
    by_hash = {c.hash: c.id for c in p.cases}
    return {
        by_hash[o["case_hash"]]: JudgeOutput.model_validate(o)
        for o in _jsonl(RUNS / f"{name}.jsonl")
        if o["case_hash"] in by_hash
    }


# --- corrections ------------------------------------------------------------------------


def reason_for(case: Case, item: str) -> str:
    facts = case.metadata["facts"]
    if facts.get("out_of_domain"):
        return REASONS[("ood", "true")]
    factor = FACT_FOR_ITEM[item]
    return REASONS[(factor, str(facts[factor]))]


def stream(p: Pack, base: dict[str, JudgeOutput]) -> list[dict[str, Any]]:
    by_item: dict[str, list[dict[str, Any]]] = {i: [] for i in ITEMS}
    for c in p.cases:
        if split_of(c) != "pool":
            continue
        d = decide(p, base[c.id], [])
        for item in ITEMS:
            if d[item].label != c.golden[item]:
                by_item[item].append(
                    {
                        "case_id": c.id,
                        "item": item,
                        "ai_label": d[item].label,
                        "human_label": c.golden[item],
                        "reason": reason_for(c, item),
                    }  # fmt: skip
                )
    rng = random.Random(7)
    for lst in by_item.values():
        rng.shuffle(lst)
    out: list[dict[str, Any]] = []
    while len(out) < 30 and any(by_item.values()):
        for item in ITEMS:
            if by_item[item] and len(out) < 30:
                out.append(by_item[item].pop())
    for n, corr in enumerate(out, 1):
        corr["id"] = f"C-{n:02d}"
    (OUT / "corrections.json").write_text(json.dumps(out, indent=1))
    return out


def corrections() -> list[dict[str, Any]]:
    return json.loads((OUT / "corrections.json").read_text())


def as_correction(p: Pack, c: dict[str, Any]) -> Correction:
    case = p.case(c["case_id"])
    return Correction(id=c["id"], pack=p.id, case_id=case.id, case_hash=case.hash, item=c["item"],
                      ai_label=c["ai_label"], human_label=c["human_label"], reviewer="bench",
                      error_type="policy_misinterpretation", note=c["reason"])  # fmt: skip


def example_block(p: Pack, corrs: list[dict[str, Any]], title: str) -> str:
    parts = [title]
    for c in corrs:
        parts.append(
            f"Case:\n<<<\n{p.case(c['case_id']).text}\n>>>\nItem {c['item']}: correct label "
            f"{c['human_label']}. Reason: {c['reason']}"
        )
    return "\n\n".join(parts)


def guideline_block(corrs: list[dict[str, Any]]) -> str:
    reasons = list(dict.fromkeys(c["reason"] for c in corrs))
    return "## Reviewer guidelines from past corrections\n" + "\n".join(f"- {r}" for r in reasons)


def placebo_block(length: int) -> str:
    out = ["## Reviewer guidelines"]
    i = 0
    while len("\n".join(out)) < length:
        out.append(f"- {PLACEBO_SENTENCES[i % len(PLACEBO_SENTENCES)]}")
        i += 1
    return "\n".join(out)


# --- phases ---------------------------------------------------------------------------


def phase_base() -> None:
    p = pack()
    run_judge(GuidedJudge(p, "A0"), p.cases, "A0")
    stream(p, load_run("A0", p))


def test_cases(p: Pack) -> list[Case]:
    return [c for c in p.cases if split_of(c) == "test"]


def dev_cases(p: Pack) -> list[Case]:
    return [c for c in p.cases if split_of(c) == "dev"]


def phase_prompts() -> None:
    p = pack()
    corrs = corrections()
    tests = test_cases(p)
    sim = SimilarityClient()
    for cp in CHECKPOINTS:
        upto = corrs[:cp]
        if not upto:
            continue
        a3 = guideline_block(upto)
        run_judge(
            GuidedJudge(
                p, f"A1-{cp}", example_block(p, upto, "## Earlier decisions corrected by reviewers")
            ),
            tests,
            f"A1-{cp}",
        )
        run_judge(GuidedJudge(p, f"A3-{cp}", a3), tests, f"A3-{cp}")
        run_judge(GuidedJudge(p, f"P-{cp}", placebo_block(len(a3))), tests, f"P-{cp}")
        pool_texts = {c["id"]: p.case(c["case_id"]).text for c in upto}
        per_case = {}
        for t in tests:
            near = sim.nearest(t.text, pool_texts, k=min(5, len(upto)))
            chosen = [next(c for c in upto if c["id"] == n.case_id) for n in near]
            per_case[t.id] = example_block(
                p, chosen, "## Similar earlier decisions corrected by reviewers"
            )
        run_judge(GuidedJudge(p, f"A2-{cp}", per_case=per_case), tests, f"A2-{cp}")


def _flips(
    p: Pack, before: dict[str, JudgeOutput], after: dict[str, JudgeOutput], cases: list[Case]
) -> tuple[int, int]:
    neg = pos = 0
    for c in cases:
        b, a = decide(p, before[c.id], []), decide(p, after[c.id], [])
        for item in ITEMS:
            rb, ra = b[item].label == c.golden[item], a[item].label == c.golden[item]
            neg += rb and not ra
            pos += ra and not rb
    return neg, pos


def phase_gated() -> None:
    p = pack()
    corrs = corrections()
    base = load_run("A0", p)
    devs, tests = dev_cases(p), test_cases(p)
    log: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    for n, (lo, hi) in enumerate([(0, 15), (15, 30)], 1):
        batch = corrs[lo:hi]
        if not batch:
            continue
        candidate = accepted + batch
        dev_out = run_judge(
            GuidedJudge(p, f"A3g-dev-{n}", guideline_block(candidate)), devs, f"A3g-dev-{n}"
        )
        neg, pos = _flips(p, base, dev_out, devs)
        keep = neg == 0
        log.append(
            {
                "batch": n,
                "corrections": [c["id"] for c in batch],
                "dev_negative": neg,
                "dev_positive": pos,
                "kept": keep,
            }
        )
        if keep:
            accepted = candidate
        if accepted:
            run_judge(GuidedJudge(p, f"A3g-{hi}", guideline_block(accepted)), tests, f"A3g-{hi}")
    (OUT / "a3g_log.json").write_text(json.dumps(log, indent=1))
    print(log)


# --- rule drafting (B arms) ---------------------------------------------------------------

DRAFT_PROMPT = """You turn one reviewer correction of an AI judge into a rule.
A rule says: when these yes/no predicates have these answers, the item gets this label.
You may only use predicates from the library below. Use 1 to 3 conditions. The rule must fire on the corrected case,
so every condition must match the judge's predicate answers for that case shown below (an answer of "unknown" never matches).
State the reason, not a surface feature: prefer the predicates that make the reviewer's label right.
If no rule in this vocabulary can express the correction, reply {"expressible": false}.
Reply with JSON only: {"expressible": true, "title": "...", "when": [{"predicate": "...", "equals": "yes|no"}], "then": "<label>"}"""


def _ask(client: httpx.Client, system: str, user: str) -> dict[str, Any]:
    body = {"model": DRAFT_MODEL, "temperature": 0, "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}  # fmt: skip
    for _ in range(3):
        r = client.post(f"{BASE_URL}/chat/completions", json=body)
        r.raise_for_status()
        try:
            return extract_json(r.json()["choices"][0]["message"]["content"] or "")
        except ValueError:
            continue
    return {"expressible": False, "error": "no JSON"}


def _draft_user(p: Pack, corr: dict[str, Any], out: JudgeOutput, feedback: str = "") -> str:
    lib = "\n".join(f"- {pr.id}: {pr.question}" for pr in p.predicates)
    answers = "\n".join(f"- {k}: {v.value}" for k, v in out.predicates.items())
    labels = ", ".join(p.item(corr["item"]).label_ids())
    return (
        f"Predicate library:\n{lib}\n\nCorrected case:\n<<<\n{p.case(corr['case_id']).text}\n>>>\n"
        f"Judge's predicate answers on this case:\n{answers}\n\nItem: {corr['item']} (labels: {labels})\n"
        f"The judge said {corr['ai_label']}; the reviewer says {corr['human_label']}.\nReviewer's reason: {corr['reason']}\n"
        + (
            f"\nYour previous rule was blocked by the gate:\n{feedback}\nNarrow it so it stops changing those cases."
            if feedback
            else ""
        )
    )


def to_rule(p: Pack, corr: dict[str, Any], d: dict[str, Any], version: int = 1) -> Rule | None:
    if not d.get("expressible") or not d.get("when"):
        return None
    try:
        when = [
            Condition(predicate=c["predicate"], equals=c.get("equals", "yes")) for c in d["when"]
        ]
        rule = Rule(id=f"R-{corr['id']}", version=version, pack=p.id, item=corr["item"], title=str(d.get("title", ""))[:120] or corr["reason"],
                    rationale=corr["reason"], when=when, then=str(d.get("then", corr["human_label"])),
                    source_corrections=[corr["id"]], examples=[corr["case_id"]], counter_examples=[], author="drafter")  # fmt: skip
    except Exception:
        return None
    known = {pr.id for pr in p.predicates}
    if (
        any(c.predicate not in known for c in rule.when)
        or rule.then not in p.item(rule.item).label_ids()
    ):
        return None
    return rule


def phase_draft() -> None:
    p = pack()
    base = load_run("A0", p)
    drafts = {}
    headers = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}
    with httpx.Client(timeout=600, headers=headers) as client:
        for corr in corrections():
            d = _ask(client, DRAFT_PROMPT, _draft_user(p, corr, base[corr["case_id"]]))
            drafts[corr["id"]] = d
            print(corr["id"], json.dumps(d)[:160], flush=True)
    (OUT / "drafts.json").write_text(json.dumps(drafts, indent=1))


def _gate_pack(p: Pack, corrs_so_far: list[dict[str, Any]]) -> Pack:
    """What a gate may see: dev labels, plus the pool cases behind corrections (no other pool labels)."""
    pool_ids = {c["case_id"] for c in corrs_so_far}
    cases = [c for c in p.cases if split_of(c) == "dev"]
    cases += [c.model_copy(update={"golden": {}}) for c in p.cases if c.id in pool_ids]
    return p.model_copy(update={"cases": cases})


def _mine_counter_examples(
    p: Pack, rule: Rule, base: dict[str, JudgeOutput], sim: SimilarityClient, k: int = 2
) -> list[str]:
    """Nearest dev cases to the source case where the rule does not fire (embedding miner)."""
    src = p.case(rule.examples[0])
    cands = {c.id: c.text for c in dev_cases(p) if not rule_fires(rule, base[c.id])}
    return [n.case_id for n in sim.nearest(src.text, cands, k=k)]


def phase_rules() -> None:
    p = pack()
    base = load_run("A0", p)
    drafts = json.loads((OUT / "drafts.json").read_text())
    corrs = corrections()
    sim = SimilarityClient()
    results: dict[str, Any] = {}
    revisions_cache: dict[str, Any] = (
        json.loads((OUT / "revisions.json").read_text())
        if (OUT / "revisions.json").exists()
        else {}
    )
    headers = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}
    with httpx.Client(timeout=600, headers=headers) as client:
        for seed in ORDERS:
            order = corrs[:]
            random.Random(seed).shuffle(order)
            b1: list[Rule] = []
            b2: list[Rule] = []
            log = []
            for n, corr in enumerate(order, 1):
                rule = to_rule(p, corr, drafts[corr["id"]])
                entry: dict[str, Any] = {"correction": corr["id"], "expressible": rule is not None}
                if rule is not None:
                    b1.append(rule)
                    rule = rule.model_copy(
                        update={"counter_examples": _mine_counter_examples(p, rule, base, sim)}
                    )
                    so_far = [c for c in order[:n]]
                    gp = _gate_pack(p, so_far)
                    outs = {c.id: base[c.id] for c in gp.cases}
                    cs = [as_correction(p, c) for c in so_far]
                    rep = run_gate(gp, outs, b2, rule, cs)
                    entry["first_gate"] = rep.decision
                    if rep.decision == "BLOCKED":
                        key = f"{corr['id']}|{rule.content_hash()[:12]}"
                        if key not in revisions_cache:
                            fb = "; ".join(f"{c.name}: {c.detail}" for c in rep.blocking_failures)
                            revisions_cache[key] = _ask(
                                client,
                                DRAFT_PROMPT,
                                _draft_user(p, corr, base[corr["case_id"]], fb),
                            )
                        rev = to_rule(p, corr, revisions_cache[key], version=2)
                        if rev is not None:
                            rev = rev.model_copy(
                                update={
                                    "counter_examples": _mine_counter_examples(p, rev, base, sim)
                                }
                            )
                            rep = run_gate(gp, outs, b2, rev, cs)
                            entry["second_gate"] = rep.decision
                            rule = rev
                    if rep.decision == "PASSED":
                        b2 = [r for r in b2 if r.id != rule.id] + [rule]
                    entry["accepted"] = rep.decision == "PASSED"
                # a stream shorter than a checkpoint is read at its end, as the A arms are
                for cp in CHECKPOINTS:
                    if n == min(cp, len(order)):
                        entry.setdefault("checkpoints", []).append(cp)
                        results.setdefault(f"order{seed}", {})[str(cp)] = {
                            "B1": [r.model_dump(mode="json") for r in b1],
                            "B2": [r.model_dump(mode="json") for r in b2],
                        }
                log.append(entry)
            results.setdefault(f"order{seed}", {})["log"] = log
    (OUT / "revisions.json").write_text(json.dumps(revisions_cache, indent=1))
    (OUT / "rules_runs.json").write_text(json.dumps(results, indent=1))
    print("rules done")


def phase_stability() -> None:
    p = pack()
    run_judge(GuidedJudge(p, "A0-rerun", guidance="\n"), test_cases(p), "A0-rerun")


# --- analysis -----------------------------------------------------------------------------


def _decisions(
    p: Pack, outs: dict[str, JudgeOutput], cases: list[Case], rules: list[Rule] | None = None
) -> dict[tuple[str, str], str]:
    return {
        (c.id, item): decide(p, outs[c.id], rules or [])[item].label
        for c in cases
        for item in ITEMS
    }


def _score(
    p: Pack, cases: list[Case], base: dict[tuple[str, str], str], arm: dict[tuple[str, str], str]
) -> dict[str, Any]:
    keys = [(c.id, i) for c in cases for i in ITEMS]
    gold = {(c.id, i): c.golden[i] for c in cases for i in ITEMS}
    right = sum(arm[k] == gold[k] for k in keys)
    neg = [k for k in keys if base[k] == gold[k] and arm[k] != gold[k]]
    pos = [k for k in keys if base[k] != gold[k] and arm[k] == gold[k]]
    cases_right = sum(all(arm[(c.id, i)] == gold[(c.id, i)] for i in ITEMS) for c in cases)
    per_item = {i: sum(arm[(c.id, i)] == gold[(c.id, i)] for c in cases) for i in ITEMS}
    # locality: contrast pairs in this set where a verdict flips right → wrong
    groups: dict[str, list[str]] = {}
    for c in cases:
        if c.metadata.get("contrast"):
            groups.setdefault(str(c.metadata["group"]), []).append(c.id)
    neg_cases = {k[0] for k in neg}
    locality_violations = sum(1 for ids in groups.values() if any(i in neg_cases for i in ids))
    return {
        "n": len(keys), "right": right, "accuracy": right / len(keys), "ci": wilson(right, len(keys)),
        "negative_flips": len(neg), "positive_flips": len(pos), "mcnemar_vs_A0": mcnemar_exact(len(pos), len(neg)),
        "cases_all_right": cases_right, "per_item": per_item, "locality_violations": locality_violations,
        "contrast_groups": len(groups), "negative": [list(k) for k in neg],
    }  # fmt: skip


def _fact_value(case: Case, item: str) -> str:
    facts = case.metadata["facts"]
    return "out_of_domain" if facts.get("out_of_domain") else str(facts[FACT_FOR_ITEM[item]])


def _prompt_tokens(outs: dict[str, JudgeOutput], cases: list[Case]) -> int:
    toks = [int(outs[c.id].meta.get("usage", {}).get("prompt_tokens", 0)) for c in cases]
    return round(sum(toks) / len(toks)) if toks else 0


def _secondary_and_exploratory(
    p: Pack,
    tests: list[Case],
    base_out: dict[str, JudgeOutput],
    base: dict[tuple[str, str], str],
    arms: dict[str, dict[str, Any]],
    rr: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    corrs = corrections()
    if not corrs:
        return {}, {}
    corrected = {(c["item"], _fact_value(p.case(c["case_id"]), c["item"])) for c in corrs}
    gold = {(c.id, i): c.golden[i] for c in tests for i in ITEMS}
    eligible = [
        (c.id, i)
        for c in tests
        for i in ITEMS
        if base[(c.id, i)] != gold[(c.id, i)] and (i, _fact_value(c, i)) in corrected
    ]
    final_rules = [Rule.model_validate(x) for x in rr.get("order1", {}).get("30", {}).get("B2", [])]
    runs = {
        "A0": (base_out, []),
        "A1@30": (load_run("A1-30", p), []),
        "A2@30": (load_run("A2-30", p), []),
        "A3@30": (load_run("A3-30", p), []),
        "P@30": (load_run("P-30", p), []),
        "B2@30": (base_out, final_rules),
    }
    secondary: dict[str, Any] = {}
    for key, (outs, rules) in runs.items():
        if key not in arms or any(c.id not in outs for c in tests):
            continue
        dec = _decisions(p, outs, tests, rules)
        secondary[key] = {
            "eligible": len(eligible),
            "generalised": sum(dec[k] == gold[k] for k in eligible),
            "prompt_tokens": _prompt_tokens(outs, tests),
        }

    notes: list[str] = []
    # where the negative flips of each arm concentrate
    for key in ("A0-rerun", "A1@30", "A2@30", "A3@30", "P@30"):
        if key not in arms or not arms[key]["negative"]:
            continue
        kinds: dict[str, int] = {}
        for cid, item in arms[key]["negative"]:
            v = _fact_value(p.case(cid), item)
            k = "out-of-domain calls" if v == "out_of_domain" else f"`{FACT_FOR_ITEM[item]} = {v}`"
            kinds[k] = kinds.get(k, 0) + 1
        top, n = max(kinds.items(), key=lambda kv: kv[1])
        notes.append(
            f"{key.replace('@30', '')}: {n} of its {arms[key]['negative_flips']} right→wrong flips fall on {top}."
        )
    # rules on top of retrieved examples: the rules read A2's own predicate answers (no new call)
    a2 = runs["A2@30"][0]
    if "A2@30" in arms and len(a2) == len(tests) and final_rules:
        s = _score(p, tests, base, _decisions(p, a2, tests, final_rules))
        notes.append(
            f"B2's rules applied on top of A2's outputs: {s['right']}/{s['n']} ({s['accuracy']:.1%}), "
            f"{s['negative_flips']} right→wrong, {s['positive_flips']} wrong→right."
        )
    # corrections no rule could express: did the judge support a "yes" with the customer's words?
    drafts = json.loads((OUT / "drafts.json").read_text()) if (OUT / "drafts.json").exists() else {}
    inexpressible = [c for c in corrs if drafts and not drafts.get(c["id"], {}).get("expressible")]
    if inexpressible:
        # predicates that ask what the agent did; a customer's line is no evidence for them
        agent_preds = {pr.id for pr in p.predicates if "the agent" in pr.question.lower()}
        items: dict[str, int] = {}
        misread: dict[str, int] = {}
        customer = 0
        for c in inexpressible:
            items[c["item"]] = items.get(c["item"], 0) + 1
            case, out = p.case(c["case_id"]), base_out[c["case_id"]]
            hits = [
                k
                for k, a in out.predicates.items()
                if k in agent_preds
                and a.value == "yes"
                and a.quote is not None
                and _spoken_by(case.text, a.quote, "Customer")
            ]
            customer += bool(hits)
            for k in hits:
                misread[k] = misread.get(k, 0) + 1
        notes.append(
            f"{len(inexpressible)} of {len(corrs)} corrections could not be written as a rule "
            f"({', '.join(f'{k} ×{v}' for k, v in items.items())}). In {customer} of them the judge answered "
            f"a question about the agent with the customer's words ("
            + ", ".join(f"`{k} = yes` ×{v}" for k, v in misread.items())
            + "): a perception error, which a rule over the judge's own answers cannot repair. "
            "A predicate bound to a speaker (`speaker: Agent`, used in the demo pack but not in the frozen "
            "benchmark library) would have rejected those quotes."
        )
    cost = sum(
        float(o.meta.get("usage", {}).get("cost", 0) or 0)
        for f in sorted(RUNS.glob("*.jsonl"))
        for o in (JudgeOutput.model_validate(x) for x in _jsonl(f))
    )
    if cost:
        notes.append(f"Judge calls recorded for this judge cost ${cost:.2f} on OpenRouter in total.")
    return secondary, {"notes": notes}


def holm(pvals: dict[str, float]) -> dict[str, float]:
    ordered = sorted(pvals.items(), key=lambda kv: kv[1])
    m, out, running = len(ordered), {}, 0.0
    for i, (k, pv) in enumerate(ordered):
        running = max(running, min(1.0, (m - i) * pv))
        out[k] = running
    return out


def phase_analyze() -> None:
    p = pack()
    tests = test_cases(p)
    base_out = load_run("A0", p)
    base = _decisions(p, base_out, tests)
    arms: dict[str, dict[str, Any]] = {"A0": _score(p, tests, base, base)}
    n_corr = len(corrections())
    # with an empty stream there is nothing to feed back: only the baseline exists
    arm_names = ("A1", "A2", "A3", "P", "A3g") if n_corr else ()
    for name in arm_names:
        for cp in CHECKPOINTS:
            run = load_run(f"{name}-{cp}", p)
            if len(run) == len(tests):
                arms[f"{name}@{cp}"] = _score(p, tests, base, _decisions(p, run, tests))
            elif name == "A3g":  # batch rejected → same as A0 at this checkpoint
                arms[f"{name}@{cp}"] = {**arms["A0"], "note": "no batch accepted"}
    rerun = load_run("A0-rerun", p)
    if len(rerun) == len(tests):
        arms["A0-rerun"] = _score(p, tests, base, _decisions(p, rerun, tests))
    rr = (
        json.loads((OUT / "rules_runs.json").read_text())
        if (OUT / "rules_runs.json").exists()
        else {}
    )
    for arm in ("B1", "B2") if n_corr else ():
        for cp in CHECKPOINTS:
            scores = []
            for seed in ORDERS:
                rules = [
                    Rule.model_validate(r)
                    for r in rr.get(f"order{seed}", {}).get(str(cp), {}).get(arm, [])
                ]
                scores.append(_score(p, tests, base, _decisions(p, base_out, tests, rules)))
            if scores:
                arms[f"{arm}@{cp}"] = {
                    **scores[0],
                    "orders": [
                        {k: s[k] for k in ("accuracy", "negative_flips", "positive_flips")}
                        for s in scores
                    ],
                    "negative_flips_mean": sum(s["negative_flips"] for s in scores) / len(scores),
                    "accuracy_mean": sum(s["accuracy"] for s in scores) / len(scores),
                }
    # H1: B2@30 vs A1/A2/A3@30 on negative flips (paired per verdict), Holm-corrected
    comps = {}
    if "B2@30" in arms:
        b2neg = {tuple(k) for k in arms["B2@30"]["negative"]}
        for other in ("A1@30", "A2@30", "A3@30"):
            if other in arms:
                oneg = {tuple(k) for k in arms[other]["negative"]}
                comps[other] = mcnemar_exact(len(oneg - b2neg), len(b2neg - oneg))
    coverage = {}
    for seed in ORDERS:
        log = rr.get(f"order{seed}", {}).get("log", [])
        if log:
            coverage[f"order{seed}"] = {
                "corrections": len(log),
                "expressible": sum(e["expressible"] for e in log),
                "accepted": sum(bool(e.get("accepted")) for e in log),
                "revised": sum("second_gate" in e for e in log),
            }
    secondary, exploratory = _secondary_and_exploratory(p, tests, base_out, base, arms, rr)
    pool = [c for c in p.cases if split_of(c) == "pool"]
    pool_dec = _decisions(p, base_out, pool)
    all_dec = _decisions(p, base_out, p.cases)
    result = {
        "judge": JUDGE_MODEL,
        "all_verdicts": len(all_dec),
        "all_right": sum(all_dec[(c.id, i)] == c.golden[i] for c in p.cases for i in ITEMS),
        "pool_verdicts": len(pool_dec),
        "pool_errors": sum(pool_dec[(c.id, i)] != c.golden[i] for c in pool for i in ITEMS),
        "pack_cases": len(p.cases),
        "test_cases": len(tests),
        "corrections": n_corr,
        "checkpoints": {str(cp): min(cp, n_corr) for cp in CHECKPOINTS},
        "arms": arms,
        "h1_mcnemar_holm": holm(comps) if comps else {},
        "coverage": coverage,
        "secondary": secondary,
        "exploratory": exploratory,
        "a3g_log": json.loads((OUT / "a3g_log.json").read_text())
        if (OUT / "a3g_log.json").exists()
        else [],
    }
    (OUT / "results.json").write_text(json.dumps(result, indent=1))
    (OUT / "RESULTS.md").write_text(render_results(result), encoding="utf-8")
    print(
        json.dumps(
            {
                k: {kk: v[kk] for kk in ("accuracy", "negative_flips", "positive_flips") if kk in v}
                for k, v in arms.items()
            },
            indent=1,
        )
    )


ARM_LABELS = {
    "A0": "no corrections (baseline judge)",
    "A1": "all corrections as few-shot examples",
    "A2": "top-5 retrieved corrected examples (bge-m3 + reranker)",
    "A3": "reasons pasted into the prompt as guidelines",
    "A3g": "guidelines, batch kept only if dev shows no regression",
    "P": "placebo paragraph of the same length",
    "B1": "predicate rules, ungated",
    "B2": "predicate rules through the Precedent gate",
    "A0-rerun": "baseline judge re-run (noise floor)",
}


def render_results(r: dict[str, Any]) -> str:
    arms = r["arms"]

    def row(key: str) -> str:
        a = arms[key]
        name, _, cp = key.partition("@")
        lo, hi = a["ci"]
        neg = f"{a['negative_flips']}"
        if "orders" in a:
            negs = [o["negative_flips"] for o in a["orders"]]
            neg = f"{a['negative_flips_mean']:.1f} ({min(negs)}–{max(negs)})"
        shown = r.get("checkpoints", {}).get(cp, cp)
        if cp and str(shown) != cp:
            shown = f"{shown} (whole stream)"
        return (
            f"| {name} | {shown or '—'} | {ARM_LABELS.get(name, '')} | {a['right']}/{a['n']} "
            f"({a['accuracy']:.1%}, {lo:.1%}–{hi:.1%}) | {neg} | {a['positive_flips']} | "
            f"{a['mcnemar_vs_A0']:.3f} | {a['cases_all_right']}/{r['test_cases']} |"
        )

    order = ["A0", "A0-rerun"] + [
        f"{a}@{cp}" for cp in CHECKPOINTS for a in ("A1", "A2", "A3", "A3g", "P", "B1", "B2")
    ]
    lines = [
        "# Results: correction-stream benchmark",
        "",
        f"Generated by `run.py analyze`. Sealed test: {r['test_cases']} cases × 4 items = "
        f"{r['test_cases'] * 4} verdicts. Corrections in the stream: {r['corrections']}. "
        "Design and hypotheses: [PREREGISTRATION.md](PREREGISTRATION.md); deviations: [DEVIATIONS.md](DEVIATIONS.md).",
        "",
        "A **negative flip** is a verdict the baseline judge got right that the arm gets wrong. "
        "B arms run in three correction orders; their negative flips are shown as mean (range).",
        "",
        f"Judge: `{r.get('judge', '')}`. Baseline verdicts right on all {r.get('pack_cases')} "
        f"cases: {r.get('all_right', '?')}/{r.get('all_verdicts', '?')}. Wrong verdicts on the pool split, the source of corrections: "
        f"{r.get('pool_errors', '?')} of {r.get('pool_verdicts', '?')}."
        + (
            " The stream is empty, so no arm differs from A0 and the hypotheses cannot be tested with this judge."
            if r["corrections"] == 0
            else ""
        ),
        "",
        "| arm | after N corrections | what happens to corrections | verdicts right (95% Wilson CI) | negative flips | positive flips | exact McNemar vs A0 | cases all four right |",
        "|---|---|---|---|---|---|---|---|",
    ]
    lines += [row(k) for k in order if k in arms]

    # hypotheses, as pre-registered; a verdict needs the pre-registered test, not just the direction
    lines += ["", "## Hypotheses (pre-registered)", ""] if r["corrections"] else []
    final = r.get("checkpoints", {}).get("30", 30)

    def neg(key: str) -> float:
        a = arms[key]
        return float(a.get("negative_flips_mean", a["negative_flips"]))

    def short(key: str) -> str:
        return key.split("@")[0]

    prompt = [k for k in ("A1@30", "A2@30", "A3@30") if k in arms]
    if "B2@30" in arms and prompt:
        holm_p = r.get("h1_mcnemar_holm", {})
        fewer = {k: neg("B2@30") < neg(k) for k in prompt}
        sig = {k: fewer[k] and holm_p.get(k, 1.0) < 0.05 for k in prompt}
        h1 = (
            "supported"
            if all(sig.values())
            else "partly supported"
            if any(sig.values())
            else "direction only, not significant"
            if all(fewer.values())
            else "not supported"
        )
        parts = [
            f"{short(k)} {neg(k):.0f} (Holm p={holm_p.get(k, float('nan')):.3f}"
            + ("" if sig[k] else ", not significant")
            + ")"
            for k in prompt
        ]
        lines.append(
            f"- **H1** (B2 has fewer negative flips than each prompt arm, final checkpoint = {final} corrections): "
            f"**{h1}**. B2 {neg('B2@30'):.1f}; " + ", ".join(parts) + "."
        )
        best = max(prompt, key=lambda k: arms[k]["accuracy"])
        b2acc = arms["B2@30"].get("accuracy_mean", arms["B2@30"]["accuracy"])
        margin = b2acc - arms[best]["accuracy"]
        lines.append(
            f"- **H2** (B2 non-inferior to the best prompt arm on accuracy, margin 2 points): "
            f"**{'supported' if margin >= -0.02 else 'not supported'}**. B2 {b2acc:.1%} vs {short(best)} "
            f"{arms[best]['accuracy']:.1%} ({margin * 100:+.1f} points)."
        )
    if "B1@30" in arms and "B2@30" in arms:
        b1n, b2n = neg("B1@30"), neg("B2@30")
        cov = list(r.get("coverage", {}).values())
        blocked_none = bool(cov) and all(c["accepted"] == c["expressible"] for c in cov)
        rules_txt = f"Rules B1 {b1n:.1f} → B2 {b2n:.1f}" + (
            " (no difference: the gate blocked none of the drafted rules)" if blocked_none else ""
        )
        a3g_log = r.get("a3g_log", [])
        prompt_txt = ""
        if "A3@30" in arms and "A3g@30" in arms:
            prompt_txt = f"; guidelines A3 {neg('A3@30'):.0f} → A3g {neg('A3g@30'):.0f}"
            if a3g_log and not any(b["kept"] for b in a3g_log):
                regress = ", ".join(str(b["dev_negative"]) for b in a3g_log)
                prompt_txt += (
                    f" (the dev check rejected every batch, with {regress} right→wrong flips on dev, "
                    "so A3g is the unchanged baseline: no flips and no gains)"
                )
        reduced = [b2n < b1n, "A3g@30" in arms and neg("A3g@30") < neg("A3@30")]
        h3 = "supported" if all(reduced) else "partly supported" if any(reduced) else "not supported"
        lines.append(f"- **H3** (gating reduces negative flips in each family): **{h3}**. {rules_txt}{prompt_txt}.")
    if "P@30" in arms and prompt:
        pn = neg("P@30")
        above = [short(k) for k in prompt if neg(k) > pn]
        h4 = (
            "supported"
            if len(above) == len(prompt)
            else "partly supported"
            if above
            else "not supported"
        )
        lines.append(
            f"- **H4** (prompt edits flip more right verdicts than a placebo): **{h4}**. Placebo {pn:.0f}; "
            + ", ".join(f"{short(k)} {neg(k):.0f}" for k in prompt)
            + "."
        )
    if "A0-rerun" in arms:
        lines.append(
            f"- **Noise floor**: re-running the baseline judge unchanged flips {arms['A0-rerun']['negative_flips']} "
            f"right verdicts and {arms['A0-rerun']['positive_flips']} wrong ones. Prompt arms re-judge every case and "
            "inherit this noise; rule arms read the baseline's recorded answers and do not."
        )
    sec = r.get("secondary", {})
    if sec:
        lines += [
            "",
            f"## Secondary endpoints (final checkpoint, {final} corrections)",
            "",
            "Generalisation: test verdicts wrong under A0 whose item and deciding fact match a corrected one, "
            "and that the arm gets right. Locality: contrast pairs with a right→wrong flip on either side. "
            "Prompt tokens: mean per judge call.",
            "",
            "| arm | per item (threat / escalation / company / recording, of 80) | generalisation | locality violations | prompt tokens |",
            "|---|---|---|---|---|",
        ]
        for key, v in sec.items():
            a = arms[key]
            pi = " / ".join(str(a["per_item"][i]) for i in ITEMS)
            lines.append(
                f"| {key.replace('@30', '')} | {pi} | {v['generalised']}/{v['eligible']} | "
                f"{a['locality_violations']}/{a['contrast_groups']} | {v['prompt_tokens']} |"
            )
    ex = r.get("exploratory", {})
    if ex:
        lines += ["", "## Exploratory (not pre-registered)", ""]
        lines += [f"- {line}" for line in ex.get("notes", [])]
    if r.get("coverage"):
        lines += [
            "",
            "## Rules (B arms)",
            "",
            "| order | corrections | expressible in the frozen library | accepted by the gate | revised after gate feedback |",
            "|---|---|---|---|---|",
        ]
        for order, c in r["coverage"].items():
            lines.append(
                f"| {order} | {c['corrections']} | {c['expressible']} | {c['accepted']} | {c['revised']} |"
            )
    if r.get("a3g_log"):
        lines += [
            "",
            "## A3g batches",
            "",
            "| batch | corrections | right→wrong on dev | wrong→right on dev | kept |",
            "|---|---|---|---|---|",
        ]
        for b in r["a3g_log"]:
            lines.append(
                f"| {b['batch']} | {len(b['corrections'])} | {b['dev_negative']} | {b['dev_positive']} | {'yes' if b['kept'] else 'no'} |"
            )
    lines.append("")
    return "\n".join(lines)


PHASES = {
    "build": build, "base": phase_base, "prompts": phase_prompts, "gated": phase_gated,
    "draft": phase_draft, "rules": phase_rules, "stability": phase_stability, "analyze": phase_analyze,
}  # fmt: skip

if __name__ == "__main__":
    RUNS.mkdir(parents=True, exist_ok=True)
    for phase in sys.argv[1:] or ["analyze"]:
        print(f"== {phase}", flush=True)
        PHASES[phase]()
