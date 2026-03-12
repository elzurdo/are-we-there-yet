"""
Tests for utils/stats.py — core statistical functions.
"""
import numpy as np
import pytest
from scipy.stats import beta, norm, t as student_t
from scipy.stats import norm as scipy_norm

from utils.stats import (
    HDIofICDF,
    successes_failures_to_hdi_ci_limits,
    continuous_hdi_ci_limits,
    beta_overlap,
    binary_difference_hdi,
    check_clt_conditions,
    continuous_difference_hdi,
    binomial_rate_ci_width_to_sample_size,
    CI_FRACTION,
)


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


# ──────────────────────────────────────────────────────────────


class TestHDIofICDF:
    """Tests for HDIofICDF — the numerical HDI optimizer."""

    def test_normal_dist_symmetric(self):
        """Standard Normal HDI should be symmetric around 0."""
        hdi_min, hdi_max = HDIofICDF(scipy_norm, ci_fraction=0.95, loc=0, scale=1)
        assert hdi_min == pytest.approx(-hdi_max, abs=1e-4), "Normal HDI should be symmetric"

    def test_normal_matches_ppf(self):
        """Normal(5, 2) 95% HDI should match equal-tailed quantiles."""
        from scipy.stats import norm as scipy_norm
        hdi_min, hdi_max = HDIofICDF(scipy_norm, ci_fraction=0.95, loc=5, scale=2)
        dist = scipy_norm(loc=5, scale=2)
        assert hdi_min == pytest.approx(dist.ppf(0.025), abs=1e-3)
        assert hdi_max == pytest.approx(dist.ppf(0.975), abs=1e-3)

    def test_returns_two_values(self):
        """Should always return exactly two values (min, max)."""
        result = HDIofICDF(beta, ci_fraction=0.95, a=10, b=10)
        assert len(result) == 2
        assert result[0] < result[1]


# ──────────────────────────────────────────────────────────────


class TestContinuousHdiCiLimits:
    """Tests for continuous_hdi_ci_limits (Student-t HDI for a sample mean)."""

    def test_symmetric_around_mean(self):
        """HDI should be centered on the sample mean."""
        hdi_min, hdi_max = continuous_hdi_ci_limits(sample_mean=10.0, sample_std=2.0, n=50)
        midpoint = (hdi_min + hdi_max) / 2
        assert midpoint == pytest.approx(10.0, abs=1e-6)

    def test_wider_with_larger_std(self):
        """Larger std → wider HDI, same n and mean."""
        lo1, hi1 = continuous_hdi_ci_limits(0.0, 1.0, 30)
        lo2, hi2 = continuous_hdi_ci_limits(0.0, 3.0, 30)
        assert (hi2 - lo2) > (hi1 - lo1)

    def test_narrower_with_more_data(self):
        """More data → narrower HDI, same mean and std."""
        lo1, hi1 = continuous_hdi_ci_limits(0.0, 2.0, 10)
        lo2, hi2 = continuous_hdi_ci_limits(0.0, 2.0, 100)
        assert (hi2 - lo2) < (hi1 - lo1)

    def test_raises_for_n_less_than_2(self):
        """n < 2 should raise ValueError."""
        with pytest.raises(ValueError):
            continuous_hdi_ci_limits(0.0, 1.0, n=1)

    def test_matches_t_ppf(self):
        """Cross-check against scipy Student-t quantiles."""
        mean, std, n = 5.0, 2.0, 20
        hdi_min, hdi_max = continuous_hdi_ci_limits(mean, std, n, ci_fraction=0.95)
        se = std / np.sqrt(n)
        df = n - 1
        dist = student_t(df=df, loc=mean, scale=se)
        assert hdi_min == pytest.approx(dist.ppf(0.025), abs=1e-4)
        assert hdi_max == pytest.approx(dist.ppf(0.975), abs=1e-4)


# ──────────────────────────────────────────────────────────────


