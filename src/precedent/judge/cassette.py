"""Record and replay judge outputs.

A live LLM judge is slow, costs money and is not deterministic. A cassette
stores its outputs keyed by case hash, so the gate, the demo and CI can replay
a real model's judgements exactly, offline.
"""

from __future__ import annotations

from pathlib import Path

from precedent.judge import Judge
from precedent.models import Case, JudgeOutput


class MissingJudgement(KeyError):
    pass


class Cassette:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def load(self) -> dict[str, JudgeOutput]:
        if not self.path.is_file():
            return {}
        outputs: dict[str, JudgeOutput] = {}
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                out = JudgeOutput.model_validate_json(line)
                outputs[out.case_hash] = out
        return outputs

    def append(self, output: JudgeOutput) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(output.model_dump_json() + "\n")


class ReplayJudge:
    """Serves recorded outputs; refuses cases it has no recording for."""

    def __init__(self, path: Path | str) -> None:
        self.cassette = Cassette(path)
        self._outputs = self.cassette.load()
        ids = {o.judge_id for o in self._outputs.values()}
        if len(ids) > 1:
            raise ValueError(f"cassette {path} mixes judges: {sorted(ids)}")
        self._judge_id = f"replay:{next(iter(ids))}" if ids else "replay:empty"

    @property
    def judge_id(self) -> str:
        return self._judge_id

    def judge(self, case: Case) -> JudgeOutput:
        try:
            out = self._outputs[case.hash]
        except KeyError as exc:
            raise MissingJudgement(f"no recorded judgement for {case.id}") from exc
        return out.model_copy(update={"case_id": case.id})


class RecordingJudge:
    """Wraps a judge; reuses recorded outputs and records new ones."""

    def __init__(self, inner: Judge, path: Path | str) -> None:
        self.inner = inner
        self.cassette = Cassette(path)
        self._outputs = {
            h: o for h, o in self.cassette.load().items() if o.judge_id == self.inner.judge_id
        }

    @property
    def judge_id(self) -> str:
        return self.inner.judge_id

    def judge(self, case: Case) -> JudgeOutput:
        hit = self._outputs.get(case.hash)
        if hit is not None:
            return hit.model_copy(update={"case_id": case.id})
        out = self.inner.judge(case)
        self.cassette.append(out)
        self._outputs[case.hash] = out
        return out
