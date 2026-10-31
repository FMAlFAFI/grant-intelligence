"""Compare each grant's progress against the timetable in its own proposal.

Reports are quarterly, so completion is only known to the quarter. A task is compared by quarter:
the quarter its planned "to month" falls in, against the first report where the matching stage is
at 100%. Slip is in quarters; positive means later than planned.
"""
import logging
import math

import pandas as pd

from app.progress.progress_trajectories import STAGES

logger = logging.getLogger(__name__)

# "Data collection" and "جمع البيانات" -> "data_collection", using Member C's stage names
TASK_TO_STAGE = {name.strip().lower(): key for key, names in STAGES.items() for name in names}
SLIP_COLUMNS = ["grant_id", "stage", "planned_to_month", "planned_quarter", "done_quarter",
                "last_quarter", "slip_quarters", "status"]


def load_timetables(path):
    """planned_timetables.csv with one row per grant and stage. The researcher column is dropped."""
    df = pd.read_csv(path, encoding="utf-8-sig")
    df = df.drop(columns=["researcher"], errors="ignore")  # names stay out of everything we write
    df = df.rename(columns={"proposal_number": "grant_id"})
    df["stage"] = df["task"].astype(str).str.strip().str.lower().map(TASK_TO_STAGE)
    unknown = df["stage"].isna()
    if unknown.any():
        logger.warning("%d timetable tasks do not match a progress stage: %s", int(unknown.sum()),
                       sorted(df.loc[unknown, "task"].astype(str).unique()))
    df = df[~unknown]
    df["to_month"] = pd.to_numeric(df["to_month"], errors="coerce")
    df["duration_months"] = pd.to_numeric(df["duration_months"], errors="coerce")
    return df


def planned_quarter(to_month, interval=3):
    return math.ceil(to_month / interval)


def grant_slip(plan, reports, interval=3, as_of=None):
    """Slip rows for one grant. `as_of` limits the reports to quarters up to that one."""
    if as_of is not None:
        reports = reports[reports["quarter"] <= as_of]
    last_quarter = int(reports["quarter"].max()) if not reports.empty else 0
    rows = []
    for _, task in plan.iterrows():
        if pd.isna(task["to_month"]):
            continue
        due = planned_quarter(task["to_month"], interval)
        done = reports.loc[reports[task["stage"]] >= 100, "quarter"]
        done_quarter = int(done.min()) if not done.empty else None
        if done_quarter is not None:
            slip = done_quarter - due
            status = "late" if slip > 0 else "early" if slip < 0 else "on time"
        elif last_quarter > due:
            slip, status = last_quarter - due, "overdue"  # at least this late, still not finished
        else:
            slip, status = None, "not due yet"
        rows.append({
            "grant_id": task["grant_id"], "stage": task["stage"], "planned_to_month": int(task["to_month"]),
            "planned_quarter": due, "done_quarter": done_quarter, "last_quarter": last_quarter,
            "slip_quarters": slip, "status": status,
        })
    return rows


def compute(timetables, trajectories, interval=3):
    """Slip for every task of every grant that has both a timetable and progress reports."""
    rows = []
    reports_by_grant = dict(list(trajectories.groupby("grant_id")))
    for grant_id, plan in timetables.groupby("grant_id", sort=True):
        if grant_id in reports_by_grant:
            rows += grant_slip(plan, reports_by_grant[grant_id], interval)
    return pd.DataFrame(rows, columns=SLIP_COLUMNS)


def first_behind(plan, reports, interval=3, min_quarters=1):
    """First report quarter where some task is `min_quarters` or more past its planned quarter and
    still not finished, or None. Only uses reports up to that quarter, so it can be used for prediction."""
    for quarter in sorted(reports["quarter"]):
        so_far = reports[reports["quarter"] <= quarter]
        for _, task in plan.iterrows():
            if pd.isna(task["to_month"]):
                continue
            behind = quarter - planned_quarter(task["to_month"], interval)
            if behind >= min_quarters and not (so_far[task["stage"]] >= 100).any():
                return int(quarter)
    return None
