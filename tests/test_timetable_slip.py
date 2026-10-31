import pandas as pd

from app.progress.stall_detector import STAGE_COLUMNS
from app.progress.timetable_slip import TASK_TO_STAGE, first_behind, grant_slip, load_timetables, planned_quarter


def reports(rows):
    return pd.DataFrame([{"grant_id": "G1", "quarter": q, **{s: row.get(s, 0.0) for s in STAGE_COLUMNS}}
                         for q, row in enumerate(rows, start=1)])


def plan(tasks):
    return pd.DataFrame([{"grant_id": "G1", "stage": s, "to_month": m, "duration_months": 12} for s, m in tasks])


def test_tasks_map_to_stages_in_both_languages():
    assert TASK_TO_STAGE["data collection"] == "data_collection"
    assert TASK_TO_STAGE["جمع البيانات"] == "data_collection"


def test_month_to_quarter():
    assert [planned_quarter(m) for m in (1, 3, 4, 7, 12)] == [1, 1, 2, 3, 4]


def test_slip_status_for_each_case():
    df = reports([{"ethics_approval": 100, "data_collection": 30},
                  {"ethics_approval": 100, "data_collection": 60, "data_analysis": 100},
                  {"ethics_approval": 100, "data_collection": 90, "data_analysis": 100}])
    rows = {r["stage"]: r for r in grant_slip(plan([("ethics_approval", 3), ("data_collection", 4),
                                                    ("data_analysis", 9), ("writing_results", 11)]), df)}
    assert rows["ethics_approval"]["status"] == "on time"
    assert rows["data_collection"]["status"] == "overdue"  # due Q2, still 90% at Q3
    assert rows["data_collection"]["slip_quarters"] == 1
    assert rows["data_analysis"]["status"] == "early"  # due Q3, done Q2
    assert rows["writing_results"]["status"] == "not due yet"


def test_first_behind_only_looks_at_reports_so_far():
    df = reports([{"data_collection": 40}, {"data_collection": 70}, {"data_collection": 100}])
    assert first_behind(plan([("data_collection", 3)]), df) == 2
    assert first_behind(plan([("data_collection", 6)]), df) is None


def test_researcher_names_are_dropped_on_load(tmp_path):
    path = tmp_path / "planned_timetables.csv"
    pd.DataFrame([{"proposal_number": "G1", "source_file": "G1_proposal_en.docx", "duration_months": 12,
                   "task": "Data collection", "researcher": "Dr. Fake-Omar Echo", "from_month": 2,
                   "to_month": 6, "planned_months": 5}]).to_csv(path, index=False)
    df = load_timetables(path)
    assert "researcher" not in df.columns
    assert df.iloc[0]["stage"] == "data_collection"
