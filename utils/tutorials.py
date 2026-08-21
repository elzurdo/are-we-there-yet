"""
Tutorial text constants for the DPitG Decision Advisor.

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
   The DPitG method explicitly plans for a precision goal.

4. **Ignores practical equivalence**: NHST can't distinguish between "no effect" and "effect is 
   too small to matter." The ROPE addresses this directly.

**DPitG combines:**
- **Precision** (HDI width ≤ Goal) — ensures your estimate is narrow enough
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
The DPitG algorithm checks whether the HDI width meets the precision goal *and*
whether the HDI location is conclusive relative to the ROPE.

---

**Estimating the sample size needed to reach the precision goal**

By the Bernstein–von Mises theorem, the HDI width of a Beta posterior shrinks
proportionally to $N^{-1/2}$ as data accumulate. Under a Normal approximation:

$$\text{HDI width} \approx 2 z_* \sqrt{\frac{V(\theta)}{N}}$$

where $z_*$ is the critical value for the chosen HDI mass (e.g. $z_* \approx 1.96$ for 95%)
and $V(\theta) = \hat\theta(1-\hat\theta)$ is the per-observation variance of the
Bernoulli estimator. Setting HDI width $= \omega_{\rm goal}$ and solving for $N$:

$$N_{\rm goal} \approx \frac{4 z_*^2 \, \hat\theta(1-\hat\theta)}{\omega_{\rm goal}^2}$$

Note that $\hat\theta(1-\hat\theta)$ is maximised at $\hat\theta = 0.5$, so a balanced
outcome demands the most data for any given precision goal; estimates near 0 or 1
converge faster.

This is an approximation — it assumes the observed rate $\hat\theta$ is close to
the true value. The estimate becomes more reliable as sample size grows.
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

---

**Estimating the sample size needed to reach the precision goal**

By the Bernstein–von Mises theorem, the HDI width shrinks proportionally to $N^{-1/2}$:

$$\text{HDI width} \approx 2 z_* \sqrt{\frac{V(\theta)}{N}}$$

where $V(\theta)$ is the per-observation variance of the estimator and $z_*$ is the critical
value for the chosen HDI mass (e.g. $z_* \approx 1.96$ for 95%).

Setting HDI width $= \omega_{\rm goal}$ and solving for $N$:

$$N_{\rm goal} \approx \frac{4 z_*^2 \, V(\theta)}{\omega_{\rm goal}^2}$$

This formula is **generic** — only $V(\theta)$ changes across contexts:

| Context | $V(\theta)$ |
|---|---|
| Binary single group | $\hat\theta(1-\hat\theta)$ |
| Binary between groups | see below |
| Continuous single group | $s^2$ |

**Between-groups case — preserving the observed group ratio**

$\text{SE}^2$ receives an independent contribution from each group — one for $\hat{p}_A$
and one for $\hat{p}_B$ — because we are estimating a *difference* and the groups are
independent, so their variances add. This is **not** variance pooling: no assumption of
equal proportions is made, and each group retains its own term.

Let $r = n_A / (n_A + n_B)$ be the current allocation ratio, treated as a fixed constant
going forward. Writing $n_A = r\,N_{\rm total}$ and $n_B = (1-r)\,N_{\rm total}$:

$$\text{SE}^2 = \frac{\hat{p}_A(1-\hat{p}_A)}{r\,N_{\rm total}} + \frac{\hat{p}_B(1-\hat{p}_B)}{(1-r)\,N_{\rm total}} \;\equiv\; \frac{V_{\rm eff}}{N_{\rm total}}$$

where $V_{\rm eff} = \dfrac{\hat{p}_A(1-\hat{p}_A)}{r} + \dfrac{\hat{p}_B(1-\hat{p}_B)}{1-r}$ is a constant
(it depends only on the observed rates and the fixed ratio). Solving:

$$N_{\rm total,\, goal} = \left\lceil \frac{4 z_*^2 \, V_{\rm eff}}{\omega_{\rm goal}^2} \right\rceil$$

The per-group targets are recovered by splitting via the same ratio:

$$n_{A,\rm goal} = \lceil r \cdot N_{\rm total,\, goal} \rceil, \qquad n_{B,\rm goal} = N_{\rm total,\, goal} - n_{A,\rm goal}$$

<details>
<summary>💡 Why is N_total,goal four times larger than the single-group formula when p_A = p_B = p and n_A = n_B?</summary>

Why is $$N_{\rm total,\,goal}$$ four times larger than the single-group formula when $\hat{p}_A = \hat{p}_B = p$ and $n_A = n_B$?

With equal groups ($r = 0.5$) and equal proportions ($\hat{p}_A = \hat{p}_B = p$):

$$V_{\rm eff} = \frac{p(1-p)}{0.5} + \frac{p(1-p)}{0.5} = 4\,p(1-p)$$

so $N_{\rm total,\,goal} \approx 16 z_*^2 p(1-p)\,/\,\omega_{\rm goal}^2$, which is 4× the single-group formula $4 z_*^2 p(1-p)\,/\,\omega_{\rm goal}^2$. The factor of 4 comes from two independent doublings:

1. **Half the data per group.** Each group receives only $N_{\rm total}/2$ observations, so
   each proportion's variance is $p(1-p)/(N_{\rm total}/2) = 2p(1-p)/N_{\rm total}$ — twice as
   large as if all data went to one group.
2. **Variances add for differences.** $\operatorname{Var}(\hat{p}_A - \hat{p}_B) = \operatorname{Var}(\hat{p}_A) + \operatorname{Var}(\hat{p}_B)$,
   doubling the variance a second time.

$2 \times 2 = 4$. This is the unavoidable cost of estimating a *difference* from two
groups rather than a single proportion from one.
</details>

This is only an approximation — it assumes the observed rates $\hat{p}_A, \hat{p}_B$ are
close to the true values. The estimate becomes more reliable as sample size grows.
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

**HDI width** is our precision measure. The DPitG algorithm ensures both 
precision (HDI width ≤ Goal) and conclusiveness (HDI vs ROPE).

---

**Estimating the sample size needed to reach the precision goal**

Under the Student-t posterior, the HDI width also shrinks proportionally to $N^{-1/2}$.
Using a Normal approximation (valid for moderate to large $n$):

$$\text{HDI width} \approx 2 z_* \sqrt{\frac{V(\mu)}{N}}$$

where $z_*$ is the critical value for the chosen HDI mass (e.g. $z_* \approx 1.96$ for 95%)
and $V(\mu) = s^2$ is the sample variance, the per-observation variance of the mean
estimator. Setting HDI width $= \omega_{\rm goal}$ and solving for $N$:

$$N_{\rm goal} \approx \frac{4 z_*^2 \, s^2}{\omega_{\rm goal}^2}$$

Unlike the binary case, $s^2$ has no fixed upper bound — a noisier measurement
process requires more data to achieve the same precision. Also, the units of measure
of $$\mu$$, $$s$$ and $$\omega_{\rm goal}$$ are the same (e.g centimeters
if $$\mu$$ is measures height), so they cancle out when
calculating $N_{\rm goal}$, which is unitless as expected.

This is an approximation — the exact formula uses the t-distribution quantile
(which depends on $n$ itself), so for small samples the true requirement is
slightly larger than $N_{\rm goal}$. For $n \gtrsim 30$ the difference is negligible.
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

**HDI width** is our precision measure: the DPitG algorithm
checks whether it's below the precision goal *and* whether
the HDI is conclusive relative to the ROPE.

---

**Estimating the sample size needed to reach the precision goal**

$\text{SE}^2$ receives an independent contribution from each group because we are
estimating a *difference* between independent groups, so their variances add.
This is **not** variance pooling: each group keeps its own $s^2$, and no assumption
of equal variances is made (consistent with Welch's t).

Let $r = n_A / (n_A + n_B)$ be the current allocation ratio, treated as a fixed constant
going forward. Writing $n_A = r\,N_{\rm total}$ and $n_B = (1-r)\,N_{\rm total}$:

$$\text{SE}^2 = \frac{s_A^2}{r\,N_{\rm total}} + \frac{s_B^2}{(1-r)\,N_{\rm total}} \;\equiv\; \frac{V_{\rm eff}}{N_{\rm total}}$$

where $V_{\rm eff} = \dfrac{s_A^2}{r} + \dfrac{s_B^2}{1-r}$ is a constant for fixed
$r$, $s_A$, and $s_B$. Solving:

$$N_{\rm total,\, goal} = \left\lceil \frac{4 z_*^2 \, V_{\rm eff}}{\omega_{\rm goal}^2} \right\rceil$$

The per-group targets are recovered by splitting via the same ratio:

$$n_{A,\rm goal} = \lceil r \cdot N_{\rm total,\, goal} \rceil, \qquad n_{B,\rm goal} = N_{\rm total,\, goal} - n_{A,\rm goal}$$

This is an approximation — it assumes the observed standard deviations $s_A, s_B$ are
close to the true population values, and uses a Normal rather than t quantile. Both
assumptions improve as sample size grows.
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

# ──────────────────────────────────────────────────────────────
# Glossary
# ──────────────────────────────────────────────────────────────

# TODO: add entries for:
# ROPE
# HDI
GLOSSARY_TABLE = """
<table>
  <thead>
    <tr><th>Term</th><th>Definition</th><th>Role</th></tr>
  </thead>
  <tbody>
    <tr>
      <td>&theta;<sub>null</sub></td>
      <td>Null value</td>
      <td>The hypothesised reference proportion (e.g. 0.5 for a fair coin). The ROPE region must contain this value.</td>
    </tr>
    <tr>
      <td>&theta;&#x0302;</td>
      <td>Observed proportion</td>
      <td>Point estimate of the true proportion from the current sample: &theta;&#x0302; = s / n.</td>
    </tr>
    <tr>
      <td>ω<sub>ROPE</sub></td>
      <td>ROPE Width</td>
      <td>ω<sub>ROPE</sub> = ROPE<sub>max</sub> − ROPE<sub>min</sub>. Effects inside this band are considered practically equivalent to the null.</td>
    </tr>
    <tr>
      <td>ω<sub>goal</sub></td>
      <td>Precision Goal</td>
      <td>Target posterior width used as a stopping criterion.<br>By definition ω<sub>goal</sub> ≤ ω<sub>ROPE</sub>.</td>
    </tr>
    <tr>
      <td>ω<sub>HDI</sub></td>
      <td>HDI Width</td>
      <td>Actual posterior width of the current sample. <br>ω<sub>HDI</sub>= HDI<sub>max</sub> − HDI<sub>min</sub>. <br>Stopping requires ω<sub>HDI</sub> ≤ ω<sub>goal</sub>.</td>
    </tr>
  </tbody>
