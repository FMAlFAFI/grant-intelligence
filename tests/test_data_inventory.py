import shutil
from collections import Counter
from pathlib import Path

import pytest

from ingestion.data_inventory import detect_language, empty_fields, english, fields, parse_form, round_of, scan

PROPOSALS = Path(__file__).resolve().parents[1] / "data" / "synthetic" / "raw" / "proposals"

needs_data = pytest.mark.skipif(not PROPOSALS.exists(), reason="synthetic data not unzipped in data/synthetic")

FORM = "\n".join([
    "1. المعلومات الأساسية / 1. Basic information",
    "3. الملخص / 3. Abstract",
    "A short abstract.",
    "4. الكلمات المفتاحية / 4. Keywords",
    "رقم المقترح / Proposal number | NAUSS-24-R02-017",
    "القسم / Department | ",
    "نوع المشروع / Project type | small",
])


def test_english_half_of_a_bilingual_label():
    assert english("القسم / Department") == "Department"
    assert english("القسم") == "القسم"


def test_form_is_split_into_sections_and_fields():
    sections, rows = parse_form(FORM)
    assert sections["3. Abstract"] == ["A short abstract."]
    assert sections["4. Keywords"] == []
    assert fields(rows)["Proposal number"] == "NAUSS-24-R02-017"


def test_empty_text_sections_and_blank_values_are_reported():
    sections, rows = parse_form(FORM)
    assert empty_fields(sections, rows) == ["4. Keywords", "Department"]


def test_language_follows_the_script():
    assert detect_language("دراسة عن الجرائم السيبرانية") == "ar"
    assert detect_language("A study of cybercrime") == "en"


def test_round_comes_from_the_grant_id():
    assert round_of("NAUSS-24-R02-017") == "2024 (round 2)"


@needs_data
def test_synthetic_proposals_per_round(tmp_path):
    shutil.copytree(PROPOSALS, tmp_path / "proposals")
    proposals = scan(tmp_path)["proposals"]
    assert len(proposals) == 100
    assert Counter(round_of(grant) for grant in proposals) == {
        "2023 (round 1)": 30,
        "2024 (round 2)": 35,
        "2025 (round 3)": 35,
    }
    assert Counter(p["language"] for p in proposals.values()) == {"ar": 50, "en": 50}
