import pandas as pd
import streamlit as st

from ingestion.grant_register import STAGES


def present(value):
    return value is not None and not pd.isna(value)


def build_events(grant, history):
    year = int(grant["year"])
    events = [("Submitted", f"Round {int(grant['round'])} ({year}) proposal received")]
    if present(grant.get("assessment")):
        events.append(("Initial assessment", str(grant["assessment"]).capitalize()))
    if grant.get("n_reviews"):
        events.append(("Peer review", f"{int(grant['n_reviews'])} reviewers, mean {grant['mean_review_total']:.1f} / 100"))
    events.append(("Funding decision", "Funded" if grant["funded"] else "Not funded"))
    for row in history.itertuples():
        events.append((f"Quarter {int(row.quarter)} report",
                       f"{row.overall_progress:.0f}% overall, at stage {int(row.current_stage)} "
                       f"({STAGES[int(row.current_stage) - 1]}), {row.budget_spent:,.0f} SAR spent"))
    if grant["funded"] and grant["extended"]:
        events.append(("Extension", "Ran past the planned end of the timetable"))
    if grant["funded"]:
        events.append(("Final report", "Received" if grant["final_report"] else "Not received yet"))
    return events


def timeline(grant, history):
    for step, detail in build_events(grant, history):
        left, right = st.columns([1, 3])
        left.markdown(f"**{step}**")
        right.markdown(detail)
