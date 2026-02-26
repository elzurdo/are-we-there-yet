"""
Tutorial text constants for the ePitG Decision Advisor.

Centralized source of truth for all tutorial and explanatory content
to avoid duplication across tabs.
"""

# ──────────────────────────────────────────────────────────────
# Shared Tutorial Texts
# ──────────────────────────────────────────────────────────────

NHST_LIMITATIONS = """
**Limitations of NHST (p-value) stopping criteria:**

1. **No precision guarantee**: A p < 0.05 doesn't tell you how narrow your confidence interval is. 
   You could have a very wide CI that still yields statistical significance.

2. **Dichotomous thinking**: NHST forces a binary decision (reject/not reject) that ignores effect size. 
   A tiny, practically meaningless difference can be "significant" with enough data.

3. **No stopping rule**: Traditional NHST doesn't tell you *when* to stop collecting data. 
   The ePitG method explicitly plans for a precision goal.

4. **Ignores practical equivalence**: NHST can't distinguish between "no effect" and "effect is 
   too small to matter." The ROPE addresses this directly.

**ePitG combines:**
- **Precision** (HDI width < Goal) — ensures your estimate is narrow enough
- **Location** (HDI vs ROPE) — ensures you can make a conclusive decision about practical significance

This gives you both statistical confidence *and* practical interpretability.
"""


# ──────────────────────────────────────────────────────────────
# Binary Variables: Maths Tutorials
# ──────────────────────────────────────────────────────────────

MATHS_BINARY_SINGLE_GROUP = r"""
**Single proportion inference using Bayesian Beta posterior**

When we observe binary outcomes (successes and failures):
- Successes: $s$
- Failures: $f$
- Total: $n = s + f$

**Bayesian approach with uniform prior:**

The posterior distribution for the true proportion $\theta$ is a Beta distribution:

$$\theta \mid \text{data} \;\sim\; \text{Beta}(s + 1,\; f + 1)$$

This is a **conjugate prior** setup: Beta prior + Binomial likelihood → Beta posterior.

**The HDI** (Highest Density Interval) is computed numerically on this Beta distribution 
to find the narrowest interval containing the specified mass (e.g., 95%).

**Advantages of Bayesian HDI over frequentist CI:**
- Direct probability interpretation: "95% of the posterior mass is in this interval"
- No reliance on asymptotic approximations (works even with small samples)
- Naturally incorporates prior information (uniform prior = minimal assumptions)

**HDI width** is our precision measure: narrower intervals give more precise estimates.
The ePitG algorithm checks whether the HDI width meets the precision goal *and* 
whether the HDI location is conclusive relative to the ROPE.
"""

MATHS_BINARY_BETWEEN_GROUPS = r"""
**Comparing two proportions using the Central Limit Theorem**

When we observe binary outcomes in two independent groups:
- Group A: $\hat{p}_A = s_A / n_A$
- Group B: $\hat{p}_B = s_B / n_B$

We're interested in their **difference**: $\delta = \hat{p}_A - \hat{p}_B$

**By the CLT**, each proportion is approximately Normal for large enough samples:

$$\hat{p}_i \;\dot\sim\; N\!\left(p_i,\; \frac{p_i(1 - p_i)}{n_i}\right)$$

Since the groups are independent, the difference is also Normal:

$$\delta \;\dot\sim\; N\!\left(\hat{p}_A - \hat{p}_B,\;\; \text{SE}^2\right)$$

where the **standard error** is:

$$\text{SE} = \sqrt{\frac{\hat{p}_A(1 - \hat{p}_A)}{n_A} + \frac{\hat{p}_B(1 - \hat{p}_B)}{n_B}}$$

**The HDI** (Highest Density Interval) for a Normal distribution is symmetric:

$$\text{HDI} = \delta \pm z_{\alpha/2} \cdot \text{SE}$$

where $z_{\alpha/2} = \Phi^{-1}\!\left(\frac{1 + \text{HDI mass}}{2}\right)$

**HDI width** (our precision measure):

$$\text{HDI width} = 2 \cdot z_{\alpha/2} \cdot \text{SE}$$

---

**Rule of thumb for CLT validity:** All four of these should be ≥ 5:

$n_A \hat{p}_A$, $\;n_A(1-\hat{p}_A)$, $\;n_B \hat{p}_B$, $\;n_B(1-\hat{p}_B)$

When any condition fails, the Normal approximation may be inaccurate —
the true distribution of the difference can be skewed.
"""


