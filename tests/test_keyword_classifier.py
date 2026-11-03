from pathlib import Path

import pytest

from app.classification.keyword_classifier import (
    UNKNOWN,
    claimed_priority,
    classify,
    count_matches,
    load_priorities,
    normalize,
    proposal_fields,
)

PRIORITIES = load_priorities()
PROPOSALS = Path(__file__).resolve().parents[1] / "data" / "synthetic" / "raw" / "proposals"

needs_data = pytest.mark.skipif(not PROPOSALS.exists(), reason="synthetic data not unzipped in data/synthetic")


def test_arabic_normalization_strips_article_and_hamza():
    assert normalize("المخدرات") == normalize("مخدرات")
    assert normalize("إدارة الأزمات") == normalize("ادارة ازمات")


def test_longest_keyword_wins_over_shorter_overlap():
    text = normalize("document fraud at the border")
    assert count_matches(text, [normalize(w).strip() for w in ["fraud", "document fraud"]]) == ["document fraud"]


def test_title_outweighs_secondary_topic_in_abstract():
    fields = {
        "title": "Rehabilitation outcomes for drug addiction treatment",
        "keywords": "",
        "abstract": "The project also examines links with machine learning.",
    }
    predicted, _, _ = classify(fields, PRIORITIES)
    assert predicted == "Narcotics and Psychotropic Substances"


def test_arabic_text_is_classified():
    fields = {"title": "كشف غسل الأموال في المعاملات المصرفية الرقمية", "keywords": "", "abstract": ""}
    predicted, _, _ = classify(fields, PRIORITIES)
    assert predicted == "Cybercrimes and Financial Crimes"


def test_empty_proposal_is_unclassified():
    predicted, _, evidence = classify({"title": "", "keywords": "", "abstract": ""}, PRIORITIES)
    assert predicted == UNKNOWN
    assert evidence == []


def test_claimed_priority_matches_both_languages():
    assert claimed_priority("الجرائم السيبرانية والجرائم المالية", PRIORITIES) == "Cybercrimes and Financial Crimes"
    assert claimed_priority("AI and Emerging Technologies", PRIORITIES) == "AI and Emerging Technologies"


@needs_data
def test_background_is_read_from_arabic_and_english_forms():
    arabic = proposal_fields(PROPOSALS / "NAUSS-23-R01-025_proposal_ar.docx")
    english = proposal_fields(PROPOSALS / "NAUSS-23-R01-004_proposal_en.docx")
    assert arabic["background"].startswith("لا تزال الدراسات السابقة حول إساءة استخدام العملات المشفرة")
    assert english["background"] == "Previous studies on machine learning for crime pattern prediction remain limited and mostly descriptive."
    assert english["abstract"].startswith("This study investigates machine learning")
