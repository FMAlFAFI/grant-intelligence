import altair as alt
import streamlit as st

from ingestion.grant_register import COMPLETED, COMPLETED_LATE, NOT_FUNDED, OVERDUE, REJECTED, RUNNING, STATUSES

CHART_COLORS = {
    REJECTED: "#a3a29c",
    NOT_FUNDED: "#6b6a65",
    RUNNING: "#2a78d6",
    OVERDUE: "#fab219",
    COMPLETED: "#0ca30c",
    COMPLETED_LATE: "#6250d6",
}
BADGES = {
    REJECTED: ("gray", ":material/block:"),
    NOT_FUNDED: ("gray", ":material/money_off:"),
    RUNNING: ("blue", ":material/autorenew:"),
    OVERDUE: ("orange", ":material/schedule:"),
    COMPLETED: ("green", ":material/check_circle:"),
    COMPLETED_LATE: ("violet", ":material/event_repeat:"),
}


def status_scale():
    return alt.Scale(domain=STATUSES, range=[CHART_COLORS[status] for status in STATUSES])


def badge(status):
    color, icon = BADGES.get(status, ("gray", None))
    st.badge(status, color=color, icon=icon)
