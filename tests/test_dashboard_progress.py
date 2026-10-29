import pandas as pd

from dashboard.data.progress import (
    DONE_LATE, DONE_ON_PLAN, OPEN_LATE, OPEN_ON_PLAN, STAGE_KEYS, agreement_with_register, plan_vs_actual,
    stage_number,
)

GRANT = "NAUSS-24-R02-001"


def trajectory(quarter, *percents):
    row = {"source_file": f"{GRANT}_Q{quarter:02d}_progress.docx", "project_number": GRANT, "quarter": quarter}
    row.update(dict(zip(STAGE_KEYS, list(percents) + [0] * (len(STAGE_KEYS) - len(percents)))))
    return row


def timetable(task, start, end):
    return {"proposal_number": GRANT, "task": task, "from_month": start, "to_month": end}


def test_arabic_and_english_task_names_map_to_the_same_stage():
    assert stage_number("Data collection") == 4
    assert stage_number("جمع البيانات") == 4
    assert stage_number("  literature   review ") == 1
    assert stage_number("Something else") is None


def test_each_stage_is_compared_with_the_quarter_its_timetable_ends():
    trajectories = pd.DataFrame([
        trajectory(1, 100, 100, 40),
        trajectory(2, 100, 100, 100, 30),
        trajectory(3, 100, 100, 100, 60),
    ])
    timetables = pd.DataFrame([
        timetable("Literature review", 1, 1),
        timetable("Instrument design", 2, 3),
        timetable("الموافقة الأخلاقية", 3, 3),
        timetable("Data collection", 4, 6),
        timetable("Data analysis", 10, 12),
    ])
    stages = plan_vs_actual(trajectories, timetables).set_index("stage")
    assert stages.loc[1, "state"] == DONE_ON_PLAN
    assert stages.loc[2, "state"] == DONE_ON_PLAN
    assert stages.loc[3, "state"] == DONE_LATE
    assert stages.loc[3, "slip_quarters"] == 1
    assert stages.loc[4, "state"] == OPEN_LATE
    assert stages.loc[4, "slip_quarters"] == 1
    assert stages.loc[5, "state"] == OPEN_ON_PLAN
    assert stages.loc[5, "slip_quarters"] == 0


def test_a_timetable_row_ending_before_it_starts_uses_its_later_month():
    trajectories = pd.DataFrame([trajectory(4, *[100] * 7)])
    timetables = pd.DataFrame([timetable("Paper submission", 12, 11)])
    stage = plan_vs_actual(trajectories, timetables).iloc[0]
    assert stage["planned_end"] == 12
    assert stage["planned_quarter"] == 4


def test_agreement_counts_reports_with_the_same_eight_percentages():
    trajectories = pd.DataFrame([trajectory(1, 100, 50), trajectory(2, 100, 100)])
    history = pd.DataFrame([
        {"grant_id": GRANT, "quarter": 1, **{f"stage{i}": v for i, v in enumerate([100, 50] + [0] * 6, 1)}},
        {"grant_id": GRANT, "quarter": 2, **{f"stage{i}": v for i, v in enumerate([100, 90] + [0] * 6, 1)}},
    ])
    assert agreement_with_register(trajectories, history) == (1, 2)
