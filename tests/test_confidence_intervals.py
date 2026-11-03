import math
import numpy as np
import pytest

from app.models import load_prompt_file
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
    # Holm step-down for 4 tests: sorted [0.005*4=0.02, 0.01*3=0.03, 0.03*2=0.06, 0.04*1=0.06]
    assert np.allclose(holm_bonferroni(raw_p), [0.03, 0.06, 0.06, 0.02])
    # Benjamini-Hochberg FDR for 4 tests: sorted [0.005*4/1=0.02, 0.01*4/2=0.02, 0.03*4/3=0.04, 0.04*4/4=0.04]
    assert np.allclose(benjamini_hochberg(raw_p), [0.02, 0.04, 0.04, 0.02])


def test_versioned_prompt_loads_from_disk():
    text = load_prompt_file("classify_v1.md")
    assert "Qwen/Qwen3-Embedding-0.6B" in text
