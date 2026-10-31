import streamlit as st

from dashboard.components.charts import plan_chart
from dashboard.components.notices import guarded, missing_outputs
from dashboard.components.rtl import labelled
from dashboard.components.source_viewer import source_viewer
from dashboard.components.status_badge import badge
from dashboard.components.timeline import timeline
from dashboard.data.adapters import load_extensions, load_slip, load_stalls, load_tracker, progress_outputs
from dashboard.data.health import HEALTH_COLORS, ON_TRACK, extension_sentence, stage_label, stage_plan
from dashboard.data.loaders import load_predictions, load_progress_history, load_register


def selected_grant(ids):
    wanted = st.query_params.get("grant_id") or st.session_state.get("grant_id") or ids[0]
    index = ids.index(wanted) if wanted in ids else 0
    grant_id = st.selectbox("Choose a grant", ids, index=index, key="detail_grant")
    st.query_params["grant_id"] = grant_id
    st.session_state["grant_id"] = grant_id
    return grant_id


register = load_register()
missing = missing_outputs(progress_outputs())
tracker = load_tracker().set_index("grant_id")
ids = sorted(register["grant_id"], key=lambda value: (value not in tracker.index, value))
grant_id = selected_grant(ids)
grant = register.set_index("grant_id").loc[grant_id].copy()
grant["grant_id"] = grant_id

st.title(grant_id)
st.markdown(f"**{grant['title']}**")
with st.container(horizontal=True):
    badge(grant["status"])
    if grant_id in tracker.index and not missing:
        health = tracker.loc[grant_id, "health"]
        st.badge(health, color=HEALTH_COLORS[health])

columns = st.columns(3)
with columns[0]:
    labelled("Funding round", grant["round_label"])
with columns[1]:
    labelled("College", grant["college"])
with columns[2]:
    labelled("Planned length", f"{grant['planned_months']:.0f} months")

if not grant["funded"]:
    st.info("This proposal was not funded, so there is no progress to follow.", icon=":material/info:")
elif not missing:
    info = tracker.loc[grant_id]
    if info["health"] != ON_TRACK:
        st.warning(f"{info['reason']}.", icon=":material/flag:")

    columns = st.columns(3)
    with columns[0]:
        labelled("Done", f"{info['overall_progress']:.0f}%")
    with columns[1]:
        labelled("Current stage", info["current_stage_name"])
    with columns[2]:
        labelled("Time used", info["months"])

    st.subheader("Plan against reality")
    st.caption("Empty circle: when the stage should end. Blue dot: when it really ended. "
               "The line shows the gap. Counted in quarters, because reports come every three months.")
    plan = stage_plan(load_slip().frame, grant_id)
    if plan.empty:
        st.caption("No timetable found for this grant.")
    else:
        plan_chart(plan)
        st.dataframe(plan[["stage_name", "result"]], hide_index=True, width="stretch",
                     column_config={"stage_name": "Stage", "result": "Result"})

    st.subheader("Stages that stopped moving")
    stalls = load_stalls().frame
    stalls = stalls[stalls["grant_id"] == grant_id]
    if stalls.empty:
        st.caption("None. Every stage kept moving from one report to the next.")
    for row in stalls.itertuples():
        ending = "and is still stuck" if row.ongoing else f"until quarter {row.end_quarter}"
        st.markdown(f"- {stage_label(row.stage)} stayed at {row.to_pct:.0f}% from quarter {row.start_quarter} {ending}.")

    st.subheader("Extension check")
    st.write(extension_sentence(load_extensions().frame, grant))

    with st.expander("Full history"):
        history = load_progress_history()
        timeline(grant, history[history["grant_id"] == grant_id].sort_values("quarter"))

predictions = guarded(load_predictions, "embedding", "standard")
if predictions is not None:
    row = predictions[predictions["grant_id"] == grant_id]
    if not row.empty:
        row = row.iloc[0]
        st.subheader("Research priority")
        st.write(f"Claimed: {row['claimed_priority']}. Found in the text: {row['predicted_priority']}.")

st.subheader("Documents")
source_viewer(grant_id)
