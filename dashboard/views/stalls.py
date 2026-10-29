import streamlit as st

from dashboard.components.charts import bar_chart, stacked_states
from dashboard.components.kpi import tile, tile_row
from dashboard.components.notices import guarded, pending_panel
from dashboard.components.proposal_table import proposal_table
from dashboard.data.adapters import load_stalls, load_timetables, load_trajectories
from dashboard.data.loaders import load_progress_history, load_register
from dashboard.data.progress import (
    DONE_LATE, DONE_ON_PLAN, OPEN_LATE, OPEN_ON_PLAN, STAGE_NAMES, agreement_with_register, plan_vs_actual,
)
from ingestion.grant_register import OVERDUE, RUNNING, STAGES

WILL_SHOW = [
    "How many grants are stalled, out of the funded ones",
    "Stalled grants per stage, each bar opening its list",
    "Retrospective extension prediction: detection rate, false positives, lead time",
]
TABLE_COLUMNS = ["grant_id", "year", "college", "status", "current_stage_name", "overall_progress", "reports"]
STATE_COLORS = {DONE_ON_PLAN: "#0ca30c", DONE_LATE: "#ec835a", OPEN_LATE: "#d03b3b", OPEN_ON_PLAN: "#2a78d6"}
STAGE_ORDER = [f"{number}. {name}" for number, name in enumerate(STAGE_NAMES, start=1)]


def stage_counts(frame, column):
    names = frame[column].map(lambda number: f"{int(number)}. {STAGES[int(number) - 1]}")
    counts = names.value_counts().reindex([f"{i}. {name}" for i, name in enumerate(STAGES, 1)], fill_value=0)
    return names, counts.rename_axis("stage").reset_index(name="count")


def plan_section(filters, register):
    trajectories = load_trajectories()
    timetables = load_timetables()
    for output, title in ((trajectories, "Progress trajectories"), (timetables, "Planned timetables")):
        if not output.ready:
            pending_panel(output, title, ["Each stage compared with the proposal's own timetable"])
            return
    st.subheader("Progress against each proposal's timetable")
    st.caption("From Member C's files: the stage percentages of every quarterly report "
               "(app/progress/progress_trajectories.py) and the timetable of every proposal (inspect_proposals.py). "
               "Reports are quarterly, so a stage is compared with the quarter in which the timetable ends it.")
    stages = filters.apply(plan_vs_actual(trajectories.frame, timetables.frame))
    stages = stages.merge(register[["grant_id", "year", "college", "status"]], on="grant_id", how="left")
    finished = stages[stages["done_quarter"].notna()]
    late_grants = stages.loc[stages["state"].isin([DONE_LATE, OPEN_LATE]), "grant_id"].nunique()
    columns = tile_row(3)
    with columns[0]:
        tile("Stages finished late", int((finished["state"] == DONE_LATE).sum()), len(finished),
             f"of {len(finished)} finished stages")
    with columns[1]:
        open_stages = stages[stages["done_quarter"].isna()]
        tile("Open stages past their planned end", int((open_stages["state"] == OPEN_LATE).sum()), len(open_stages),
             f"of {len(open_stages)} unfinished stages")
    with columns[2]:
        tile("Grants with at least one late stage", late_grants, stages["grant_id"].nunique(),
             "of the funded grants with a timetable")

    cells = stacked_states(stages, "stage_name", "state", STAGE_ORDER, STATE_COLORS, key="plan_states",
                           title="Funded grants")
    if cells:
        cell = cells[0]
        rows = stages
        if "stage_name" in cell:
            rows = rows[rows["stage_name"] == cell["stage_name"]]
        if "state" in cell:
            rows = rows[rows["state"] == cell["state"]]
        st.markdown(f"**{cell.get('stage_name', 'All stages')}, {cell.get('state', 'all states')}**")
        proposal_table(rows.sort_values("slip_quarters", ascending=False), "plan_table",
                       ["grant_id", "year", "college", "status", "stage_name", "planned_quarter", "done_quarter",
                        "slip_quarters", "percent_now"])

    history = guarded(load_progress_history)
    if history is not None:
        agree, total = agreement_with_register(trajectories.frame, history)
        st.caption(f"Cross-check: Member C's trajectories and the grant register give the same eight "
                   f"percentages for {agree} of {total} quarterly reports.")


st.title("Progress and stalls")
st.caption("Where do projects get stuck? Stage 5 of the brief: trajectories, slip against the timetable, stalls.")

filters = st.session_state["filters"]
register = filters.apply(load_register()).copy()
register["reports"] = register["reports_received"].astype(str) + " / " + register["reports_planned"].astype(str)

plan_section(filters, register)

stalls = load_stalls()
if stalls.ready:
    st.subheader("Stall alerts")
    frame = filters.apply(stalls.frame).merge(register, on="grant_id", how="left")
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

st.subheader("Current stage of running grants")
st.caption("From the latest quarterly report of each grant (grant register).")
running = register[register["status"].isin([RUNNING, OVERDUE])]
if running.empty:
    st.info("No running grants in this view.")
else:
    names, counts = stage_counts(running, "current_stage")
    chosen = bar_chart(counts, "stage", key="running_stages", total=len(running), sort=None)
    rows = running[names.isin(chosen)] if chosen else running
    proposal_table(rows, "running_table", TABLE_COLUMNS)
