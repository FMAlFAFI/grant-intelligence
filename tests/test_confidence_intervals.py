import math

import pytest

from app.statistics.confidence_intervals import rate, wilson


def test_wilson_against_worked_values():
    # 8 of 24 and 0 of 24, checked by hand with z = 1.96
    assert wilson(8, 24) == pytest.approx((0.1797, 0.5329), abs=1e-3)
    low, high = wilson(0, 24)
    assert low == 0 and high == pytest.approx(0.1380, abs=1e-3)


def test_wilson_stays_inside_zero_and_one():
    assert wilson(24, 24)[1] == 1.0
    assert all(math.isnan(x) for x in wilson(0, 0))


def test_rate_text_carries_the_denominator():
    assert rate(8, 24) == "8 of 24 (33%, 95% CI 18%-53%)"
    assert rate(0, 0) == "0 of 0 (no data)"
