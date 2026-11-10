"""Stage 6.3: does the initial assessment (the gate) agree with the reviewers on the same ground."""
import numpy as np
import pandas as pd

from app.review.criteria import load_rubric
from app.statistics.confidence_intervals import wilson
from app.statistics.resampling import cohens_kappa, kappa_interval
from config.config import get_config


def gate_agreement(assessments, reviews, rubric=None):
    """Compare each overlapping gate answer with the reviewers' mean score on the matching criteria.

    A proposal passes with the reviewers when its mean score on the matching criteria is at least the
    pass share of their combined maximum. The main share is GATE_PASS_SHARE; the shares in
    GATE_PASS_CHECKS are reported next to it as a sensitivity check.

    Args:
        assessments: one row per initial assessment (app.review.tables.assessment_frame)
        reviews: one row per review (app.review.tables.review_frame)
        rubric: the rubric from app.review.criteria.load_rubric

    Returns:
        One row per gate question and pass share, for proposals that were assessed and reviewed.
    """
    cfg, rubric = get_config(), rubric or load_rubric()
    means = reviews.groupby("grant_id")[rubric["comparable"]].mean()
    rows = []
    for gate, codes in rubric["gate_overlap"].items():
        share = means[codes].sum(axis=1) / sum(rubric["maxima"][code] for code in codes)
        table = assessments[["grant_id", gate]].dropna().set_index("grant_id").join(share.rename("share"), how="inner")
        gate_yes = table[gate].astype(bool).to_numpy()
        for pass_share in (cfg.GATE_PASS_SHARE, *cfg.GATE_PASS_CHECKS):
            reviewer_yes = (table["share"] >= pass_share).to_numpy()
            n, agree = len(table), int((gate_yes == reviewer_yes).sum())
            low, high = wilson(agree, n, cfg.CONFIDENCE_LEVEL)
            passed, passed_low = int(gate_yes.sum()), int((gate_yes & ~reviewer_yes).sum())
            passed_ci = wilson(passed_low, passed, cfg.CONFIDENCE_LEVEL)
            # Kappa needs both answers on both sides; a gate that passed every reviewed proposal has none
            varies = len(np.unique(gate_yes)) > 1 and len(np.unique(reviewer_yes)) > 1
            kappa = cohens_kappa(gate_yes, reviewer_yes) if varies else np.nan
            kappa_ci = kappa_interval(gate_yes, reviewer_yes) if varies else (np.nan, np.nan)
            rows.append({
                "gate_question": gate, "rubric_criteria": "+".join(codes), "pass_share": pass_share,
                "main_rule": pass_share == cfg.GATE_PASS_SHARE, "proposals": n,
                "agree": agree, "agree_share": round(agree / n, 3) if n else np.nan,
                "agree_ci_low": round(low, 3), "agree_ci_high": round(high, 3),
                "kappa": round(kappa, 3), "kappa_ci_low": round(kappa_ci[0], 3), "kappa_ci_high": round(kappa_ci[1], 3),
                "passed_gate": passed, "passed_gate_scored_low": passed_low,
                "scored_low_ci_low": round(passed_ci[0], 3), "scored_low_ci_high": round(passed_ci[1], 3),
                "note": "" if varies else "kappa not estimable: the gate or the reviewers gave one answer throughout",
            })
    return pd.DataFrame(rows)
