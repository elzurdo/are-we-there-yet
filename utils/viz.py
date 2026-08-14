"""
Visualization utilities for posterior distributions with HDI and ROPE.
"""
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import beta, t as student_t

from utils.decision import DecisionResult, DECISION_DISPLAY
from utils.stats import binomial_rate_ci_width_to_sample_size


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


def plot_two_beta_posteriors(a1, b1, a2, b2, overlap, decimal_places: int = 3,
                             label_a: str = "Group A", label_b: str = "Group B"):
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
    label_a : str
        Label for the first group (default "Group A").
    label_b : str
        Label for the second group (default "Group B").

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
    ax.plot(x, y_a, color="steelblue", linewidth=2, label=f"{label_a} (p̂={mean_a:{fmt}})")
    ax.plot(x, y_b, color="darkorange", linewidth=2, label=f"{label_b} (p̂={mean_b:{fmt}})")

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


def plot_two_continuous_posteriors(
    mean_a, std_a, n_a, mean_b, std_b, n_b,
    overlap, decimal_places: int = 3,
    label_a: str = "Group A", label_b: str = "Group B",
):
    """
    Plot two Student-t posteriors on the same axes with overlap shading.

    Parameters
    ----------
    mean_a, std_a, n_a : float
        Sample mean, std, and size for group A.
    mean_b, std_b, n_b : float
        Sample mean, std, and size for group B.
    overlap : float
        Pre-computed overlap coefficient (displayed in title).
    decimal_places : int
        Number of decimal places for annotations.
    label_a : str
        Label for the first group (default "Group A").
    label_b : str
        Label for the second group (default "Group B").

    Returns
    -------
    matplotlib.figure.Figure
    """
    fmt = f".{decimal_places}f"

    se_a = std_a / np.sqrt(n_a)
    se_b = std_b / np.sqrt(n_b)
    dist_a = student_t(df=n_a - 1, loc=mean_a, scale=se_a)
    dist_b = student_t(df=n_b - 1, loc=mean_b, scale=se_b)

    # x range: cover both distributions
    x_lo = min(dist_a.ppf(0.001), dist_b.ppf(0.001))
    x_hi = max(dist_a.ppf(0.999), dist_b.ppf(0.999))
    x = np.linspace(x_lo, x_hi, 1000)
    y_a = dist_a.pdf(x)
    y_b = dist_b.pdf(x)

    fig, ax = plt.subplots(figsize=(8, 4))

    ax.plot(x, y_a, color="steelblue", linewidth=2, label=f"{label_a} (x̄={mean_a:{fmt}})")
    ax.plot(x, y_b, color="darkorange", linewidth=2, label=f"{label_b} (x̄={mean_b:{fmt}})")

    y_min = np.minimum(y_a, y_b)
    ax.fill_between(x, y_min, alpha=0.25, color="mediumpurple", label=f"Overlap = {overlap:{fmt}}")
    ax.fill_between(x, y_a, alpha=0.08, color="steelblue")
    ax.fill_between(x, y_b, alpha=0.08, color="darkorange")

    ax.set_title(f"Individual Group Posteriors  —  Overlap = {overlap:{fmt}}", fontsize=13)
    ax.set_xlabel("μ", fontsize=12)
    ax.set_ylabel("Density", fontsize=12)
    ax.legend(loc="upper right", fontsize=9)
    ax.set_yticks([])
    fig.tight_layout()
    return fig


