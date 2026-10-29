import pandas as pd
import streamlit as st

from dashboard.components.charts import funnel_chart, status_by_round_chart
from dashboard.components.kpi import tile, tile_row
from dashboard.components.proposal_table import proposal_table
from dashboard.data.loaders import load_register
from ingestion.grant_register import COMPLETED, COMPLETED_LATE, OVERDUE, RUNNING, STATUSES

TABLE_COLUMNS = ["grant_id", "year", "lang", "college", "type", "assessment", "mean_review_total", "funded",
                 "status", "current_stage_name", "overall_progress", "reports", "spent_share"]


def with_display_columns(frame):
    frame = frame.copy()
    frame["round_name"] = frame.apply(lambda row: f"Round {row['round']} ({row['year']})", axis=1)
    frame["reports"] = frame.apply(
        lambda row: f"{row['reports_received']} / {row['reports_planned']}" if row["funded"] else "", axis=1)
    return frame


def funnel_steps(frame):
    steps = [
        ("Submitted", frame),
        ("Passed initial assessment", frame[frame["assessment"] != "reject"]),
        ("Peer reviewed", frame[frame["n_reviews"] > 0]),
        ("Funded", frame[frame["funded"] == 1]),
        ("Final report received", frame[frame["final_report"] == 1]),
    ]
    return steps


st.title("Project tracking")
st.caption("Where each grant stands, from submission to the final report. "
           "Read from the Word forms by ingestion/grant_register.py.")

frame = with_display_columns(st.session_state["filters"].apply(load_register()))
funded = frame[frame["funded"] == 1]

columns = tile_row(5)
with columns[0]:
    tile("Submitted", len(frame), len(frame), "proposals in view")
with columns[1]:
    tile("Funded", len(funded), len(frame), None)
with columns[2]:
    running = funded["status"].isin([RUNNING, OVERDUE]).sum()
    tile("Still running", int(running), len(funded), f"of {len(funded)} funded")
with columns[3]:
    done = funded["status"].isin([COMPLETED, COMPLETED_LATE]).sum()
    tile("Completed", int(done), len(funded), f"of {len(funded)} funded")
with columns[4]:
    tile("Extended", int(funded["extended"].sum()), len(funded), f"of {len(funded)} funded")

left, right = st.columns(2, gap="large")
with left:
    st.subheader("From submission to final report")
    steps = funnel_steps(frame)
    chosen = funnel_chart(pd.DataFrame({"step": [name for name, _ in steps],
                                        "count": [len(rows) for _, rows in steps]}), key="funnel")
with right:
    st.subheader("Status by funding round")
    cells = status_by_round_chart(frame, key="status_round")

if chosen:
    rows = dict(steps)[chosen[0]]
    st.markdown(f"**{chosen[0]}**")
    proposal_table(rows, "funnel_table", TABLE_COLUMNS)
if cells:
    cell = cells[0]
    rows = frame
    if "round_name" in cell:
        rows = rows[rows["round_name"] == cell["round_name"]]
    if "status" in cell:
        rows = rows[rows["status"] == cell["status"]]
    st.markdown(f"**{cell.get('round_name', 'All rounds')}, {cell.get('status', 'all statuses')}**")
    proposal_table(rows, "status_table", TABLE_COLUMNS)

st.subheader("All grants")
statuses = st.multiselect("Status", STATUSES, default=[], placeholder="All statuses", key="status_filter")
rows = frame[frame["status"].isin(statuses)] if statuses else frame
proposal_table(rows.sort_values(["year", "grant_id"]), "all_table", TABLE_COLUMNS)