</table>
"""

GLOSSARY_TABLE_BETWEEN_GROUPS = """
<table>
  <thead>
    <tr><th>Term</th><th>Definition</th><th>Role</th></tr>
  </thead>
  <tbody>
    <tr>
      <td>&theta;<sub>null</sub></td>
      <td>Null value</td>
      <td>The hypothesised reference proportion (e.g. 0.5 for a fair coin). The ROPE region must contain this value.</td>
    </tr>
    <tr>
      <td>&theta;&#x0302;</td>
      <td>Observed proportion</td>
      <td>Point estimate of the true proportion from the current sample: &theta;&#x0302; = s / n.</td>
    </tr>
    <tr>
      <td>ω<sub>ROPE</sub></td>
      <td>ROPE Width</td>
      <td>ω<sub>ROPE</sub> = ROPE<sub>max</sub> − ROPE<sub>min</sub>. Effects inside this band are considered practically equivalent to the null.</td>
    </tr>
    <tr>
      <td>ω<sub>goal</sub></td>
      <td>Precision Goal</td>
      <td>Target posterior width used as a stopping criterion.<br>By definition ω<sub>goal</sub> ≤ ω<sub>ROPE</sub>.</td>
    </tr>
    <tr>
      <td>ω<sub>HDI</sub></td>
      <td>HDI Width</td>
      <td>Actual posterior width of the current sample. <br>ω<sub>HDI</sub>= HDI<sub>max</sub> − HDI<sub>min</sub>. <br>Stopping requires ω<sub>HDI</sub> ≤ ω<sub>goal</sub>.</td>
    </tr>
    <tr>
      <td>r</td>
      <td>Group ratio</td>
      <td>Allocation fraction: r = n<sub>A</sub> / (n<sub>A</sub> + n<sub>B</sub>). Equal group sizes correspond to r&nbsp;=&nbsp;0.5.</td>
    </tr>
  </tbody>
