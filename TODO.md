# Are We There Yet — TODO

Items to bring the app in sync with the published preprint
(Kazin 2026, arXiv:2608.05301).

---

## 1. Rename ePitG → DPitG throughout the codebase

There is an existing `# TODO: rename all ePitG → DPitG` comment in `app.py:144`.
The paper uses **DPitG (Decisive Precision is the Goal)**; the old name was
**ePitG (Enhanced Precision is the Goal)**. These files still use the old name:

### `utils/tutorials.py`

| Location | Current text | Should be |
|----------|-------------|-----------|
| Module docstring (line 4) | `"Tutorial text constants for the ePitG Decision Advisor."` | `"... DPitG Decision Advisor."` |
| `NHST_LIMITATIONS` (line 27) | `"**ePitG combines:**"` | `"**DPitG combines:**"` |
| `MATHS_BINARY_SINGLE_GROUP` (line 65) | `"The ePitG algorithm checks whether the HDI width meets the precision goal..."` | `"The DPitG algorithm checks..."` |
| `MATHS_CONTINUOUS_SINGLE_GROUP` (line 232) | `"The ePitG algorithm ensures both precision (HDI width ≤ Goal) and conclusiveness"` | `"The DPitG algorithm ensures..."` |
| `MATHS_CONTINUOUS_BETWEEN_GROUPS` (line 295) | `"the ePitG algorithm checks whether it's below the precision goal"` | `"the DPitG algorithm checks..."` |
| `BAYES_FACTOR_INTERPRETATION` (line 384) | `"**Key differences from ePitG:**"` | `"**Key differences from DPitG:**"` |

### `utils/decision.py`

- Function `epitg_decision()` → consider renaming to `dpitg_decision()`
- Update the docstring, which refers to "ePitG two-condition stopping rule"
- Update all callers (tabs and tests)

### `CLAUDE.md` (already updated)

- Project overview fixed in this session ✓

---

## 2. Quantitative claims in the About section

The "When is this calculator most useful?" expander is accurate in spirit but contains
no numbers. Consider adding the headline result from the paper:

> At ω_goal = 0.08, DPitG reduces PitG's 62% inconclusive rate to 2% at a median
> cost of only 5% more samples, with zero false positives.

---

## 3. NHST_LIMITATIONS content — minor conceptual gap

`NHST_LIMITATIONS` in `utils/tutorials.py` says (point 3):
> "The ePitG method explicitly plans for a precision goal."

This is true of both PitG and DPitG. The text should clarify that DPitG additionally
requires a conclusive verdict — that is what distinguishes it from plain PitG. Suggested
revision for point 3:

> "Unlike NHST, DPitG plans for a precision goal **and** requires a conclusive verdict
> before stopping — eliminating the high inconclusive rate of plain Precision-is-the-Goal."

---

## 4. Glossary — missing ROPE and HDI entries

`utils/tutorials.py` has a `# TODO: add entries for: ROPE, HDI` comment on line 341.
These are the two most important concepts in the framework; add them:

| Term | Definition | Role |
|------|-----------|------|
| HDI | Highest Density Interval | Shortest credible interval containing the target posterior mass (e.g. 95%). Used as the precision and location metric. |
| ROPE | Region of Practical Equivalence | Pre-specified interval [ROPE_min, ROPE_max] around the null. Effects inside are considered practically equivalent to the null. |

---

## 5. Extensions not yet implemented in the app

The paper's appendices derive (but do not simulate) extensions to:
- Continuous single group (implemented ✓)
- Continuous between groups (implemented ✓)
- Binary between groups (implemented ✓)

The paper notes these are *theoretical derivations*; stopping-property validation
via simulation is future work. Consider adding a note in the relevant tab
tooltips/disclaimers that the validated empirical guarantees are from the
single-group Bernoulli setting.

---

## 6. ROPE Advisor dialog — resolved + follow-ups

**Status: ✅ Resolved** — the `@st.dialog` → `_rope_advisor_result` → flush pattern
works correctly for binary single-group. Preset switching also fixed (session-state
writes before widget instantiation).

