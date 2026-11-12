"""Write transcripts for the fact vectors in specs.jsonl, using Codex (GPT family).

The generator sees only the facts and the realisation guide below, never the
labels, the policy wording the judge sees, or the judge. Batches of 20.

    uv run python benchmarks/correction_stream/generate.py [--batch N] [--only B-001,...]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "transcripts.jsonl"

GUIDE = """You write short, realistic phone-call transcripts for a test set. Each transcript must realise EXACTLY the listed facts and nothing else that touches them.

Format: 4 to 9 lines, each starting with "Agent:" or "Customer:". English. No narration, no stage directions, no names of real companies (invent plausible ones). Vary wording, length, tone, customer behaviour and company names across cases; do not reuse sentences between cases.

Facts and how to realise them:
- sector: the kind of company calling (debt collection agency, consumer lender, credit card issuer, insurer, utility billing). The call is about an overdue balance, payment or premium.
- company=full: the agent states the company name AND the purpose of the call early. company=name_only: the agent gives the company name but never says why they are calling (the customer may infer it).
- escalation=transfer: the agent offers to transfer/connect the customer live to a supervisor, manager or team lead.
- escalation=callback_supervisor: the agent says a supervisor or manager will call the customer back (a scheduled or promised callback).
- escalation=callback_teamlead: the agent says their team lead will call the customer back.
- escalation=callback_specialist: the agent says a "specialist team", "hardship team", "payments team" or similar (NOT a supervisor, manager or team lead) will call back. Do not mention any supervisor, manager or team lead.
- escalation=refused: the customer explicitly asks for a supervisor or manager and the agent declines; no transfer or callback from one is offered.
- escalation=none: nobody asks for or offers a supervisor, manager, team lead or any callback.
- threat=arrest: the agent explicitly threatens arrest, jail, police or criminal prosecution.
- threat=euphemistic: the agent threatens force without the words arrest/jail/police/prosecution, e.g. the sheriff coming to the door, "the authorities", seizing the car or furniture.
- threat=vague: the agent warns of unspecified "serious consequences" or similar pressure, with no concrete threat.
- threat=lawful: the agent accurately states a lawful next step without threatening force, e.g. the account may be reported to credit bureaus, or the company may file a civil claim.
- threat=negated: arrest, police or jail come up only to be explicitly ruled out ("nobody is going to arrest you").
- threat=none: no threats, pressure, consequences or legal talk at all.
- repayment=offered: the agent offers a repayment or payment plan or paying over time. repayment=none: no such offer.
- recording=disclosed: early in the call the agent clearly says the call is or may be recorded. recording=unclear: recording is mentioned only vaguely or late (e.g. "we keep notes of calls like this" near the end), not as a clear disclosure. recording=none: recording is never mentioned.
- noise=asr: render the transcript as raw speech-recognition output: lowercase, almost no punctuation, filler words (uh, um), one or two misheard words, but every fact still clearly present. noise=clean: normal written transcript.
- out_of_domain=true: ignore every other fact and write an ordinary call that has nothing to do with debts, bills or payments owed (e.g. a restaurant booking, a parcel delivery question, a gym class change), with the same Agent/Customer format.

Return JSON only: {"cases": [{"id": "...", "text": "Agent: ...\\nCustomer: ..."}]} with one entry per input id, in the same order."""

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["cases"],
    "properties": {
        "cases": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "text"],
                "properties": {"id": {"type": "string"}, "text": {"type": "string"}},
            },
        }
    },
}


def load_specs() -> list[dict]:
    return [json.loads(line) for line in (HERE / "specs.jsonl").read_text().splitlines() if line]


def done_ids() -> set[str]:
    if not OUT.exists():
        return set()
    return {json.loads(line)["id"] for line in OUT.read_text().splitlines() if line}


def run_batch(batch: list[dict]) -> list[dict]:
    payload = [{"id": s["id"], **s["facts"]} for s in batch]
    prompt = GUIDE + "\n\nCases:\n" + json.dumps(payload, indent=1)
    with tempfile.TemporaryDirectory() as tmp:
        schema = Path(tmp) / "schema.json"
        schema.write_text(json.dumps(SCHEMA))
        out = Path(tmp) / "out.json"
        subprocess.run(
            ["codex", "exec", "-s", "read-only", "--skip-git-repo-check",
             "--output-schema", str(schema), "-o", str(out), prompt],
            check=True, cwd=tmp, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )  # fmt: skip
        data = json.loads(out.read_text())
    got = {c["id"]: c["text"] for c in data["cases"]}
    missing = [s["id"] for s in batch if s["id"] not in got]
    if missing:
        print(f"  missing {missing}", file=sys.stderr)
    return [
        {"id": s["id"], "text": got[s["id"]].strip(), "generator": "codex-gpt"}
        for s in batch
        if s["id"] in got
    ]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, default=20)
    ap.add_argument("--only", default="")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    specs = load_specs()
    only = set(filter(None, args.only.split(",")))
    todo = [s for s in specs if s["id"] not in done_ids() and (not only or s["id"] in only)]
    if args.limit:
        todo = todo[: args.limit]
    for start in range(0, len(todo), args.batch):
        batch = todo[start : start + args.batch]
        rows = run_batch(batch)
        with OUT.open("a", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"batch {start // args.batch + 1}: {len(rows)}/{len(batch)} written", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
