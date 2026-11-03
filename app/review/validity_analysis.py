"""Stage 6.4: 14-criteria predictive validity and multiple testing corrections."""
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.preprocessing import StandardScaler

from app.statistics.multiple_comparison import benjamini_hochberg, holm_bonferroni


def evaluate_14_criteria_validity(df: pd.DataFrame, rubric_cols: list[str]) -> tuple[pd.DataFrame, float, str]:
    """
    Evaluate all 14 review rubric criteria against on-time project completion (n=140)
    with Bonferroni, Holm-Bonferroni, and Benjamini-Hochberg (FDR) corrections.
    """
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

    X = StandardScaler().fit_transform(df[criteria_cols].fillna(0))
    y = df["is_successful"]
    clf = LogisticRegression(random_state=42).fit(X, y)
    y_pred = clf.predict(X)
    y_prob = clf.predict_proba(X)[:, 1]
    auc_score = float(roc_auc_score(y, y_prob))
    report_str = classification_report(y, y_pred)

    return res_df, auc_score, report_str
