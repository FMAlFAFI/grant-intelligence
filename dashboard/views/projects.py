import streamlit as st

from dashboard.components.notices import missing_outputs
from dashboard.components.proposal_table import COLUMN_LABELS, proposal_table
from dashboard.data.adapters import load_tracker, progress_outputs
from dashboard.data.health import FINISHED_STATUSES, HEALTHS, RUNNING_STATUSES

TABLE_COLUMNS = ["health_label", "grant_id", "title", "college", "round_label", "current_stage_name",
                 "overall_progress", "months"]
EXPORT_COLUMNS = ["health", *TABLE_COLUMNS[1:], "status", "reason"]
GROUPS = {"Running": RUNNING_STATUSES, "Completed": FINISHED_STATUSES}

st.title("Projects")
st.caption("One line per funded grant, most urgent first.")

if missing_outputs(progress_outputs()):
    st.stop()

tracker = st.session_state["filters"].apply(load_tracker())
left, right = st.columns(2, vertical_alignment="bottom")
with left:
    group = st.segmented_control("Show", [*GROUPS, "All"], default="Running", key="projects_group")
with right:
    healths = st.pills("Health", HEALTHS, selection_mode="multi", default=[], key="projects_health")

rows = tracker[tracker["status"].isin(GROUPS[group])] if group in GROUPS else tracker
if healths:
    rows = rows[rows["health"].isin(healths)]

rows = rows.assign(college=rows["college"].str.removeprefix("College of "),
                   round_label=rows["round_label"].str.split(" (", regex=False).str[0])
proposal_table(rows, "projects_table", TABLE_COLUMNS)
st.caption("**On track**: nothing to report. **Watch**: a stage stopped moving in the latest report. "
           "**Late**: a stage is past its planned end, or the grant went past its planned end date. "
           "These are prompts to check in with the team, not a judgement of the researchers.")

export = rows[EXPORT_COLUMNS].rename(columns={**COLUMN_LABELS, "health": "Health", "reason": "Reason"})
st.download_button("Download this list (CSV)", export.to_csv(index=False).encode("utf-8-sig"),
                   file_name="projects.csv", mime="text/csv", icon=":material/download:")
