import os
import pandas as pd

from app.review.agreement import identify_bias
from app.review.criterion_stats import compute_criterion_discrimination
from app.review.validity_analysis import evaluate_14_criteria_validity
from app.supplementary.factors import evaluate_supplementary_factors, export_supplementary_chart


def load_project_dataset():
    """
    Load and merge the project's synthetic ground-truth grants and reviews datasets.
    Evaluates completed grants (Stage 6 & Stage 7 methodology).
    """
    grants_path = "data/synthetic/ground_truth/grants.csv"
    reviews_path = "data/synthetic/ground_truth/reviews.csv"

    if not (os.path.exists(grants_path) and os.path.exists(reviews_path)):
        raise FileNotFoundError("Project ground-truth datasets not found in data/synthetic/ground_truth/.")

    print(f"[INFO] Loading project datasets from '{grants_path}' and '{reviews_path}'...")
    grants = pd.read_csv(grants_path, encoding="utf-8-sig")
    reviews = pd.read_csv(reviews_path, encoding="utf-8-sig")

    # Stage 6.1: Criterion discrimination check
    disc_df = compute_criterion_discrimination(reviews)
    low_work_count = int(disc_df["Doing_Little_Work"].sum())
    print(f"[INFO] Stage 6.1 Criterion Discrimination Audit: {len(disc_df)} criteria checked, {low_work_count} flagged as low-work.")

    sub_cols = ["B3C", "B3D", "B3E", "B3F"]
    reviews["B3_unified"] = reviews["B3_combined"].fillna(reviews[sub_cols].sum(axis=1))

    rubric_cols = ["A1", "A2", "A3", "A4", "A5", "B1", "B2", "B3C", "B3D", "B3E", "B3F", "C1", "D1", "E1"]
    for col in rubric_cols:
        if col in sub_cols:
            reviews[col] = reviews[col].fillna(reviews["B3_unified"] / 4.0)

    # Stage 6.2: Two-reviewer categorical agreement audit
    rev_a = reviews[reviews["review_id"].str.endswith("-A")].set_index("grant_id")
    rev_b = reviews[reviews["review_id"].str.endswith("-B")].set_index("grant_id")
    shared = rev_a.index.intersection(rev_b.index)
    if len(shared) > 0:
        tier_a = pd.cut(rev_a.loc[shared, "total"], bins=[0, 60, 75, 100], labels=[1, 2, 3]).astype(int).tolist()
        tier_b = pd.cut(rev_b.loc[shared, "total"], bins=[0, 60, 75, 100], labels=[1, 2, 3]).astype(int).tolist()
        bias_report = identify_bias(tier_a, tier_b)
        print(f"[INFO] Stage 6.2 Two-Reviewer Agreement Audit (n={len(shared)} pairs): Kappa={bias_report['kappa_score']}")

    agg_reviews = reviews.groupby("grant_id", as_index=False)[rubric_cols + ["total"]].mean()
    merged = grants.merge(agg_reviews, on="grant_id", how="inner")

    completed = merged[merged["completed"] == 1].copy().reset_index(drop=True)
    completed["prior_publications"] = completed["prior_pubs"]
    completed["is_successful"] = (completed["extended"] == 0).astype(int)

    for idx, r_col in enumerate(rubric_cols, start=1):
        completed[f"criterion_{idx}"] = completed[r_col]

    return completed, rubric_cols


def perform_supplementary_analyses(df):
    """Execute Stage 7 supplementary analyses via app.supplementary.factors."""
    print("\n" + "=" * 65)
    print("1. SUPPLEMENTARY ANALYSES (BUDGET & PRIOR PUBLICATIONS, n = 140)")
    print("=" * 65)

    summary_df = evaluate_supplementary_factors(df)
    print(summary_df.to_string(index=False))
    export_supplementary_chart(df, "supplementary_analyses_results.png")
    print("[SAVED] Visual chart exported to 'supplementary_analyses_results.png'")


def test_14_criteria_predictive_validity(df, rubric_cols):
    """Execute Stage 6.4 predictive validity analysis via app.review.validity_analysis."""
    print("\n" + "=" * 65)
    print("2. PREDICTIVE VALIDITY & MULTIPLE TESTING CORRECTIONS (14 CRITERIA)")
    print("=" * 65)

    res_df, auc_score, report_str = evaluate_14_criteria_validity(df, rubric_cols)
    print(res_df.to_string(index=False))
    res_df.to_csv("criteria_validity_results.csv", index=False, encoding="utf-8-sig")
    print("[SAVED] Detailed table exported to 'criteria_validity_results.csv'")
    print(f"\nCombined 14-Criteria ROC-AUC Score: {auc_score:.4f}")
    print("Classification Report:")
    print(report_str)


if __name__ == "__main__":
    dataset, rubric_codes = load_project_dataset()
    perform_supplementary_analyses(dataset)
    test_14_criteria_predictive_validity(dataset, rubric_codes)
