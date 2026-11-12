"""Judges turn a case into item labels and predicate answers."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from precedent.models import Case, JudgeOutput


class Judge(Protocol):
    @property
    def judge_id(self) -> str: ...

    def judge(self, case: Case) -> JudgeOutput: ...


def judge_all(judge: Judge, cases: Iterable[Case]) -> dict[str, JudgeOutput]:
    return {case.id: judge.judge(case) for case in cases}
