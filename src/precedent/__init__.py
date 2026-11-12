"""Precedent: pull requests for AI judgment.

A human correction of an AI judge becomes a scoped, versioned rule. The rule
has to pass a blocking gate before it can change a single verdict, needs a
second person to approve it, and can be reverted. Every step is written to a
hash-chained event log.

The public API is what this module exports; everything else is internal.
"""

from importlib.metadata import PackageNotFoundError, version

from precedent.engine import Decision, decide
from precedent.events import EventStore, VerifyResult
from precedent.gate import run_gate
from precedent.judge import Judge, judge_all
from precedent.judge.factory import make_judge
from precedent.models import (
    Case,
    Condition,
    Correction,
    GateReport,
    JudgeOutput,
    Rule,
    Tally,
)
from precedent.pack import Pack, load_pack, load_rule
from precedent.registry import Registry, RegistryError

try:
    __version__ = version("precedent-llm")
except PackageNotFoundError:  # pragma: no cover - running from a source tree
    __version__ = "0+unknown"

__all__ = [
    "Case",
    "Condition",
    "Correction",
    "Decision",
    "EventStore",
    "GateReport",
    "Judge",
    "JudgeOutput",
    "Pack",
    "Registry",
    "RegistryError",
    "Rule",
    "Tally",
    "VerifyResult",
    "__version__",
    "decide",
    "judge_all",
    "load_pack",
    "load_rule",
    "make_judge",
    "run_gate",
]
