import pandas as pd
import streamlit as st

from dashboard.components.charts import funnel_chart, status_by_round_chart
from dashboard.components.kpi import big_number
from dashboard.components.notices import missing_outputs
from dashboard.components.proposal_table import proposal_table
from dashboard.data.adapters import load_tracker, progress_outputs
from dashboard.data.health import FINISHED_STATUSES, RUNNING_STATUSES, needs_attention
from dashboard.data.loaders import load_register

TABLE_COLUMNS = ["grant_id", "title", "round_label", "college", "status"]

st.title("Portfolio at a glance")
st.caption("Where all the research grants stand today.")

filters = st.session_state["filters"]
frame = filters.apply(load_register()).copy()
frame["round_name"] = frame["round_label"]
funded = frame[frame["funded"] == 1]
running = int(funded["status"].isin(RUNNING_STATUSES).sum())
missing = missing_outputs(progress_outputs())
attention = "—" if missing else len(needs_attention(filters.apply(load_tracker())))

columns = st.columns(5, gap="small")
with columns[0]:
    big_number("Proposals", len(frame), "Submitted so far")
with columns[1]:
    big_number("Funded", len(funded), "Received funding")
with columns[2]:
    big_number("Running", running, "Work in progress", page="views/projects.py")
with columns[3]:
    big_number("Needs attention", attention, f"Of the {running} running", page="views/alerts.py")
with columns[4]:
    big_number("Completed", int(funded["status"].isin(FINISHED_STATUSES).sum()), "Final report received")

left, right = st.columns(2, gap="large")
with left:
    st.subheader("From proposal to final report")
    st.caption("Each bar shows how many proposals reached that step. The bars shrink as proposals are "
               "rejected, not funded, or still under way. Click a bar to list its grants.")
    steps = [
        ("Submitted", frame),
        ("Passed first check", frame[frame["assessment"] != "reject"]),
        ("Peer reviewed", frame[frame["n_reviews"] > 0]),
        ("Funded", funded),
        ("Final report received", frame[frame["final_report"] == 1]),
    ]
    chosen = funnel_chart(pd.DataFrame({"step": [name for name, _ in steps],
                                        "count": [len(rows) for _, rows in steps]}), key="funnel")
with right:
    st.subheader("Each funding round")
    st.caption("One bar per round, split by where its proposals ended up. Older rounds should be mostly "
               "completed, recent ones still have running grants. Click a colour to list its grants.")
    cells = status_by_round_chart(frame, key="status_round")

if chosen:
    st.markdown(f"**{chosen[0]}**")
    proposal_table(dict(steps)[chosen[0]], "funnel_table", TABLE_COLUMNS)
if cells:
    cell = cells[0]
    rows = frame
    if "round_name" in cell:
        rows = rows[rows["round_name"] == cell["round_name"]]
    if "status" in cell:
        rows = rows[rows["status"] == cell["status"]]
    st.markdown(f"**{cell.get('round_name', 'All rounds')}, {cell.get('status', 'all statuses')}**")
    proposal_table(rows, "status_table", TABLE_COLUMNS)
