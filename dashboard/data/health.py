import pandas as pd

from app.progress.stall_detector import STAGE_COLUMNS
from ingestion.grant_register import COMPLETED, COMPLETED_LATE, OVERDUE, RUNNING

LATE = "Late"
WATCH = "Watch"
ON_TRACK = "On track"
HEALTHS = [LATE, WATCH, ON_TRACK]
HEALTH_LABELS = {LATE: "🔴 Late", WATCH: "🟠 Watch", ON_TRACK: "🟢 On track"}
HEALTH_COLORS = {LATE: "red", WATCH: "orange", ON_TRACK: "green"}
RUNNING_STATUSES = [RUNNING, OVERDUE]
FINISHED_STATUSES = [COMPLETED, COMPLETED_LATE]
MONTHS_PER_REPORT = 3


def stage_label(stage):
    return stage.replace("_", " ").capitalize()


def quarters(count):
    count = int(count)
    return f"{count} quarter" if count == 1 else f"{count} quarters"


def health_of(open_stall, overdue_stage, extended):
    if overdue_stage or extended:
        return LATE
    return WATCH if open_stall else ON_TRACK


def open_stalls(episodes, running):
    return episodes[episodes["grant_id"].isin(running) & episodes["ongoing"].astype(bool)]


def overdue_stages(slip):
    rows = slip[slip["status"] == "overdue"].copy()
    rows["order"] = rows["stage"].map(STAGE_COLUMNS.index)
    return rows.sort_values(["grant_id", "order"])


def stall_sentence(stage, reports):
    return f"Stuck in {stage_label(stage)} for {quarters(reports)}"


def overdue_sentence(rows):
    first = rows.iloc[0]
    sentence = f"{stage_label(first['stage'])} is {quarters(first['slip_quarters'])} past its planned end"
    others = len(rows) - 1
    if others == 1:
        return f"{sentence}, and 1 later stage is late too"
    return f"{sentence}, and {others} later stages are late too" if others else sentence


def reasons_for(grant_id, status, stalled, overdue):
    reasons = [stall_sentence(row.stage, row.reports) for row in stalled[stalled["grant_id"] == grant_id].itertuples()]
    rows = overdue[overdue["grant_id"] == grant_id]
    if not rows.empty:
        reasons.append(overdue_sentence(rows))
    if status == OVERDUE:
        reasons.append("Still running after its planned end date")
    if status == COMPLETED_LATE:
        reasons.append("Needed an extension to finish")
    return reasons


def build_tracker(register, episodes, slip):
    funded = register[register["funded"] == 1].copy()
    running = set(funded.loc[funded["status"].isin(RUNNING_STATUSES), "grant_id"])
    stalled = open_stalls(episodes, running)
    overdue = overdue_stages(slip)
    stalled_ids, overdue_ids = set(stalled["grant_id"]), set(overdue["grant_id"])

    funded["health"] = [
        health_of(row.grant_id in stalled_ids, row.grant_id in overdue_ids, bool(row.extended))
        for row in funded.itertuples()
    ]
    funded["reason"] = [
        ". ".join(reasons_for(row.grant_id, row.status, stalled, overdue)) for row in funded.itertuples()
    ]
    funded["health_label"] = funded["health"].map(HEALTH_LABELS)
    funded["months"] = [
        f"{int(row.last_quarter) * MONTHS_PER_REPORT} of {int(row.planned_months)} months"
        for row in funded.itertuples()
    ]
    funded["rank"] = funded["health"].map(HEALTHS.index)
    return funded.sort_values(["rank", "grant_id"]).drop(columns="rank").reset_index(drop=True)


def needs_attention(tracker):
    running = tracker[tracker["status"].isin(RUNNING_STATUSES)]
    return running[running["health"] != ON_TRACK]


def stage_result(row):
    if row["status"] == "not due yet":
        return "Not due yet"
    if row["status"] == "overdue":
        return f"Not finished, {quarters(row['slip_quarters'])} late"
    if row["status"] == "late":
        return f"Finished {quarters(row['slip_quarters'])} late"
    if row["status"] == "early":
        return f"Finished {quarters(abs(row['slip_quarters']))} early"
    return "Finished on time"


def stage_plan(slip, grant_id):
    rows = slip[slip["grant_id"] == grant_id].copy()
    rows["order"] = rows["stage"].map(STAGE_COLUMNS.index)
    rows = rows.sort_values("order")
    rows["stage_name"] = rows["stage"].map(stage_label)
    rows["result"] = rows.apply(stage_result, axis=1)
    return rows


def extension_sentence(predictions, grant):
    if grant["status"] in RUNNING_STATUSES:
        return "Still running. This check is only done once a grant is finished."
    row = predictions[predictions["grant_id"] == grant["grant_id"]]
    if row.empty:
        return "No check for this grant."
    row = row.iloc[0]
    warned = pd.notna(row["flag_quarter"])
    if row["extended"] and warned and row["lead_months"] > 0:
        return (f"This grant needed an extension, and the warning came "
                f"{int(row['lead_months'])} months before its planned end.")
    if row["extended"] and warned:
        return "This grant needed an extension, and the warning only came at its planned end."
    if row["extended"]:
        return "This grant needed an extension, and no warning appeared before its planned end."
    if warned:
        return f"A warning appeared in quarter {int(row['flag_quarter'])}, but the grant finished on time."
    return "This grant finished on time and no warning appeared."


def warning_record(predictions):
    extended = predictions[predictions["extended"].astype(bool)]
    on_time = predictions[~predictions["extended"].astype(bool)]
    return {"warned": int(extended["flag_quarter"].notna().sum()), "extended": len(extended),
            "false_alarms": int(on_time["flag_quarter"].notna().sum()), "on_time": len(on_time)}
