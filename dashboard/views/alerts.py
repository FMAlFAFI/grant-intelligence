import streamlit as st

from dashboard.components.notices import missing_outputs
from dashboard.components.proposal_table import open_detail
from dashboard.data.adapters import load_extensions, load_tracker, progress_outputs
from dashboard.data.health import HEALTH_LABELS, LATE, WATCH, needs_attention, warning_record

st.title("Alerts")
st.caption("Running grants someone should check on, and why.")

if missing_outputs(progress_outputs()):
    st.stop()

alerts = needs_attention(st.session_state["filters"].apply(load_tracker()))
if alerts.empty:
    st.success("No running grant needs attention right now.", icon=":material/check_circle:")
    st.stop()

columns = st.columns(2, gap="small")
columns[0].metric(HEALTH_LABELS[LATE], int((alerts["health"] == LATE).sum()))
columns[1].metric(HEALTH_LABELS[WATCH], int((alerts["health"] == WATCH).sum()))

for row in alerts.itertuples():
    with st.container(border=True):
        text, action = st.columns([5, 1], vertical_alignment="center")
        with text:
            st.markdown(f"{row.health_label} · **{row.grant_id}** · {row.college}")
            st.markdown(f"{row.reason}.")
        with action:
            if st.button("Open", key=f"alert_{row.grant_id}", width="stretch"):
                open_detail(row.grant_id)

record = warning_record(load_extensions().frame)
st.caption(f"How far to trust these signals: on finished grants, a stalled stage warned of {record['warned']} of the "
           f"{record['extended']} grants that later needed an extension, with {record['false_alarms']} false alarm(s) "
           f"on the {record['on_time']} that finished on time. An alert is a reason to talk to the team, nothing more.")
