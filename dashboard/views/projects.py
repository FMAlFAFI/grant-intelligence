import streamlit as st

from dashboard.components.notices import health_legend, missing_outputs, page_help
from dashboard.components.proposal_table import COLUMN_LABELS, proposal_table
from dashboard.data.adapters import load_all_projects, progress_outputs
from dashboard.data.health import HEALTHS
from ingestion.grant_register import STATUSES

TABLE_COLUMNS = ["grant_id", "title", "round_label", "college", "status", "health_label", "current_stage_name",
                 "overall_progress", "months"]
EXPORT_COLUMNS = [*TABLE_COLUMNS, "reason"]

st.title("Projects")
page_help("The list of all proposals, with the running projects that need attention at the top. Status says where a "
          "proposal is in its life, health says how a funded project is doing. Select a line to open its file.")

if missing_outputs(progress_outputs()):
    st.stop()

projects = load_all_projects()
rows = st.session_state["filters"].apply(projects)
left, right = st.columns(2, vertical_alignment="bottom")
with left:
    statuses = st.multiselect("Status", STATUSES, default=[], placeholder="All", key="projects_status")
with right:
    healths = st.pills("Health", HEALTHS, selection_mode="multi", default=[], key="projects_health")

if statuses:
    rows = rows[rows["status"].isin(statuses)]
if healths:
    rows = rows[rows["health"].isin(healths)]

st.caption(f"Showing {len(rows)} of {len(projects)} projects")
health_legend()
rows = rows.assign(college=rows["college"].str.removeprefix("College of "),
                   round_label=rows["round_label"].str.split(" (", regex=False).str[0])
proposal_table(rows, "projects_table", TABLE_COLUMNS, height=560)

export = rows[EXPORT_COLUMNS].rename(columns={**COLUMN_LABELS, "reason": "Reason"})
st.download_button("Download this list (CSV)", export.to_csv(index=False).encode("utf-8-sig"),
                   file_name="projects.csv", mime="text/csv", icon=":material/download:")
