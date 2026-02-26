"""
Bayes Factor computations for comparing hypotheses.

Currently implements:
- Binary single-group: Beta-Binomial analytical solution

TODO: Consider using `pingouin` library for:
- Continuous single-group (JZS Bayes Factor for t-tests)
- Between-groups analysis (both binary and continuous)
- More sophisticated prior specifications
"""
import numpy as np
from scipy.special import beta as beta_function
from typing import Tuple, Dict


# ══════════════════════════════════════════════════════════════
# Prior Specifications
# ══════════════════════════════════════════════════════════════

PRIOR_SPECS = {
    "uniform": {
        "alpha": 1.0,
        "beta": 1.0,
        "description": "Beta(1, 1) — Maximum uncertainty, all values equally likely",
    },
    "jeffreys": {
        "alpha": 0.5,
        "beta": 0.5,
        "description": "Beta(0.5, 0.5) — Jeffreys prior, emphasis on extremes",
    },
    "weakly_informative": {
        "alpha": 2.0,
        "beta": 2.0,
        "description": "Beta(2, 2) — Slight preference for moderate values",
    },
}


# ══════════════════════════════════════════════════════════════
# Bayes Factor Computation
# ══════════════════════════════════════════════════════════════

def binary_single_group_bayes_factor(
    successes: int,
    n: int,
    theta_null: float,
    prior_alpha: float = 1.0,
    prior_beta: float = 1.0,
) -> float:
    """
    Compute Bayes Factor (BF₁₀) for binary single-group analysis.
    
    Compares:
    - H₀: θ = θ_null (point null)
    - H₁: θ ~ Beta(α, β) (prior distribution)
    
    Uses analytical Beta-Binomial conjugate solution:
    
    BF₁₀ = P(data | H₁) / P(data | H₀)
         = [B(s+α, f+β) / B(α, β)] / [θ_null^s × (1-θ_null)^f]
    
    where s = successes, f = failures = n - s, B = Beta function.
    
    Parameters
    ----------
    successes : int
        Number of successes observed
    n : int
        Total sample size
    theta_null : float
        Null hypothesis value (0 < θ_null < 1)
    prior_alpha : float
        Shape parameter α for Beta prior under H₁
    prior_beta : float
        Shape parameter β for Beta prior under H₁
    
    Returns
    -------
    bf10 : float
        Bayes Factor in favor of H₁ over H₀.
        BF₁₀ > 1: Evidence for H₁
        BF₁₀ < 1: Evidence for H₀
        BF₁₀ = 1: No preference
    
    Notes
    -----
    - Common priors:
      * Uniform: Beta(1, 1) — maximum uncertainty
      * Jeffreys: Beta(0.5, 0.5) — emphasizes extremes
      * Weakly informative: Beta(2, 2) — slight center preference
    
    - This is exact for conjugate Beta-Binomial
    - For between-groups or continuous cases, numerical methods needed
    """
    failures = n - successes
    
    # Marginal likelihood under H₁: Beta-Binomial
    # P(data | H₁) = C(n,s) × B(s+α, f+β) / B(α, β)
    ml_h1 = (
        beta_function(successes + prior_alpha, failures + prior_beta)
        / beta_function(prior_alpha, prior_beta)
    )
    
    # Likelihood under H₀: Binomial
    # P(data | H₀) = C(n,s) × θ_null^s × (1-θ_null)^f
    ml_h0 = (theta_null ** successes) * ((1 - theta_null) ** failures)
    
    # Bayes Factor (binomial coefficient cancels)
    bf10 = ml_h1 / ml_h0
    
    return bf10


# ══════════════════════════════════════════════════════════════
# Interpretation Scales
# ══════════════════════════════════════════════════════════════

def interpret_bayes_factor_jeffreys(bf10: float) -> Tuple[str, str]:
    """
    Interpret Bayes Factor using Jeffreys (1961) scale.
    
    Returns
    -------
    category : str
        Evidence category (e.g., "Moderate evidence for H₁")
    color_emoji : str
        Visual indicator (🔴/🟠/🟡/🟢/🔵)
    """
    abs_bf = bf10 if bf10 >= 1 else 1 / bf10
    direction = "H₁" if bf10 >= 1 else "H₀"
    
    if abs_bf < 1:
        # Should not happen, but safety
        category = "Error"
        emoji = "⚠️"
    elif abs_bf < 3:
        category = f"Weak evidence for {direction}"
        emoji = "🟡"
    elif abs_bf < 10:
        category = f"Moderate evidence for {direction}"
        emoji = "🟠"
    elif abs_bf < 30:
        category = f"Strong evidence for {direction}"
        emoji = "🔵"
    elif abs_bf < 100:
        category = f"Very strong evidence for {direction}"
        emoji = "🟢"
    else:
        category = f"Decisive evidence for {direction}"
        emoji = "🔴"
    
    return category, emoji


def interpret_bayes_factor_kass_raftery(bf10: float) -> Tuple[str, str]:
    """
    Interpret Bayes Factor using Kass & Raftery (1995) scale.
    
    Returns
    -------
    category : str
        Evidence category
    color_emoji : str
        Visual indicator
    """
    abs_bf = bf10 if bf10 >= 1 else 1 / bf10
    direction = "H₁" if bf10 >= 1 else "H₀"
    
    if abs_bf < 1:
        category = "Error"
        emoji = "⚠️"
    elif abs_bf < 3:
        category = f"Not worth more than a bare mention for {direction}"
        emoji = "🟡"
    elif abs_bf < 20:
        category = f"Positive evidence for {direction}"
        emoji = "🟠"
    elif abs_bf < 150:
        category = f"Strong evidence for {direction}"
        emoji = "🔵"
    else:
        category = f"Very strong evidence for {direction}"
        emoji = "🟢"
    
    return category, emoji


def get_interpretation_scales() -> Dict[str, callable]:
    """Return available interpretation scales."""
    return {
        "jeffreys": interpret_bayes_factor_jeffreys,
        "kass_raftery": interpret_bayes_factor_kass_raftery,
    }
