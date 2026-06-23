from __future__ import annotations

import math
import random
from collections.abc import Iterable
from statistics import median
from typing import Any


def paired_metric_test(
    treatment: Iterable[float],
    baseline: Iterable[float],
    *,
    seed: int = 1337,
    bootstrap_samples: int = 1000,
) -> dict[str, Any]:
    treatment_values = list(treatment)
    baseline_values = list(baseline)
    pairs = list(zip(treatment_values, baseline_values))
    if not pairs:
        return {
            "test": "paired_sign_test_with_bootstrap_ci",
            "query_count": 0,
            "mean_delta": 0.0,
            "median_delta": 0.0,
            "ci95_low": 0.0,
            "ci95_high": 0.0,
            "p_value": 1.0,
            "wins": 0,
            "losses": 0,
            "ties": 0,
        }

    deltas = [left - right for left, right in pairs]
    wins = sum(1 for delta in deltas if delta > 1e-12)
    losses = sum(1 for delta in deltas if delta < -1e-12)
    ties = len(deltas) - wins - losses
    ci_low, ci_high = bootstrap_ci(deltas, seed=seed, samples=bootstrap_samples)

    return {
        "test": "paired_sign_test_with_bootstrap_ci",
        "query_count": len(deltas),
        "mean_delta": _round(mean(deltas)),
        "median_delta": _round(median(deltas)),
        "ci95_low": _round(ci_low),
        "ci95_high": _round(ci_high),
        "p_value": _round(sign_test_p_value(wins, losses), digits=6),
        "wins": wins,
        "losses": losses,
        "ties": ties,
    }


def bootstrap_ci(
    values: list[float],
    *,
    seed: int = 1337,
    samples: int = 1000,
    confidence: float = 0.95,
) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    if len(values) == 1 or samples <= 0:
        value = mean(values)
        return value, value

    rng = random.Random(seed)
    estimates: list[float] = []
    count = len(values)
    for _ in range(samples):
        sample = [values[rng.randrange(count)] for _ in range(count)]
        estimates.append(mean(sample))
    estimates.sort()

    lower_q = (1.0 - confidence) / 2.0
    upper_q = 1.0 - lower_q
    lower = estimates[min(max(math.floor(lower_q * samples), 0), samples - 1)]
    upper = estimates[min(max(math.ceil(upper_q * samples) - 1, 0), samples - 1)]
    return lower, upper


def sign_test_p_value(wins: int, losses: int) -> float:
    trials = wins + losses
    if trials == 0:
        return 1.0

    lower_tail = min(wins, losses)
    probability = sum(math.comb(trials, index) for index in range(lower_tail + 1)) / (2**trials)
    return min(1.0, 2.0 * probability)


def mean(values: Iterable[float]) -> float:
    items = list(values)
    return sum(items) / len(items) if items else 0.0


def _round(value: float, digits: int = 4) -> float:
    return round(float(value), digits)
