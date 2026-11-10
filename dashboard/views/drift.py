import streamlit as st

from app.drift.drift_calculator import CLASSES, FRAMING, LINKAGE
from app.drift.threshold_calibration import load_thresholds
from app.statistics.confidence_intervals import rate
from dashboard.components.charts import histogram
from dashboard.components.kpi import tile, tile_row
from dashboard.components.notices import page_help
from dashboard.components.proposal_table import proposal_table
from dashboard.data.adapters import load_drift
from dashboard.data.loaders import load_register

st.title("Proposal to output distance")
page_help("How far are the published papers from what each grant proposed? A distance is a measurement, "
          "not a judgement about the work or the researcher.")

drift = load_drift()
if not drift.ready:
    st.info(f"{drift.owner} has not delivered the drift results yet, so there is nothing on main to show.",
            title="Not available yet", icon=":material/hourglass_top:")
    st.stop()

thresholds = load_thresholds()["abstract"]
register = load_register()[["grant_id", "year", "lang", "college", "status"]]
frame = st.session_state["filters"].apply(drift.frame).merge(register, on="grant_id", how="left")
measured = frame[frame["n_papers"] > 0]

st.info(FRAMING)
st.caption(LINKAGE.format(papers=int(frame["n_papers"].sum())))
st.caption(f"Cut-offs calibrated on labelled sets (docs/drift-calibration.md). Agreement with the labels on held-out "
           f"sets: kappa {thresholds['held_out_kappa']:.2f}, 95% CI {thresholds['held_out_kappa_ci'][0]:.2f} to "
           f"{thresholds['held_out_kappa_ci'][1]:.2f}. That is weak, so a class is a prompt to look, not a result.")

columns = tile_row(4)
with columns[0]:
    tile("Completed grants with papers", len(measured), len(frame))
for column, name in zip(columns[1:], CLASSES):
    with column:
        tile(f"Measured {name}", int((measured["alignment"] == name).sum()), len(measured))

st.subheader("By language pairing")
st.caption("An Arabic proposal compared with an English paper scores lower than a same-language pair at the same "
           "alignment, so the two are never mixed.")
for pairing, group in measured.groupby("pairing"):
    st.markdown(f"**{pairing}** ({len(group)} grants): " + "; ".join(
        f"{name} {rate(int((group['alignment'] == name).sum()), len(group))}" for name in CLASSES))

histogram(measured, "similarity", threshold=thresholds["distant_cut"], title="Similarity of papers to the proposal abstract")
st.subheader("Grants measured as distant")
st.caption("Distance measured. Select a line to open the project file and read the proposal and the papers.")
proposal_table(measured[measured["drift_flag"] == 1].sort_values("similarity"), "drift_table",
               ["grant_id", "year", "lang", "college", "status", "pairing", "similarity", "n_papers", "n_distant"])