class TestBetaOverlap:
    """Tests for beta_overlap — overlap coefficient between two Beta distributions."""

    def test_identical_distributions_overlap_is_one(self):
        """Identical Beta distributions should have overlap ≈ 1."""
        overlap = beta_overlap(10, 10, 10, 10)
        assert overlap == pytest.approx(1.0, abs=0.01)

    def test_non_overlapping_distributions(self):
        """Very separated distributions should have overlap ≈ 0."""
        overlap = beta_overlap(1, 200, 200, 1)  # one near 0, one near 1
        assert overlap < 0.01

    def test_overlap_between_zero_and_one(self):
        """Overlap must always be in [0, 1]."""
        for params in [(2, 5, 5, 2), (10, 2, 2, 10), (1, 1, 1, 1)]:
            a1, b1, a2, b2 = params
            o = beta_overlap(a1, b1, a2, b2)
            assert 0.0 <= o <= 1.0, f"Out of range for params {params}"

    def test_symmetric_params_equal_overlap(self):
        """beta_overlap(a1,b1,a2,b2) == beta_overlap(a2,b2,a1,b1)."""
        o1 = beta_overlap(3, 10, 10, 3)
        o2 = beta_overlap(10, 3, 3, 10)
        assert o1 == pytest.approx(o2, abs=1e-4)


# ──────────────────────────────────────────────────────────────


class TestBinaryDifferenceHdi:
    """Tests for binary_difference_hdi (CLT Normal HDI for p_A - p_B)."""

    def test_equal_proportions_centered_at_zero(self):
        """p_A == p_B → HDI should be centered at 0."""
        hdi_min, hdi_max = binary_difference_hdi(0.5, 100, 0.5, 100)
        midpoint = (hdi_min + hdi_max) / 2
        assert midpoint == pytest.approx(0.0, abs=1e-6)

    def test_returns_ordered_bounds(self):
        """hdi_min must always be less than hdi_max."""
        for p_a, p_b in [(0.3, 0.5), (0.7, 0.2), (0.5, 0.5)]:
            lo, hi = binary_difference_hdi(p_a, 100, p_b, 100)
            assert lo < hi

    def test_positive_delta_shifts_interval_up(self):
        """p_A > p_B → both bounds should be positive."""
        hdi_min, hdi_max = binary_difference_hdi(0.8, 200, 0.2, 200)
        assert hdi_min > 0, "Lower bound should be positive when p_A >> p_B"

    def test_matches_normal_ppf(self):
        """Cross-check bounds against manual z × SE calculation."""
        p_a, n_a, p_b, n_b = 0.6, 100, 0.4, 100
        delta = p_a - p_b
        se = np.sqrt(p_a * (1 - p_a) / n_a + p_b * (1 - p_b) / n_b)
        z = norm.ppf(0.975)
        expected_lo = delta - z * se
        expected_hi = delta + z * se

        hdi_min, hdi_max = binary_difference_hdi(p_a, n_a, p_b, n_b, ci_fraction=0.95)
        assert hdi_min == pytest.approx(expected_lo, abs=1e-6)
        assert hdi_max == pytest.approx(expected_hi, abs=1e-6)

    def test_narrower_with_more_data(self):
        """Larger samples → narrower HDI."""
        lo1, hi1 = binary_difference_hdi(0.5, 50, 0.4, 50)
        lo2, hi2 = binary_difference_hdi(0.5, 500, 0.4, 500)
        assert (hi2 - lo2) < (hi1 - lo1)


# ──────────────────────────────────────────────────────────────


class TestCheckCltConditions:
    """Tests for check_clt_conditions."""

    def test_all_pass_with_large_balanced_samples(self):
        """Large, balanced samples should pass all four conditions."""
        conditions = check_clt_conditions(0.5, 100, 0.5, 100)
        assert all(c["passed"] for c in conditions)

    def test_returns_four_conditions(self):
        """Should always return exactly 4 condition dicts."""
        conditions = check_clt_conditions(0.5, 100, 0.5, 100)
        assert len(conditions) == 4

    def test_each_dict_has_required_keys(self):
        """Each condition dict must have 'label', 'value', 'passed'."""
        for c in check_clt_conditions(0.5, 50, 0.5, 50):
            assert "label" in c
            assert "value" in c
            assert "passed" in c

    def test_fails_when_n_times_p_below_threshold(self):
        """n_A=10, p_A=0.1 → n_A*p_A=1 < 5: first condition should fail."""
        conditions = check_clt_conditions(0.1, 10, 0.5, 100)
        assert not conditions[0]["passed"], "n_A×p̂_A should fail"

    def test_boundary_exactly_at_threshold(self):
        """n*p == threshold (5) should pass (>=)."""
        conditions = check_clt_conditions(0.1, 50, 0.5, 100)  # 50*0.1 == 5
        assert conditions[0]["passed"], "n_A×p̂_A == 5 should pass"

    def test_custom_threshold(self):
        """threshold=10: n=50, p=0.1 → value=5 < 10 → should fail."""
        conditions = check_clt_conditions(0.1, 50, 0.5, 100, threshold=10)
        assert not conditions[0]["passed"]


