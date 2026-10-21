from classification.keyword_classifier import (
    UNKNOWN,
    claimed_priority,
    classify,
    count_matches,
    load_priorities,
    normalize,
)

PRIORITIES = load_priorities()


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
