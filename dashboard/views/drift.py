import streamlit as st

from dashboard.components.charts import histogram
from dashboard.components.kpi import tile, tile_row
from dashboard.components.proposal_table import proposal_table
from dashboard.data.adapters import load_drift
from dashboard.data.loaders import load_register

st.title("Proposal to output drift")
st.caption("Did we fund what was proposed? Compares the proposal with the papers it produced.")

drift = load_drift()
if not drift.ready:
    st.info(f"{drift.owner} has not delivered the drift results yet, so there is nothing on main to show.",
            title="Not available yet", icon=":material/hourglass_top:")
    st.stop()

register = load_register()[["grant_id", "year", "lang", "college", "status"]]
frame = st.session_state["filters"].apply(drift.frame).merge(register, on="grant_id", how="left")
columns = tile_row(2)
with columns[0]:
    tile("Drifted grants", int(frame["drift_flag"].sum()), len(frame))
with columns[1]:
    tile("Grants with papers", int((frame["n_papers"] > 0).sum()), len(frame))
histogram(frame, "similarity", threshold=frame["threshold"].iloc[0] if len(frame) else None,
          title="Proposal to paper similarity")
proposal_table(frame[frame["drift_flag"] == 1].sort_values("similarity"), "drift_table",
               ["grant_id", "year", "lang", "college", "status", "similarity", "n_papers"])