**Follow-ups:**

### 6a. Apply the same advisor pattern to the other three cases
- Binary between-groups
- Continuous single-group
- Continuous between-groups

### 6b. Domain presets — future additions
Consider adding presets for:
- **Manufacturing / defect rate** — binary single-group (defective or not)
- **Customer churn** — binary single-group (churned or not)

### 6c. Medical preset — edge-case example near 0%
The current medical preset uses a ~70% treatment response rate. A complementary
example with a low-rate scenario (e.g. 2–3% surgical complication or infection rate)
would be valuable, but first verify the algorithm behaves well when θ_null is near
0% or 100% (the Beta posterior becomes highly skewed).

### 6d. Dynamic preset narratives
Preset narratives currently hard-code example rates (e.g. "around 3%"). Make them
dynamic so they update if the user overrides the preset values in Steps 1–3.

### 6e. ✅ Show estimated sample size in the advisor preview
**Done.** Added as Step 3 in the advisor dialog. Features: θ and ω_goal sliders
(live N_goal metric + `plot_n_goal_by_parameter` with highlighted curve and dot),
advanced expander for z* and background ω range. Plot refactored in `utils/viz.py`
to show transparent background curves with the user's curve prominent.

### 6f. ✅ Simplify Step 2 — default to fraction mode
**Done.** Removed the fraction-vs-absolute radio from Step 2; now shows only the
fraction slider. Absolute-width mode noted as a TODO in the Step 3 Advanced
expander for future re-addition.

### 6g. ✅ Add orientation landmarks to the precision slider (Step 2)
**Done.** Added as help text on the slider: "70–80% is typical; above 90%
requires substantially more data."

### 6i. ✅ Propagate explorer values on Apply
**Done.** Step 3's ω_goal and θ slider values are propagated to the main page
on Apply. `_on_apply_click` reads explorer state; `tabs/binary.py` flush block
writes `binary_theta_null`. Step 2 shows an override caption when Step 3's
ω_goal differs. Step 3 shows a second preview box once any slider is touched,
reporting whether θ_null and ω_goal were updated or remain the same.

### 6h. ✅ "What happens next" note near Apply
**Done.** Added caption below Apply button: "These values will fill in the sidebar —
then enter your observed data to get a verdict."

### 6j. Add sensible y-axis ticks to the N_goal plot
`plot_n_goal_by_parameter` currently hides y-axis ticks (`set_yticks([])`).
For a sample-size plot, showing actual N values is more informative. Ticks
should use rounded values in the range of interest — e.g. thousands when
N_goal is in the thousands, hundreds when in the hundreds.

---

## 7. ✅ Forced-Decision Frameworks (when budget is exhausted)

**Status: ✅ Implemented for single-group binary** — `utils/forced_decision.py` +
`tabs/binary.py`.

When `result.can_stop` is False (verdict is `NEEDS_MORE_DATA` or `INCONCLUSIVE`),
the "Let Me Peek! 👀" expander is replaced by a **"Let Me Peek! 👀 · Decide Now! 🎲"**
collapsed expander containing two tabs:
- **🔍 Posterior Peek** — existing metrics, posterior plot, and alternative methods
- **Decide Now! 🎲** — risk-based forced decision (7a + 7b below)

### 7a. ✅ Posterior Tail Probability — implemented

`posterior_tail_probability(successes, failures, theta_null, observed_rate)` in
`utils/forced_decision.py`. Direction auto-detected from observed rate vs θ_null.
UI: metric + decision threshold slider (default 0.95) + amber forced-verdict box.

### 7b. ✅ Bayesian Expected Loss — implemented

`bayesian_expected_loss(successes, failures, rope_min, rope_max, loss_ratio)` in
`utils/forced_decision.py`. UI: single cost-ratio slider L₀/L₁ (default 1×) inside
"⚖️ Account for decision costs" expander + EL metrics + amber forced-verdict box.

A **📚 Methods & References** expander inside "Decide Now!" shows the equations
and citations for both 7a and 7b.