def plot_nhst_posterior(
    observed: float,
    null_value: float,
    se: float,
    test_stat: float,
    p_value: float,
    dist=None,
    x_label: str = "θ",
    decimal_places: int = 3,
):
    """
    Plot posterior/sampling distribution with color-coded p-value tail regions.

    Parameters
    ----------
    observed : float
        Observed statistic.
    null_value : float
        Null hypothesis value.
    se : float
        Standard error.
    test_stat : float
        z or t statistic.
    p_value : float
        Two-tailed p-value.
    dist : scipy.stats frozen distribution, optional
        The distribution to plot. If None, uses Normal(null_value, se).
    x_label : str
        X-axis label (default "θ").
    decimal_places : int
        Number of decimal places for annotations.

    Returns
    -------
    matplotlib.figure.Figure
    """
    from scipy.stats import norm

    fmt = f".{decimal_places}f"

    if dist is None:
        dist = norm(loc=null_value, scale=se)

    # X range: center on null, extend to show tails
    margin = 4 * se
    x_min = null_value - margin
    x_max = null_value + margin
    x = np.linspace(x_min, x_max, 1000)
    y = dist.pdf(x)

    fig, ax = plt.subplots(figsize=(8, 4))

    # Plot PDF
    ax.plot(x, y, color="steelblue", linewidth=2)

    # Shade tail regions (p-value areas) in red
    # Compute critical value: how far from null is the observed?
    distance = abs(observed - null_value)
    left_tail = null_value - distance
    right_tail = null_value + distance

    # Left tail
    left_mask = x <= left_tail
    ax.fill_between(x, y, where=left_mask, alpha=0.3, color="salmon",
                    label=f"p-value tails")

    # Right tail
    right_mask = x >= right_tail
    ax.fill_between(x, y, where=right_mask, alpha=0.3, color="salmon")

    # Main body (non-tail region)
    body_mask = (x > left_tail) & (x < right_tail)
    ax.fill_between(x, y, where=body_mask, alpha=0.15, color="steelblue")

    # Null hypothesis line
    ax.axvline(null_value, color="gray", linestyle="--", linewidth=1.5,
               alpha=0.7, label=f"H₀: {x_label} = {null_value:{fmt}}")

    # Observed value line
    ax.axvline(observed, color="darkred", linestyle="-", linewidth=2,
               alpha=0.8, label=f"Observed = {observed:{fmt}}")

    # Annotations
    stat_label = "z" if hasattr(dist, "cdf") and dist.dist.name == "norm" else "t"
    ax.annotate(
        f"{stat_label} = {test_stat:{fmt}}\np = {p_value:.4f}",
        xy=(0.98, 0.95), xycoords="axes fraction",
        fontsize=10, verticalalignment="top", horizontalalignment="right",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="white", alpha=0.8)
    )

    ax.set_title("NHST: Sampling Distribution Under H₀", fontsize=13)
    ax.set_xlabel(x_label, fontsize=12)
    ax.set_ylabel("Density", fontsize=12)
    ax.legend(loc="upper left", fontsize=9)
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

    # ROPE region
    ax.axvspan(result.rope_min, result.rope_max, alpha=0.12, color="gray",
               label="ROPE")
    ax.axvline(result.rope_min, color="gray", linestyle="--", linewidth=1, alpha=0.7)
    ax.axvline(result.rope_max, color="gray", linestyle="--", linewidth=1, alpha=0.7)

    # Plot PDF
    ax.plot(x, y, color="purple", linewidth=2)

    # Shade HDI region
    hdi_mask = (x >= result.hdi_min) & (x <= result.hdi_max)
    ax.fill_between(x, y, where=hdi_mask, alpha=0.3, color="purple",
                    label=f"{result.ci_fraction:.0%} HDI")


    # HDI boundaries: No need to much clutter
    #ax.axvline(result.hdi_min, color="purple", linestyle=":", linewidth=1.5, alpha=0.8)
    #ax.axvline(result.hdi_max, color="purple", linestyle=":", linewidth=1.5, alpha=0.8)

    # Point estimate
    estimate_str = r"$\hat{\theta}$"
    ax.axvline(result.point_estimate, color="purple", linestyle="-", linewidth=1.5,
               alpha=0.9, label=f"{estimate_str} = {result.point_estimate:{fmt}}")

    # Annotations
    y_max = ax.get_ylim()[1]
    ax.annotate(f"HDI : [{result.hdi_min:{fmt}}, {result.hdi_max:{fmt}}]",
                xy=(0.02, 0.95), xycoords="axes fraction",
                fontsize=9, color="purple", verticalalignment="top")

    ax.annotate(f"ROPE: [{result.rope_min:{fmt}}, {result.rope_max:{fmt}}]",
                xy=(0.02, 0.88), xycoords="axes fraction",
                fontsize=9, color="gray", verticalalignment="top")

    # Title with verdict
    # TODO: look into why the emoji doesn't display
    # verdict_text = f"{display['emoji']} {display['label']}"
    verdict_text = f"{display['label']}"
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


