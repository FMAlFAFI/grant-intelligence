import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from dashboard.components.filters import sidebar_filters
from dashboard.components.notices import guarded
from dashboard.components.rtl import inject_css
from dashboard.data.adapters import load_drift
from dashboard.data.loaders import load_register


def section_title(title, output):
    return title if output.ready else f"{title} (not available yet)"


st.set_page_config(page_title="Grant Intelligence", page_icon=":material/insights:", layout="wide")
inject_css()

drift = load_drift()
pages = {
    "Follow-up": [
        st.Page("views/glance.py", title="Portfolio at a glance", icon=":material/dashboard:", default=True),
        st.Page("views/projects.py", title="Projects", icon=":material/assignment:"),
        st.Page("views/project_file.py", title="Project file", icon=":material/description:"),
        st.Page("views/alerts.py", title="Alerts", icon=":material/notifications:"),
    ],
    "Analysis": [
        st.Page("views/portfolio.py", title="Portfolio map", icon=":material/bar_chart:"),
        st.Page("views/priority_check.py", title="Priority check", icon=":material/rule:"),
        st.Page("views/drift.py", title=section_title("Drift", drift), icon=":material/compare_arrows:"),
    ],
}
navigation = st.navigation(pages)

register = guarded(load_register)
if register is None:
    st.stop()
st.session_state["filters"] = sidebar_filters(register)
navigation.run()
