from pathlib import Path

import pandas as pd
import pytest

from ingestion.grant_register import (
    COMPLETED, COMPLETED_LATE, NOT_FUNDED, OVERDUE, REJECTED, RUNNING, STAGE_COLUMNS,
    build_progress_history, build_register, current_stage, lifecycle_status,
)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "synthetic" / "raw"
TRUTH = ROOT / "data" / "synthetic" / "ground_truth" / "grants.csv"


def record(**changes):
    base = {"assessment": "approve", "funded": 1, "final_report": 0, "extended": 0}
    base.update(changes)
    return base


def test_lifecycle_status_follows_the_forms():
    assert lifecycle_status(record(assessment="reject", funded=0)) == REJECTED
    assert lifecycle_status(record(funded=0)) == NOT_FUNDED
    assert lifecycle_status(record()) == RUNNING
    assert lifecycle_status(record(extended=1)) == OVERDUE
    assert lifecycle_status(record(final_report=1)) == COMPLETED
    assert lifecycle_status(record(final_report=1, extended=1)) == COMPLETED_LATE


def test_current_stage_is_the_first_unfinished_one():
    row = dict.fromkeys(STAGE_COLUMNS, 0)
    row.update(stage1=100, stage2=100, stage3=40)
    assert current_stage(row) == 3
    assert current_stage(dict.fromkeys(STAGE_COLUMNS, 100)) == 8


@pytest.fixture(scope="module")
def register():
    if not RAW.exists():
        pytest.skip("synthetic forms not generated")
    history = build_progress_history(RAW)
    return build_register(RAW, history).set_index("grant_id"), history


def test_register_matches_the_generator_ground_truth(register):
    frame, _ = register
    truth = pd.read_csv(TRUTH, encoding="utf-8-sig").set_index("grant_id").loc[frame.index]
    assert len(frame) == len(truth)
    assert (frame["assessment"] == truth["assessment"]).all()
    assert (frame["n_reviews"] == truth["n_reviews"]).all()
    assert (frame["funded"] == truth["funded"]).all()
    assert (frame["mean_review_total"].fillna(-1) == truth["mean_review_total"].fillna(-1)).all()
    funded = truth["funded"] == 1
    assert (frame.loc[funded, "final_report"] == truth.loc[funded, "completed"]).all()
    assert (frame.loc[funded, "extended"] == truth.loc[funded, "extended"]).all()


def test_every_funded_grant_has_a_progress_history(register):
    frame, history = register
    funded = set(frame.index[frame["funded"] == 1])
    assert set(history["grant_id"]) == funded
    assert history[STAGE_COLUMNS].notna().all().all()
