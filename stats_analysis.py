import os
import pandas as pd
import numpy as np
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, roc_auc_score
import matplotlib.pyplot as plt
import seaborn as sns

from app.statistics.multiple_comparison import benjamini_hochberg, holm_bonferroni
from app.supplementary import evaluate_supplementary_factors
from app.review import identify_bias


def load_project_dataset():
    """
    Load and merge the project's synthetic ground-truth grants and reviews datasets.
    Evaluates completed grants (Stage 6.4 & Stage 7 methodology).
    """
    grants_path = "data/synthetic/ground_truth/grants.csv"
    reviews_path = "data/synthetic/ground_truth/reviews.csv"

    if not (os.path.exists(grants_path) and os.path.exists(reviews_path)):
        raise FileNotFoundError("Project ground-truth datasets not found in data/synthetic/ground_truth/.")

    print(f"[INFO] Loading project datasets from '{grants_path}' and '{reviews_path}'...")
    grants = pd.read_csv(grants_path, encoding="utf-8-sig")
    reviews = pd.read_csv(reviews_path, encoding="utf-8-sig")

    sub_cols = ["B3C", "B3D", "B3E", "B3F"]
    reviews["B3_unified"] = reviews["B3_combined"].fillna(reviews[sub_cols].sum(axis=1))

    rubric_cols = ["A1", "A2", "A3", "A4", "A5", "B1", "B2", "B3C", "B3D", "B3E", "B3F", "C1", "D1", "E1"]
    for col in rubric_cols:
        if col in sub_cols:
            reviews[col] = reviews[col].fillna(reviews["B3_unified"] / 4.0)

    # Audit two-reviewer categorical agreement via app.review
    rev_a = reviews[reviews["review_id"].str.endswith("-A")].set_index("grant_id")
    rev_b = reviews[reviews["review_id"].str.endswith("-B")].set_index("grant_id")
    shared = rev_a.index.intersection(rev_b.index)
    if len(shared) > 0:
        tier_a = pd.cut(rev_a.loc[shared, "total"], bins=[0, 60, 75, 100], labels=[1, 2, 3]).astype(int).tolist()
        tier_b = pd.cut(rev_b.loc[shared, "total"], bins=[0, 60, 75, 100], labels=[1, 2, 3]).astype(int).tolist()
        bias_report = identify_bias(tier_a, tier_b)
        print(f"[INFO] Two-Reviewer Agreement Audit (n={len(shared)} pairs): Kappa={bias_report['kappa_score']}")

    agg_reviews = reviews.groupby("grant_id", as_index=False)[rubric_cols + ["total"]].mean()
    merged = grants.merge(agg_reviews, on="grant_id", how="inner")

    completed = merged[merged["completed"] == 1].copy().reset_index(drop=True)
    completed["prior_publications"] = completed["prior_pubs"]
    completed["is_successful"] = (completed["extended"] == 0).astype(int)

    for idx, r_col in enumerate(rubric_cols, start=1):
        completed[f"criterion_{idx}"] = completed[r_col]

    return completed, rubric_cols


def perform_supplementary_analyses(df):
    """Execute Stage 7 supplementary analyses via app.supplementary."""
    print("\n" + "=" * 65)
    print("1. SUPPLEMENTARY ANALYSES (BUDGET & PRIOR PUBLICATIONS, n = 140)")
    print("=" * 65)

    summary_df = evaluate_supplementary_factors(df)
    print(summary_df.to_string(index=False))

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    sns.boxplot(x="is_successful", y="prior_publications", hue="is_successful", data=df, ax=axes[0], palette="Set2", legend=False)
    axes[0].set_title("Impact of Prior Publications on On-Time Completion")
    axes[0].set_xlabel("Outcome (0 = Extended, 1 = Completed On-Time)")
    axes[0].set_ylabel("Prior Publications Count")

    sns.boxplot(x="is_successful", y="budget", hue="is_successful", data=df, ax=axes[1], palette="Set2", legend=False)
    axes[1].set_title("Impact of Requested Budget on On-Time Completion")
    axes[1].set_xlabel("Outcome (0 = Extended, 1 = Completed On-Time)")
    axes[1].set_ylabel("Requested Budget (SAR)")

    plt.tight_layout()
    plt.savefig("supplementary_analyses_results.png", dpi=300)
    plt.close(fig)
    print("[SAVED] Visual chart exported to 'supplementary_analyses_results.png'")


def test_14_criteria_predictive_validity(df, rubric_cols):
    """Test 14 review criteria using app.statistics.multiple_comparison."""
    print("\n" + "=" * 65)
    print("2. PREDICTIVE VALIDITY & MULTIPLE TESTING CORRECTIONS (14 CRITERIA)")
    print("=" * 65)

    criteria_cols = [f"criterion_{i}" for i in range(1, 15)]
    results = []

    for col, code in zip(criteria_cols, rubric_cols):
        series = df[col].fillna(df[col].median())
        r_val, p_val = stats.spearmanr(series, df["is_successful"])
        results.append({
            "Criterion": f"{col} ({code})",
            "Correlation (r)": round(float(r_val), 4),
            "Raw_p_value": round(float(p_val), 6),
        })

    res_df = pd.DataFrame(results)
    n_tests = len(criteria_cols)

    res_df["Bonferroni_p"] = np.minimum(res_df["Raw_p_value"] * n_tests, 1.0).round(6)
    res_df["Holm_p"] = holm_bonferroni(res_df["Raw_p_value"].values).round(6)
    res_df["FDR_BH_p"] = benjamini_hochberg(res_df["Raw_p_value"].values).round(6)
    res_df = res_df.sort_values("Raw_p_value").reset_index(drop=True)
    res_df["Valid_After_Correction"] = res_df["Holm_p"] < 0.05

    print(res_df.to_string(index=False))
    res_df.to_csv("criteria_validity_results.csv", index=False, encoding="utf-8-sig")
    print("[SAVED] Detailed table exported to 'criteria_validity_results.csv'")

    X = StandardScaler().fit_transform(df[criteria_cols].fillna(0))
    y = df["is_successful"]
    clf = LogisticRegression(random_state=42).fit(X, y)
    y_pred = clf.predict(X)
    y_prob = clf.predict_proba(X)[:, 1]

    print(f"\nCombined 14-Criteria ROC-AUC Score: {roc_auc_score(y, y_prob):.4f}")
    print("Classification Report:")
    print(classification_report(y, y_pred))


if __name__ == "__main__":
    dataset, rubric_codes = load_project_dataset()
    perform_supplementary_analyses(dataset)
    test_14_criteria_predictive_validity(dataset, rubric_codes)
