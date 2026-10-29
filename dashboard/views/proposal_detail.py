import pandas as pd
import streamlit as st

from dashboard.components.charts import progress_line, stage_bars
from dashboard.components.notices import guarded
from dashboard.components.proposal_table import COLUMN_LABELS
from dashboard.components.rtl import labelled
from dashboard.components.source_viewer import source_viewer
from dashboard.components.status_badge import badge
from dashboard.components.timeline import timeline
from dashboard.data.adapters import load_drift, load_stalls
from dashboard.data.loaders import load_predictions, load_progress_history, load_register
from ingestion.grant_register import STAGE_COLUMNS, STAGES


def selected_grant(ids):
    wanted = st.query_params.get("grant_id") or st.session_state.get("grant_id") or ids[0]
    index = ids.index(wanted) if wanted in ids else 0
    grant_id = st.selectbox("Grant", ids, index=index, key="detail_grant")
    st.query_params["grant_id"] = grant_id
    st.session_state["grant_id"] = grant_id
    return grant_id


register = load_register()
grant_id = selected_grant(sorted(register["grant_id"]))
grant = register.set_index("grant_id").loc[grant_id]
history = load_progress_history()
history = history[history["grant_id"] == grant_id].sort_values("quarter")

st.title(grant_id)
badge(grant["status"])

columns = st.columns(4)
with columns[0]:
    labelled("Funding round", f"Round {grant['round']} ({grant['year']})")
    labelled("Language", grant["lang"])
with columns[1]:
    labelled("College", grant["college"])
    labelled("Department", grant["department"])
with columns[2]:
    labelled("Project type", grant["type"])
    labelled("Planned duration", f"{grant['planned_months']:.0f} months")
with columns[3]:
    labelled("Requested budget", f"{grant['budget']:,.0f} SAR")
    if grant["funded"]:
        labelled("Budget spent", f"{grant['budget_spent']:,.0f} SAR ({grant['spent_share']:.0%})")

st.subheader("Lifecycle")
left, right = st.columns([3, 2], gap="large")
with left:
    timeline(grant, history)
with right:
    if history.empty:
        st.caption("No quarterly report: the grant was not funded.")
    else:
        progress_line(history)
        last = history.iloc[-1]
        st.caption(f"Stages in the last report (quarter {int(last['quarter'])})")
        stage_bars([{"stage": name, "percent": last[column]} for name, column in zip(STAGES, STAGE_COLUMNS)])

st.subheader("Priority")
predictions = guarded(load_predictions, "embedding", "standard")
if predictions is not None:
    row = predictions[predictions["grant_id"] == grant_id]
    if row.empty:
        st.caption("Not classified.")
    else:
        row = row.iloc[0]
        columns = st.columns(4)
        with columns[0]:
            labelled("Claimed priority", row["claimed_priority"])
        with columns[1]:
            labelled("Priority from the text", row["predicted_priority"])
        with columns[2]:
            labelled("Similarity", f"{row['similarity']:.3f}")
        with columns[3]:
            labelled("Margin to runner up", f"{row['margin']:.3f}")
        if row["claimed_priority"] != row["predicted_priority"]:
            st.warning(f"The claimed priority differs from the text. Runner up: {row.get('runner_up', '')}",
                       icon=":material/rule:")

st.subheader("Drift and stalls")
columns = st.columns(2)
for column, output, label in ((columns[0], load_drift(), "Drift"), (columns[1], load_stalls(), "Stall detection")):
    with column:
        if not output.ready:
            st.caption(f"{label}: not finished yet ({output.owner}).")
            continue
        match = output.frame[output.frame["grant_id"] == grant_id]
        if match.empty:
            st.caption(f"{label}: no row for this grant.")
        else:
            row = match.iloc[0].drop(labels=["grant_id"])
            st.dataframe(pd.DataFrame({"Field": [COLUMN_LABELS.get(name, name) for name in row.index],
                                       "Value": row.values}), hide_index=True, width="stretch")

st.subheader("Source Word files")
source_viewer(grant_id)
