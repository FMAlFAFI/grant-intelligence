import streamlit as st
import pandas as pd
import os
from dashboard.institutional_module import render_capture_form

st.title("Proposal Submissions & Validation")
st.divider()

capture_tab, stats_tab = st.tabs(["Institutional Capture Form", "Statistical Validity Analysis"])

with capture_tab:
    # Save captured institutional proposals to a dedicated CSV file
    render_capture_form("data/captured_proposals.csv")

with stats_tab:
    # Display the 14-criteria predictive validity table and supplementary chart
    st.subheader("14-Criteria Predictive Validity & Multiple Testing Corrections")
    if os.path.exists("criteria_validity_results.csv"):
        st.dataframe(pd.read_csv("criteria_validity_results.csv"), use_container_width=True)
    if os.path.exists("supplementary_analyses_results.png"):
        st.image("supplementary_analyses_results.png", caption="Impact of Prior Publications & Budget on Success")