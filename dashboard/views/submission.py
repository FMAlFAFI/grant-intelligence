import pandas as pd
import streamlit as st

from app.classification.keyword_classifier import load_priorities
from app.ingestion.grant_register import STAGES
from app.review.agreement import LIMITATION
from app.review.criteria import load_rubric
from app.review.validity_analysis import TRUNCATION
from config.config import ROOT, get_config
from forms.capture import render_assessment_form, render_progress_form, render_proposal_form, render_review_form

RESULTS = get_config().RESULTS_DIR
TABLES = [
    ("Which criteria discriminate (6.1)", RESULTS / "review" / "criterion_discrimination.csv", None),
    ("Do the two reviewers agree (6.2)", RESULTS / "review" / "agreement.csv", LIMITATION),
    ("Does the gate agree with the reviewers (6.3)", RESULTS / "review" / "gate_comparison.csv", None),
    ("Did any criterion predict the outcome (6.4)", RESULTS / "review" / "validity.csv", TRUNCATION),
    ("Recurring concerns in reviewer comments (6.5)", RESULTS / "review" / "concerns.csv", None),
    ("Prior publications against outcome (7)", RESULTS / "supplementary" / "prior_publications.csv", TRUNCATION),
    ("Budget composition against outcome (7)", RESULTS / "supplementary" / "budget_composition.csv", TRUNCATION),
]

st.title("Capture forms and review analysis")
forms_tab, analysis_tab = st.tabs(["Capture forms", "Review analysis"])

with forms_tab:
    st.caption("One form per institutional record. Names are stored as pseudonym codes and the saved rows go to "
               "the capture folder under data/raw, which is not in version control.")
    proposal, assessment, review, progress = st.tabs(["Proposal", "Initial assessment", "Review", "Progress report"])
    with proposal:
        render_proposal_form(st, load_priorities())
    with assessment:
        render_assessment_form(st)
    with review:
        render_review_form(st, load_rubric())
    with progress:
        render_progress_form(st, STAGES)

with analysis_tab:
    st.caption("Every table is an aggregate over proposals or grants; none describes an individual reviewer or "
               "researcher. Intervals, corrections and the full text are in docs/review-analysis.md.")
    for title, path, statement in TABLES:
        st.subheader(title)
        if statement:
            st.info(statement)
        if path.exists():
            st.dataframe(pd.read_csv(path, encoding="utf-8-sig"), width="stretch", hide_index=True)
        else:
            st.warning(f"Not produced yet. Run: python stats_analysis.py ({path.relative_to(ROOT).as_posix()})")
    chart = RESULTS / "supplementary" / "supplementary_analyses.png"
    if chart.exists():
        st.image(str(chart), caption="Prior publications and equipment share of the budget, by outcome. "
                                     "A description of this dataset, not a funding recommendation.")