</table>
"""

BAYES_FACTOR_INTERPRETATION = """
**Interpretation:**
- **BF₁₀ > 1**: Data favor H₁ (effect exists)
- **BF₁₀ < 1**: Data favor H₀ (no effect, or BF₀₁ > 1)
- **BF₁₀ ≈ 1**: Data are uninformative

**Key differences from DPitG:**
- BF requires specifying a prior under H₁ (subjective)
- BF doesn't directly measure precision (HDI width)
- BF grows indefinitely with sample size, even for tiny effects
- BF compares *relative evidence*, not practical significance (ROPE)

**Evidence scale references:**
- Jeffreys, H. (1961). *Theory of Probability* (3rd ed.). Oxford University Press.
- Kass, R.E. & Raftery, A.E. (1995). Bayes Factors. *Journal of the American Statistical Association*, 90(430), 773–795.
"""

BAYES_FACTOR_INTRO_BINARY_BG = """
**Bayes Factor (BF₁₀)** tests whether the two groups share a common proportion:
- **H₀**: θ_A = θ_B (equality; both groups share one proportion)
- **H₁**: θ_A and θ_B are independent, each with a Beta(α, β) prior

BF₁₀ = B(s_A+α, f_A+β) × B(s_B+α, f_B+β) / [B(α, β) × B(s_A+s_B+α, f_A+f_B+β)]

