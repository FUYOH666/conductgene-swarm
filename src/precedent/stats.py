"""Agreement statistics without numpy: exact enough for gate decisions."""

from __future__ import annotations

import math
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


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    """Wilson score interval for k successes out of n (95% by default)."""
    if n == 0:
        return (0.0, 1.0)
    phat = k / n
    denom = 1 + z * z / n
    centre = (phat + z * z / (2 * n)) / denom
    half = z * math.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def mcnemar_exact(fixes: int, breaks: int) -> float:
    """Two-sided exact McNemar p-value on the discordant pairs.

    Only verdicts that changed carry information about whether a rule helps:
    ``fixes`` went wrong → right, ``breaks`` went right → wrong.
    """
    n = fixes + breaks
    if n == 0:
        return 1.0
    k = min(fixes, breaks)
    tail: float = sum(math.comb(n, i) for i in range(k + 1)) / 2**n
    return min(1.0, 2.0 * tail)
