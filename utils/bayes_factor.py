"""
Bayes Factor computations for comparing hypotheses.

Implements:
- Binary single-group:    Beta-Binomial analytical (Savage-Dickey)
- Binary between-groups:  Beta-Binomial analytical (Gunel & Dickey 1974)
- Continuous single-group:  JZS prior, 1D numerical integration (Rouder et al. 2009)
- Continuous between-groups: JZS prior, 1D numerical integration (Rouder et al. 2009)
"""
import numpy as np
from scipy.special import beta as beta_function, betaln
from scipy.integrate import quad
from scipy.stats import t as student_t
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

# Cauchy scale options for the JZS prior (continuous BF).
# r controls prior width on standardised effect size δ = (μ − μ_null)/σ.
JZS_PRIOR_SPECS = {
    "narrow": {
        "r": 0.5,
        "description": "Cauchy(0, 0.5) — Conservative; concentrates mass near zero",
    },
    "medium": {
        "r": 1.0 / np.sqrt(2),   # ≈ 0.707 — JASP / BayesFactor R package default
        "description": "Cauchy(0, √½ ≈ 0.707) — JASP / BayesFactor R default",
    },
    "wide": {
        "r": 1.0,
        "description": "Cauchy(0, 1) — Generous; allows larger effects a priori",
    },
}


# ══════════════════════════════════════════════════════════════
# Binary — Single Group
# ══════════════════════════════════════════════════════════════

def binary_single_group_bayes_factor(
    successes: int,
    n: int,
    theta_null: float,
    prior_alpha: float = 1.0,
    prior_beta: float = 1.0,
) -> float:
    """
    BF₁₀ for binary single-group analysis (Beta-Binomial conjugate).

    H₀: θ = θ_null (point null)
    H₁: θ ~ Beta(α, β)

    BF₁₀ = [B(s+α, f+β) / B(α, β)] / [θ_null^s × (1−θ_null)^f]

    where s = successes, f = failures.
    """
    failures = n - successes

    ml_h1 = (
        beta_function(successes + prior_alpha, failures + prior_beta)
        / beta_function(prior_alpha, prior_beta)
    )
    ml_h0 = (theta_null ** successes) * ((1 - theta_null) ** failures)

    return ml_h1 / ml_h0


# ══════════════════════════════════════════════════════════════
# Binary — Between Groups
# ══════════════════════════════════════════════════════════════

def binary_between_groups_bayes_factor(
    s_a: int,
    f_a: int,
    s_b: int,
    f_b: int,
    prior_alpha: float = 1.0,
    prior_beta: float = 1.0,
) -> float:
    """
    BF₁₀ for binary between-groups analysis (Beta-Binomial conjugate).

    H₀: θ_A = θ_B (shared proportion, one Beta(α,β) prior)
    H₁: θ_A, θ_B independent, each Beta(α, β)

    BF₁₀ = B(s_A+α, f_A+β) × B(s_B+α, f_B+β)
            ─────────────────────────────────────────
            B(α, β) × B(s_A+s_B+α, f_A+f_B+β)

    Computed in log-space via betaln for numerical stability.

    Parameters
    ----------
    s_a, f_a : int
        Successes and failures for group A.
    s_b, f_b : int
        Successes and failures for group B.
    prior_alpha, prior_beta : float
        Shared Beta prior parameters under H₁.

    Notes
    -----
    # TODO (non-zero null): This BF tests H₀: θ_A = θ_B (Δ₀ = 0) only.
    # Supporting a general null Δ₀ = θ_A − θ_B ≠ 0 requires 1D numerical
    # integration because the constraint θ_A − θ_B = Δ₀ is not conjugate —
    # there is no closed-form marginal likelihood under H₀ for Δ₀ ≠ 0.
    # Not implemented because: (a) Δ₀ = 0 covers the overwhelming majority
    # of use cases; (b) no standard reference prior exists for the constrained
    # case; (c) the ROPE framework already handles the effect-size question.
    # See also TODO.md § 10a.

    Reference
    ---------
    Gunel, E. & Dickey, J. (1974). Bayes Factors for Independence in
    Contingency Tables. Biometrika, 61(3), 545–557.
    """
    # TODO (tests): Add unit tests covering:
    # - Equal groups (s_a=f_a=s_b=f_b) → BF10 < 1 (data favor H₀: shared proportion)
    # - Highly unequal groups (s_a≈n_a, s_b≈0) → BF10 >> 1
    # - All three PRIOR_SPECS (uniform, jeffreys, weakly_informative)
    # - Symmetry: BF(s_a,f_a,s_b,f_b) == BF(s_b,f_b,s_a,f_a)
    # - Edge: single observation per group (s_a=1, f_a=0, s_b=0, f_b=1)
    log_bf = (
        betaln(s_a + prior_alpha, f_a + prior_beta)
        + betaln(s_b + prior_alpha, f_b + prior_beta)
        - betaln(prior_alpha, prior_beta)
        - betaln(s_a + s_b + prior_alpha, f_a + f_b + prior_beta)
    )
    return float(np.exp(log_bf))


