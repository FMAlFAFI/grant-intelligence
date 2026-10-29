import streamlit as st

DETAIL_PAGE = "views/proposal_detail.py"

COLUMN_LABELS = {
    "grant_id": "Grant",
    "year": "Round",
    "lang": "Lang",
    "college": "College",
    "type": "Type",
    "assessment": "Initial assessment",
    "mean_review_total": "Mean review /100",
    "funded": "Funded",
    "status": "Status",
    "current_stage_name": "Current stage",
    "overall_progress": "Progress %",
    "reports": "Reports",
    "spent_share": "Budget spent",
    "claimed_priority": "Claimed priority",
    "predicted_priority": "Priority from the text",
    "content_priority": "True priority",
    "margin": "Margin",
    "similarity": "Similarity",
    "runner_up": "Runner up",
    "n_papers": "Papers",
    "stall_stage": "Stall stage",
    "stall_quarters": "Quarters stuck",
    "slip_months": "Slip (months)",
    "threshold": "Threshold",
    "drift_flag": "Drifted",
    "alert": "Alert",
    "quarter": "Quarter",
}


def open_detail(grant_id):
    st.session_state["grant_id"] = grant_id
    st.switch_page(DETAIL_PAGE, query_params={"grant_id": grant_id})


def proposal_table(frame, key, columns, caption=None):
    shown = [column for column in columns if column in frame.columns]
    if caption:
        st.caption(caption)
    if frame.empty:
        st.info("No grants match this selection.")
        return
    config = {column: COLUMN_LABELS.get(column, column) for column in shown}
    config["overall_progress"] = st.column_config.ProgressColumn("Progress %", min_value=0, max_value=100, format="%.0f%%")
    config["spent_share"] = st.column_config.NumberColumn("Budget spent", format="percent")
    config["funded"] = st.column_config.CheckboxColumn("Funded")
    event = st.dataframe(
        frame[shown],
        key=key,
        hide_index=True,
        width="stretch",
        column_config={column: config[column] for column in shown},
        on_select="rerun",
        selection_mode="single-row",
    )
    st.caption(f"{len(frame)} grants. Select a row to open its record.")
    rows = event.selection.rows if event and event.selection else []
    if rows:
        open_detail(frame.iloc[rows[0]]["grant_id"])