### Leave as TODOs

- 7c (Predictive Probability of Success) — useful retrospective diagnostic; no directional call
- 7d (Minimum Bayes Factor) — for expert users only; low interpretability
- 7e (One-Sided ROPE / single boundary) — natural extension once 7a is live
- 7f (Clinical trial adaptive frameworks) — reference material only

### 7 follow-up: Apply to other data types

Apply the same "Decide Now!" pattern to:
- Binary between-groups
- Continuous single-group
- Continuous between-groups

Do in a separate session after validating the single-group binary pattern.

---

### 7a. Posterior Tail Probability (Probability of Direction)

**Description.** Compute P(θ > θ_null | data) directly from the Beta(k+1, n−k+1)
posterior. This is the fraction of posterior mass on the "effect" side of the null.
The complementary quantity, min(PD, 1−PD), is sometimes called the *probability of
direction* (PD). It is the Bayesian analogue of a one-sided p-value.

**Formula.** For Beta(α, β) posterior:
```
P(θ > θ_null | data) = 1 − CDF_Beta(θ_null; α, β)
```
Standard thresholds mirror frequentist conventions: 0.95 (≈ one-sided α=0.05),
0.975 (≈ one-sided α=0.025), 0.99 (≈ one-sided α=0.01). Equivalently for
two-sided: report whether this probability clears 0.975 in either direction.

**Caveats.** Thresholds are arbitrary conventions, not calibrated to posterior
uncertainty. A posterior that just clears 0.95 from a wide, uninformative posterior
is very different from the same number from a concentrated one.

**Interpretability.** High — "there is a 97% probability that θ exceeds 0.5."

