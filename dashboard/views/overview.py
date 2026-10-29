import pandas as pd
import streamlit as st

from dashboard.components.kpi import pending_tile, tile, tile_row, value_tile
from dashboard.components.notices import guarded
from dashboard.data.adapters import load_drift, load_stalls, load_timetables, load_trajectories
from dashboard.data.loaders import load_claim_disagreements, load_metrics, load_predictions, load_register, macro_f1
from dashboard.data.progress import DONE_LATE, OPEN_LATE, plan_vs_actual

st.title("Overview")
st.caption("One line per question of the brief. Every number shows its denominator.")

filters = st.session_state["filters"]
register = filters.apply(load_register())
drift = load_drift()
stalls = load_stalls()
trajectories = load_trajectories()
timetables = load_timetables()

columns = tile_row(3)
with columns[0]:
    tile("Funded grants", int(register["funded"].sum()), len(register), page="views/projects.py")
predictions = guarded(load_predictions, "embedding", "standard")
disagreements = guarded(load_claim_disagreements, "embedding", "standard")
with columns[1]:
    if predictions is not None and disagreements is not None:
        shown = filters.apply(predictions)
        tile("Claimed priority differs from the text", len(filters.apply(disagreements)), len(shown),
             page="views/priority_check.py")
with columns[2]:
    standard = guarded(load_metrics, "embedding", "standard")
    hard = guarded(load_metrics, "embedding", "hard")
    if standard is not None and hard is not None:
        value_tile("Priority classifier macro-F1", f"{macro_f1(standard):.2f} / {macro_f1(hard):.2f}",
                   "standard / hard set, Qwen3 embeddings, all proposals", page="views/priority_check.py")

columns = tile_row(3)
with columns[0]:
    if drift.ready:
        flagged = filters.apply(drift.frame)
        tile("Drift from proposal to papers", int(flagged["drift_flag"].sum()), len(flagged), page="views/drift.py")
    else:
        pending_tile("Drift from proposal to papers", drift.owner, page="views/drift.py")
with columns[1]:
    if stalls.ready:
        alerts = filters.apply(stalls.frame)
        tile("Stall alerts", int(alerts["alert"].sum()), len(alerts), page="views/stalls.py")
    elif trajectories.ready and timetables.ready:
        stages = filters.apply(plan_vs_actual(trajectories.frame, timetables.frame))
        late = stages.loc[stages["state"].isin([DONE_LATE, OPEN_LATE]), "grant_id"].nunique()
        tile("Grants with a stage late against plan", late, stages["grant_id"].nunique(),
             "stall alerts not finished yet", page="views/stalls.py")
    else:
        pending_tile("Stall alerts", stalls.owner, page="views/stalls.py")
with columns[2]:
    reviewed = register[register["n_reviews"] > 0]
    value_tile("Mean review total", f"{reviewed['mean_review_total'].mean():.1f} / 100",
               f"over {len(reviewed)} reviewed proposals")

st.subheader("Team modules")
modules = pd.DataFrame([
    {"Module": "Grant register and project tracking", "Owner": "Member A", "State": "Ready", "Missing": ""},
    {"Module": "Priority classification and portfolio", "Owner": "Member A",
     "State": "Ready" if predictions is not None else "Not run", "Missing": ""},
    {"Module": "Progress trajectories", "Owner": trajectories.owner,
     "State": "Ready" if trajectories.ready else "Not run", "Missing": "; ".join(trajectories.missing[:1])},
    {"Module": "Planned timetables", "Owner": timetables.owner,
     "State": "Ready" if timetables.ready else "Not run", "Missing": "; ".join(timetables.missing[:1])},
    {"Module": "Proposal to output drift", "Owner": drift.owner,
     "State": "Ready" if drift.ready else "Not finished", "Missing": "; ".join(drift.missing[:1])},
    {"Module": "Stall detection", "Owner": stalls.owner,
     "State": "Ready" if stalls.ready else "Not finished", "Missing": "; ".join(stalls.missing[:1])},
])
st.dataframe(modules, hide_index=True, width="stretch")
