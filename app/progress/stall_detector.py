"""Find stages that stop moving between quarterly progress reports.

A stage is stalled at a report when it had started (> 0%), is still not finished (< 100%) and gained
`tolerance` percentage points or less since the previous report. The rule and its numbers were fixed
in docs/statistics-methodology.md before running it. Output is about grants and stages only: an alert
means "review recommended", not that anything is wrong.
"""
import logging

import pandas as pd

from app.progress.progress_trajectories import STAGES
from config.config import get_config

logger = logging.getLogger(__name__)

STAGE_COLUMNS = list(STAGES)
EPISODE_COLUMNS = ["grant_id", "stage", "start_quarter", "alert_quarter", "end_quarter", "reports",
                   "from_pct", "to_pct", "ongoing"]


def load_trajectories(path):
    """Member C's progress_trajectories.csv as one row per grant and quarter, sorted."""
    df = pd.read_csv(path, encoding="utf-8-sig")
    df = df.rename(columns={"project_number": "grant_id"})
    df["quarter"] = pd.to_numeric(df["quarter"], errors="coerce")
    bad = df["grant_id"].isna() | df["quarter"].isna()
    if bad.any():
        logger.warning("Skipping %d report rows with no grant ID or quarter", int(bad.sum()))
        df = df[~bad]
    df["quarter"] = df["quarter"].astype(int)
    return df.sort_values(["grant_id", "quarter"]).reset_index(drop=True)


def is_stalled(previous, current, tolerance):
    """True when a started stage is still unfinished and gained `tolerance` points or less.

    Reaching 100% is never a stall, even from 96%. Missing values never stall.
    """
    if pd.isna(previous) or pd.isna(current):
        return False
    return 0 < previous < 100 and current < 100 and current - previous <= tolerance


def grant_episodes(reports, tolerance, min_reports=1):
    """Stall episodes for one grant's reports (sorted by quarter).

    An episode is a run of consecutive reports in which the same stage stayed stalled. It raises an
    alert at the report where the run reaches `min_reports`; shorter runs are not returned.
    """
    episodes = []
    quarters = reports["quarter"].tolist()
    last = len(quarters) - 1
    for stage in STAGE_COLUMNS:
        values = reports[stage].tolist()
        run_start, run = None, 0
        for i in range(1, len(values) + 1):
            if i <= last and is_stalled(values[i - 1], values[i], tolerance):
                if run == 0:
                    run_start = i - 1
                run += 1
                continue
            if run >= min_reports:
                end = i - 1
                episodes.append({
                    "grant_id": reports["grant_id"].iloc[0],
                    "stage": stage,
                    "start_quarter": quarters[run_start],
                    "alert_quarter": quarters[run_start + min_reports],
                    "end_quarter": quarters[end],
                    "reports": run,
                    "from_pct": values[run_start],
                    "to_pct": values[end],
                    "ongoing": end == last,
                })
            run = 0
    return episodes


def detect(trajectories, tolerance=None, min_reports=None):
    cfg = get_config()
    if tolerance is None:
        tolerance = cfg.STALL_TOLERANCE
    if min_reports is None:
        min_reports = cfg.STALL_MIN_REPORTS
        
    """Stall episodes for every grant, as a DataFrame (empty but with columns if there are none)."""
    rows = []
    for _, reports in trajectories.groupby("grant_id", sort=True):
        rows += grant_episodes(reports, tolerance, min_reports)
    return pd.DataFrame(rows, columns=EPISODE_COLUMNS)


def first_alert(episodes):
    """{grant_id: quarter of its first alert}."""
    if episodes.empty:
        return {}
    return episodes.groupby("grant_id")["alert_quarter"].min().to_dict()
