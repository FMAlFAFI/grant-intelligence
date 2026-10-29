import altair as alt
import pandas as pd
import streamlit as st

from dashboard.components.status_badge import status_scale
from ingestion.grant_register import STATUSES

SERIES = "#2a78d6"
MUTED = "#a3a29c"
INK_SECONDARY = "#52514e"
GRID = "#e4e3df"
SEQUENTIAL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]


def styled(chart, height):
    return (chart.properties(height=height)
            .configure_view(strokeWidth=0)
            .configure_axis(gridColor=GRID, domainColor=GRID, tickColor=GRID, labelColor=INK_SECONDARY,
                            titleColor=INK_SECONDARY, labelFontSize=11, titleFontSize=11, labelLimit=260)
            .configure_legend(labelColor=INK_SECONDARY, titleColor=INK_SECONDARY, orient="bottom", columns=3,
                              labelLimit=220))


def picked(event, name):
    if not event:
        return []
    selection = event.get("selection", {}) if isinstance(event, dict) else getattr(event, "selection", {})
    value = selection.get(name) if selection else None
    if isinstance(value, dict):
        value = [value]
    return [row for row in value or [] if row]


def bar_chart(frame, category, count="count", key=None, title=None, total=None, sort="-x", height=None):
    data = frame.copy()
    denominator = total or int(data[count].sum())
    data["label"] = data[count].map(lambda value: f"{int(value)} of {denominator}")
    pick = alt.selection_point(fields=[category], name="pick")
    base = alt.Chart(data).encode(y=alt.Y(f"{category}:N", sort=sort, title=None))
    bars = base.mark_bar(cornerRadiusEnd=4, height={"band": 0.7}).encode(
        x=alt.X(f"{count}:Q", title=title or "Grants", axis=alt.Axis(tickMinStep=1),
                scale=alt.Scale(domain=[0, max(1, data[count].max()) * 1.25])),
        color=alt.condition(pick, alt.value(SERIES), alt.value(MUTED)),
        tooltip=[alt.Tooltip(f"{category}:N", title="Group"), alt.Tooltip("label:N", title="Grants")],
    ).add_params(pick)
    labels = base.mark_text(align="left", dx=4, color=INK_SECONDARY, fontSize=11).encode(
        x=f"{count}:Q", text="label:N")
    chart = styled(bars + labels, height or max(120, 34 * len(data)))
    event = st.altair_chart(chart, key=key, on_select="rerun", width="stretch")
    return [row[category] for row in picked(event, "pick") if category in row]


def funnel_chart(steps, key=None):
    data = steps.copy()
    first = int(data["count"].iloc[0]) or 1
    data["label"] = data["count"].map(lambda value: f"{int(value)} of {first} ({value / first:.0%})")
    order = list(data["step"])
    pick = alt.selection_point(fields=["step"], name="pick")
    base = alt.Chart(data).encode(y=alt.Y("step:N", sort=order, title=None))
    bars = base.mark_bar(cornerRadiusEnd=4, height={"band": 0.7}).encode(
        x=alt.X("count:Q", title="Grants", scale=alt.Scale(domain=[0, first * 1.3])),
        color=alt.condition(pick, alt.value(SERIES), alt.value(MUTED)),
        tooltip=[alt.Tooltip("step:N", title="Step"), alt.Tooltip("label:N", title="Grants")],
    ).add_params(pick)
    labels = base.mark_text(align="left", dx=4, color=INK_SECONDARY, fontSize=11).encode(x="count:Q", text="label:N")
    event = st.altair_chart(styled(bars + labels, 40 * len(data)), key=key, on_select="rerun", width="stretch")
    return [row["step"] for row in picked(event, "pick") if "step" in row]


def status_by_round_chart(frame, key=None):
    data = frame.groupby(["round_name", "status"]).size().reset_index(name="count")
    totals = frame.groupby("round_name").size()
    data["label"] = data.apply(lambda row: f"{row['count']} of {totals[row['round_name']]}", axis=1)
    pick = alt.selection_point(fields=["round_name", "status"], name="pick")
    chart = alt.Chart(data).mark_bar(stroke="#fcfcfb", strokeWidth=2).encode(
        y=alt.Y("round_name:N", title=None, axis=alt.Axis(labelOverlap=False)),
        x=alt.X("count:Q", title="Grants", stack="zero"),
        color=alt.Color("status:N", scale=status_scale(), title="Status"),
        opacity=alt.condition(pick, alt.value(1.0), alt.value(0.35)),
        order=alt.Order("status_rank:Q"),
        tooltip=[alt.Tooltip("round_name:N", title="Round"), alt.Tooltip("status:N", title="Status"),
                 alt.Tooltip("label:N", title="Grants")],
    ).transform_calculate(status_rank=status_rank_expression()).add_params(pick)
    event = st.altair_chart(styled(chart, 48 * len(totals)), key=key, on_select="rerun", width="stretch")
    return picked(event, "pick")


