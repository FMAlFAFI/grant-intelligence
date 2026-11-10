"""Stage 6.2: do the two reviewers of a proposal agree, per criterion and on the total.

With two reviewers this measures agreement, not reliability: it can show that reviewers diverge on a
criterion, never which of them was right. Every figure is an aggregate over proposals; nothing here
describes an individual reviewer.
"""
import numpy as np
import pandas as pd

from app.review.criteria import load_rubric
from app.statistics.confidence_intervals import wilson
from app.statistics.resampling import cohens_kappa, kappa_interval, mean_interval, spearman, spearman_interval
from config.config import get_config

LIMITATION = ("With two reviewers per proposal we measure agreement, not reliability. We can say that reviewers "
              "diverge on a criterion, but not which one was right, because there is no third opinion.")


def calculate_cohens_kappa(first, second):
    """Cohen's kappa for two equally long lists of categories, rounded to four decimals."""
    if len(first) != len(second):
        raise ValueError("Both lists must cover the same proposals.")
    return round(cohens_kappa(first, second), 4)


def score_agreement(pairs, rubric=None):
    """Spearman correlation and mean absolute difference per criterion and for the total, with intervals.

    Args:
        pairs: one row per proposal with two reviews, columns suffixed _a and _b (app.review.tables.pair_frame)
        rubric: the rubric from app.review.criteria.load_rubric

    Returns:
        One row per criterion. The total is reported on its own row. The four separate C to F criteria
        use only pairs in which both reviews used the standard form.
    """
    cfg, rubric = get_config(), rubric or load_rubric()
    rows = []
    for code in rubric["comparable"] + rubric["separate"] + ["total"]:
        both = pairs[[f"{code}_a", f"{code}_b"]].dropna()
        first, second = both[f"{code}_a"].to_numpy(float), both[f"{code}_b"].to_numpy(float)
        maximum = rubric["maxima"].get(code, sum(rubric["maxima"][c] for c in rubric["comparable"]))
        row = {"criterion": code, "max_score": maximum, "pairs": len(both),
               "basis": "both reviews on the standard form" if code in rubric["separate"] else "all pairs"}
        if len(both) < cfg.MIN_REVIEWS_PER_CELL:
            rows.append({**row, "note": f"fewer than {cfg.MIN_REVIEWS_PER_CELL} pairs, not reported"})
            continue
        difference = np.abs(first - second)
        rho_low, rho_high = spearman_interval(first, second)
        mad_low, mad_high = mean_interval(difference)
        rows.append({
            **row,
            "spearman": round(spearman(first, second), 3),
            "spearman_ci_low": round(rho_low, 3), "spearman_ci_high": round(rho_high, 3),
            "mean_abs_difference": round(float(difference.mean()), 2),
            "mad_ci_low": round(mad_low, 2), "mad_ci_high": round(mad_high, 2),
            "mad_share_of_max": round(float(difference.mean()) / maximum, 3),
            "note": "",
        })
    return pd.DataFrame(rows)


def classification_agreement(pairs):
    """Cohen's kappa and share of pairs that agree on basic versus applied research."""
    cfg = get_config()
    both = pairs[["classification_a", "classification_b"]].dropna()
    first, second = both["classification_a"].to_numpy(), both["classification_b"].to_numpy()
    agree, n = int((first == second).sum()), len(both)
    low, high = wilson(agree, n, cfg.CONFIDENCE_LEVEL)
    kappa_low, kappa_high = kappa_interval(first, second) if n else (np.nan, np.nan)
    return {"pairs": n, "agree": agree, "agree_ci_low": low, "agree_ci_high": high,
            "kappa": cohens_kappa(first, second), "kappa_ci_low": kappa_low, "kappa_ci_high": kappa_high}


def total_versus_criteria(pairs, rubric=None):
    """Count pairs that agree on the total but differ on at least two criteria.

    Returns:
        pairs, agree_on_total (within TOTAL_AGREE_POINTS) and of those differ_on_criteria (two or more
        comparable criteria at least CRITERION_DIFFER_POINTS apart)
    """
    cfg, rubric = get_config(), rubric or load_rubric()
    close = (pairs["total_a"] - pairs["total_b"]).abs() <= cfg.TOTAL_AGREE_POINTS
    apart = sum(((pairs[f"{code}_a"] - pairs[f"{code}_b"]).abs() >= cfg.CRITERION_DIFFER_POINTS).astype(int)
                for code in rubric["comparable"])
    return {"pairs": len(pairs), "agree_on_total": int(close.sum()),
            "differ_on_criteria": int((close & (apart >= 2)).sum())}
