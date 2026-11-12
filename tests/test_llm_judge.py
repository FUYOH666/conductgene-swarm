from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from precedent.judge.cassette import RecordingJudge, ReplayJudge
from precedent.judge.factory import make_judge
from precedent.judge.llm import JudgeError, LLMJudge, build_system_prompt, extract_json
from precedent.pack import Pack

BASE = "http://llm.test/v1"


def _reply(content: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "choices": [{"message": {"content": content}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        },
    )


def _answer(pack: Pack, **overrides: Any) -> dict[str, Any]:
    items = {
        "threat_language": {"label": "pass", "quote": "", "clause_ids": []},
        "escalation_offered": {
            "label": "pass",
            "quote": "my team lead can call you back tomorrow",
            "clause_ids": [pack.clauses[0].id, "made-up-id"],
            "rationale": "callback offered",
        },
        "company_disclosure": {"label": "pass", "quote": "This is ABC Collections"},
        "recording_disclosure": {"label": "not_applicable", "quote": ""},
    }
    preds = {p.id: {"value": "no", "quote": ""} for p in pack.predicates}
    preds["supervisor_contact_offered"] = {"value": "yes", "quote": "team lead can call you back"}
    preds["threat_of_arrest"] = {"value": "yes", "quote": "we will arrest you"}  # not in the text
    data: dict[str, Any] = {"abstain": False, "items": items, "predicates": preds}
    data.update(overrides)
    return data


def test_system_prompt_lists_the_rubric(pack: Pack) -> None:
    prompt = build_system_prompt(pack)
    assert "escalation_offered" in prompt and "supervisor_contact_offered" in prompt
    assert pack.clauses[0].id in prompt


def test_extract_json_tolerates_think_blocks_and_fences() -> None:
    raw = '<think>{"not": "this"}</think>\n```json\n{"a": 1}\n```'
    assert extract_json(raw) == {"a": 1}
    with pytest.raises(ValueError):
        extract_json("no json here")


@respx.mock
def test_parse_verifies_every_claim(pack: Pack) -> None:
    respx.post(f"{BASE}/chat/completions").mock(
        return_value=_reply("Sure:\n" + json.dumps(_answer(pack)))
    )
    judge = LLMJudge(pack, base_url=BASE, model="m")
    out = judge.judge(pack.case("CASE-019"))
    assert out.items["escalation_offered"].label == "pass"
    assert out.items["escalation_offered"].quote is not None
    assert out.items["escalation_offered"].clause_ids == [pack.clauses[0].id]
    assert out.predicates["supervisor_contact_offered"].value == "yes"
    # a "yes" whose quote is not in the transcript is downgraded, not trusted
    assert out.predicates["threat_of_arrest"].value == "unknown"
    assert any("threat_of_arrest" in n for n in out.notes)
    assert any("made-up-id" in n for n in out.notes)
    assert out.meta["usage"]["prompt_tokens"] == 10
    assert judge.judge_id.startswith("llm:m:")


@respx.mock
def test_unquoted_or_invalid_labels_become_review(pack: Pack) -> None:
    data = _answer(pack)
    data["items"]["escalation_offered"]["quote"] = "a sentence that is not in the call"
    data["items"]["threat_language"]["label"] = "catastrophic"
    respx.post(f"{BASE}/chat/completions").mock(return_value=_reply(json.dumps(data)))
    out = LLMJudge(pack, base_url=BASE, model="m").judge(pack.case("CASE-019"))
    assert out.items["escalation_offered"].label == "needs_review"
    assert out.items["threat_language"].label == "needs_review"


@respx.mock
def test_abstain_and_retry_on_bad_json(pack: Pack) -> None:
    route = respx.post(f"{BASE}/chat/completions")
    route.side_effect = [
        _reply("I think this is not a debt call."),
        _reply(json.dumps({"abstain": True, "abstain_reason": "hotel booking", "predicates": {}})),
    ]
    out = LLMJudge(pack, base_url=BASE, model="m").judge(pack.case("CASE-022"))
    assert out.abstained and out.abstain_reason == "hotel booking"
    assert out.meta["attempts"] == 2


@respx.mock
def test_gives_up_after_three_bad_replies(pack: Pack) -> None:
    respx.post(f"{BASE}/chat/completions").mock(return_value=_reply("nope"))
    with pytest.raises(JudgeError):
        LLMJudge(pack, base_url=BASE, model="m").judge(pack.case("CASE-001"))


@respx.mock
def test_falls_back_when_json_mode_is_unsupported(pack: Pack) -> None:
    route = respx.post(f"{BASE}/chat/completions")
    route.side_effect = [
        httpx.Response(400, json={"error": "response_format not supported"}),
        _reply(json.dumps(_answer(pack))),
    ]
    judge = LLMJudge(pack, base_url=BASE, model="m")
    judge.judge(pack.case("CASE-019"))
    sent = json.loads(route.calls[1].request.content)
    assert "response_format" not in sent


@respx.mock
def test_record_then_replay_offline(pack: Pack, tmp_path: Path) -> None:
    route = respx.post(f"{BASE}/chat/completions").mock(
        return_value=_reply(json.dumps(_answer(pack)))
    )
    cassette = tmp_path / "c.jsonl"
    recorder = RecordingJudge(LLMJudge(pack, base_url=BASE, model="m"), cassette)
    case = pack.case("CASE-019")
    first = recorder.judge(case)
    again = recorder.judge(case)
    assert route.call_count == 1 and first == again

    replay = ReplayJudge(cassette)
    assert replay.judge_id == f"replay:{first.judge_id}"
    assert replay.judge(case).items == first.items
    with pytest.raises(KeyError):
        replay.judge(pack.case("CASE-001"))


def test_factory(pack: Pack, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert make_judge(pack, "heuristic").judge_id.startswith("heuristic:")
    monkeypatch.delenv("PRECEDENT_LLM_MODEL", raising=False)
    with pytest.raises(ValueError):
        make_judge(pack, "llm")
    judge = make_judge(pack, "llm:some-model", record_to=tmp_path)
    assert isinstance(judge, RecordingJudge)
    with pytest.raises(ValueError):
        make_judge(pack, "oracle")
