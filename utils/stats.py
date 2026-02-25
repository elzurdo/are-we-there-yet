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