# ══════════════════════════════════════════════════════════════
# Continuous — Single Group (JZS)
# ══════════════════════════════════════════════════════════════

def continuous_single_group_bayes_factor(
    sample_mean: float,
    sample_std: float,
    n: int,
    mu_null: float = 0.0,
    r: float = 1.0 / np.sqrt(2),
) -> float:
    """
    BF₁₀ for continuous single-group analysis using the JZS prior.

    H₀: μ = μ_null (point null)
    H₁: δ = (μ − μ_null)/σ ~ Cauchy(0, r)

    BF₁₀ = [∫₀^∞ (1+ng)^(−½) (1+t²/(ν(1+ng)))^(−(ν+1)/2) g^(−3/2) e^{−1/(2r²g)} / √(2πr²) dg]
            ─────────────────────────────────────────────────────────────────────────────────────────
            Student-t pdf(t; ν)

    where t = (x̄ − μ_null)/(s/√n), ν = n − 1.

    The integral is evaluated via adaptive quadrature on log(g) for stability.

    Parameters
    ----------
    sample_mean, sample_std : float
        Observed mean and standard deviation.
    n : int
        Sample size.
    mu_null : float
        Null hypothesis value for the mean.
    r : float
        Cauchy scale for the JZS prior (default √½ ≈ 0.707, JASP default).

    Reference
    ---------
    Rouder, J.N., Speckman, P.L., Sun, D., Morey, R.D., & Iverson, G. (2009).
    Bayesian t tests for accepting and rejecting the null hypothesis.
    Psychonomic Bulletin & Review, 16(2), 225–237.
    """
    t_stat = (sample_mean - mu_null) / (sample_std / np.sqrt(n))
    df = n - 1

    # TODO (tests): Add unit tests covering:
    # - Mean at null (sample_mean == mu_null) → BF10 < 1 (data favor H₀)
    # - Mean far from null (large |t|) → BF10 >> 1
    # - All three JZS_PRIOR_SPECS (narrow, medium, wide)
    # - Increasing n with fixed t should increase BF10 (more data = more evidence)
    # - Cross-check selected values against the BayesFactor R package or pingouin
    # - Edge: n=2 (df=1, heavy-tailed posterior)

    # Integrate over u = log(g) on a finite range — the integrand is
    # effectively 0 outside [-50, 50] for any practical n, t, r.
    # Using log-space arithmetic avoids exp overflow/underflow.
    # After the u-substitution the g^(-3/2)*g Jacobian simplifies to g^(-1/2).
    def log_space_integrand(u: float) -> float:
        g = np.exp(u)
        inner = 1.0 + n * g
        t_term = 1.0 + t_stat ** 2 / (df * inner)
        exp_arg = -1.0 / (2.0 * r ** 2 * g)
        log_val = (
            -0.5 * np.log(inner)
            - (df + 1) / 2.0 * np.log(t_term)
            - 0.5 * u
            + exp_arg
            - 0.5 * np.log(2.0 * np.pi * r ** 2)
        )
        return float(np.exp(log_val)) if np.isfinite(log_val) else 0.0

    numerator, _ = quad(log_space_integrand, -50.0, 50.0, limit=500)
    denominator = float(student_t.pdf(t_stat, df=df))

    if denominator == 0.0:
        return np.inf
    return numerator / denominator


# ══════════════════════════════════════════════════════════════
# Continuous — Between Groups (JZS)
# ══════════════════════════════════════════════════════════════

