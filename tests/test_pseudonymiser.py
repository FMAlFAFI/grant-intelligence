import csv
import shutil
from pathlib import Path

import pytest
from docx import Document
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

from app.ingestion.pseudonymiser import (Mapping, check_outside_repo, find_names, leftovers, name_key,
                                         paragraph_text, replace_in_paragraph, run)
from ingestion.text_extractor import extract_text

RAW = Path(__file__).resolve().parents[1] / "data" / "synthetic" / "raw"
GRANT = "NAUSS-23-R01-006"  # Arabic proposal, two reviews, progress reports and a final report

needs_data = pytest.mark.skipif(not RAW.exists(), reason="synthetic data not unzipped in data/synthetic")


def test_titles_spaces_and_case_do_not_split_a_person():
    assert name_key("Dr.  Fake-Ahmed Alpha") == name_key("fake-ahmed alpha") == "fake-ahmed alpha"
    assert name_key("د. أحمد الوهمي") == name_key("أحمد الوهمي")
    assert name_key("أ.د. أحمد الوهمي") == "أحمد الوهمي"


def test_codes_are_stable_and_numbered_per_role(tmp_path):
    mapping = Mapping(tmp_path / "map.csv")
    assert mapping.code("RESEARCHER", "Dr. Fake-Ahmed Alpha") == "RESEARCHER-001"
    assert mapping.code("RESEARCHER", "Dr. Fake-Sara Bravo") == "RESEARCHER-002"
    assert mapping.code("REVIEWER", "Dr. Fake-Ahmed Alpha") == "REVIEWER-01"  # roles are not linked
    assert mapping.code("RESEARCHER", "fake-ahmed  alpha") == "RESEARCHER-001"
    mapping.save()
    again = Mapping(tmp_path / "map.csv")
    assert again.code("RESEARCHER", "Dr. Fake-Sara Bravo") == "RESEARCHER-002"
    assert again.new == 0


def test_mapping_is_refused_inside_the_repo(tmp_path):
    with pytest.raises(ValueError):
        check_outside_repo(tmp_path / "repo" / "data" / "map.csv", repo=tmp_path / "repo")
    check_outside_repo(tmp_path / "private" / "map.csv", repo=tmp_path / "repo")


def test_name_split_over_runs_is_replaced():
    doc = Document()
    paragraph = doc.add_paragraph("Submitted by ")
    paragraph.add_run("Dr. Fake-")
    paragraph.add_run("Ahmed Alpha").bold = True
    paragraph.add_run(" on time.")
    assert replace_in_paragraph(paragraph._p, "Dr. Fake-Ahmed Alpha", "RESEARCHER-001")
    assert paragraph_text(paragraph._p) == "Submitted by RESEARCHER-001 on time."


def test_name_inside_a_content_control_is_found_and_replaced():
    doc = Document()
    table = doc.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "الباحث الرئيس / Principal investigator"
    # python-docx's own cell.text does not see text inside a content control
    table.cell(0, 1).paragraphs[0]._p.append(parse_xml(
        f"<w:sdt {nsdecls('w')}><w:sdtContent><w:r><w:t>Dr. Fake-Omar Echo</w:t></w:r></w:sdtContent></w:sdt>"))
    assert find_names(doc) == [("RESEARCHER", "Dr. Fake-Omar Echo")]
    p = table.cell(0, 1).paragraphs[0]._p
    assert replace_in_paragraph(p, "Dr. Fake-Omar Echo", "RESEARCHER-005")
    assert paragraph_text(p) == "RESEARCHER-005"


def test_placeholder_text_is_not_taken_as_a_name():
    doc = Document()
    table = doc.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "المحكم / Reviewer"
    table.cell(0, 1).text = "Click or tap here to enter text."
    assert find_names(doc) == []


@pytest.fixture
def one_grant(tmp_path):
    """Every synthetic form of one grant, copied into a small raw folder."""
    raw = tmp_path / "raw"
    for doc_type in ["proposals", "assessments", "reviews", "progress_reports", "final_reports"]:
        (raw / doc_type).mkdir(parents=True)
        for path in (RAW / doc_type).glob(f"{GRANT}*.docx"):
            shutil.copy(path, raw / doc_type)
    return raw


@needs_data
def test_synthetic_grant_has_no_names_left(one_grant, tmp_path):
    out, mapping = tmp_path / "out", tmp_path / "private" / "map.csv"
    summary = run(one_grant, out, mapping)
    assert summary["files"] == len(list(one_grant.rglob("*.docx")))
    assert summary["flagged"] == []

    with mapping.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    names = [r["name"] for r in rows]
    for path in out.rglob("*.docx"):
        text = extract_text(path)
        assert not any(name in text for name in names), path.name
        assert leftovers(path) == 0

    review = extract_text(out / "reviews" / f"{GRANT}-A_review.docx")
    assert "REVIEWER-" in review and "RESEARCHER-" not in review
    pi = next(r["pseudonym"] for r in rows if r["first_seen"].startswith("proposals"))
    assert pi in extract_text(next((out / "final_reports").glob("*.docx")))


@needs_data
def test_running_twice_gives_the_same_output(one_grant, tmp_path):
    mapping = tmp_path / "private" / "map.csv"
    run(one_grant, tmp_path / "first", mapping)
    before = mapping.read_bytes()
    summary = run(one_grant, tmp_path / "second", mapping)
    assert summary["new"] == 0
    assert mapping.read_bytes() == before
    for path in (tmp_path / "first").rglob("*.docx"):
        assert extract_text(path) == extract_text(tmp_path / "second" / path.relative_to(tmp_path / "first"))