def plot_bayes_factor_prior_posterior(
    successes: int,
    failures: int,
    prior_alpha: float,
    prior_beta: float,
    theta_null: float,
    bf_10: float,
    show_density_ratio: bool = False,
    decimal_places: int = 3,
):
    """
    Plot prior vs posterior distributions for Bayes Factor interpretation.
    
    Visualizes how the data updated beliefs from prior to posterior, with
    optional Savage-Dickey density ratio visualization.
    
    Parameters
    ----------
    successes : int
        Number of successes observed
    failures : int
        Number of failures observed
    prior_alpha : float
        Beta prior shape parameter α
    prior_beta : float
        Beta prior shape parameter β
    theta_null : float
        Null hypothesis value
    bf_10 : float
        Computed Bayes Factor
    show_density_ratio : bool
        If True, show Savage-Dickey density ratio visualization
    decimal_places : int
        Number of decimal places for annotations
    
    Returns
    -------
    matplotlib.figure.Figure
    """
    fmt = f".{decimal_places}f"
    
    # Create distributions
    prior_dist = beta(prior_alpha, prior_beta)
    posterior_dist = beta(successes + prior_alpha, failures + prior_beta)
    
    # Generate x values
    x = np.linspace(0, 1, 1000)
    y_prior = prior_dist.pdf(x)
    y_posterior = posterior_dist.pdf(x)
    
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 5))
    
    # Plot prior and posterior
    ax.plot(x, y_prior, '--', color='gray', linewidth=2, alpha=0.7, 
            label=f'Prior: Beta({prior_alpha}, {prior_beta})')
    ax.plot(x, y_posterior, '-', color='steelblue', linewidth=2.5, 
            label=f'Posterior: Beta({successes + prior_alpha}, {failures + prior_beta})')
    
    # Mark null hypothesis
    ax.axvline(theta_null, color='red', linestyle=':', linewidth=2, alpha=0.6,
               label=f'H₀: θ = {theta_null:{fmt}}')
    
    if show_density_ratio:
        # Savage-Dickey visualization: show density heights at theta_null
        prior_density_at_null = prior_dist.pdf(theta_null)
        posterior_density_at_null = posterior_dist.pdf(theta_null)
        
        # Plot dots at the densities
        ax.plot(theta_null, prior_density_at_null, 'o', color='gray', 
                markersize=10, label=f'Prior density at θ₀')
        ax.plot(theta_null, posterior_density_at_null, 'o', color='steelblue', 
                markersize=10, label=f'Posterior density at θ₀')
        
        # Draw connecting line
        ax.plot([theta_null, theta_null], 
                [posterior_density_at_null, prior_density_at_null],
                'k-', linewidth=1, alpha=0.4)
        
        # Annotate the ratio
        mid_y = (prior_density_at_null + posterior_density_at_null) / 2
        ratio_text = (
            f"Savage-Dickey Ratio:\n"
            f"BF₁₀ = {prior_density_at_null:.2f} / {posterior_density_at_null:.2f}\n"
            f"     ≈ {bf_10:.3f}"
        )
        ax.annotate(ratio_text, 
                    xy=(theta_null, mid_y),
                    xytext=(15, 0), textcoords='offset points',
                    fontsize=9, color='black',
                    bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.3),
                    ha='left')
    
    # Title with BF interpretation
    if bf_10 > 1:
        direction = "H₁"
        color = "darkgreen"
    elif bf_10 < 1:
        direction = "H₀"
        color = "darkred"
    else:
        direction = "neither"
        color = "gray"
    
    title = f"Prior vs Posterior | BF₁₀ = {bf_10:.3f} (favors {direction})"
    ax.set_title(title, fontsize=13, fontweight='bold', color=color)
    
    # Annotations box
    info_text = (
        f"Data: {successes} successes, {failures} failures\n"
        f"Posterior mean: {posterior_dist.mean():{fmt}}\n"
        f"Shift from prior: {posterior_dist.mean() - prior_dist.mean():+{fmt}}"
    )
    ax.text(0.02, 0.98, info_text,
            transform=ax.transAxes,
            fontsize=9, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))
    
    # Labels and legend
    ax.set_xlabel('θ (success probability)', fontsize=12)
    ax.set_ylabel('Density', fontsize=12)
    ax.legend(loc='upper right', fontsize=9)
    ax.set_xlim(0, 1)
    
    # Remove y-ticks for cleaner look
    ax.set_yticks([])
    
    fig.tight_layout()
    return fig