def status_rank_expression():
    cases = " : ".join(f"datum.status === '{status}' ? {rank}" for rank, status in enumerate(STATUSES))
    return f"{cases} : 99"


def heatmap(matrix, key=None):
    data = matrix.reset_index().melt(id_vars=matrix.index.name or "index", var_name="predicted", value_name="count")
    data = data.rename(columns={matrix.index.name or "index": "true"})
    order = list(matrix.index)
    totals = data.groupby("true")["count"].transform("sum")
    data["label"] = data["count"].astype(int).astype(str) + " of " + totals.astype(int).astype(str)
    pick = alt.selection_point(fields=["true", "predicted"], name="pick")
    base = alt.Chart(data).encode(
        x=alt.X("predicted:N", sort=order, title="Priority from the text",
              axis=alt.Axis(labelAngle=-25, labelOverlap=False, labelLimit=200)),
        y=alt.Y("true:N", sort=order, title="True priority"),
    )
    cells = base.mark_rect(stroke="#fcfcfb", strokeWidth=2, cornerRadius=3).encode(
        color=alt.Color("count:Q", scale=alt.Scale(range=SEQUENTIAL[:5]), legend=None),
        opacity=alt.condition(pick, alt.value(1.0), alt.value(0.4)),
        tooltip=[alt.Tooltip("true:N", title="True"), alt.Tooltip("predicted:N", title="Predicted"),
                 alt.Tooltip("label:N", title="Proposals")],
    ).add_params(pick)
    text = base.mark_text(fontSize=12).encode(
        text="count:Q",
        color=alt.condition(alt.datum.count > data["count"].max() / 2, alt.value("#ffffff"), alt.value("#0b0b0b")),
    )
    event = st.altair_chart(styled(cells + text, 320), key=key, on_select="rerun", width="stretch")
    return picked(event, "pick")


def progress_line(history):
    data = history.copy()
    chart = alt.Chart(data).mark_line(point=alt.OverlayMarkDef(size=64, filled=True), strokeWidth=2, color=SERIES).encode(
        x=alt.X("quarter:O", title="Quarter"),
        y=alt.Y("overall_progress:Q", title="Overall progress %", scale=alt.Scale(domain=[0, 100])),
        tooltip=[alt.Tooltip("quarter:O", title="Quarter"),
                 alt.Tooltip("overall_progress:Q", title="Progress %", format=".0f"),
                 alt.Tooltip("current_stage_name:N", title="Stage")],
    )
    st.altair_chart(styled(chart, 220), width="stretch")


def stage_bars(stages):
    data = pd.DataFrame(stages)
    chart = alt.Chart(data).mark_bar(cornerRadiusEnd=4, color=SERIES, height={"band": 0.7}).encode(
        y=alt.Y("stage:N", sort=list(data["stage"]), title=None),
        x=alt.X("percent:Q", title="Completion %", scale=alt.Scale(domain=[0, 100])),
        tooltip=[alt.Tooltip("stage:N", title="Stage"), alt.Tooltip("percent:Q", title="Completion %")],
    )
    st.altair_chart(styled(chart, 30 * len(data)), width="stretch")


def histogram(frame, column, threshold=None, title=None):
    chart = alt.Chart(frame).mark_bar(color=SERIES, cornerRadiusEnd=3).encode(
        x=alt.X(f"{column}:Q", bin=alt.Bin(maxbins=20), title=title or column),
        y=alt.Y("count():Q", title="Grants"),
        tooltip=[alt.Tooltip("count():Q", title="Grants")],
    )
    if threshold is not None:
        rule = alt.Chart(pd.DataFrame({"threshold": [threshold]})).mark_rule(color="#d03b3b", strokeWidth=2).encode(
            x="threshold:Q")
        chart = chart + rule
    st.altair_chart(styled(chart, 240), width="stretch")
