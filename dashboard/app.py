import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from dashboard.components.filters import sidebar_filters
from dashboard.components.notices import guarded
from dashboard.components.rtl import inject_css
from dashboard.data.adapters import load_drift, load_stalls
from dashboard.data.loaders import load_register


def section_title(title, output):
    return title if output.ready else f"{title} (not finished)"


st.set_page_config(page_title="Grant Intelligence", page_icon=":material/insights:", layout="wide")
inject_css()

drift = load_drift()
stalls = load_stalls()
pages = {
    "Projects": [
        st.Page("views/projects.py", title="Project tracking", icon=":material/assignment:", default=True),
        st.Page("views/overview.py", title="Overview", icon=":material/dashboard:"),
    ],
    "Analysis": [
        st.Page("views/portfolio.py", title="Portfolio", icon=":material/bar_chart:"),
        st.Page("views/priority_check.py", title="Priority check", icon=":material/rule:"),
        st.Page("views/drift.py", title=section_title("Drift", drift), icon=":material/compare_arrows:"),
        st.Page("views/stalls.py", title=section_title("Stalls", stalls), icon=":material/report:"),
    ],
    "Records": [
        st.Page("views/proposal_detail.py", title="Proposal record", icon=":material/description:"),
    ],
}
navigation = st.navigation(pages)

register = guarded(load_register)
if register is None:
    st.stop()
st.session_state["filters"] = sidebar_filters(register)
navigation.run()
