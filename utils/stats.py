"""
Core statistical functions for HDI (Highest Density Interval) computation.

Ported from precision-goal/py/utils_stats.py
"""
from scipy.optimize import fmin
from scipy.stats import beta, t as student_t
import numpy as np


CI_FRACTION = 0.95


def HDIofICDF(dist_name, ci_fraction=CI_FRACTION, **args):
    """
    Find the Highest Density Interval (HDI) of a probability density function
    specified mathematically in Python.

    Parameters
    ----------
    dist_name : scipy.stats distribution
        A scipy.stats continuous distribution (e.g., beta, student_t).
    ci_fraction : float
        Fraction of the distribution mass to include (default 0.95).
    **args
        Parameters passed to the distribution (e.g., a=, b= for beta).

    Returns
    -------
    np.ndarray
        Array of [hdi_min, hdi_max].

    Example
    -------
    >>> HDIofICDF(beta, a=100, b=100)
    array([0.431, 0.569])  # approximate
    """
    distri = dist_name(**args)
    incredMass = 1.0 - ci_fraction

    def intervalWidth(lowTailPr):
        return distri.ppf(ci_fraction + lowTailPr) - distri.ppf(lowTailPr)

    HDIlowTailPr = fmin(intervalWidth, incredMass, ftol=1e-8, disp=False)[0]
    return distri.ppf([HDIlowTailPr, ci_fraction + HDIlowTailPr])


def successes_failures_to_hdi_ci_limits(a, b, ci_fraction=CI_FRACTION):
    """
    Compute the HDI for a Beta(a, b) posterior (binary/Bernoulli data).

    Parameters
    ----------
    a : float
        Number of successes (alpha parameter of Beta distribution).
    b : float
        Number of failures (beta parameter of Beta distribution).
    ci_fraction : float
        Credible interval fraction (default 0.95).

    Returns
    -------
    tuple
        (hdi_min, hdi_max)
    """
    return HDIofICDF(beta, a=a, b=b, ci_fraction=ci_fraction)


def continuous_hdi_ci_limits(sample_mean, sample_std, n, ci_fraction=CI_FRACTION):
    """
    Calculate HDI for the mean of a continuous distribution using Student-t distribution.

    Based on CLT: the posterior of the mean is Student-t distributed
    when the population variance is unknown and estimated from the sample.

    Parameters
    ----------
    sample_mean : float
        Sample mean.
    sample_std : float
        Sample standard deviation.
    n : int
        Sample size.
    ci_fraction : float
        Credible interval fraction (default 0.95).

    Returns
    -------
    tuple
        (hdi_min, hdi_max)

    Raises
    ------
    ValueError
        If n < 2.
    """
    if n < 2:
        raise ValueError(
            f"Sample size must be at least 2 for t-distribution HDI calculation. Got n={n}"
        )

    df = n - 1
    se = sample_std / np.sqrt(n)

    return HDIofICDF(student_t, df=df, loc=sample_mean, scale=se, ci_fraction=ci_fraction)


def beta_overlap(a1, b1, a2, b2, n_points=2000):
    """
    Compute the overlap coefficient between two Beta distributions.

    OVL = ∫₀¹ min(f₁(x), f₂(x)) dx

    Returns a value in [0, 1]:
    - 0 means no overlap (distributions are completely separated)
    - 1 means identical distributions

    Parameters
    ----------
    a1, b1 : float
        Alpha and beta parameters of the first Beta distribution.
    a2, b2 : float
        Alpha and beta parameters of the second Beta distribution.
    n_points : int
        Number of grid points for numerical integration (default 2000).

    Returns
    -------
    float
        Overlap coefficient in [0, 1].
    """
    x = np.linspace(0, 1, n_points)
    pdf1 = beta(a1, b1).pdf(x)
    pdf2 = beta(a2, b2).pdf(x)
    overlap = np.trapz(np.minimum(pdf1, pdf2), x)
    return float(overlap)


def binary_difference_hdi(p_a, n_a, p_b, n_b, ci_fraction=CI_FRACTION):
    """
    Compute the HDI for the difference δ = p_A - p_B using the CLT approximation.

    The difference of two independent proportions is approximately Normal:
        δ ~ N(p_A - p_B, SE²)
    where SE = sqrt(p_A(1-p_A)/n_A + p_B(1-p_B)/n_B)

    The HDI for a Normal distribution is symmetric:
        HDI = δ ± z_{α/2} · SE

    Parameters
    ----------
    p_a : float
        Observed proportion in group A.
    n_a : int
        Sample size in group A.
    p_b : float
        Observed proportion in group B.
    n_b : int
        Sample size in group B.
    ci_fraction : float
        Credible interval fraction (default 0.95).

    Returns
    -------
    tuple
        (hdi_min, hdi_max)

    Raises
    ------
    ValueError
        If CLT conditions are not met (any of the four np >= 5 checks fail).
    """
    from scipy.stats import norm

    delta = p_a - p_b
    se = np.sqrt(p_a * (1 - p_a) / n_a + p_b * (1 - p_b) / n_b)

    z = norm.ppf((1 + ci_fraction) / 2)
    hdi_min = delta - z * se
    hdi_max = delta + z * se

    return (hdi_min, hdi_max)


