"""Stage 6.4: did any review criterion predict the outcome of a completed grant.

Predictors, outcomes, tests and corrections follow docs/statistics-methodology.md section 6.4.
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from app.review.criteria import load_rubric
from app.statistics.association import adjust_family, proportion_association, rank_association
from config.config import get_config

TRUNCATION = ("Outcomes exist only for proposals that passed the gate, were reviewed and were funded. Rejected "
              "proposals have no outcome, so every result here describes how criteria behave among funded grants. "
              "A criterion can predict nothing here simply because low scorers were never funded.")
OUTCOMES = {
    "on_time": "completed without extension",
    "has_paper": "at least one paper listed in the final report (self-reported, not verified in OpenAlex)",
}
MAIN, DETAIL = "6.4 review validity (main)", "6.4 methodology detail (standard-form reviews)"
COLUMNS = ["family", "predictor", "outcome", "measure", "n", "outcome_yes", "outcome_no", "estimate", "ci_low",
           "ci_high", "p_raw", "p_holm", "p_bh", "tests_in_family", "significant_after_holm", "note"]


def completed_table(predictors, outcomes):
    """Completed grants with their review predictors: the only grants an outcome exists for."""
    return predictors.merge(outcomes, on="grant_id", how="inner")


def validity_table(table, rubric=None):
    """Test every predictor against both outcomes and correct within each family.

    Args:
        table: one row per completed grant (completed_table)
        rubric: the rubric from app.review.criteria.load_rubric

    Returns:
        One row per predictor and outcome: the main family (12 comparable criteria, total score, reviewer
        disagreement, basic versus applied) and the detail family (the four separate C to F criteria,
        grants with at least one standard-form review).
    """
    cfg, rubric = get_config(), rubric or load_rubric()
    inferential = len(table) >= cfg.DESCRIPTIVE_BELOW
    families = {MAIN: [], DETAIL: []}
    for outcome in OUTCOMES:
        for predictor in rubric["comparable"] + ["total", "disagreement"]:
            row = rank_association(table[predictor], table[outcome], inferential)
            families[MAIN].append({"family": MAIN, "predictor": predictor, "outcome": outcome, **row})
        row = proportion_association(table["applied"], table[outcome], inferential)
        families[MAIN].append({"family": MAIN, "predictor": "applied (versus basic)", "outcome": outcome, **row})
        for predictor in rubric["separate"]:
            row = rank_association(table[predictor], table[outcome], inferential)
            families[DETAIL].append({"family": DETAIL, "predictor": predictor, "outcome": outcome, **row})
    rows = [row for family in families.values() for row in adjust_family(family)]
    return pd.DataFrame(rows)[COLUMNS]


def exploratory_model(table, rubric=None):
    """Logistic regression of on-time completion on the 12 comparable criteria, scored two ways.

    This is not one of the pre-specified tests. The apparent AUC is computed on the grants the model
    was fitted to and is optimistic; the cross-validated AUC is the honest figure.

    Returns:
        dict with n, apparent_auc and cross_validated_auc (five stratified folds, configured seed)
    """
    cfg, rubric = get_config(), rubric or load_rubric()
    data = table.dropna(subset=rubric["comparable"] + ["on_time"])
    features, target = data[rubric["comparable"]].to_numpy(float), data["on_time"].to_numpy(int)
    model = make_pipeline(StandardScaler(), LogisticRegression(random_state=cfg.SEED))
    apparent = roc_auc_score(target, model.fit(features, target).predict_proba(features)[:, 1])
    folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=cfg.SEED)
    held_out = cross_val_predict(model, features, target, cv=folds, method="predict_proba")[:, 1]
    return {"n": len(data), "apparent_auc": float(apparent),
            "cross_validated_auc": float(roc_auc_score(target, held_out)),
            "outcome_yes": int(np.sum(target == 1)), "outcome_no": int(np.sum(target == 0))}
