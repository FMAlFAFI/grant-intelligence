import pandas as pd
import streamlit as st

from dashboard.components.charts import heatmap
from dashboard.components.kpi import tile, tile_row, value_tile
from dashboard.components.notices import guarded, page_help
from dashboard.components.proposal_table import proposal_table
from dashboard.data.loaders import (
    PRIORITY_ORDER, load_claim_disagreements, load_metrics, load_predictions, macro_f1,
)

METHODS = {"Qwen3 embeddings": "embedding", "Keyword baseline": "keyword"}
DATASETS = {"Standard set": "standard", "Hard set": "hard"}
SUBSETS = {"Both languages": "all", "Arabic": "ar", "English": "en"}
TABLE_COLUMNS = ["grant_id", "lang", "claimed_priority", "predicted_priority", "content_priority",
                 "similarity", "margin"]

st.title("Priority check")
page_help("Does each proposal really match the priority it claims? The classifier reads the text and picks a priority. "
          "The first numbers show how reliable it is, the list at the end shows the proposals to check by hand.")

left, middle, right = st.columns(3)
method = METHODS[left.selectbox("Method", list(METHODS), key="priority_method")]
dataset = DATASETS[middle.selectbox("Proposal set", list(DATASETS), key="priority_dataset")]
subset = SUBSETS[right.selectbox("Language", list(SUBSETS), key="priority_subset")]
if dataset == "hard":
    st.info("The hard set reuses the grant ids with rewritten texts (data/synthetic/hard). "
            "Opening a record shows the standard forms.", icon=":material/info:")

metrics = guarded(load_metrics, method, dataset)
predictions = guarded(load_predictions, method, dataset)
disagreements = guarded(load_claim_disagreements, method, dataset)
if metrics is None or predictions is None or disagreements is None:
    st.stop()

filters = st.session_state["filters"]
predictions = filters.apply(predictions)
disagreements = filters.apply(disagreements)
if subset != "all":
    predictions = predictions[predictions["lang"] == subset]
    disagreements = disagreements[disagreements["lang"] == subset]

columns = tile_row(3)
with columns[0]:
    value_tile("Macro-F1", f"{macro_f1(metrics, subset):.2f}", "over all proposals of this set, filters not applied")
with columns[1]:
    correct = int((predictions["predicted_priority"] == predictions["content_priority"]).sum())
    tile("Correct priority", correct, len(predictions))
with columns[2]:
    tile("Claim differs from the text", len(disagreements), len(predictions))

st.subheader("F1 per priority")
rows = metrics[metrics["subset"] == subset].set_index("priority").reindex(PRIORITY_ORDER).reset_index()
scores = {name: st.column_config.ProgressColumn("F1" if name == "f1" else name.capitalize(),
                                               min_value=0, max_value=1, format="%.2f")
          for name in ("precision", "recall", "f1")}
st.dataframe(rows[["priority", "support", "precision", "recall", "f1"]], hide_index=True, width="stretch",
             column_config={"priority": "Priority", "support": "Proposals", **scores})

st.subheader("Confusion matrix")
st.caption("Rows are the true priority, columns what the classifier read in the text. Select a cell to list it.")
labels = PRIORITY_ORDER + sorted(set(predictions["predicted_priority"]) - set(PRIORITY_ORDER))
matrix = pd.crosstab(predictions["content_priority"], predictions["predicted_priority"])
matrix = matrix.reindex(index=PRIORITY_ORDER, columns=labels, fill_value=0)
matrix.index.name = "true"
cells = heatmap(matrix, key=f"confusion_{method}_{dataset}_{subset}")
if cells and "true" in cells[0]:
    cell = cells[0]
    rows = predictions[(predictions["content_priority"] == cell["true"]) &
                       (predictions["predicted_priority"] == cell["predicted"])]
    st.markdown(f"**True {cell['true']}, read as {cell['predicted']}**")
    proposal_table(rows, "confusion_table", TABLE_COLUMNS)

st.subheader("Claimed priority differs from the text")
st.caption("Sorted by margin: a small margin means the classifier hesitated between two priorities.")
proposal_table(disagreements.sort_values("margin"), "claims_table",
               ["grant_id", "lang", "claimed_priority", "predicted_priority", "runner_up", "similarity", "margin"])
