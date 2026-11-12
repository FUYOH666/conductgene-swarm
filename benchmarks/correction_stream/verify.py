"""Check each transcript against its fact vector with a second model family (Qwen).

The verifier reads only the transcript and the fact definitions and must pick
one value per factor. Disagreements with the specification go to
``mismatches.jsonl`` for adjudication (``adjudication.jsonl``).

    uv run python benchmarks/correction_stream/verify.py
"""

from __future__ import annotations

import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

from precedent.judge.llm import extract_json

HERE = Path(__file__).resolve().parent
BASE_URL = os.environ.get("PRECEDENT_LLM_BASE_URL", "https://openrouter.ai/api/v1")
MODEL = os.environ.get("VERIFIER_MODEL", "qwen/qwen3.8-27b")
API_KEY = os.environ.get("PRECEDENT_LLM_API_KEY", "")
WORKERS = int(os.environ.get("BENCH_WORKERS", "8"))

FACTORS = {
    "out_of_domain": ["false", "true"],
    "company": ["full", "name_only"],
    "escalation": [
        "transfer",
        "callback_supervisor",
        "callback_teamlead",
        "callback_specialist",
        "refused",
        "none",
    ],
    "threat": ["arrest", "euphemistic", "vague", "lawful", "negated", "none"],
    "repayment": ["offered", "none"],
    "recording": ["disclosed", "unclear", "none"],
}

DEFINITIONS = """Classify the phone-call transcript. For each factor pick exactly one value.
- out_of_domain: true if the call is not about a debt, bill, premium or payment owed.
- company: full = the agent states the company name AND the purpose of the call; name_only = the name but never the purpose.
- escalation: transfer = agent offers a live transfer to a supervisor/manager/team lead; callback_supervisor = a supervisor or manager will call back; callback_teamlead = the agent's team lead will call back; callback_specialist = some other team (specialist/hardship/payments) will call back; refused = customer asks for a supervisor/manager and the agent declines; none = nothing of the kind.
- threat: arrest = explicit arrest/jail/police/prosecution threat; euphemistic = threat of force without those words (sheriff, authorities, seizing property); vague = unspecified serious consequences; lawful = an accurate lawful next step (credit reporting, civil claim) without threatening force; negated = arrest/police/jail mentioned only to rule it out; none = nothing of the kind.
- repayment: offered = the agent offers a repayment/payment plan or paying over time; none otherwise.
- recording: disclosed = early, clear statement that the call is or may be recorded; unclear = recording or keeping notes mentioned only vaguely or late; none = never mentioned.
If out_of_domain is true, still pick values for the others (usually none / name_only).
Reply with JSON only: {"out_of_domain": "...", "company": "...", "escalation": "...", "threat": "...", "repayment": "...", "recording": "..."}"""


def classify(client: httpx.Client, text: str) -> dict[str, str]:
    body = {
        "model": MODEL,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": DEFINITIONS},
            {"role": "user", "content": f"Transcript:\n<<<\n{text}\n>>>"},
        ],
    }
    for _ in range(3):
        resp = client.post(f"{BASE_URL}/chat/completions", json=body)
        resp.raise_for_status()
        try:
            data = extract_json(resp.json()["choices"][0]["message"]["content"] or "")
            return {k: str(data.get(k, "")).lower() for k in FACTORS}
        except ValueError:
            continue
    return {k: "" for k in FACTORS}


def main() -> int:
    specs = {
        json.loads(line)["id"]: json.loads(line)
        for line in (HERE / "specs.jsonl").read_text().splitlines()
    }
    texts = [json.loads(line) for line in (HERE / "transcripts.jsonl").read_text().splitlines()]
    out = HERE / "verification.jsonl"
    done = (
        {json.loads(line)["id"] for line in out.read_text().splitlines()} if out.exists() else set()
    )
    todo = [row for row in texts if row["id"] not in done]
    lock = threading.Lock()
    headers = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}
    with httpx.Client(timeout=300, headers=headers) as client, out.open("a") as fh:

        def one(row: dict) -> None:
            got = classify(client, row["text"])
            facts = specs[row["id"]]["facts"]
            want = {k: str(facts[k]).lower() for k in FACTORS}
            diff = {k: {"spec": want[k], "verifier": got[k]} for k in FACTORS if got[k] != want[k]}
            with lock:
                fh.write(
                    json.dumps({"id": row["id"], "verifier": MODEL, "got": got, "mismatch": diff})
                    + "\n"
                )
                fh.flush()

        with ThreadPoolExecutor(WORKERS) as pool:
            list(pool.map(one, todo))
    rows = [json.loads(line) for line in out.read_text().splitlines()]
    bad = [r for r in rows if r["mismatch"]]
    (HERE / "mismatches.jsonl").write_text("".join(json.dumps(r) + "\n" for r in bad))
    print(f"verified {len(rows)}, mismatches {len(bad)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
