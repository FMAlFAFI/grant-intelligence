"""Experiment 6: would the stall and slip signals have warned us before a grant needed an extension?

Retrospective, on completed grants only. For each grant the detector only sees the reports up to the
grant's planned end, because an extended grant has extra reports *because* it was extended and using
them would give the answer away. Detection rate, false positive rate and lead time are always reported
together (brief, Stage 5).
"""
import logging
from pathlib import Path

import pandas as pd

from app.progress.stall_detector import detect, first_alert
from app.progress.timetable_slip import first_behind
from ingestion.data_inventory import GRANT_ID, english, fields, parse_form
from ingestion.text_extractor import extract_text

logger = logging.getLogger(__name__)


def read_outcomes(final_reports_dir):
    """{grant_id: True if the final report says the period was extended}. One entry per completed grant."""
    outcomes = {}
    for path in sorted(Path(final_reports_dir).glob("*.docx")):
        match = GRANT_ID.search(path.name)
        if not match or path.name.startswith("~$"):
            continue
        try:
            _, rows = parse_form(extract_text(path))
        except Exception as exc:  # unreadable file: report it, keep going
            logger.warning("Could not read %s: %s", path.name, exc)
            continue
        value = fields(rows).get("Period extended", "")
        outcomes[match.group(0)] = english(value).lower().startswith("yes") or "نعم" in value
    return outcomes


def rules(tolerance, min_reports):
    """The main rule from docs/statistics-methodology.md and the sensitivity versions next to it."""
    return [
        {"name": f"stall, {tolerance:g} points (main)", "tolerance": tolerance, "min_reports": min_reports, "slip": False},
        {"name": "stall, exact freeze (0 points)", "tolerance": 0, "min_reports": min_reports, "slip": False},
        {"name": "stall, 10 points", "tolerance": 10, "min_reports": min_reports, "slip": False},
        {"name": "stall, 2 reports in a row", "tolerance": tolerance, "min_reports": 2, "slip": False},
        {"name": "timetable slip only", "tolerance": None, "min_reports": None, "slip": True},
        {"name": "stall or timetable slip", "tolerance": tolerance, "min_reports": min_reports, "slip": True},
    ]


def predict(trajectories, timetables, outcomes, rule, interval=3):
    """One row per completed grant: was it flagged before its planned end, and how early."""
    rows = []
    plans = dict(list(timetables.groupby("grant_id")))
    for grant_id, reports in trajectories.groupby("grant_id", sort=True):
        if grant_id not in outcomes or grant_id not in plans:
            continue
        plan = plans[grant_id]
        planned_months = int(plan["duration_months"].iloc[0])
        before_end = reports[reports["quarter"] * interval <= planned_months]

        flags = []
        if rule["tolerance"] is not None:
            alert = first_alert(detect(before_end, rule["tolerance"], rule["min_reports"])).get(grant_id)
            if alert is not None:
                flags.append(alert)
        if rule["slip"]:
            behind = first_behind(plan, before_end, interval)
            if behind is not None:
                flags.append(behind)
        flag = min(flags) if flags else None
        rows.append({
            "grant_id": grant_id,
            "extended": outcomes[grant_id],
            "planned_months": planned_months,
            "reports_used": len(before_end),
            "flag_quarter": flag,
            "lead_months": planned_months - flag * interval if flag is not None else None,
        })
    return pd.DataFrame(rows)


def summarise(predictions, interval=3):
    """Counts behind the three Experiment 6 numbers."""
    extended = predictions[predictions["extended"]]
    on_time = predictions[~predictions["extended"]]
    detected = extended[extended["flag_quarter"].notna()]
    return {
        "extended": len(extended),
        "detected": len(detected),
        # A flag at the last planned report is not much of a warning, so count the early ones separately
        "detected_early": int((detected["lead_months"] >= interval).sum()),
        "on_time": len(on_time),
        "false_alarms": int(on_time["flag_quarter"].notna().sum()),
        "lead_months": sorted(detected["lead_months"].astype(int).tolist()),
        "missed": sorted(extended.loc[extended["flag_quarter"].isna(), "grant_id"]),
    }
