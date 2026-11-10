import math

import numpy as np
import pytest
from scipy import stats

from app.statistics.association import adjust_family, proportion_association, rank_association
from app.statistics.resampling import (clustered_mean_sd, cohens_kappa, kappa_interval, newcombe, spearman,
                                       spearman_interval, spearman_permutation_p)


def test_spearman_matches_scipy_with_ties():
    x = np.array([1, 2, 2, 3, 5, 5, 6, 8])
    y = np.array([0, 0, 1, 0, 1, 1, 1, 1])
    assert spearman(x, y) == pytest.approx(stats.spearmanr(x, y).statistic)


def test_newcombe_interval_against_the_published_example():
    # Newcombe (1998), 56 of 70 against 48 of 80: difference 0.20, interval 0.0524 to 0.3339
    difference, low, high = newcombe(56, 70, 48, 80)
    assert difference == pytest.approx(0.20)
    assert (low, high) == pytest.approx((0.0524, 0.3339), abs=1e-3)


def test_interval_and_p_value_are_the_same_on_every_run():
    rng = np.random.default_rng(7)
    x = rng.normal(size=60)
    y = (x + rng.normal(size=60) > 0).astype(float)
    assert spearman_interval(x, y) == spearman_interval(x, y)
    assert spearman_permutation_p(x, y) == spearman_permutation_p(x, y)


def test_interval_covers_the_estimate_and_a_strong_relation_has_a_small_p():
    rng = np.random.default_rng(3)
    x = rng.normal(size=80)
    y = (x > 0).astype(float)
    low, high = spearman_interval(x, y)
    assert low < spearman(x, y) < high
    assert spearman_permutation_p(x, y) < 0.001
    assert spearman_permutation_p(x, rng.integers(0, 2, size=80).astype(float)) > 0.05


def test_clustered_bootstrap_keeps_the_point_estimates():
    values = [3, 4, 5, 2, 5, 4, 1, 3]
    mean, mean_ci, sd, sd_ci = clustered_mean_sd(values, ["a", "a", "b", "b", "c", "c", "d", "d"])
    assert mean == pytest.approx(np.mean(values)) and sd == pytest.approx(np.std(values, ddof=1))
    assert mean_ci[0] <= mean <= mean_ci[1] and sd_ci[0] < sd_ci[1]


def test_kappa_values_and_interval():
    assert cohens_kappa(["a", "b", "a", "b"], ["a", "b", "a", "b"]) == 1.0
    assert cohens_kappa(["a", "a", "b", "b"], ["a", "b", "a", "b"]) == 0.0
    assert math.isnan(cohens_kappa(["a", "a"], ["a", "a"]))  # chance agreement is already 1
    low, high = kappa_interval(np.array(list("aabbabab" * 5)), np.array(list("aabbabba" * 5)))
    assert -1 <= low < high <= 1


def test_a_test_with_a_tiny_outcome_group_is_not_run():
    row = rank_association(np.arange(20.0), np.array([1.0] * 17 + [0.0] * 3))
    assert math.isnan(row["p_raw"]) and row["note"].startswith("not testable")
    row = proportion_association(np.array([1.0] * 10 + [0.0] * 2), np.array([1.0, 0.0] * 6))
    assert row["note"].startswith("not testable")


def test_too_few_completed_grants_gives_estimates_without_p_values():
    row = rank_association(np.arange(20.0), np.array([0.0, 1.0] * 10), inferential=False)
    assert not math.isnan(row["estimate"]) and math.isnan(row["p_raw"])
    assert row["note"].startswith("descriptive only")


def test_correction_is_within_the_family_and_keeps_the_raw_values():
    # Failure mode in the brief: many tests, and the one significant raw p-value reported alone
    rows = [{"p_raw": p} for p in (0.01, 0.04, 0.03, 0.005, math.nan)]
    adjust_family(rows)
    assert [row["p_raw"] for row in rows[:4]] == [0.01, 0.04, 0.03, 0.005]
    assert np.allclose([row["p_holm"] for row in rows[:4]], [0.03, 0.06, 0.06, 0.02])
    assert [row["significant_after_holm"] for row in rows] == [True, False, False, True, False]
    assert all(row["tests_in_family"] == 4 for row in rows)
