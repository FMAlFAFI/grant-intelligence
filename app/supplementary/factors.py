"""Stage 7: Supplementary statistical analyses for prior publications and budget."""
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from scipy import stats

from app.statistics.multiple_comparison import holm_bonferroni


def evaluate_supplementary_factors(df: pd.DataFrame) -> pd.DataFrame:
    """Compute Welch's t-test and Spearman rank correlation for prior publications and budget."""
    success_grp = df[df["is_successful"] == 1]
    fail_grp = df[df["is_successful"] == 0]
    t_pub, p_pub = stats.ttest_ind(success_grp["prior_publications"], fail_grp["prior_publications"], equal_var=False)
    t_bud, p_bud = stats.ttest_ind(success_grp["budget"], fail_grp["budget"], equal_var=False)
    r_pub, _ = stats.spearmanr(df["prior_publications"], df["is_successful"])
    r_bud, _ = stats.spearmanr(df["budget"], df["is_successful"])
    return pd.DataFrame({
        "Factor": ["Prior Publications (5 yrs)", "Requested Budget (SAR)"],
        "Mean (On-Time)": [round(success_grp["prior_publications"].mean(), 2), round(success_grp["budget"].mean(), 2)],
        "Mean (Extended)": [round(fail_grp["prior_publications"].mean(), 2), round(fail_grp["budget"].mean(), 2)],
        "Spearman_r": [round(float(r_pub), 4), round(float(r_bud), 4)],
        "Welch_t": [round(float(t_pub), 4), round(float(t_bud), 4)],
        "p_value": [round(float(p_pub), 4), round(float(p_bud), 4)],
        "Holm_p": holm_bonferroni([p_pub, p_bud]).round(4),
        "Significant (p < 0.05)": [bool(p_pub < 0.05), bool(p_bud < 0.05)],
    })


def export_supplementary_chart(df: pd.DataFrame, out_path: str = "supplementary_analyses_results.png") -> None:
    """Export boxplot comparison for prior publications and requested budget."""
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
    plt.savefig(out_path, dpi=300)
    plt.close(fig)
