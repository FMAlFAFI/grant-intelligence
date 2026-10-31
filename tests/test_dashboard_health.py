import pandas as pd

from dashboard.data.health import (
    LATE, NO_HEALTH, ON_TRACK, WATCH, all_projects, build_tracker, extension_sentence, health_of, needs_attention, overdue_sentence,
    stage_result, stall_sentence, warning_record,
)
from ingestion.grant_register import COMPLETED, COMPLETED_LATE, NOT_FUNDED, OVERDUE, RUNNING


def grant(grant_id, status, extended=0, funded=1):
    return {"grant_id": grant_id, "status": status, "extended": extended, "funded": funded, "last_quarter": 2,
            "planned_months": 12}


def stall(grant_id, ongoing=True, stage="data_collection", reports=3):
    return {"grant_id": grant_id, "stage": stage, "reports": reports, "ongoing": ongoing}


def overdue(grant_id, stage="data_analysis", quarters=2):
    return {"grant_id": grant_id, "stage": stage, "slip_quarters": quarters, "status": "overdue"}


def tracker(grants, stalls=(), slips=()):
    episodes = pd.DataFrame(list(stalls), columns=["grant_id", "stage", "reports", "ongoing"])
    slip = pd.DataFrame(list(slips), columns=["grant_id", "stage", "slip_quarters", "status"])
    return build_tracker(pd.DataFrame(grants), episodes, slip)


def test_late_beats_watch_and_nothing_means_on_track():
    assert health_of(open_stall=False, overdue_stage=False, extended=False) == ON_TRACK
    assert health_of(open_stall=True, overdue_stage=False, extended=False) == WATCH
    assert health_of(open_stall=True, overdue_stage=True, extended=False) == LATE
    assert health_of(open_stall=False, overdue_stage=False, extended=True) == LATE


def test_tracker_lists_late_grants_first_and_only_funded_ones():
    frame = tracker(
        [grant("G1", RUNNING), grant("G2", RUNNING), grant("G3", RUNNING), grant("G4", NOT_FUNDED, funded=0)],
        stalls=[stall("G2")], slips=[overdue("G3")])
    assert list(frame["grant_id"]) == ["G3", "G2", "G1"]
    assert list(frame["health"]) == [LATE, WATCH, ON_TRACK]


def test_all_projects_lists_every_proposal_with_running_grants_first():
    register = pd.DataFrame([grant("G1", COMPLETED_LATE, extended=1), grant("G2", RUNNING), grant("G3", RUNNING),
                             grant("G4", NOT_FUNDED, funded=0)])
    frame = tracker(register.to_dict("records"), stalls=[stall("G3")])
    listed = all_projects(register, frame)
    assert list(listed["grant_id"]) == ["G3", "G2", "G1", "G4"]
    assert listed.set_index("grant_id").loc["G4", "health_label"] == NO_HEALTH


def test_a_stall_on_a_finished_grant_is_no_longer_open():
    frame = tracker([grant("G1", COMPLETED)], stalls=[stall("G1")])
    assert frame.loc[0, "health"] == ON_TRACK


def test_a_past_stall_on_a_running_grant_does_not_count():
    frame = tracker([grant("G1", RUNNING)], stalls=[stall("G1", ongoing=False)])
    assert frame.loc[0, "health"] == ON_TRACK


def test_extended_grants_are_late_and_say_why():
    frame = tracker([grant("G1", OVERDUE, extended=1), grant("G2", COMPLETED_LATE, extended=1)])
    assert set(frame["health"]) == {LATE}
    assert frame.set_index("grant_id").loc["G1", "reason"] == "Still running after its planned end date"


def test_attention_is_for_running_grants_only():
    frame = tracker([grant("G1", COMPLETED_LATE, extended=1), grant("G2", RUNNING), grant("G3", RUNNING)],
                    stalls=[stall("G3")])
    assert list(needs_attention(frame)["grant_id"]) == ["G3"]


def test_reasons_read_as_plain_sentences():
    assert stall_sentence("data_collection", 3) == "Stuck in Data collection for 3 quarters"
    rows = pd.DataFrame([overdue("G1", "data_collection", 1), overdue("G1", "data_analysis", 1)])
    assert overdue_sentence(rows) == "Data collection is 1 quarter past its planned end, and 1 later stage is late too"


def test_stage_result_has_no_jargon():
    assert stage_result({"status": "late", "slip_quarters": 2}) == "Finished 2 quarters late"
    assert stage_result({"status": "early", "slip_quarters": -1}) == "Finished 1 quarter early"
    assert stage_result({"status": "overdue", "slip_quarters": 1}) == "Not finished, 1 quarter late"
    assert stage_result({"status": "on time", "slip_quarters": 0}) == "Finished on time"
    assert stage_result({"status": "not due yet", "slip_quarters": None}) == "Not due yet"


def test_extension_sentence_and_record():
    predictions = pd.DataFrame([
        {"grant_id": "G1", "extended": True, "flag_quarter": 2.0, "lead_months": 6.0},
        {"grant_id": "G2", "extended": True, "flag_quarter": None, "lead_months": None},
        {"grant_id": "G3", "extended": False, "flag_quarter": None, "lead_months": None},
    ])
    assert "6 months before" in extension_sentence(predictions, {"grant_id": "G1", "status": COMPLETED_LATE})
    assert "no warning" in extension_sentence(predictions, {"grant_id": "G2", "status": COMPLETED_LATE})
    assert "Still running" in extension_sentence(predictions, {"grant_id": "G9", "status": RUNNING})
    at_the_end = predictions.assign(lead_months=0.0)
    assert "only came at its planned end" in extension_sentence(at_the_end, {"grant_id": "G1", "status": COMPLETED_LATE})
    assert warning_record(predictions) == {"warned": 1, "extended": 2, "false_alarms": 0, "on_time": 1}
