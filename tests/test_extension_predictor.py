import csv
from pathlib import Path

import pandas as pd
import pytest

from app.progress.extension_predictor import predict, read_outcomes, rules, summarise
from app.progress.stall_detector import STAGE_COLUMNS

DATA = Path(__file__).resolve().parents[1] / "data" / "synthetic"
FINAL_REPORTS = DATA / "raw" / "final_reports"

needs_data = pytest.mark.skipif(not FINAL_REPORTS.exists(), reason="synthetic data not unzipped in data/synthetic")

STALL = rules(5, 1)[0]


def reports(grant, rows):
    return pd.DataFrame([{"grant_id": grant, "quarter": q, **{s: row.get(s, 0.0) for s in STAGE_COLUMNS}}
                         for q, row in enumerate(rows, start=1)])


def plan(grant, months=12):
    return pd.DataFrame([{"grant_id": grant, "stage": "data_collection", "to_month": 6, "duration_months": months}])


def test_reports_after_the_planned_end_are_not_used():
    # The stall happens in quarters 5-6, after the 12-month plan ended: only visible because of the extension
    late = reports("G1", [{"data_collection": 30}, {"data_collection": 100}, {}, {}, {"data_analysis": 50},
                          {"data_analysis": 50}])
    result = predict(late, plan("G1"), {"G1": True}, STALL)
    assert result.iloc[0]["reports_used"] == 4
    assert pd.isna(result.iloc[0]["flag_quarter"])


def test_lead_time_and_summary():
    trajectories = pd.concat([
        reports("G1", [{"data_collection": 20}, {"data_collection": 20}, {"data_collection": 100}]),
        reports("G2", [{"data_collection": 50}, {"data_collection": 100}]),
        reports("G3", [{"data_collection": 40}, {"data_collection": 40}]),
    ])
    timetables = pd.concat([plan("G1"), plan("G2"), plan("G3")])
    result = predict(trajectories, timetables, {"G1": True, "G2": True, "G3": False}, STALL)
    assert result.set_index("grant_id").loc["G1", "lead_months"] == 12 - 2 * 3
    summary = summarise(result)
    assert (summary["detected"], summary["extended"]) == (1, 2)
    assert (summary["false_alarms"], summary["on_time"]) == (1, 1)
    assert summary["missed"] == ["G2"]


@needs_data
def test_outcomes_from_final_reports_match_the_answer_key():
    outcomes = read_outcomes(FINAL_REPORTS)
    with (DATA / "ground_truth" / "grants.csv").open(encoding="utf-8-sig") as f:
        truth = {r["grant_id"]: r["extended"] in ("1", "True") for r in csv.DictReader(f) if r["completed"] in ("1", "True")}
    assert outcomes == truth
    assert len(outcomes) == 48 and sum(outcomes.values()) == 24
