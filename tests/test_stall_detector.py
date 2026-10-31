import csv
from pathlib import Path

import pandas as pd
import pytest

from app.progress.bottleneck import NO_STALL, distribution
from app.progress.stall_detector import STAGE_COLUMNS, detect, first_alert, grant_episodes, is_stalled, load_trajectories

ROOT = Path(__file__).resolve().parents[1]
TRAJECTORIES = ROOT / "data" / "processed" / "progress_trajectories.csv"
TRUTH = ROOT / "data" / "synthetic" / "ground_truth"

needs_data = pytest.mark.skipif(not TRAJECTORIES.exists(), reason="progress_trajectories.csv not generated")


def reports(grant, rows):
    """Small trajectory: rows are {stage: pct} per quarter, other stages 0."""
    return pd.DataFrame([{"grant_id": grant, "quarter": q, **{s: row.get(s, 0.0) for s in STAGE_COLUMNS}}
                         for q, row in enumerate(rows, start=1)])


def test_stall_rule_matches_the_briefs_example():
    assert is_stalled(40, 45, tolerance=5)
    assert not is_stalled(40, 46, tolerance=5)


def test_finishing_or_not_starting_is_not_a_stall():
    assert not is_stalled(96, 100, tolerance=5)
    assert not is_stalled(0, 0, tolerance=5)
    assert not is_stalled(100, 100, tolerance=5)
    assert not is_stalled(float("nan"), 40, tolerance=5)


def test_episode_length_alert_and_ongoing():
    df = reports("G1", [{"data_collection": 20}, {"data_collection": 20}, {"data_collection": 22},
                        {"data_collection": 60}, {"data_collection": 60}])
    episodes = grant_episodes(df, tolerance=5)
    assert [(e["start_quarter"], e["alert_quarter"], e["end_quarter"], e["reports"], e["ongoing"])
            for e in episodes] == [(1, 2, 3, 2, False), (4, 5, 5, 1, True)]
    # Asking for two reports in a row drops the short one and moves the alert later
    assert [(e["alert_quarter"], e["reports"]) for e in grant_episodes(df, 5, min_reports=2)] == [(3, 2)]


def test_first_alert_per_grant():
    df = pd.concat([reports("G1", [{"data_analysis": 50}, {"data_analysis": 50}]),
                    reports("G2", [{"data_analysis": 10}, {"data_analysis": 40}])])
    assert first_alert(detect(df, tolerance=5)) == {"G1": 2}


def test_bottleneck_counts_each_grant_once_and_adds_up():
    df = pd.concat([
        reports("G1", [{"ethics_approval": 50, "data_collection": 10}] * 3),  # both stalled 2 reports: tie
        reports("G2", [{"data_analysis": 30}] * 2),
        reports("G3", [{"data_analysis": 30}, {"data_analysis": 90}]),
    ])
    dist = distribution(detect(df, tolerance=5), ["G1", "G2", "G3"]).set_index("stage")["grants"]
    assert dist["ethics_approval"] == 1  # the tie goes to the earlier stage
    assert dist["data_analysis"] == 1
    assert dist[NO_STALL] == 1
    assert dist.sum() == 3


@needs_data
def test_synthetic_stalls_are_exactly_the_frozen_stages_in_the_answer_key():
    with (TRUTH / "progress.csv").open(encoding="utf-8-sig") as f:
        truth = pd.DataFrame(list(csv.DictReader(f)))
    stages = [f"stage{i}" for i in range(1, 9)]
    truth[stages] = truth[stages].astype(float)
    truth["quarter"] = truth["quarter"].astype(int)
    frozen = set()
    for grant, rows in truth.sort_values(["grant_id", "quarter"]).groupby("grant_id"):
        values = rows[stages].to_numpy()
        for i in range(1, len(values)):
            if any(0 < a < 100 and b == a for a, b in zip(values[i - 1], values[i])):
                frozen.add(grant)

    found = set(detect(load_trajectories(TRAJECTORIES), tolerance=5)["grant_id"])
    assert found == frozen
    assert len(found) == 48

    # The stall_stage column only partly agrees: every detected grant has a label, but 36 of the 84
    # labelled grants never stop moving in their reports (see docs/stall-detection.md)
    with (TRUTH / "grants.csv").open(encoding="utf-8-sig") as f:
        labelled = {row["grant_id"] for row in csv.DictReader(f) if row["stall_stage"]}
    assert found <= labelled
    assert len(labelled) == 84
