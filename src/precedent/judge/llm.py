"""Structured LLM judge over any OpenAI-compatible endpoint.

One call per case returns a label per rubric item and an answer per predicate.
Every quote is checked against the case text (and, for predicates about one
speaker, against that speaker's lines) and every label against the pack. A
claim whose quote fails is downgraded (label → review label, predicate →
``unknown``); unknown clause ids are dropped. Each such event is kept in
``notes``. A verified quote proves the words exist, not that they support the
claim.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

import httpx

from precedent.hashing import sha256_hex
from precedent.models import Case, ItemVerdict, JudgeOutput, PredicateAnswer, Span
from precedent.pack import Pack
from precedent.spans import find_quote

PROMPT_VERSION = "judge-v1"
MAX_ATTEMPTS = 3

_SYSTEM = """You are a careful reviewer. You answer a fixed rubric about one case.

## Rubric items (pick exactly one label per item)
{items}

## Predicates (answer each literally: "yes", "no" or "unknown")
{predicates}

## Policy clauses (cite by id)
{clauses}

## Rules
1. Every "quote" must be copied verbatim from the case text. Never paraphrase inside "quote".
2. Labels {evidence_required} need a quote from the case that supports them. If you cannot quote, use "{review_label}".
3. A predicate answered "yes" needs a quote. Answer "no" when the case clearly lacks it, "unknown" when you cannot tell.
4. Judge the items and the predicates independently.
5. If this case is not the kind of case the rubric is about, set "abstain" to true.

