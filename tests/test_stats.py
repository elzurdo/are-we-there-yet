"""
Tests for utils/stats.py — core statistical functions.
"""
import numpy as np
import pytest
from scipy.stats import beta

from utils.stats import successes_failures_to_hdi_ci_limits, CI_FRACTION


class TestSuccessesFailuresToHdiCiLimits:
    """Tests for successes_failures_to_hdi_ci_limits (Beta posterior HDI)."""

    def test_symmetric_beta_centered_at_half(self):
        """Beta(100, 100) should give an HDI roughly symmetric around 0.5."""
        hdi_min, hdi_max = successes_failures_to_hdi_ci_limits(100, 100)
        midpoint = (hdi_min + hdi_max) / 2
        assert hdi_min < 0.5 < hdi_max, "HDI should contain 0.5"
        assert midpoint == pytest.approx(0.5, abs=0.005), "Midpoint should be ≈ 0.5"

    def test_hdi_bounds_within_0_1(self):
        """HDI bounds must lie in [0, 1] for any Beta distribution."""
        for a, b in [(1, 1), (2, 5), (50, 50), (1, 100), (100, 1)]:
            hdi_min, hdi_max = successes_failures_to_hdi_ci_limits(a, b)
            assert 0.0 <= hdi_min < hdi_max <= 1.0, f"Failed for Beta({a},{b})"

    def test_hdi_width_shrinks_with_more_data(self):
        """More observations (a+b larger) should produce a narrower HDI."""
        _, max_small = successes_failures_to_hdi_ci_limits(10, 10)
        min_small, _ = successes_failures_to_hdi_ci_limits(10, 10)
        width_small = max_small - min_small

        _, max_large = successes_failures_to_hdi_ci_limits(100, 100)
        min_large, _ = successes_failures_to_hdi_ci_limits(100, 100)
        width_large = max_large - min_large

        assert width_large < width_small, "HDI should narrow with more data"

    def test_asymmetric_beta_skew(self):
        """Beta(90, 10) — HDI should be well above 0.5."""
        hdi_min, hdi_max = successes_failures_to_hdi_ci_limits(90, 10)
        assert hdi_min > 0.5, "Beta(90,10): HDI lower bound should be > 0.5"

    def test_known_95_hdi_beta_100_100(self):
        """Verify against scipy's Beta(100,100) PPF for a 95% interval.

        The HDI of a symmetric Beta equals the equal-tailed CI, so we can
        cross-check against quantile values.
        """
        hdi_min, hdi_max = successes_failures_to_hdi_ci_limits(100, 100, ci_fraction=0.95)

        # For symmetric Beta the HDI ≈ equal-tailed CI
        dist = beta(100, 100)
        expected_lo = dist.ppf(0.025)
        expected_hi = dist.ppf(0.975)

        assert hdi_min == pytest.approx(expected_lo, abs=0.002)
        assert hdi_max == pytest.approx(expected_hi, abs=0.002)

    def test_custom_ci_fraction(self):
        """ci_fraction=0.90 should give a narrower interval than 0.95."""
        hdi_min_90, hdi_max_90 = successes_failures_to_hdi_ci_limits(50, 50, ci_fraction=0.90)
        hdi_min_95, hdi_max_95 = successes_failures_to_hdi_ci_limits(50, 50, ci_fraction=0.95)

        width_90 = hdi_max_90 - hdi_min_90
        width_95 = hdi_max_95 - hdi_min_95
        assert width_90 < width_95, "90% HDI should be narrower than 95% HDI"
