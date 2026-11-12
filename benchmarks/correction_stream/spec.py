"""Specification-first synthetic data for the correction-stream benchmark.

Every case starts as a *fact vector* sampled from a factorial design. Gold
labels are a pure function of the facts and the written policy (`policy/`),
so a label never depends on how a model happened to phrase the call. A
language model then writes a transcript that realises exactly those facts;
a second model family checks the facts back (see verify.py).

Run: uv run python benchmarks/correction_stream/spec.py   → specs.jsonl
"""

from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass, replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEED = 20261112

ESCALATION = [
    "transfer",  # live transfer to a supervisor/manager/team lead
    "callback_supervisor",  # a supervisor or manager will call back
    "callback_teamlead",  # a team lead will call back
    "callback_specialist",  # a "specialist/hardship team" will call back: NOT an escalation
    "refused",  # the customer asks for a supervisor, the agent declines
    "none",  # nothing offered, nothing asked
]
THREAT = [
    "arrest",  # explicit arrest / jail / police / prosecution
    "euphemistic",  # sheriff at the door, "the authorities", seizure, without the usual words
    "vague",  # "serious consequences"
    "lawful",  # an accurate lawful next step: credit reporting, a civil claim
    "negated",  # "nobody is going to arrest you"
    "none",
]
REPAYMENT = ["offered", "none"]
RECORDING = ["disclosed", "unclear", "none"]
COMPANY = ["full", "name_only"]
NOISE = ["clean", "asr"]
SECTORS = [
    "debt collection agency",
    "consumer lender",
    "credit card issuer",
    "insurer",
    "utility billing",
]

ITEMS = ["threat_language", "escalation_offered", "company_disclosure", "recording_disclosure"]


@dataclass(frozen=True)
class Facts:
    escalation: str
    threat: str
    repayment: str
    recording: str
    company: str
    noise: str
    sector: str
    out_of_domain: bool = False


def gold(f: Facts) -> dict[str, str]:
    """The written policy, as code. See policy/*.md for the same rules in prose."""
    if f.out_of_domain:
        return {item: "abstain" for item in ITEMS}
    threat = {"arrest": "fail", "euphemistic": "fail", "vague": "needs_review"}.get(
        f.threat, "pass"
    )
    escalation = (
        "pass"
        if f.escalation in ("transfer", "callback_supervisor", "callback_teamlead")
        else "needs_review"
    )
    company = "pass" if f.company == "full" else "needs_review"
    recording = {"disclosed": "pass", "unclear": "needs_review"}.get(f.recording, "not_applicable")
    return {
        "threat_language": threat,
        "escalation_offered": escalation,
        "company_disclosure": company,
        "recording_disclosure": recording,
    }


# The single factor each contrast pair varies, and the two values it contrasts.
CONTRASTS = [
    ("escalation", "callback_teamlead", "callback_specialist"),
    ("escalation", "callback_supervisor", "callback_specialist"),
    ("escalation", "transfer", "refused"),
    ("threat", "euphemistic", "lawful"),
    ("threat", "arrest", "negated"),
    ("threat", "vague", "lawful"),
    ("recording", "disclosed", "unclear"),
    ("company", "full", "name_only"),
]


def _random_facts(rng: random.Random) -> Facts:
    return Facts(
        escalation=rng.choice(ESCALATION),
        threat=rng.choice(THREAT),
        repayment=rng.choice(REPAYMENT),
        recording=rng.choices(RECORDING, weights=[2, 1, 3])[0],
        company=rng.choices(COMPANY, weights=[4, 1])[0],
        noise=rng.choices(NOISE, weights=[3, 1])[0],
        sector=rng.choice(SECTORS),
    )


def build(
    n: int = 240, contrast_pairs: int = 36, out_of_domain: int = 12
) -> list[dict[str, object]]:
    rng = random.Random(SEED)
    rows: list[dict[str, object]] = []
    groups: list[list[Facts]] = []
    for i in range(contrast_pairs):
        factor, a, b = CONTRASTS[i % len(CONTRASTS)]
        base = _random_facts(rng)
        groups.append([replace(base, **{factor: a}), replace(base, **{factor: b})])
    singles = n - 2 * contrast_pairs - out_of_domain
    # cover every escalation and threat level evenly in the singles
    for i in range(singles):
        base = _random_facts(rng)
        base = replace(
            base, escalation=ESCALATION[i % len(ESCALATION)], threat=THREAT[(i // 6) % len(THREAT)]
        )
        groups.append([base])
    for _ in range(out_of_domain):
        groups.append([replace(_random_facts(rng), out_of_domain=True)])

    # split whole groups so a contrast pair never straddles pool / dev / test
    rng.shuffle(groups)
    splits = ["pool", "dev", "test"]
    sizes = {s: 0 for s in splits}
    target = n // 3
    k = 0
    for gi, group in enumerate(groups):
        split = min(
            (s for s in splits if sizes[s] + len(group) <= target),
            key=lambda s: sizes[s],
            default="test",
        )
        sizes[split] += len(group)
        for f in group:
            k += 1
            rows.append(
                {
                    "id": f"B-{k:03d}",
                    "group": f"G-{gi:03d}",
                    "split": split,
                    "contrast": len(group) == 2,
                    "facts": asdict(f),
                    "golden": gold(f),
                }
            )
    return rows


def main() -> int:
    rows = build()
    out = HERE / "specs.jsonl"
    out.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    from collections import Counter

    print(
        len(rows), Counter(r["split"] for r in rows), "contrast:", sum(r["contrast"] for r in rows)
    )
    print("escalation:", Counter(r["facts"]["escalation"] for r in rows))
    print("threat:", Counter(r["facts"]["threat"] for r in rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