def continuous_between_groups_bayes_factor(
    mean_a: float,
    std_a: float,
    n_a: int,
    mean_b: float,
    std_b: float,
    n_b: int,
    r: float = 1.0 / np.sqrt(2),
) -> float:
    """
    BF₁₀ for continuous between-groups analysis using the JZS prior.

    H₀: μ_A − μ_B = 0
    H₁: δ = (μ_A − μ_B)/σ_pooled ~ Cauchy(0, r)

    Uses Welch's t-statistic and Welch-Satterthwaite degrees of freedom,
    with effective sample size n_eff = n_A·n_B/(n_A+n_B).

    Same integrand as the one-sample case with n → n_eff and ν → ν_Welch.

    Parameters
    ----------
    mean_a, std_a, n_a : float, float, int
        Group A summary statistics.
    mean_b, std_b, n_b : float, float, int
        Group B summary statistics.
    r : float
        Cauchy scale for the JZS prior (default √½ ≈ 0.707, JASP default).

    Notes
    -----
    # TODO (non-zero null): This BF tests H₀: μ_A − μ_B = 0 only.
    # Extending to Δ₀ ≠ 0 is straightforward — replace t with
    # t′ = (x̄_A − x̄_B − Δ₀) / SE_Welch in the same integrand — but is
    # omitted because Δ₀ = 0 covers the common use case and the ROPE
    # already handles effect-size reasoning. See also TODO.md § 10c.

    Reference
    ---------
    Rouder, J.N., Speckman, P.L., Sun, D., Morey, R.D., & Iverson, G. (2009).
    Bayesian t tests for accepting and rejecting the null hypothesis.
    Psychonomic Bulletin & Review, 16(2), 225–237.
    """
    var_a = std_a ** 2
    var_b = std_b ** 2
    se = np.sqrt(var_a / n_a + var_b / n_b)
    t_stat = (mean_a - mean_b) / se

    # Welch-Satterthwaite degrees of freedom
    df = (var_a / n_a + var_b / n_b) ** 2 / (
        (var_a / n_a) ** 2 / (n_a - 1) + (var_b / n_b) ** 2 / (n_b - 1)
    )

    # Effective sample size for the JZS prior scaling
    n_eff = (n_a * n_b) / (n_a + n_b)

    # TODO (tests): Add unit tests covering:
    # - Equal groups (mean_a == mean_b) → BF10 < 1 (data favor H₀: no difference)
    # - Means far apart (large |t|) → BF10 >> 1
    # - All three JZS_PRIOR_SPECS (narrow, medium, wide)
    # - Symmetry: BF(a, b) == BF(b, a) (swapping groups leaves BF unchanged)
    # - Unequal variances and unequal n (Welch path is exercised)
    # - Cross-check selected values against BayesFactor R package or pingouin
    def log_space_integrand(u: float) -> float:
        g = np.exp(u)
        inner = 1.0 + n_eff * g
        t_term = 1.0 + t_stat ** 2 / (df * inner)
        exp_arg = -1.0 / (2.0 * r ** 2 * g)
        log_val = (
            -0.5 * np.log(inner)
            - (df + 1) / 2.0 * np.log(t_term)
            - 0.5 * u
            + exp_arg
            - 0.5 * np.log(2.0 * np.pi * r ** 2)
        )
        return float(np.exp(log_val)) if np.isfinite(log_val) else 0.0

    numerator, _ = quad(log_space_integrand, -50.0, 50.0, limit=500)
    denominator = float(student_t.pdf(t_stat, df=df))

    if denominator == 0.0:
        return np.inf
    return numerator / denominator


# ══════════════════════════════════════════════════════════════
# Interpretation Scales
# ══════════════════════════════════════════════════════════════

def interpret_bayes_factor_jeffreys(bf10: float) -> Tuple[str, str]:
    """
    Interpret Bayes Factor using Jeffreys (1961) scale.

    Returns (category, emoji).
    """
    abs_bf = bf10 if bf10 >= 1 else 1 / bf10
    direction = "H₁" if bf10 >= 1 else "H₀"

    if abs_bf < 3:
        return f"Weak evidence for {direction}", "🟡"
    elif abs_bf < 10:
        return f"Moderate evidence for {direction}", "🟠"
    elif abs_bf < 30:
        return f"Strong evidence for {direction}", "🔵"
    elif abs_bf < 100:
        return f"Very strong evidence for {direction}", "🟢"
    else:
        return f"Decisive evidence for {direction}", "🔴"


def interpret_bayes_factor_kass_raftery(bf10: float) -> Tuple[str, str]:
    """
    Interpret Bayes Factor using Kass & Raftery (1995) scale.

    Returns (category, emoji).
    """
    abs_bf = bf10 if bf10 >= 1 else 1 / bf10
    direction = "H₁" if bf10 >= 1 else "H₀"

    if abs_bf < 3:
        return f"Not worth more than a bare mention for {direction}", "🟡"
    elif abs_bf < 20:
        return f"Positive evidence for {direction}", "🟠"
    elif abs_bf < 150:
        return f"Strong evidence for {direction}", "🔵"
    else:
        return f"Very strong evidence for {direction}", "🟢"


def get_interpretation_scales() -> Dict[str, callable]:
    """Return available interpretation scale callables."""
    return {
        "jeffreys": interpret_bayes_factor_jeffreys,
        "kass_raftery": interpret_bayes_factor_kass_raftery,
    }