# ──────────────────────────────────────────────────────────────


class TestContinuousDifferenceHdi:
    """Tests for continuous_difference_hdi (Welch t HDI for mean_A - mean_B)."""

    def test_equal_means_centered_at_zero(self):
        """mean_A == mean_B → HDI should be centered at 0."""
        hdi_min, hdi_max, se, df = continuous_difference_hdi(5.0, 2.0, 30, 5.0, 2.0, 30)
        midpoint = (hdi_min + hdi_max) / 2
        assert midpoint == pytest.approx(0.0, abs=1e-6)

    def test_returns_four_values(self):
        """Should return (hdi_min, hdi_max, se, df)."""
        result = continuous_difference_hdi(1.0, 1.0, 20, 0.0, 1.0, 20)
        assert len(result) == 4

    def test_positive_delta_shifts_interval(self):
        """mean_A >> mean_B → both HDI bounds should be positive."""
        hdi_min, hdi_max, _, _ = continuous_difference_hdi(10.0, 1.0, 50, 0.0, 1.0, 50)
        assert hdi_min > 0

    def test_raises_for_small_n(self):
        """n < 2 in either group should raise ValueError."""
        with pytest.raises(ValueError):
            continuous_difference_hdi(1.0, 1.0, 1, 0.0, 1.0, 30)
        with pytest.raises(ValueError):
            continuous_difference_hdi(1.0, 1.0, 30, 0.0, 1.0, 1)

    def test_welch_df_less_than_or_equal_pooled(self):
        """Welch df ≤ n_A + n_B - 2 (pooled df); usually strictly less for unequal var."""
        _, _, _, df = continuous_difference_hdi(0.0, 1.0, 20, 0.0, 3.0, 20)
        pooled_df = 20 + 20 - 2
        assert df <= pooled_df + 1e-6  # allow float rounding

    def test_narrower_with_more_data(self):
        """Larger samples → narrower HDI."""
        lo1, hi1, _, _ = continuous_difference_hdi(1.0, 2.0, 10, 0.0, 2.0, 10)
        lo2, hi2, _, _ = continuous_difference_hdi(1.0, 2.0, 100, 0.0, 2.0, 100)
        assert (hi2 - lo2) < (hi1 - lo1)


# ──────────────────────────────────────────────────────────────


class TestBinomialRateCiWidthToSampleSize:
    """Tests for binomial_rate_ci_width_to_sample_size."""

    def test_p_half_gives_largest_n(self):
        """p=0.5 maximises variance → largest required n for a given width."""
        n_half = binomial_rate_ci_width_to_sample_size(0.5, 0.1)
        n_low = binomial_rate_ci_width_to_sample_size(0.1, 0.1)
        assert n_half > n_low

    def test_narrower_width_needs_more_samples(self):
        """Smaller CI width → more samples required."""
        n_wide = binomial_rate_ci_width_to_sample_size(0.5, 0.2)
        n_narrow = binomial_rate_ci_width_to_sample_size(0.5, 0.05)
        assert n_narrow > n_wide

    def test_result_is_positive(self):
        """Sample size should be positive for sensible inputs."""
        n = binomial_rate_ci_width_to_sample_size(0.5, 0.1)
        assert n > 0

    def test_known_approximation(self):
        """Cross-check against textbook formula: n = p(1-p)/(w/2z*)^2 - 1."""
        p, w, z = 0.5, 0.1, 1.96
        expected = p * (1 - p) / (0.5 * w / z) ** 2 - 1
        result = binomial_rate_ci_width_to_sample_size(p, w, z_star=z)
        assert result == pytest.approx(expected, rel=1e-6)
