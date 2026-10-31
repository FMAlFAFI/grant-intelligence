import math

import pandas as pd

from app.progress.progress_trajectories import STAGES as TRAJECTORY_STAGES

STAGE_KEYS = list(TRAJECTORY_STAGES)
STAGE_NAMES = [labels[0] for labels in TRAJECTORY_STAGES.values()]
STAGE_BY_LABEL = {
    " ".join(label.split()).casefold(): number
    for number, labels in enumerate(TRAJECTORY_STAGES.values(), start=1)
    for label in labels
}

DONE_ON_PLAN = "Finished on plan"
DONE_LATE = "Finished late"
OPEN_LATE = "Not finished, past its planned end"
OPEN_ON_PLAN = "Not finished, not due yet"
STAGE_STATES = [DONE_ON_PLAN, DONE_LATE, OPEN_LATE, OPEN_ON_PLAN]


def stage_number(task):
    return STAGE_BY_LABEL.get(" ".join(str(task).split()).casefold())


def quarter_of(month):
    return math.ceil(month / 3)


def planned_stages(timetables):
    frame = timetables.rename(columns={"proposal_number": "grant_id"}).copy()
    frame["stage"] = frame["task"].map(stage_number)
    frame = frame.dropna(subset=["stage"])
    frame["stage"] = frame["stage"].astype(int)
    frame["planned_end"] = frame[["from_month", "to_month"]].max(axis=1)
    plan = (frame.groupby(["grant_id", "stage"])
            .agg(planned_start=("from_month", "min"), planned_end=("planned_end", "max"))
            .reset_index())
    plan["planned_quarter"] = plan["planned_end"].map(quarter_of)
    return plan


def finished_stages(trajectories):
    frame = trajectories.rename(columns={"project_number": "grant_id"})
    frame = frame.dropna(subset=["grant_id", "quarter"]).copy()
    frame["quarter"] = frame["quarter"].astype(int)
    rows = []
    for grant_id, reports in frame.groupby("grant_id"):
        reports = reports.sort_values("quarter")
        last = int(reports["quarter"].max())
        for number, key in enumerate(STAGE_KEYS, start=1):
            done = reports.loc[reports[key] >= 100, "quarter"]
            rows.append({
                "grant_id": grant_id,
                "stage": number,
                "done_quarter": int(done.min()) if len(done) else None,
                "last_quarter": last,
                "percent_now": reports[key].iloc[-1],
            })
    return pd.DataFrame(rows)


def stage_state(row):
    if pd.notna(row["done_quarter"]):
        return DONE_LATE if row["slip_quarters"] > 0 else DONE_ON_PLAN
    return OPEN_LATE if row["last_quarter"] > row["planned_quarter"] else OPEN_ON_PLAN


def plan_vs_actual(trajectories, timetables):
    merged = finished_stages(trajectories).merge(planned_stages(timetables), on=["grant_id", "stage"], how="inner")
    reached = merged["done_quarter"].fillna(merged["last_quarter"])
    merged["slip_quarters"] = (reached - merged["planned_quarter"]).clip(lower=0).astype(int)
    merged["state"] = merged.apply(stage_state, axis=1)
    merged["stage_name"] = merged["stage"].map(lambda number: f"{number}. {STAGE_NAMES[number - 1]}")
    return merged


def agreement_with_register(trajectories, history):
    frame = trajectories.rename(columns={"project_number": "grant_id"}).dropna(subset=["quarter"]).copy()
    frame["quarter"] = frame["quarter"].astype(int)
    merged = frame.merge(history, on=["grant_id", "quarter"], how="outer", indicator=True)
    both = merged[merged["_merge"] == "both"]
    equal = pd.Series(True, index=both.index)
    for number, key in enumerate(STAGE_KEYS, start=1):
        equal &= both[key].fillna(-1) == both[f"stage{number}"].fillna(-1)
    return int(equal.sum()), len(merged)
