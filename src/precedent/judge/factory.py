"""Build a judge from a short spec string.

- ``heuristic``           deterministic baseline from the pack (offline)
- ``replay:PATH``         recorded outputs from a cassette (offline)
- ``llm`` / ``llm:MODEL`` OpenAI-compatible endpoint; recorded to a cassette
  when ``record_to`` is given. Endpoint and key come from the environment:
  ``PRECEDENT_LLM_BASE_URL`` (default: LM Studio on localhost),
  ``PRECEDENT_LLM_MODEL``, ``PRECEDENT_LLM_API_KEY``.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from precedent.judge import Judge
from precedent.judge.cassette import RecordingJudge, ReplayJudge
from precedent.judge.heuristic import HeuristicJudge
from precedent.judge.llm import LLMJudge
from precedent.pack import Pack

DEFAULT_BASE_URL = "http://127.0.0.1:1234/v1"


def cassette_name(judge_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", judge_id) + ".jsonl"


def make_judge(pack: Pack, spec: str = "heuristic", *, record_to: Path | None = None) -> Judge:
    if spec == "heuristic":
        return HeuristicJudge(pack)
    if spec.startswith("replay:"):
        path = Path(spec.removeprefix("replay:"))
        if not path.is_absolute() and not path.exists() and pack.judgements_dir():
            candidate = pack.judgements_dir() / path  # type: ignore[operator]
            if candidate.exists():
                path = candidate
        return ReplayJudge(path)
    if spec == "llm" or spec.startswith("llm:"):
        model = spec.removeprefix("llm:") if spec.startswith("llm:") else ""
        model = model or os.environ.get("PRECEDENT_LLM_MODEL", "")
        if not model:
            raise ValueError("set a model: --judge llm:<model> or PRECEDENT_LLM_MODEL")
        judge = LLMJudge(
            pack,
            base_url=os.environ.get("PRECEDENT_LLM_BASE_URL", DEFAULT_BASE_URL),
            model=model,
            api_key=os.environ.get("PRECEDENT_LLM_API_KEY") or None,
        )
        if record_to is not None:
            return RecordingJudge(judge, record_to / cassette_name(judge.judge_id))
        return judge
    raise ValueError(f"unknown judge spec {spec!r}: use heuristic, replay:PATH or llm[:MODEL]")
