import pandas as pd
import streamlit as st

from dashboard.components.charts import bar_chart
from dashboard.components.kpi import tile, tile_row
from dashboard.components.notices import pending_panel
from dashboard.components.proposal_table import proposal_table
from dashboard.data.adapters import load_stalls
from dashboard.data.loaders import load_register
from ingestion.grant_register import OVERDUE, RUNNING, STAGES

WILL_SHOW = [
    "How many grants are stalled, out of the funded ones",
    "The portfolio bottleneck: stalled grants per stage, each bar opening its list",
    "Slip against each proposal's own timetable",
]
TABLE_COLUMNS = ["grant_id", "year", "college", "status", "current_stage_name", "overall_progress", "reports"]


def stage_counts(frame, column):
    names = frame[column].map(lambda number: f"{int(number)}. {STAGES[int(number) - 1]}")
    counts = names.value_counts().reindex([f"{i}. {name}" for i, name in enumerate(STAGES, 1)], fill_value=0)
    return names, counts.rename_axis("stage").reset_index(name="count")


st.title("Stalls")
st.caption("Where do projects get stuck? Stall detection over the quarterly progress reports.")

register = st.session_state["filters"].apply(load_register()).copy()
register["reports"] = register["reports_received"].astype(str) + " / " + register["reports_planned"].astype(str)
stalls = load_stalls()

if stalls.ready:
    frame = st.session_state["filters"].apply(stalls.frame).merge(register, on="grant_id", how="left")
    alerts = frame[frame["alert"] == 1]
    columns = tile_row(2)
    with columns[0]:
        tile("Stall alerts", len(alerts), len(frame))
    with columns[1]:
        tile("Median quarters stuck", int(alerts["stall_quarters"].median() or 0), len(alerts), "among alerts")
    names, counts = stage_counts(alerts, "stall_stage")
    chosen = bar_chart(counts, "stage", key="stall_stages", total=len(alerts), sort=None)
    rows = alerts[names.isin(chosen)] if chosen else alerts
    proposal_table(rows, "stall_table", TABLE_COLUMNS + ["stall_stage", "stall_quarters", "slip_months"])
else:
    pending_panel(stalls, "Stall detection", WILL_SHOW)

st.subheader("Available now: current stage of running grants")
st.caption("From the latest quarterly report of each grant (grant register). This is not stall detection.")
running = register[register["status"].isin([RUNNING, OVERDUE])]
if running.empty:
    st.info("No running grants in this view.")
else:
    names, counts = stage_counts(running, "current_stage")
    chosen = bar_chart(counts, "stage", key="running_stages", total=len(running), sort=None)
    rows = running[names.isin(chosen)] if chosen else running
    proposal_table(rows, "running_table", TABLE_COLUMNS)
