import math
import numpy as np
import pandas as pd
import pytest

from app.models.embedding_client import load_prompt_file
from app.review.agreement import calculate_cohens_kappa
from app.review.criteria import load_rubric
from app.review.criterion_stats import criterion_discrimination
from app.schemas.contracts import CONTRACTS, check
from app.statistics.confidence_intervals import rate, wilson
from app.statistics.multiple_comparison import benjamini_hochberg, holm_bonferroni


def test_wilson_against_worked_values():
    assert wilson(8, 24) == pytest.approx((0.1797, 0.5329), abs=1e-3)
    low, high = wilson(0, 24)
    assert low == 0 and high == pytest.approx(0.1380, abs=1e-3)


def test_wilson_stays_inside_zero_and_one():
    assert wilson(24, 24)[1] == 1.0
    assert all(math.isnan(x) for x in wilson(0, 0))


def test_rate_text_carries_the_denominator():
    assert rate(8, 24) == "8 of 24 (33%, 95% CI 18%-53%)"
    assert rate(0, 0) == "0 of 0 (no data)"


def test_holm_and_benjamini_hochberg_textbook_values():
    raw_p = [0.01, 0.04, 0.03, 0.005]
    assert np.allclose(holm_bonferroni(raw_p), [0.03, 0.06, 0.06, 0.02])
    assert np.allclose(benjamini_hochberg(raw_p), [0.02, 0.04, 0.04, 0.02])


def test_versioned_prompt_loads_from_disk():
    text = load_prompt_file("classify_v1.md")
    assert "Qwen/Qwen3-Embedding-0.6B" in text


def test_review_modules_and_schema_contracts():
    assert calculate_cohens_kappa([1, 2, 3, 1], [1, 2, 3, 1]) == 1.0
    assert calculate_cohens_kappa([1, 1, 2, 2], [1, 2, 1, 2]) == 0.0
    reviews = pd.DataFrame({"grant_id": [f"G{i}" for i in range(6)], "A1": [3, 4, 5, 2, 5, 4],
                            "A2": [10, 12, 14, 8, 9, 15]})
    table = criterion_discrimination(reviews)
    assert list(table["criterion"]) == ["A1", "A2"]
    assert table.loc[0, "reviews"] == 6 and table.loc[0, "max_score"] == 5
    assert table.loc[0, "mean_ci_low"] <= table.loc[0, "mean"] <= table.loc[0, "mean_ci_high"]
    assert "drift" in CONTRACTS


def test_the_rubric_comes_from_the_configuration_file():
    rubric = load_rubric()
    assert len(rubric["form_codes"]) == 15
    assert sum(rubric["maxima"][code] for code in rubric["form_codes"]) == 100
    # C to F as one mark out of 12 gives the 12 criteria every review has
    assert len(rubric["comparable"]) == 12 and rubric["maxima"]["B3"] == 12
    assert not set(rubric["separate"]) & set(rubric["comparable"])
