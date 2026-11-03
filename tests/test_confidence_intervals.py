import math
import numpy as np
import pandas as pd
import pytest

from app.models.embedding_client import load_prompt_file
from app.review.agreement import calculate_cohens_kappa, identify_bias
from app.review.criterion_stats import compute_criterion_discrimination
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
    bias = identify_bias([1, 1, 1, 1], [3, 3, 3, 3])
    assert bias["agreement_level"] == "Low"
    df_rev = pd.DataFrame({"A1": [3, 4, 5, 2], "A2": [10, 12, 14, 8]})
    disc = compute_criterion_discrimination(df_rev)
    assert len(disc) == 2
    assert "drift" in CONTRACTS