# ──────────────────────────────────────────────────────────────
# Continuous Variables: Maths Tutorials
# ──────────────────────────────────────────────────────────────

MATHS_CONTINUOUS_SINGLE_GROUP = r"""
**Single mean inference using Student-t posterior**

When we observe continuous data with unknown variance:
- Sample mean: $\bar{x}$
- Sample standard deviation: $s$
- Sample size: $n$

**The posterior distribution** for the true mean $\mu$ follows a Student-t distribution:

$$\mu \mid \text{data} \;\sim\; t_{\nu}\!\left(\bar{x},\; \frac{s}{\sqrt{n}}\right)$$

where $\nu = n - 1$ is the degrees of freedom.

**Why Student-t instead of Normal?**

Unlike the binary case (where we used Normal via CLT), the Student-t distribution 
accounts for **uncertainty in the variance estimate**. With small samples, we don't 
know $\sigma^2$ exactly — we only have $s^2$. The t-distribution has heavier tails 
than the Normal, reflecting this extra uncertainty.

As $n \to \infty$, the t-distribution converges to Normal.

**The HDI** is computed numerically on this t-distribution to find the 
narrowest interval containing the specified mass.

**HDI width** is our precision measure. The ePitG algorithm ensures both 
precision (HDI width < Goal) and conclusiveness (HDI vs ROPE).
"""

MATHS_CONTINUOUS_BETWEEN_GROUPS = r"""
**Comparing two continuous means using Welch's t-approximation**

When we observe continuous outcomes in two independent groups:
- Group A: $\bar{x}_A$, $s_A$, $n_A$
- Group B: $\bar{x}_B$, $s_B$, $n_B$

We're interested in their **difference**: $\delta = \bar{x}_A - \bar{x}_B$

**Welch's t-approximation** (does *not* assume equal variances):

$$\delta \;\dot\sim\; t_\nu\!\left(\bar{x}_A - \bar{x}_B,\;\; \text{SE}\right)$$

where the **standard error** is:

$$\text{SE} = \sqrt{\frac{s_A^2}{n_A} + \frac{s_B^2}{n_B}}$$

and the **Welch–Satterthwaite degrees of freedom**:

$$\nu = \frac{\left(\frac{s_A^2}{n_A} + \frac{s_B^2}{n_B}\right)^2}{\frac{\left(\frac{s_A^2}{n_A}\right)^2}{n_A - 1} + \frac{\left(\frac{s_B^2}{n_B}\right)^2}{n_B - 1}}$$

**Why Welch's t instead of Normal (CLT)?**

Unlike the binary case (which uses the CLT Normal approximation),
Welch's t accounts for **uncertainty in the variance estimate**.
This makes it more appropriate for continuous data — especially
with smaller sample sizes — because the Student-t distribution
has heavier tails than the Normal.

**The HDI** is computed numerically on this Student-t distribution
(it won't be perfectly symmetric if $\nu$ is small, though the
asymmetry is usually negligible).

**HDI width** is our precision measure: the ePitG algorithm
checks whether it's below the precision goal *and* whether
the HDI is conclusive relative to the ROPE.
"""


# ──────────────────────────────────────────────────────────────
# Bayes Factor: Explanations
# ──────────────────────────────────────────────────────────────

BAYES_FACTOR_INTRO = """
**Bayes Factor (BF₁₀)** quantifies the relative evidence for two hypotheses:
- **H₀**: θ = null value (point hypothesis)
- **H₁**: θ ~ Beta(α, β) (prior distribution)

BF₁₀ = P(data | H₁) / P(data | H₀)
"""

BAYES_FACTOR_INTERPRETATION = """
**Interpretation:**
- **BF₁₀ > 1**: Data favor H₁ (effect exists)
- **BF₁₀ < 1**: Data favor H₀ (no effect, or BF₀₁ > 1)
- **BF₁₀ ≈ 1**: Data are uninformative

**Key differences from ePitG:**
- BF requires specifying a prior under H₁ (subjective)
- BF doesn't directly measure precision (HDI width)
- BF grows indefinitely with sample size, even for tiny effects
- BF compares *relative evidence*, not practical significance (ROPE)
"""