Return only one JSON object, no prose, no markdown:
{{"abstain": false, "abstain_reason": "", "items": {{"<item id>": {{"label": "<label>", "quote": "<verbatim>", "clause_ids": ["<id>"], "rationale": "<one sentence>"}}}}, "predicates": {{"<predicate id>": {{"value": "yes|no|unknown", "quote": "<verbatim or empty>"}}}}}}"""


class JudgeError(RuntimeError):
    pass


def _spoken_by(text: str, span: Span, speaker: str) -> bool:
    """True if the quoted span lies in a line that starts with ``speaker:``."""
    line_start = text.rfind("\n", 0, span.start) + 1
    line_end = text.find("\n", span.start)
    line_end = len(text) if line_end < 0 else line_end
    if span.end > line_end:
        return False
    return text[line_start:line_end].lstrip().lower().startswith(speaker.lower() + ":")


def build_system_prompt(pack: Pack) -> str:
    items = "\n".join(
        f"- {item.id}: {item.question}\n"
        + "\n".join(f"    - {label.id}: {label.meaning}" for label in item.labels)
        for item in pack.items
    )
    predicates = "\n".join(f"- {p.id}: {p.question}" for p in pack.predicates)
    clauses = "\n".join(f"[{c.id}] ({c.doc} / {c.section}) {c.text}" for c in pack.clauses)
    evidence = sorted({label for item in pack.items for label in item.evidence_required})
    return _SYSTEM.format(
        items=items,
        predicates=predicates,
        clauses=clauses or "(none)",
        evidence_required=", ".join(f'"{e}"' for e in evidence) or "(none)",
        review_label=pack.review_label,
    )


def extract_json(raw: str) -> dict[str, Any]:
    """Parse the first JSON object in a reply (tolerates think-blocks and fences)."""
    text = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object in reply")
    data = json.loads(text[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("reply is not a JSON object")
    return data


class LLMJudge:
    def __init__(
        self,
        pack: Pack,
        *,
        base_url: str,
        model: str,
        api_key: str | None = None,
        timeout: float = 180.0,
        temperature: float = 0.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.pack = pack
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.system_prompt = build_system_prompt(pack)
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._client = client or httpx.Client(timeout=timeout, headers=headers)
        self._json_mode = True
        self.prompt_hash = sha256_hex(
            f"{PROMPT_VERSION}|{self.system_prompt}|{pack.definition_hash()}|{temperature}"
        )

    @property
    def judge_id(self) -> str:
        return f"llm:{self.model}:{self.prompt_hash[:10]}"

    def messages(self, case: Case) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Case {case.id}:\n<<<\n{case.text}\n>>>"},
        ]

    def _complete(self, messages: list[dict[str, str]]) -> tuple[str, dict[str, Any]]:
        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }
        if self._json_mode:
            body["response_format"] = {"type": "json_object"}
        resp = self._client.post(f"{self.base_url}/chat/completions", json=body)
        if resp.status_code == 400 and self._json_mode:
            self._json_mode = False
            return self._complete(messages)
        resp.raise_for_status()
        data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            raise JudgeError("empty choices")
        return str(choices[0]["message"].get("content") or ""), dict(data.get("usage") or {})

    def judge(self, case: Case) -> JudgeOutput:
        messages = self.messages(case)
        last_error = ""
        started = time.perf_counter()
        for attempt in range(MAX_ATTEMPTS):
            raw, usage = self._complete(messages)
            try:
                data = extract_json(raw)
            except ValueError as exc:
                last_error = str(exc)
                messages = [
                    *self.messages(case),
                    {"role": "assistant", "content": raw[:2000]},
                    {
                        "role": "user",
                        "content": f"Invalid: {exc}. Reply with the JSON object only.",
                    },
                ]
                continue
            out = self.parse(case, data)
            out.meta.update(
                {
                    "latency_ms": round((time.perf_counter() - started) * 1000),
                    "attempts": attempt + 1,
                    "usage": usage,
                }
            )
            return out
        raise JudgeError(f"{case.id}: no valid JSON after {MAX_ATTEMPTS} attempts: {last_error}")

    def parse(self, case: Case, data: dict[str, Any]) -> JudgeOutput:
        notes: list[str] = []
        known_clauses = self.pack.clause_ids()
        raw_preds = data.get("predicates") or {}
        predicates: dict[str, PredicateAnswer] = {}
        for pred in self.pack.predicates:
            entry = raw_preds.get(pred.id) or {}
            value = str(entry.get("value", "unknown")).lower().strip()
            if value not in ("yes", "no", "unknown"):
                notes.append(f"predicate {pred.id}: invalid value {value!r}")
                value = "unknown"
            span = find_quote(case.text, entry.get("quote"))
            if span is not None and pred.speaker and not _spoken_by(case.text, span, pred.speaker):
                notes.append(f"predicate {pred.id}: quote is not from {pred.speaker}")
                span = None
            if value == "yes" and span is None:
                notes.append(f"predicate {pred.id}: 'yes' without a verifiable quote")
                value = "unknown"
            predicates[pred.id] = PredicateAnswer(
                predicate_id=pred.id,
                value=value,  # type: ignore[arg-type]
                quote=span if value == "yes" else None,
            )

        if bool(data.get("abstain")):
            return JudgeOutput(
                case_id=case.id,
                case_hash=case.hash,
                judge_id=self.judge_id,
                items={},
                predicates=predicates,
                abstained=True,
                abstain_reason=str(data.get("abstain_reason") or "judge abstained"),
                notes=notes,
            )

        raw_items = data.get("items") or {}
        items: dict[str, ItemVerdict] = {}
        for item in self.pack.items:
            entry = raw_items.get(item.id) or {}
            label = str(entry.get("label", "")).strip()
            if label not in item.label_ids():
                notes.append(f"item {item.id}: invalid label {label!r}")
                label = self.pack.review_label
            span = find_quote(case.text, entry.get("quote"))
            if label in item.evidence_required and span is None:
                notes.append(f"item {item.id}: {label!r} without a verifiable quote")
                label = self.pack.review_label
            cited = [str(c) for c in entry.get("clause_ids") or []]
            unknown = [c for c in cited if c not in known_clauses]
            if unknown:
                notes.append(f"item {item.id}: dropped unknown clause ids {unknown}")
            items[item.id] = ItemVerdict(
                item_id=item.id,
                label=label,
                quote=span,
                clause_ids=[c for c in cited if c in known_clauses],
                rationale=str(entry.get("rationale", ""))[:500],
            )
        return JudgeOutput(
            case_id=case.id,
            case_hash=case.hash,
            judge_id=self.judge_id,
            items=items,
            predicates=predicates,
            notes=notes,
        )