def plot_categorical_forest(
    comparisons: list,
    reference_name: str,
    rope_min: float,
    rope_max: float,
    decimal_places: int = 3,
):
    """
    Forest plot for one-vs-rest categorical comparisons.
    
    Shows HDIs for all category differences vs reference category,
    with ROPE region and color-coded verdicts.
    
    Parameters
    ----------
    comparisons : list of dict
        Each dict contains:
        - 'category': str, category name
        - 'hdi_min': float
        - 'hdi_max': float
        - 'point_estimate': float (difference from reference)
        - 'verdict': str (ACCEPT/REJECT/INCONCLUSIVE/NEEDS_MORE_DATA)
        - 'color': str (color for verdict)
    reference_name : str
        Name of the reference category
    rope_min : float
        ROPE lower bound
    rope_max : float
        ROPE upper bound
    decimal_places : int
        Number of decimal places for annotations
    
    Returns
    -------
    matplotlib.figure.Figure
    """
    fmt = f".{decimal_places}f"
    n_comparisons = len(comparisons)
    
    if n_comparisons == 0:
        # Empty plot with message
        fig, ax = plt.subplots(figsize=(10, 2))
        ax.text(0.5, 0.5, "No comparisons to display", 
                ha='center', va='center', fontsize=12)
        ax.axis('off')
        return fig
    
    # Create figure
    fig_height = max(4, 1.5 + 0.6 * n_comparisons)
    fig, ax = plt.subplots(figsize=(12, fig_height))
    
    # Determine x-axis range
    all_bounds = [c['hdi_min'] for c in comparisons] + [c['hdi_max'] for c in comparisons]
    all_bounds.extend([rope_min, rope_max, 0])
    x_min = min(all_bounds) - 0.05 * (max(all_bounds) - min(all_bounds))
    x_max = max(all_bounds) + 0.05 * (max(all_bounds) - min(all_bounds))
    
    # Plot ROPE region
    ax.axvspan(rope_min, rope_max, alpha=0.15, color='gray', 
               label='ROPE', zorder=0)
    ax.axvline(rope_min, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    ax.axvline(rope_max, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    
    # Reference line at 0
    ax.axvline(0, color='black', linestyle='-', linewidth=1.5, alpha=0.3,
               label=f'No difference from {reference_name}')
    
    # Plot each comparison
    y_positions = list(range(n_comparisons))
    
    for i, comp in enumerate(comparisons):
        y = y_positions[i]
        hdi_min = comp['hdi_min']
        hdi_max = comp['hdi_max']
        point_est = comp['point_estimate']
        category = comp['category']
        color = comp['color']
        
        # Map verdict color to matplotlib color
        color_map = {
            'green': 'darkgreen',
            'red': 'darkred',
            'orange': 'darkorange',
        }
        plot_color = color_map.get(color, 'steelblue')
        
        # Plot HDI line
        ax.plot([hdi_min, hdi_max], [y, y], 
                linewidth=3, color=plot_color, alpha=0.7, zorder=2)
        
        # Plot HDI endpoints
        ax.plot([hdi_min, hdi_max], [y, y], 
                'o', markersize=6, color=plot_color, alpha=0.9, zorder=3)
        
        # Plot point estimate
        ax.plot(point_est, y, 
                'D', markersize=8, color=plot_color, markerfacecolor='white',
                markeredgewidth=2, alpha=0.9, zorder=4)
        
        # Annotate with HDI values
        hdi_text = f"[{hdi_min:{fmt}}, {hdi_max:{fmt}}]"
        ax.text(x_max + 0.01 * (x_max - x_min), y, hdi_text,
                va='center', fontsize=9, color=plot_color)
    
    # Set y-axis labels and limits
    category_labels = [f"{c['category']} vs {reference_name}" for c in comparisons]
    ax.set_yticks(y_positions)
    ax.set_yticklabels(category_labels, fontsize=10)
    ax.set_ylim(-0.5, n_comparisons - 0.5)
    
    # Set x-axis
    ax.set_xlabel('Difference in Proportion', fontsize=12)
    ax.set_xlim(x_min, x_max)
    ax.grid(axis='x', alpha=0.3, linestyle=':', linewidth=0.5)
    
    # Title
    ax.set_title('One-vs-Rest Categorical Comparison (Forest Plot)', 
                 fontsize=14, fontweight='bold', pad=15)
    
    # Legend
    ax.legend(loc='upper right', fontsize=9, framealpha=0.9)
    
    fig.tight_layout()
    return fig


def plot_n_goal_by_parameter(
    omega_goal=None,
    theta_highlight=None,
    z_star=1.96,
    w_goal_min=0.04,
    w_goal_max=0.10,
    n_background_curves=7,
):
    thetas = np.arange(0.01, 0.99, 0.01)

    fig, ax = plt.subplots(figsize=(8, 4))

    bg_goals = np.linspace(w_goal_min, w_goal_max, n_background_curves)
    for goal in bg_goals:
        n_vals = [binomial_rate_ci_width_to_sample_size(theta, goal, z_star=z_star)
                  for theta in thetas]
        ax.plot(thetas, n_vals, color="gray", alpha=0.15, linewidth=1)

    if w_goal_min < w_goal_max:
        n_top = [binomial_rate_ci_width_to_sample_size(theta, w_goal_min, z_star=z_star)
                 for theta in thetas]
        n_bot = [binomial_rate_ci_width_to_sample_size(theta, w_goal_max, z_star=z_star)
                 for theta in thetas]
        ax.fill_between(thetas, n_bot, n_top, alpha=0.06, color="gray")
        ax.text(0.05, max(n_top) * 0.92, f"ω = {w_goal_min}–{w_goal_max}",
                fontsize=8, color="gray", alpha=0.6)

    if omega_goal is not None:
        n_user = [binomial_rate_ci_width_to_sample_size(theta, omega_goal, z_star=z_star)
                  for theta in thetas]
        ax.plot(thetas, n_user, color="steelblue", linewidth=2.5,
                label=f"ω_goal = {omega_goal:.4f}", zorder=3)

        if theta_highlight is not None:
            n_at_theta = binomial_rate_ci_width_to_sample_size(
                theta_highlight, omega_goal, z_star=z_star
            )
            ax.plot(theta_highlight, n_at_theta, "o", color="darkred",
                    markersize=10, zorder=5,
                    label=f"N_goal ≈ {max(1, int(n_at_theta)):,} at θ = {theta_highlight:.2f}")

    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)
    ax.set_xlabel(r"$\theta$", fontsize=12)
    ax.set_ylabel(r"$N_{\rm goal}(\theta,\, \omega_{\rm goal})$", fontsize=12)
    ax.set_title(
        r"Minimum $N_{\rm goal}$ to Achieve Precision Goal",
        fontsize=14,
    )
    ax.set_yticks([])
    fig.tight_layout()
    return fig
