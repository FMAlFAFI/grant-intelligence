"""Stage 7 supplementary analyses for prior publications and budget."""
from scipy import stats
import pandas as pd
from app.statistics.multiple_comparison import holm_bonferroni

def evaluate_supplementary_factors(df):
    """Compute Welch t-test and Spearman r for prior publications and budget."""
    success_grp = df[df['is_successful'] == 1]
    fail_grp = df[df['is_successful'] == 0]
    t_pub, p_pub = stats.ttest_ind(success_grp['prior_publications'], fail_grp['prior_publications'], equal_var=False)
    t_bud, p_bud = stats.ttest_ind(success_grp['budget'], fail_grp['budget'], equal_var=False)
    r_pub, _ = stats.spearmanr(df['prior_publications'], df['is_successful'])
    r_bud, _ = stats.spearmanr(df['budget'], df['is_successful'])
    return pd.DataFrame({
        'Factor': ['Prior Publications (5 yrs)', 'Requested Budget (SAR)'],
        'Mean (On-Time)': [round(success_grp['prior_publications'].mean(), 2), round(success_grp['budget'].mean(), 2)],
        'Mean (Extended)': [round(fail_grp['prior_publications'].mean(), 2), round(fail_grp['budget'].mean(), 2)],
        'Spearman_r': [round(float(r_pub), 4), round(float(r_bud), 4)],
        'Welch_t': [round(float(t_pub), 4), round(float(t_bud), 4)],
        'p_value': [round(float(p_pub), 4), round(float(p_bud), 4)],
        'Holm_p': holm_bonferroni([p_pub, p_bud]).round(4),
        'Significant (p < 0.05)': [bool(p_pub < 0.05), bool(p_bud < 0.05)],
    })
