"""Bootstrap intervals and permutation p-values (methods fixed in docs/statistics-methodology.md).

Every function draws from a generator seeded with the configured seed, so the same input gives the
same interval and p-value on every run.
"""
import math

import numpy as np
from scipy.stats import fisher_exact, rankdata

from app.statistics.confidence_intervals import wilson
from config.config import get_config


def _generator():
    return np.random.default_rng(get_config().SEED)


def resample_indices(n):
    """One row of n resampled unit indices per bootstrap resample."""
    return _generator().integers(0, n, size=(get_config().BOOTSTRAP_RESAMPLES, n))


def percentile_interval(values):
    """Percentile interval at the configured confidence level, ignoring undefined resamples."""
    values = np.asarray(values, dtype=float)
    values = values[~np.isnan(values)]
    if len(values) == 0:
        return math.nan, math.nan
    tail = (1 - get_config().CONFIDENCE_LEVEL) / 2
    low, high = np.percentile(values, [100 * tail, 100 * (1 - tail)])
    return float(low), float(high)


def pearson_rows(a, b):
    """Pearson correlation of matching rows of two 2-D arrays (nan where a row is constant)."""
    a = a - a.mean(axis=1, keepdims=True)
    b = b - b.mean(axis=1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        return (a * b).sum(axis=1) / np.sqrt((a * a).sum(axis=1) * (b * b).sum(axis=1))


def spearman(x, y):
    """Spearman rank correlation of two 1-D arrays (nan when either is constant)."""
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    return float(pearson_rows(rankdata(x)[None, :], rankdata(y)[None, :])[0])


def spearman_interval(x, y):
    """Percentile bootstrap interval for the Spearman correlation, resampling whole units."""
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    index = resample_indices(len(x))
    return percentile_interval(pearson_rows(rankdata(x[index], axis=1), rankdata(y[index], axis=1)))


def spearman_permutation_p(x, y):
    """Two-sided permutation p-value for the Spearman correlation."""
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    rank_x = rankdata(x) - (len(x) + 1) / 2
    rank_y = rankdata(y) - (len(y) + 1) / 2
    scale = math.sqrt(float((rank_x ** 2).sum() * (rank_y ** 2).sum()))
    if scale == 0:
        return math.nan
    observed = float(rank_x @ rank_y) / scale
    permutations = get_config().PERMUTATIONS
    shuffled = _generator().permuted(np.tile(rank_y, (permutations, 1)), axis=1)
    statistics = shuffled @ rank_x / scale
    return float((1 + np.sum(np.abs(statistics) >= abs(observed) - 1e-12)) / (permutations + 1))


def mean_interval(values):
    """Percentile bootstrap interval for the mean of one value per unit."""
    values = np.asarray(values, dtype=float)
    return percentile_interval(values[resample_indices(len(values))].mean(axis=1))


def clustered_mean_sd(values, clusters):
    """Mean, SD and their bootstrap intervals, resampling whole clusters (proposals), never single reviews.

    Returns:
        (mean, (low, high), sd, (low, high))
    """
    values = np.asarray(values, dtype=float)
    _, codes = np.unique(np.asarray(clusters), return_inverse=True)
    count = np.bincount(codes).astype(float)
    total = np.bincount(codes, weights=values)
    squares = np.bincount(codes, weights=values ** 2)
    index = resample_indices(len(count))
    n, s, q = count[index].sum(axis=1), total[index].sum(axis=1), squares[index].sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        means = s / n
        sds = np.sqrt(np.clip((q - s * s / n) / (n - 1), 0, None))
    sd = float(values.std(ddof=1)) if len(values) > 1 else math.nan
    return float(values.mean()), percentile_interval(means), sd, percentile_interval(sds)


def cohens_kappa(a, b):
    """Cohen's kappa for two equally long sequences of categories (nan when chance agreement is 1)."""
    a, b = np.asarray(a), np.asarray(b)
    if len(a) == 0:
        return math.nan
    observed = float(np.mean(a == b))
    expected = sum(float(np.mean(a == c)) * float(np.mean(b == c)) for c in np.unique(np.concatenate([a, b])))
    return math.nan if expected >= 1 else (observed - expected) / (1 - expected)


def kappa_interval(a, b):
    """Percentile bootstrap interval for Cohen's kappa, resampling whole pairs."""
    a, b = np.asarray(a), np.asarray(b)
    index = resample_indices(len(a))
    observed = (a[index] == b[index]).mean(axis=1)
    expected = np.zeros(len(index))
    for category in np.unique(np.concatenate([a, b])):
        expected += (a[index] == category).mean(axis=1) * (b[index] == category).mean(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        return percentile_interval(np.where(expected < 1, (observed - expected) / (1 - expected), np.nan))


def newcombe(successes_1, n_1, successes_2, n_2):
    """Newcombe interval for a difference of two proportions, built from two Wilson intervals.

    Returns:
        (difference, low, high), with the difference taken as group 1 minus group 2
    """
    level = get_config().CONFIDENCE_LEVEL
    p_1, p_2 = successes_1 / n_1, successes_2 / n_2
    low_1, high_1 = wilson(successes_1, n_1, level)
    low_2, high_2 = wilson(successes_2, n_2, level)
    difference = p_1 - p_2
    low = difference - math.sqrt((p_1 - low_1) ** 2 + (high_2 - p_2) ** 2)
    high = difference + math.sqrt((high_1 - p_1) ** 2 + (p_2 - low_2) ** 2)
    return difference, low, high


def fisher_p(successes_1, n_1, successes_2, n_2):
    """Two-sided Fisher exact p-value for a 2 x 2 table of successes and failures."""
    return float(fisher_exact([[successes_1, n_1 - successes_1], [successes_2, n_2 - successes_2]]).pvalue)