**References.**
- Makowski et al. (2019), "Indices of Effect Existence and Significance in the
  Bayesian Framework," *Frontiers in Psychology*.
  [arXiv:2005.13181](https://arxiv.org/abs/2005.13181)
- Kruschke & Liddell (2018), *Psychon Bull Rev* — HDI+ROPE decision rule context.
- Bayes Rules! textbook, Ch. 8: https://www.bayesrulesbook.com/chapter-8

---

### 7b. Bayesian Expected Loss (Optimal Bayes Action)

**Description.** Assign costs to the two error types: L₀ = cost of wrongly
rejecting H₀ (false positive), L₁ = cost of wrongly accepting H₀ (false negative).
The Bayes-optimal action is whichever action has lower posterior expected loss.

**Formula.**
```
EL(Accept | data) = L₀ · P(θ outside ROPE | data)
EL(Reject | data) = L₁ · P(θ inside ROPE  | data)

Accept H₀  if  EL(Accept) < EL(Reject)
Reject H₀  if  EL(Reject) < EL(Accept)
```
Under symmetric 0-1 loss (L₀ = L₁), this reduces to: Accept if
P(θ inside ROPE | data) > 0.5, Reject otherwise — i.e., go with the majority
of the posterior. Asymmetric loss reflects domain context (e.g. drug safety:
false positives more costly → set L₀ >> L₁).

**Interpretability.** Medium — requires the user to specify loss ratio L₀/L₁,
but this makes the trade-off explicit and honest.

**References.**
- Berger (1985), *Statistical Decision Theory and Bayesian Analysis* (Springer).
- Stats with R textbook, Ch. 3:
  https://statswithr.github.io/book/losses-and-decision-making.html
- Posterior Expected Loss Calculator:
  https://metricgate.com/docs/posterior-expected-loss-decision/

---

### 7c. Predictive Probability of Success (PPoS)

**Description.** Given current data (k successes, n trials), compute the
probability that if the trial continued to N_max, the DPitG criterion *would*
eventually be met. Uses the Beta-Binomial predictive distribution over the
n* = N_max − n remaining observations.

**Formula.** Posterior after n trials: Beta(k+1, n−k+1).
Future successes among n* remaining: BetaBinomial(n*, k+1, n−k+1).
Sum over all possible future outcomes (k*=0..n*) weighted by this distribution:

```
PPoS = Σ_{k*=0}^{n*}  P(k* | BetaBinom) · 1[DPitG met at k+k*, n_max]
```

If PPoS < threshold (e.g. 10–20%), the trial is "futile" — even collecting more
data is unlikely to produce a conclusive result. At budget exhaustion, this
collapses to a simple futility label rather than a directional decision.

**Interpretability.** High — "given your current data, there is only an 8%
chance you would ever reach a conclusive result."

**References.**
- Chen et al. (2019), "Application of Bayesian predictive probability for
  interim futility analysis in single-arm phase II trial," *Translational
  Cancer Research*. [PMC6711387](https://pmc.ncbi.nlm.nih.gov/articles/PMC6711387/)
- Cook (2006), "Predictive Probability Interim Analysis," MD Anderson:
  https://biostatistics.mdanderson.org/SoftwareDownload/SoftwareFiles/PredictiveProbabilit/PredictiveInterimAnalysis.pdf

---

### 7d. Minimum Bayes Factor (MBF)

**Description.** The MBF is the *strongest possible* evidence against H₀ that
any prior could generate for a given p-value. It provides a Bayes-factor lower
bound without specifying a full prior. Developed by Sellke, Bayarri & Berger
(2001) as a way to "calibrate" a frequentist p-value into Bayesian language.

**Formula.** Given two-sided p-value p (from binomial or normal approximation):
```
MBF(p) = −e · p · ln(p)      for p < 1/e  (≈ 0.368)
MBF(p) = 1                   otherwise
```
A p-value of 0.05 gives MBF ≈ 0.41 — so even at p=0.05, the data are at most
2.4:1 against H₀, far weaker than commonly believed. This is the key result:
p-values systematically overstate the evidence.

**Caveat.** MBF does not depend on sample size, so it becomes increasingly
conservative for large n. The R package `pcal` implements this calibration.

**Interpretability.** Low for non-statisticians — requires explaining what a
Bayes factor is. But the punchline ("p=0.05 is surprisingly weak evidence") is
memorable.

**References.**
- Sellke, Bayarri & Berger (2001), "Calibration of P Values for Testing Precise
  Null Hypotheses," *The American Statistician* 55(1):62–71.
  https://www.dcscience.net/Sellke-Bayarri-Berger-calibration-of-P-2001.pdf
- `pcal` R package: https://ptfonseca.github.io/pcal/

---

### 7e. One-Sided ROPE / Single Decision Boundary

**Description.** Instead of a symmetric ROPE = [θ_null ± Δ/2], use only one
boundary in the relevant direction. For example, if a treatment is considered
meaningful only if θ > θ_null + Δ_min, compute P(θ > θ_null + Δ_min | data).
This is equivalent to a Bayesian one-sided equivalence/superiority test.

This differs from the tail probability (7a) in that the threshold is shifted by
Δ_min (the minimum practically relevant effect), so it tests *practical* rather
than *statistical* significance.

**Formula.**
```
P(θ > θ_null + Δ_min | data) = 1 − CDF_Beta(θ_null + Δ_min; k+1, n−k+1)
```

**Interpretability.** High — "there is an 89% probability that the true rate
exceeds the minimum practically meaningful threshold."

**References.**
- Lakens (2017), "ROPE and Equivalence Testing: Practically Equivalent?"
  http://daniellakens.blogspot.com/2017/02/rope-and-equivalence-testing.html
- `bayestestR` package ROPE documentation:
  https://easystats.github.io/bayestestR/articles/region_of_practical_equivalence.html

---

### 7f. Clinical Trial Adaptive Stopping: Conditional Assurance & Futility Bounds

**Description.** In adaptive trial design, when N_max is reached without a
conclusive verdict, the standard practice is one of:

1. **Declare futility** — if PPoS (7c) was below threshold at any interim, the
   trial is stopped and the intervention considered not promising.
2. **Report the posterior** — present P(θ outside ROPE | data) with no binary
   verdict, letting domain experts decide.
3. **Conditional assurance** — the probability of success at final analysis
   given the trial was not stopped for futility, integrated over the prior.
   Unlike conditional power, it does not require specifying the true effect at
   interim and is robust to early-stopping selection bias.

**Practical recommendation for this app.** At budget exhaustion, present:
(a) the posterior tail probability as a continuous evidence measure, (b) the
expected-loss comparison if the user can supply loss weights, and (c) a PPoS
that communicates retrospectively how unlikely conclusiveness was given the data.
Avoid committing to a hard binary verdict without explicit user acknowledgment
of the residual uncertainty.

**References.**
- Gsponer et al. (2014), "A practical guide to Bayesian group sequential designs,"
  *Pharmaceutical Statistics* — conditional assurance framework.
- Jennison & Turnbull (1999), *Group Sequential Methods with Applications to
  Clinical Trials* (Chapman & Hall) — frequentist futility bounds (O'Brien-Fleming,
  Peto-Haybittle) for context.
- BMC Medical Research Methodology (2020), "Do we need to adjust for interim
  analyses in a Bayesian adaptive trial design?"
  https://bmcmedresmethodol.biomedcentral.com/articles/10.1186/s12874-020-01042-7

---

## 8. Code-quality cleanup for `utils/forced_decision.py` + `tabs/binary.py`

Identified by a 4-agent review after the Forced-Decision feature was implemented.
These are code-quality items only — no user-visible behaviour changes.

### 8a. Extract `_beta_params()` helper (reuse / simplification)

`max(successes, 1)` / `max(failures, 1)` is repeated independently in both
`posterior_tail_probability` and `bayesian_expected_loss` inside
`utils/forced_decision.py`. Extract a private `_beta_params(successes, failures)`
one-liner and call it from both functions.

### 8b. Collapse the direction if/else in `_render_forced_decision_single` (simplification)

The `prob_label` / `dir_caption` block in `tabs/binary.py` branches on `direction`
with two near-identical f-strings (only the inequality sign differs). Collapse to:
```python
ineq, op = ("≥", ">") if direction == "above" else ("<", "<")
prob_label = f"P(θ {op} θ_null | data)"
dir_caption = f"Observed rate ({observed_rate:{fmt}}) {ineq} θ_null ({theta_null:{fmt}}) → reporting P(θ {op} θ_null | data)"
```

### 8c. Collapse the EL verdict `st.warning()` pair (simplification)

The Accept / Reject `st.warning()` calls share identical structure. Collapse to:
```python
verdict, lo, hi = ("Accept", el_accept, el_reject) if forced_accept else ("Reject", el_reject, el_accept)
st.warning(f"⚠️ **Forced Decision: {verdict} θ_null** — expected loss favors {verdict} (EL={lo:.4f} < EL={hi:.4f}).")
```

### 8d. Add `render_forced_verdict()` to `utils/verdict.py` (altitude)

The `"⚠️ **Forced Decision: ...**"` banner is assembled inline in
`_render_forced_decision_single` and will be copy-pasted into three more tabs
(binary between-groups, continuous single, continuous between). Add a shared
`render_forced_verdict(verdict_label, message)` to `utils/verdict.py` — parallel
to `render_verdict_display()` — so all tabs use one canonical function.

### 8e. Add UI label constants to `utils/constants.py` (altitude)

The expander / tab labels `"Let Me Peek! 👀 · Decide Now! 🎲"`, `"🔍 Posterior Peek"`,
and `"Decide Now! 🎲"` will be repeated across every tab that adopts the
Forced-Decision pattern. Define them once in `utils/constants.py` and import
everywhere.

---

## 9. (Optional) Build a skill for the app

Consider creating a `.claude/skills/run-app.md` skill for the are-we-there-yet repo
that tells Claude Code how to launch and test the Streamlit app (`streamlit run app.py`),
what the golden-path test cases are, and how to verify the DPitG stopping logic
against the paper's hand-picked sequence (N_stop=804, Accept, fair coin experiment).
This would make future AI-assisted development faster and more reliable.
