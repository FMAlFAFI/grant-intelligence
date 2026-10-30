"""Confidence intervals used across the analyses (methods in docs/statistics-methodology.md)."""
import math
from statistics import NormalDist


def wilson(successes, n, level=0.95):
    """Wilson score interval for a proportion, as (low, high). (nan, nan) when n is 0."""
    if n == 0:
        return math.nan, math.nan
    z = NormalDist().inv_cdf(1 - (1 - level) / 2)
    p = successes / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0.0, centre - half), min(1.0, centre + half)


def rate(successes, n, level=0.95):
    """'7 of 24 (29%, 95% CI 15-49%)', the way every proportion is reported."""
    if n == 0:
        return "0 of 0 (no data)"
    low, high = wilson(successes, n, level)
    return f"{successes} of {n} ({successes / n:.0%}, {level:.0%} CI {low:.0%}-{high:.0%})"