where s = successes, f = failures, B = Beta function.

**Method:** Beta-Binomial conjugate — exact analytical solution.

> ⚠️ This BF is restricted to H₀: θ_A = θ_B (null difference Δ₀ = 0).
> A non-zero null Δ₀ ≠ 0 has no standard conjugate solution; the ROPE framework
> handles effect-size reasoning separately.

**Reference:** Gunel, E. & Dickey, J. (1974). Bayes Factors for Independence in
Contingency Tables. *Biometrika*, 61(3), 545–557.
"""

BAYES_FACTOR_INTRO_JZS = """
**Bayes Factor (BF₁₀)** using the JZS (Jeffreys-Zellner-Siow) prior:
- **H₀**: true effect = 0 (point null on the mean / mean difference)
- **H₁**: standardised effect size δ ~ Cauchy(0, r) — a scale-invariant prior

BF₁₀ = P(data | H₁) / P(data | H₀)

Computed via 1D numerical integration over the JZS mixing variable g.
The Cauchy scale r controls prior width: smaller r is conservative (mass
near zero), larger r accommodates bigger effects a priori.

**Method:** JZS prior on standardised effect size; H₀ marginal from Student-t.

**Reference:** Rouder, J.N., Speckman, P.L., Sun, D., Morey, R.D., & Iverson, G. (2009).
Bayesian *t* tests for accepting and rejecting the null hypothesis.
*Psychonomic Bulletin & Review*, 16(2), 225–237.
"""

BAYES_FACTOR_INTRO_CATEGORICAL = """
**Bayes Factor (BF₁₀)** for each category vs. the uniform null:
- **H₀**: θ_k = 1/K (category k has the expected proportion under a uniform distribution)
- **H₁**: θ_k ~ Beta(α, β)

BF₁₀ = [B(c_k+α, (N−c_k)+β) / B(α, β)] / [(1/K)^c_k × (1−1/K)^(N−c_k)]

where c_k = count of category k, N = total count, K = number of categories.

**Method:** Beta-Binomial conjugate (same as single-group binary).

**Reference:** Same analytical approach as Savage-Dickey density ratio for
Beta-Binomial models; interpretation scales from Jeffreys (1961) and
Kass & Raftery (1995).
"""


