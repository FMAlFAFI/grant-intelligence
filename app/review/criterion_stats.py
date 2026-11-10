"""Stage 6.1: which criteria discriminate (mean, SD and range used per criterion)."""
import pandas as pd

from app.review.criteria import load_rubric
from app.statistics.confidence_intervals import wilson
from app.statistics.resampling import clustered_mean_sd
from config.config import get_config


def criterion_discrimination(reviews, rubric=None):
    """Report mean, SD, range used and share at the maximum for every criterion, with intervals.

    Args:
        reviews: one row per review with a grant_id column and one column per criterion code
            (app.review.tables.review_frame)
        rubric: the rubric from app.review.criteria.load_rubric

    Returns:
        One row per criterion. The four separate C to F criteria use standard-form reviews only, and
        the combined mark uses every review. A criterion is flagged as doing little work when its SD is
        below LOW_SD_SHARE of its maximum or more than AT_MAX_SHARE of reviews give the maximum.
    """
    cfg, rubric = get_config(), rubric or load_rubric()
    rows = []
    for code in rubric["form_codes"] + [rubric["combined"]]:
        if code not in reviews.columns:
            continue
        scored = reviews[["grant_id", code]].dropna()
        maximum, n = rubric["maxima"][code], len(scored)
        basis = ("standard-form reviews" if code in rubric["separate"]
                 else "all reviews, C to F as one mark" if code == rubric["combined"] else "all reviews")
        row = {"criterion": code, "name": rubric["names"][code], "max_score": maximum, "reviews": n, "basis": basis}
        if n < cfg.MIN_REVIEWS_PER_CELL:
            rows.append({**row, "note": f"fewer than {cfg.MIN_REVIEWS_PER_CELL} reviews, not reported"})
            continue
        mean, mean_ci, sd, sd_ci = clustered_mean_sd(scored[code], scored["grant_id"])
        at_max = int((scored[code] == maximum).sum())
        low, high = wilson(at_max, n, cfg.CONFIDENCE_LEVEL)
        rows.append({
            **row,
            "mean": round(mean, 2), "mean_ci_low": round(mean_ci[0], 2), "mean_ci_high": round(mean_ci[1], 2),
            "sd": round(sd, 2), "sd_ci_low": round(sd_ci[0], 2), "sd_ci_high": round(sd_ci[1], 2),
            "sd_share_of_max": round(sd / maximum, 3),
            "min_used": float(scored[code].min()), "max_used": float(scored[code].max()),
            "at_max": at_max, "at_max_share": round(at_max / n, 3),
            "at_max_ci_low": round(low, 3), "at_max_ci_high": round(high, 3),
            "little_work": bool(sd < cfg.LOW_SD_SHARE * maximum or at_max / n > cfg.AT_MAX_SHARE),
            "note": "",
        })
    return pd.DataFrame(rows)
