import csv
from pathlib import Path

import pytest

from app.ingestion.review_variants import COMBINED, STANDARD, UNKNOWN, declared, number, scan

DATA = Path(__file__).resolve().parents[1] / "data" / "synthetic"
REVIEWS = DATA / "raw" / "reviews"

needs_data = pytest.mark.skipif(not REVIEWS.exists(), reason="synthetic data not unzipped in data/synthetic")


def test_declared_variant_is_read_in_both_languages():
    assert declared("methodology C-F combined (out of 12)") == COMBINED
    assert declared("المنهجية ج-و مجتمعة") == COMBINED
    assert declared("standard 15 criteria") == STANDARD
    assert declared("") == UNKNOWN


def test_scores_with_arabic_digits():
    assert number("١٢") == 12
    assert number(" 8 ") == 8
    assert number("") is None


@needs_data
def test_synthetic_variants_match_the_answer_key():
    records = {r["review_id"]: r for r in scan(REVIEWS)}
    with (DATA / "ground_truth" / "reviews.csv").open(encoding="utf-8-sig") as f:
        truth = {row["review_id"]: row for row in csv.DictReader(f)}
    assert set(records) == set(truth)
    for review_id, row in truth.items():
        expected = COMBINED if row["variant_combined_CF"] == "1" else STANDARD
        assert records[review_id]["variant"] == expected, review_id
        assert records[review_id]["score_sum"] == float(row["total"]), review_id
    assert sum(r["variant"] == COMBINED for r in records.values()) == 29
    assert all(r["declared_matches"] and r["total_matches"] for r in records.values())
    assert {r["methodology_scores"] for r in records.values() if r["variant"] == STANDARD} == {6}
    assert {r["methodology_scores"] for r in records.values() if r["variant"] == COMBINED} == {3}
