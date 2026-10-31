import pandas as pd
import streamlit as st

from dashboard.components.charts import bar_chart
from dashboard.components.notices import guarded, page_help
from dashboard.components.proposal_table import proposal_table
from dashboard.data.loaders import PRIORITY_ORDER, load_proposals

DIMENSIONS = {
    "Priority from the text": "predicted_priority",
    "Claimed priority": "claimed_priority",
    "Funding round": "round",
    "College": "college",
    "Department": "department",
    "Project type": "type",
}
TABLE_COLUMNS = ["grant_id", "round", "lang", "college", "department", "type", "claimed_priority",
                 "predicted_priority", "funded"]

st.title("Portfolio map")
page_help("What the proposals are about. Choose how to group them, each bar shows how many proposals fall in that "
          "group. Click a bar to list them.")

proposals = guarded(load_proposals)
if proposals is None:
    st.stop()
frame = st.session_state["filters"].apply(proposals)

label = st.segmented_control("Group by", list(DIMENSIONS), default="Priority from the text", key="portfolio_dim")
column = DIMENSIONS[label or "Priority from the text"]
counts = frame.groupby(column).agg(count=("grant_id", "count"), funded=("funded", "sum")).reset_index()
sort = "ascending" if column == "round" else "-x"
chosen = bar_chart(counts, column, key=f"portfolio_{column}", total=len(frame), sort=sort)
if chosen:
    rows = frame[frame[column].isin(chosen)]
    st.markdown(f"**{label}: {', '.join(map(str, chosen))}**")
    proposal_table(rows, f"portfolio_table_{column}", TABLE_COLUMNS)

st.subheader("Priority from the text by funding round")
table = pd.crosstab(frame["predicted_priority"], frame["round"], margins=True, margins_name="Total")
order = [priority for priority in PRIORITY_ORDER if priority in table.index]
order += [value for value in table.index if value not in order and value != "Total"] + ["Total"]
st.dataframe(table.reindex(order), width="stretch")
