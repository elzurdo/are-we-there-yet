"""
Visualization utilities for posterior distributions with HDI and ROPE.
"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from scipy.stats import beta, t as student_t

from utils.decision import DecisionResult, DECISION_DISPLAY


def plot_posterior_binary(result: DecisionResult, successes: float, failures: float,
                         decimal_places: int = 3):
    """
    Plot the Beta posterior with HDI shading and ROPE region for binary data.

    Parameters
    ----------
    result : DecisionResult
        The ePitG decision output.
    successes : float
        Number of successes (Beta alpha parameter).
    failures : float
        Number of failures (Beta beta parameter).

    Returns
    -------
    matplotlib.figure.Figure
    """
    a, b = successes, failures
    dist = beta(a, b)

    # x range: extend slightly beyond HDI for visual context
    x_min = max(0, result.hdi_min - 0.15)
    x_max = min(1, result.hdi_max + 0.15)
    x = np.linspace(x_min, x_max, 1000)
    y = dist.pdf(x)

    return _plot_posterior(x, y, result, x_bounds=(0, 1), decimal_places=decimal_places)


def plot_posterior_continuous(result: DecisionResult, sample_mean: float,
                              sample_std: float, n: int,
                              decimal_places: int = 3):
    """
    Plot the Student-t posterior with HDI shading and ROPE region for continuous data.

    Parameters
    ----------
    result : DecisionResult
        The ePitG decision output.
    sample_mean : float
        Sample mean.
    sample_std : float
        Sample standard deviation.
    n : int
        Sample size.

    Returns
    -------
    matplotlib.figure.Figure
    """
    df = n - 1
    se = sample_std / np.sqrt(n)
    dist = student_t(df=df, loc=sample_mean, scale=se)

    # x range
    margin = 4 * se
    x_min = min(result.rope_min, result.hdi_min) - margin
    x_max = max(result.rope_max, result.hdi_max) + margin
    x = np.linspace(x_min, x_max, 1000)
    y = dist.pdf(x)

    return _plot_posterior(x, y, result, decimal_places=decimal_places)


def plot_posterior_difference(result: DecisionResult, delta: float, se: float,
                              decimal_places: int = 3, dist=None):
    """
    Plot the posterior of the difference δ with HDI and ROPE.

    Works with any scipy distribution. If `dist` is not provided,
    defaults to Normal(loc=delta, scale=se) (used by binary between-groups).

    Parameters
    ----------
    result : DecisionResult
        The ePitG decision output.
    delta : float
        Observed difference.
    se : float
        Standard error of the difference.
    decimal_places : int
        Number of decimal places for display.
    dist : scipy.stats frozen distribution, optional
        The distribution to plot. If None, uses Normal(delta, se).

    Returns
    -------
    matplotlib.figure.Figure
    """
    if dist is None:
        from scipy.stats import norm
        dist = norm(loc=delta, scale=se)

    # x range
    margin = 4 * se
    x_min = min(result.rope_min, result.hdi_min) - margin
    x_max = max(result.rope_max, result.hdi_max) + margin
    x = np.linspace(x_min, x_max, 1000)
    y = dist.pdf(x)

    return _plot_posterior(x, y, result, decimal_places=decimal_places, x_label="δ (difference)")


def plot_two_beta_posteriors(a1, b1, a2, b2, overlap, decimal_places: int = 3):
    """
    Plot two Beta posteriors on the same axes with overlap shading.

    Parameters
    ----------
    a1, b1 : float
        Alpha and beta parameters for Group A posterior.
    a2, b2 : float
        Alpha and beta parameters for Group B posterior.
    overlap : float
        Pre-computed overlap coefficient (displayed in title).
    decimal_places : int
        Number of decimal places for annotations.

    Returns
    -------
    matplotlib.figure.Figure
    """
    fmt = f".{decimal_places}f"

    dist_a = beta(a1, b1)
    dist_b = beta(a2, b2)

    # x range: cover both distributions
    mean_a, mean_b = a1 / (a1 + b1), a2 / (a2 + b2)
    x_lo = max(0, min(dist_a.ppf(0.001), dist_b.ppf(0.001)))
    x_hi = min(1, max(dist_a.ppf(0.999), dist_b.ppf(0.999)))
    x = np.linspace(x_lo, x_hi, 1000)
    y_a = dist_a.pdf(x)
    y_b = dist_b.pdf(x)

    fig, ax = plt.subplots(figsize=(8, 4))

    # Plot both PDFs
    ax.plot(x, y_a, color="steelblue", linewidth=2, label=f"Group A (p̂={mean_a:{fmt}})")
    ax.plot(x, y_b, color="darkorange", linewidth=2, label=f"Group B (p̂={mean_b:{fmt}})")

    # Shade overlap region
    y_min = np.minimum(y_a, y_b)
    ax.fill_between(x, y_min, alpha=0.25, color="mediumpurple", label=f"Overlap = {overlap:{fmt}}")

    # Light shading for each distribution
    ax.fill_between(x, y_a, alpha=0.08, color="steelblue")
    ax.fill_between(x, y_b, alpha=0.08, color="darkorange")

    ax.set_title(f"Individual Group Posteriors  —  Overlap = {overlap:{fmt}}", fontsize=13)
    ax.set_xlabel("θ", fontsize=12)
    ax.set_ylabel("Density", fontsize=12)
    ax.legend(loc="upper right", fontsize=9)
    ax.set_yticks([])
    fig.tight_layout()
    return fig


def _plot_posterior(x, y, result: DecisionResult, x_bounds=None, decimal_places: int = 3,
                    x_label: str = "θ"):
    """
    Core plotting logic shared by binary and continuous posteriors.

    Parameters
    ----------
    x : np.ndarray
        X values for the PDF.
    y : np.ndarray
        PDF values.
    result : DecisionResult
        Decision output.
    x_bounds : tuple or None
        Optional (min, max) hard bounds for x-axis.

    Returns
    -------
    matplotlib.figure.Figure
    """
    fmt = f".{decimal_places}f"
    display = result.display

    fig, ax = plt.subplots(figsize=(8, 4))

    # Plot PDF
    ax.plot(x, y, color="steelblue", linewidth=2)

    # Shade HDI region
    hdi_mask = (x >= result.hdi_min) & (x <= result.hdi_max)
    ax.fill_between(x, y, where=hdi_mask, alpha=0.3, color="steelblue",
                    label=f"{result.ci_fraction:.0%} HDI")

    # ROPE region
    ax.axvspan(result.rope_min, result.rope_max, alpha=0.12, color="gray",
               label="ROPE")
    ax.axvline(result.rope_min, color="gray", linestyle="--", linewidth=1, alpha=0.7)
    ax.axvline(result.rope_max, color="gray", linestyle="--", linewidth=1, alpha=0.7)

    # HDI boundaries
    ax.axvline(result.hdi_min, color="steelblue", linestyle=":", linewidth=1.5, alpha=0.8)
    ax.axvline(result.hdi_max, color="steelblue", linestyle=":", linewidth=1.5, alpha=0.8)

    # Point estimate
    ax.axvline(result.point_estimate, color="darkblue", linestyle="-", linewidth=1.5,
               alpha=0.6, label=f"Estimate = {result.point_estimate:{fmt}}")

    # Annotations
    y_max = ax.get_ylim()[1]
    ax.annotate(f"HDI: [{result.hdi_min:{fmt}}, {result.hdi_max:{fmt}}]",
                xy=(0.02, 0.95), xycoords="axes fraction",
                fontsize=9, color="steelblue", verticalalignment="top")

    ax.annotate(f"ROPE: [{result.rope_min:{fmt}}, {result.rope_max:{fmt}}]",
                xy=(0.02, 0.88), xycoords="axes fraction",
                fontsize=9, color="gray", verticalalignment="top")

    # Title with verdict
    verdict_text = f"{display['emoji']} {display['label']}"
    ax.set_title(verdict_text, fontsize=14, fontweight="bold",
                 color=display["color"])

    ax.set_xlabel(x_label, fontsize=12)
    ax.set_ylabel("Density", fontsize=12)
    ax.legend(loc="upper right", fontsize=9)

    if x_bounds:
        current_xlim = ax.get_xlim()
        ax.set_xlim(max(x_bounds[0], current_xlim[0]),
                    min(x_bounds[1], current_xlim[1]))

    ax.set_yticks([])
    fig.tight_layout()
    return fig
