"""One predictor against one yes-or-no outcome, as fixed in docs/statistics-methodology.md (6.4 and 7).

Numeric predictors use the Spearman correlation with a bootstrap interval and a permutation p-value.
A two-group predictor uses the difference in proportions with a Newcombe interval and Fisher's exact
test. Corrections are applied within a family of tests and both raw and adjusted p-values are kept.
"""
import math

import numpy as np

from app.statistics.multiple_comparison import benjamini_hochberg, holm_bonferroni
from app.statistics.resampling import fisher_p, newcombe, spearman, spearman_interval, spearman_permutation_p
from config.config import get_config

EMPTY = {"estimate": math.nan, "ci_low": math.nan, "ci_high": math.nan, "p_raw": math.nan}


def _counts(outcome):
    yes = int(np.sum(outcome == 1))
    return yes, int(len(outcome) - yes)


def rank_association(predictor, outcome, inferential=True):
    """Spearman correlation of a numeric predictor with a 0/1 outcome.

    Args:
        predictor, outcome: one value per grant; grants with a missing value in either are left out
        inferential: False reports the estimate and interval only (too few completed grants for p-values)

    Returns:
        dict with n, the size of both outcome groups, estimate, interval, raw p-value and a note
    """
    cfg = get_config()
    predictor, outcome = np.asarray(predictor, dtype=float), np.asarray(outcome, dtype=float)
    keep = ~(np.isnan(predictor) | np.isnan(outcome))
    predictor, outcome = predictor[keep], outcome[keep]
    yes, no = _counts(outcome)
    row = {"measure": "spearman", "n": len(outcome), "outcome_yes": yes, "outcome_no": no, **EMPTY, "note": ""}
    if min(yes, no) < cfg.MIN_GROUP_SIZE:
        return {**row, "note": f"not testable: an outcome group has fewer than {cfg.MIN_GROUP_SIZE} grants"}
    if len(np.unique(predictor)) < 2:
        return {**row, "note": "not testable: the predictor has one value"}
    low, high = spearman_interval(predictor, outcome)
    row.update(estimate=spearman(predictor, outcome), ci_low=low, ci_high=high)
    if inferential:
        row["p_raw"] = spearman_permutation_p(predictor, outcome)
    else:
        row["note"] = f"descriptive only: fewer than {cfg.DESCRIPTIVE_BELOW} completed grants"
    return row


def proportion_association(group, outcome, inferential=True):
    """Difference in the outcome rate between two groups (group 1 minus group 0).

    Returns:
        dict in the same shape as rank_association
    """
    cfg = get_config()
    group, outcome = np.asarray(group, dtype=float), np.asarray(outcome, dtype=float)
    keep = ~(np.isnan(group) | np.isnan(outcome))
    group, outcome = group[keep], outcome[keep]
    yes, no = _counts(outcome)
    n_1, n_0 = int(np.sum(group == 1)), int(np.sum(group == 0))
    row = {"measure": "difference in proportions", "n": len(outcome), "outcome_yes": yes, "outcome_no": no,
           **EMPTY, "note": ""}
    if min(yes, no, n_1, n_0) < cfg.MIN_GROUP_SIZE:
        return {**row, "note": f"not testable: a group has fewer than {cfg.MIN_GROUP_SIZE} grants"}
    s_1, s_0 = int(np.sum(outcome[group == 1])), int(np.sum(outcome[group == 0]))
    difference, low, high = newcombe(s_1, n_1, s_0, n_0)
    row.update(estimate=difference, ci_low=low, ci_high=high)
    if inferential:
        row["p_raw"] = fisher_p(s_1, n_1, s_0, n_0)
    else:
        row["note"] = f"descriptive only: fewer than {cfg.DESCRIPTIVE_BELOW} completed grants"
    return row


def adjust_family(rows):
    """Add Holm and Benjamini-Hochberg adjusted p-values to the tested rows of one family, in place."""
    alpha = get_config().ALPHA
    tested = [row for row in rows if not math.isnan(row["p_raw"])]
    holm = holm_bonferroni([row["p_raw"] for row in tested])
    hochberg = benjamini_hochberg([row["p_raw"] for row in tested])
    for row in rows:
        row.update(p_holm=math.nan, p_bh=math.nan, tests_in_family=len(tested), significant_after_holm=False)
    for row, p_holm, p_bh in zip(tested, holm, hochberg):
        row.update(p_holm=float(p_holm), p_bh=float(p_bh), significant_after_holm=bool(p_holm < alpha))
    return rows
