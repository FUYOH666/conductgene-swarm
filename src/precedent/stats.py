"""Agreement statistics without numpy: exact enough for gate decisions."""

from __future__ import annotations

import random
from collections import Counter
from collections.abc import Sequence


def agreement(pairs: Sequence[tuple[str, str]]) -> float:
    if not pairs:
        return float("nan")
    return sum(1 for a, b in pairs if a == b) / len(pairs)


def cohen_kappa(pairs: Sequence[tuple[str, str]]) -> float | None:
    """Cohen's kappa for (predicted, reference) pairs; None when undefined."""
    n = len(pairs)
    if n == 0:
        return None
    observed = agreement(pairs)
    pred = Counter(a for a, _ in pairs)
    ref = Counter(b for _, b in pairs)
    expected = sum(pred[k] * ref.get(k, 0) for k in pred) / (n * n)
    if expected >= 1.0:
        return None
    return (observed - expected) / (1.0 - expected)


def paired_bootstrap_delta(
    before: Sequence[bool],
    after: Sequence[bool],
    *,
    resamples: int = 2000,
    seed: int = 0,
    level: float = 0.95,
) -> tuple[float, tuple[float, float]]:
    """Mean of ``after - before`` correctness with a percentile bootstrap CI."""
    if len(before) != len(after):
        raise ValueError("paired samples must have equal length")
    n = len(before)
    if n == 0:
        return 0.0, (0.0, 0.0)
    diffs = [int(a) - int(b) for b, a in zip(before, after, strict=True)]
    delta = sum(diffs) / n
    rng = random.Random(seed)
    stats = sorted(sum(diffs[rng.randrange(n)] for _ in range(n)) / n for _ in range(resamples))
    lo_idx = int((1 - level) / 2 * resamples)
    hi_idx = min(resamples - 1, int((1 + level) / 2 * resamples))
    return delta, (stats[lo_idx], stats[hi_idx])
