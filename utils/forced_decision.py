"""
Forced-decision methods for when the DPitG stopping criterion is not met.

7a: Posterior Tail Probability (Probability of Direction)
7b: Bayesian Expected Loss (Optimal Bayes Action)

Applied to the Beta posterior for single-group binary data.
"""
from scipy.stats import beta as beta_dist

# TODO: unit tests
def posterior_tail_probability(
    successes: int, failures: int, theta_null: float, observed_rate: float
):
    """
    Compute posterior probability on the 'effect' side of theta_null.

    Auto-detects direction from observed_rate vs theta_null.

    Returns
    -------
    (prob, direction) where direction is 'above' or 'below'.
    """
    a = max(successes, 1)
    b = max(failures, 1)

    if observed_rate >= theta_null:
        prob = 1.0 - beta_dist.cdf(theta_null, a, b)
        direction = "above"
    else:
        prob = beta_dist.cdf(theta_null, a, b)
        direction = "below"

    return prob, direction

# TODO: unit tests
def bayesian_expected_loss(
    successes: int, failures: int, rope_min: float, rope_max: float, loss_ratio: float
):
    """
    Compute Bayesian Expected Loss for a forced binary decision.

    loss_ratio = L₀/L₁ (cost of false positive / cost of false negative).

    Returns
    -------
    (p_inside, p_outside, el_accept, el_reject, forced_accept)
    """
    a = max(successes, 1)
    b = max(failures, 1)

    p_inside = beta_dist.cdf(rope_max, a, b) - beta_dist.cdf(rope_min, a, b)
    p_outside = 1.0 - p_inside

    el_accept = loss_ratio * p_outside  # L₀ · P(outside)
    el_reject = p_inside                # L₁ · P(inside), L₁ normalised to 1

    return p_inside, p_outside, el_accept, el_reject, el_accept < el_reject


FORCED_DECISION_REFERENCES = r"""
### Posterior Tail Probability

**Formula** (Beta posterior after *k* successes out of *n* trials):

$$P(\theta > \theta_\mathrm{null} \mid \mathrm{data}) = 1 - F_{\mathrm{Beta}}\!\left(\theta_\mathrm{null};\; k{+}1,\; n{-}k{+}1\right)$$

Direction is auto-detected: reports $P(\theta > \theta_\mathrm{null})$ when the observed rate exceeds the null, and $P(\theta < \theta_\mathrm{null})$ otherwise. The complementary quantity is sometimes called the *Probability of Direction* (PD) — the Bayesian analogue of a one-sided p-value.

Standard thresholds mirror frequentist conventions:

| Threshold | Frequentist analogue |
|----------:|---------------------|
| 0.95 | one-sided α = 0.05 |
| 0.975 | one-sided α = 0.025 |
| 0.99 | one-sided α = 0.01 |

**Caveat.** Thresholds are arbitrary conventions, not calibrated to posterior width. A posterior that just clears 0.95 from a wide, uninformative posterior is very different from the same number from a concentrated one.

**References**
- Makowski et al. (2019), "Indices of Effect Existence and Significance in the Bayesian Framework," *Frontiers in Psychology.* [arXiv:2005.13181](https://arxiv.org/abs/2005.13181)
- Kruschke & Liddell (2018), *Psychonomic Bulletin & Review* — HDI+ROPE decision rule context.
- Johnson et al., *Bayes Rules!*, Ch. 8. <https://www.bayesrulesbook.com/chapter-8>

---

### Bayesian Expected Loss

**Formulae:**

$$EL(\text{Accept} \mid \text{data}) = L_0 \cdot P(\theta \notin \mathrm{ROPE} \mid \text{data})$$

$$EL(\text{Reject} \mid \text{data}) = L_1 \cdot P(\theta \in \mathrm{ROPE} \mid \text{data})$$

Accept $H_0$ if $EL(\text{Accept}) < EL(\text{Reject})$; reject otherwise.

Under symmetric loss ($L_0 = L_1$, ratio = 1×) this reduces to: *accept if $P(\theta \in \mathrm{ROPE}) > 0.5$*.
Setting $L_0 > L_1$ (false positives are costlier, e.g. drug safety) requires stronger posterior support inside the ROPE before accepting.

**Caveat.** Under symmetric loss the rule is permissive: a posterior barely leaning inside the ROPE triggers Accept. Use Posterior Tail Probability as the conventional standard; Bayesian Expected Loss is more principled once you can specify your cost ratio.

**References**
- Berger (1985), *Statistical Decision Theory and Bayesian Analysis*, Springer.
- Navarro, Foxcroft & Faulkenberry, *Learning Statistics with R*, Ch. 3. <https://statswithr.github.io/book/losses-and-decision-making.html>
- Posterior Expected Loss Calculator: <https://metricgate.com/docs/posterior-expected-loss-decision/>
"""