def check_clt_conditions(p_a, n_a, p_b, n_b, threshold=5):
    """
    Check the CLT rule-of-thumb conditions for comparing two proportions.

    All four of these must hold:
        n_A * p_A >= 5,  n_A * (1-p_A) >= 5,
        n_B * p_B >= 5,  n_B * (1-p_B) >= 5

    Parameters
    ----------
    p_a : float
        Observed proportion in group A.
    n_a : int
        Sample size in group A.
    p_b : float
        Observed proportion in group B.
    n_b : int
        Sample size in group B.
    threshold : int
        Minimum value for each condition (default 5).

    Returns
    -------
    list of dict
        Each dict has keys: "label", "value", "passed".
    """
    conditions = [
        {"label": "n_A × p̂_A", "value": n_a * p_a, "passed": n_a * p_a >= threshold},
        {"label": "n_A × (1−p̂_A)", "value": n_a * (1 - p_a), "passed": n_a * (1 - p_a) >= threshold},
        {"label": "n_B × p̂_B", "value": n_b * p_b, "passed": n_b * p_b >= threshold},
        {"label": "n_B × (1−p̂_B)", "value": n_b * (1 - p_b), "passed": n_b * (1 - p_b) >= threshold},
    ]
    return conditions


def continuous_difference_hdi(mean_a, std_a, n_a, mean_b, std_b, n_b, ci_fraction=CI_FRACTION):
    """
    Compute the HDI for the difference δ = mean_A - mean_B using Welch's t-approximation.

    The difference is distributed as:
        δ ~ t_ν(mean_A - mean_B, SE)

    where SE = sqrt(s_A² / n_A + s_B² / n_B)
    and ν is the Welch–Satterthwaite degrees of freedom.

    Parameters
    ----------
    mean_a : float
        Sample mean of group A.
    std_a : float
        Sample standard deviation of group A.
    n_a : int
        Sample size of group A.
    mean_b : float
        Sample mean of group B.
    std_b : float
        Sample standard deviation of group B.
    n_b : int
        Sample size of group B.
    ci_fraction : float
        Credible interval fraction (default 0.95).

    Returns
    -------
    tuple
        (hdi_min, hdi_max, se, df) — HDI bounds, standard error, degrees of freedom.

    Raises
    ------
    ValueError
        If either sample size is less than 2.
    """
    if n_a < 2 or n_b < 2:
        raise ValueError(
            f"Both sample sizes must be at least 2. Got n_A={n_a}, n_B={n_b}"
        )

    delta = mean_a - mean_b
    var_a = std_a ** 2 / n_a
    var_b = std_b ** 2 / n_b
    se = np.sqrt(var_a + var_b)

    # Welch–Satterthwaite degrees of freedom
    df = (var_a + var_b) ** 2 / (var_a ** 2 / (n_a - 1) + var_b ** 2 / (n_b - 1))

    hdi_min, hdi_max = HDIofICDF(student_t, df=df, loc=delta, scale=se, ci_fraction=ci_fraction)

    return (hdi_min, hdi_max, se, df)


def binomial_rate_ci_width_to_sample_size(p, credible_interval_width, z_star=1.96):
    """
    Approximate sample size needed for a given CI width (normal approximation).

    Parameters
    ----------
    p : float
        Expected success rate.
    credible_interval_width : float
        Desired CI width.
    z_star : float
        Z critical value (default 1.96 for ~95%).

    Returns
    -------
    float
        Approximate sample size.
    """
    variance_ = (0.5 * credible_interval_width / z_star) ** 2
    n_ = p * (1 - p) / variance_ - 1
    return n_


# ══════════════════════════════════════════════════════════════
# TODO (v2.0): Categorical Variables - Full Dirichlet Posterior
# ══════════════════════════════════════════════════════════════
#
# For proper categorical analysis with joint uncertainty:
#
# 1. Dirichlet conjugate posterior:
#    - Data: counts (n₁, n₂, ..., nₖ) across k categories
#    - Prior: Dirichlet(α₁, ..., αₖ) [e.g., uniform α=1 for all]
#    - Posterior: Dirichlet(α₁+n₁, ..., αₖ+nₖ)
#
# 2. Multivariate HDI computation:
#    - No analytical solution for Dirichlet HDI
#    - Requires Monte Carlo sampling + convex hull algorithm
#    - Suggested approach:
#      a) Sample N points from Dirichlet posterior
#      b) Compute probability density at each point
#      c) Find threshold where mass = HDI fraction
#      d) HDI region = {points with density > threshold}
#
# 3. Implementation references:
#    - PyMC for MCMC sampling
#    - scipy.spatial.ConvexHull for region boundary
#    - Or use approximate region from marginal HDIs
#
# 4. Visualization:
#    - Ternary plot (3 categories)
#    - Parallel coordinates (4+ categories)
#    - Marginal density plots for each category
