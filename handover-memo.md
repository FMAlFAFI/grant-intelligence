# Grant Intelligence - Official Handover Memo

## 1. Executive Summary
This document serves as the final handover memorandum for the **Grant Intelligence** system. The platform provides an end-to-end AI pipeline (`main.py` and `run_dashboard.py`) and an interactive 8-page Streamlit interface (`dashboard/streamlit_app.py`) utilizing locked `Qwen/Qwen3-Embedding-0.6B` vector embeddings to classify research priorities, detect semantic drift in research outputs, capture institutional data, and evaluate submissions against standardized review criteria.

> **Important Scope Notice:** All results in this repository are generated from the controlled synthetic NAUSS dataset (`300` proposals, `180` funded grants, `140` completed grants). They validate the end-to-end software and statistical pipeline and do not describe real-world NAUSS grants.

## 2. Completed Deliverables Summary
- **Supplementary Statistical Analyses:** Executed parametric (Welch's t-test) and non-parametric (Spearman rank correlation) tests with Holm-Bonferroni corrections evaluating the impact of PI prior publications and requested budget on project completion (`stats_analysis.py` & `supplementary_analyses_results.png`).
- **Institutional Capture Forms:** Built a validated data entry interface (`dashboard/institutional_module.py` and `dashboard/views/submission.py`) integrated into the Streamlit dashboard matching institutional review forms and persisting records to `data/captured_proposals.csv`.
- **14-Criteria Predictive Validity & Multiple Testing Corrections:** Evaluated all 14 review rubric criteria against completed grant outcomes (`n = 140`) using Spearman rank correlation and multivariate Logistic Regression (`ROC-AUC = 0.7833`), reporting raw p-values alongside **Bonferroni**, **Holm-Bonferroni**, and **Benjamini-Hochberg (FDR)** multiple testing corrections (`criteria_validity_results.csv`).
- **System-Wide Caching & No Silent Fallback Policy:** Enforced persistent vector caching via `LockedEncoder` (`models.lock`), `@st.cache_resource` and `@st.cache_data` across Streamlit loaders, and `check=True` subprocess enforcement in `run_dashboard.py`. Any model or pipeline error raises an explicit runtime exception rather than falling back silently.

## 3. Strict 30-Minute Clean Clone Test Protocol
To verify repository readiness on a fresh machine within the 30-minute threshold, execute the following sequential commands:

```bash
# Step 1: Clone the repository (Target: < 2 mins)
git clone <REPOSITORY_URL> grant_intelligence_clone
cd grant_intelligence_clone

# Step 2: Initialize isolated virtual environment (Target: < 3 mins)
python -m venv venv
# Windows activation:
venv\Scripts\activate
# macOS/Linux activation:
source venv/bin/activate

# Step 3: Install locked dependencies and run regression tests (Target: < 10 mins)
python main.py

# Step 4: Run the unified 9-step pipeline and launch the dashboard (Target: < 5 mins)
python run_dashboard.py