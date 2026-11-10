import csv

import pytest

from app.review.criteria import load_rubric
from config.config import ROOT, Config
from forms import capture


@pytest.fixture
def capture_folders(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, "CAPTURE_DIR", tmp_path / "captured")
    monkeypatch.setattr(Config, "PSEUDONYM_MAP_PATH", tmp_path / "private" / "pseudonym_map.csv")
    return tmp_path


def rows(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_a_review_is_saved_with_a_pseudonym_and_never_a_name(capture_folders):
    rubric = load_rubric()
    scores = {code: 2 for code in rubric["form_codes"]}
    record = capture.review_record("PROP-0114", "Dr. Fake-Layla Kilo", scores, {"A1": "Clear title"}, False, "applied",
                                   "العينة صغيرة", rubric)
    path = capture.save_record(capture.REVIEW, record)
    saved = rows(path)[0]
    assert saved["reviewer"].startswith("REVIEWER-") and "Layla" not in path.read_text(encoding="utf-8-sig")
    assert saved["form_variant"] == "standard" and saved["total"] == str(2 * 15) and saved["B3"] == ""
    assert saved["general_comment_lang"] == "ar" and saved["A1_comment_lang"] == "en"
    mapping = rows(capture_folders / "private" / "pseudonym_map.csv")
    assert mapping[0]["name"] == "Dr. Fake-Layla Kilo"         # the link lives only in the private mapping


def test_the_combined_form_keeps_one_mark_out_of_twelve(capture_folders):
    rubric = load_rubric()
    scores = {code: 1 for code in rubric["comparable"]} | {"B3": 9}
    record = capture.review_record("PROP-0115", "Fake-Omar Echo", scores, {}, True, "basic", "", rubric)
    assert record["form_variant"] == "combined" and record["B3"] == 9 and record["B3C"] == ""
    assert record["total"] == 11 + 9


def test_records_of_one_form_share_a_file_and_other_columns_are_refused(capture_folders):
    first = capture.save_record(capture.ASSESSMENT, {"proposal_number": "PROP-1", "recommendation": "approve"})
    capture.save_record(capture.ASSESSMENT, {"proposal_number": "PROP-2", "recommendation": "reject"})
    assert [row["proposal_number"] for row in rows(first)] == ["PROP-1", "PROP-2"]
    with pytest.raises(ValueError, match="other columns"):
        capture.save_record(capture.ASSESSMENT, {"proposal_number": "PROP-3"})


def test_the_mapping_is_refused_inside_the_repository(capture_folders, monkeypatch):
    monkeypatch.setattr(Config, "PSEUDONYM_MAP_PATH", ROOT / "pseudonym_map.csv")
    with pytest.raises(ValueError, match="outside the repository"):
        capture.pseudonym(capture.RESEARCHER, "Fake-Ahmed Alpha", "captured/proposals")
