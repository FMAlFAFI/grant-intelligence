from pathlib import Path

import pytest
from docx import Document

from ingestion.text_extractor import extract_lines, extract_text

PROPOSALS = Path(__file__).resolve().parents[1] / "data" / "synthetic" / "raw" / "proposals"
AR_FILE = PROPOSALS / "NAUSS-23-R01-025_proposal_ar.docx"
EN_FILE = PROPOSALS / "NAUSS-23-R01-004_proposal_en.docx"

needs_data = pytest.mark.skipif(not EN_FILE.exists(), reason="synthetic data not unzipped in data/synthetic")


def line_after(lines, heading):
    index = next(i for i, line in enumerate(lines) if line.startswith(heading))
    return lines[index + 1]


@needs_data
def test_arabic_proposal_keeps_id_and_title():
    text = extract_text(AR_FILE)
    assert "NAUSS-23-R01-025" in text
    assert "تقييم إساءة استخدام العملات المشفرة في الجرائم المالية" in text


@needs_data
def test_tables_stay_under_their_section():
    lines = extract_lines(EN_FILE)
    assert line_after(lines, "1. المعلومات الأساسية").startswith("رقم المقترح / Proposal number | NAUSS-23-R01-004")
    assert line_after(lines, "9. الجدول الزمني").startswith("Task / المهمة")
    assert line_after(lines, "10. تفاصيل الميزانية").startswith("Item / البند")


@needs_data
def test_last_line_is_declaration_not_a_table():
    lines = extract_lines(EN_FILE)
    assert lines[-1] == "The PI confirms the information is accurate."


def test_merged_cells_are_not_repeated(tmp_path):
    doc = Document()
    table = doc.add_table(rows=2, cols=3)
    merged = table.cell(0, 0).merge(table.cell(0, 2))
    merged.text = "Research Team"
    table.cell(1, 0).text = "1"
    table.cell(1, 1).text = "Dr. Test"
    table.cell(1, 2).text = "PI"
    path = tmp_path / "merged.docx"
    doc.save(path)
    assert extract_lines(path) == ["Research Team", "1 | Dr. Test | PI"]


def test_empty_rows_and_paragraphs_are_dropped(tmp_path):
    doc = Document()
    doc.add_paragraph("Header")
    doc.add_paragraph("   ")
    table = doc.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Name"
    table.cell(0, 1).text = "Role"
    path = tmp_path / "empty.docx"
    doc.save(path)
    assert extract_lines(path) == ["Header", "Name | Role"]
