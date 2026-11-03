"""Multiple-comparison corrections specified in docs/statistics-methodology.md."""
import numpy as np


def holm_bonferroni(p_values):
    """Step-down Holm-Bonferroni family-wise error rate (FWER) adjusted p-values."""
    p_array = np.asarray(p_values, dtype=float)
    n = len(p_array)
    if n == 0:
        return np.array([], dtype=float)
    order = np.argsort(p_array)
    adjusted = np.empty(n, dtype=float)
    running_max = 0.0
    for rank, idx in enumerate(order):
        val = min(1.0, p_array[idx] * (n - rank))
        running_max = max(running_max, val)
        adjusted[idx] = running_max
    return adjusted


def benjamini_hochberg(p_values):
    """Benjamini-Hochberg false discovery rate (FDR) adjusted p-values."""
    p_array = np.asarray(p_values, dtype=float)
    n = len(p_array)
    if n == 0:
        return np.array([], dtype=float)
    order = np.argsort(p_array)
    ranked = p_array[order]
    ranks = np.arange(1, n + 1, dtype=float)
    raw_adj = np.minimum(ranked * n / ranks, 1.0)
    monotonic = np.minimum.accumulate(raw_adj[::-1])[::-1]
    adjusted = np.empty(n, dtype=float)
    adjusted[order] = monotonic
    return adjusted
