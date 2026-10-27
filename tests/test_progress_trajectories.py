from app.progress.progress_trajectories import extract_quarter, process_report


def test_extracts_quarter_above_four_from_bilingual_table_cells():
    items = ["رقم المشروع / Project number", "NAUSS-23-R01-006", "الربع / Quarter", "5"]
    assert extract_quarter(items) == "5"


def test_extracts_quarter_from_english_label_and_arabic_indic_digits():
    assert extract_quarter(["Quarter", "٦"]) == "6"


def test_extracts_quarter_from_q_notation_with_leading_zero():
    assert extract_quarter(["Reporting period: Q08"]) == "8"


def test_process_report_falls_back_to_quarter_in_filename(tmp_path, monkeypatch):
    from docx import Document

    path = tmp_path / "NAUSS-23-R01-006_Q12_progress.docx"
    Document().save(path)
    result = process_report(path)
    assert result["quarter"] == "12"
