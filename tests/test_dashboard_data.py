from pathlib import Path

import pandas as pd
import pytest

from dashboard.data.adapters import ModuleOutput, read_team_output
from dashboard.data.contracts import CONTRACTS, ContractError, check, missing_columns
from dashboard.data.sources import index_sources
from dashboard.settings import TeamOutput, load_settings

RAW = Path(__file__).resolve().parents[1] / "data" / "synthetic" / "raw"


def pending(path, name="drift"):
    return TeamOutput(name, "Member C", Path(path), "the drift module")


def test_settings_resolve_paths_against_the_repo_root():
    settings = load_settings()
    assert settings.register.is_absolute()
    assert settings.priority_dir("embedding", "hard").name.endswith("hard")
    assert set(settings.team_outputs) == {"trajectories", "timetables", "drift", "stalls", "slip", "extensions"}


def test_contract_reports_the_columns_a_file_lacks():
    frame = pd.DataFrame({"grant_id": ["NAUSS-23-R01-001"], "similarity": [0.4]})
    assert missing_columns(frame, "drift") == ["threshold", "drift_flag", "n_papers"]
    with pytest.raises(ContractError) as raised:
        check(frame, "drift")
    assert "threshold" in str(raised.value)


def test_a_missing_teammate_file_gives_an_empty_frame_and_a_reason(tmp_path):
    output = read_team_output(pending(tmp_path / "drift_scores.csv"))
    assert isinstance(output, ModuleOutput)
    assert not output.ready
    assert output.frame.empty
    assert list(output.frame.columns) == CONTRACTS["drift"]
    assert any("drift_scores.csv" in line for line in output.missing)


def test_a_teammate_file_with_the_wrong_columns_is_not_used(tmp_path):
    path = tmp_path / "drift_scores.csv"
    pd.DataFrame({"grant_id": ["NAUSS-23-R01-001"], "score": [0.4]}).to_csv(path, index=False)
    output = read_team_output(pending(path))
    assert not output.ready
    assert "similarity" in output.missing[0]


def test_a_teammate_file_that_fits_the_contract_is_read(tmp_path):
    path = tmp_path / "drift_scores.csv"
    frame = pd.DataFrame([{"grant_id": "NAUSS-23-R01-001", "similarity": 0.4, "threshold": 0.5,
                           "drift_flag": 1, "n_papers": 2}])
    frame.to_csv(path, index=False)
    output = read_team_output(pending(path))
    assert output.ready
    assert len(output.frame) == 1


def test_progress_outputs_point_at_what_stall_report_writes():
    outputs = load_settings().team_outputs
    assert outputs["stalls"].file.name == "stall_episodes.csv"
    assert outputs["slip"].file.name == "timetable_slip.csv"
    assert outputs["extensions"].file.name == "extension_predictions.csv"
    assert all(outputs[name].owner == "Member D" for name in ("stalls", "slip", "extensions"))


def test_a_missing_file_says_which_command_to_run(tmp_path):
    output = read_team_output(TeamOutput("stalls", "Member D", tmp_path / "stall_episodes.csv",
                                         "python -m app.progress.stall_report"))
    assert not output.ready
    assert output.command == "python -m app.progress.stall_report"


def test_source_index_groups_every_form_of_a_grant():
    if not RAW.exists():
        pytest.skip("synthetic forms not generated")
    index = index_sources(RAW)
    sources = index["NAUSS-23-R01-006"]
    kinds = {source["kind"] for source in sources}
    assert {"proposals", "assessments", "progress_reports", "final_reports"} <= kinds
    assert all(source["path"].exists() for source in sources)
    assert all(source["private"] for source in sources if source["kind"] == "reviews")
