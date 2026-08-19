# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Are We There Yet?** is a Streamlit web app implementing the **DPitG (Decisive Precision is the Goal)** sequential hypothesis testing algorithm. It allows users to input summary statistics and receive a stopping verdict based on two combined criteria:
1. **Precision**: HDI width ≤ precision goal
2. **Location**: HDI fully inside or outside the ROPE (Region of Practical Equivalence)

## DPitG Concept Summary

This section summarises the paper *"Precision and Decisiveness as Goals: Reliable Sequential Hypothesis Testing with a Dual Stopping Criterion"* (Kazin, 2026, arXiv:2608.05301), which the app implements.

### Three Algorithms

The paper compares three sequential stopping algorithms. All share the same **Decision Rule** (the HDI+ROPE framework) but differ in when they stop:

| Algorithm | Stop Condition | Risk |
|-----------|---------------|------|
| **HDI+ROPE** | Decision is conclusive (HDI fully inside or outside ROPE) | False positives from stopping on imprecise early posteriors |
| **PitG** (Precision is the Goal) | HDI width ≤ ω_goal | High inconclusive rate — precision alone doesn't guarantee a verdict |
| **DPitG** (Decisive Precision is the Goal) | HDI width ≤ ω_goal **AND** decision is conclusive (simultaneously) | Requires up to N_max samples; may need slightly more than N_goal |

### Shared Decision Rule (HDI+ROPE Framework)

Applied by all three algorithms once their stop condition is met:

- **Accept null**: HDI entirely inside ROPE → positive evidence of practical equivalence
- **Reject null**: HDI entirely outside ROPE → positive evidence of a meaningful effect
- **Inconclusive**: HDI straddles the ROPE boundary → collect more data

This is categorically different from NHST: both Accept and Reject are affirmative findings grounded in the pre-specified effect-size criterion (the ROPE).

### Key Parameters (must be set before data collection)

- **ROPE** = [ROPE_min, ROPE_max]: region of practical equivalence around the null (width ω_ROPE)
- **ω_goal** (precision goal): target HDI width; must satisfy ω_goal ≤ ω_ROPE
- **N_max**: maximum sample size / budget cap

### Planning Formula

Expected minimum sample size to achieve ω_goal (CLT approximation, valid for N ≳ 30):

```
N_goal ≈ 4 z²* · V(θ) / ω_goal²
```

where z* ≈ 1.96 for 95% HDI and V(θ) is the per-observation variance:

| Setting | V(θ) |
|---------|------|
| Binary single group | θ̂(1 − θ̂) |
| Binary between groups | θ̂_A(1−θ̂_A)/r + θ̂_B(1−θ̂_B)/(1−r) |
| Continuous single group | s² |
| Continuous between groups | s²_A/r + s²_B/(1−r) |

N_goal is maximised when the estimand equals 0.5 (binary) or when variance is largest; it is a conservative upper bound when θ_null = 0.5.

### Key Empirical Results (fair coin, ω_goal=0.08, ROPE=0.5±0.05)

- **PitG**: 62.1% inconclusive rate, zero false positives, stops tightly at N_goal≈599
- **DPitG**: 2.2% inconclusive rate (2.6× gain), zero false positives, median stop at 4.7% above N_goal
- **HDI+ROPE**: 1.8% inconclusive rate but **6.3% false-positive rate**

DPitG's conclusiveness holds nearly flat (97–98%) across the ω_goal range tested (0.06–0.10); PitG's collapses to 0% at ω_goal = ω_ROPE.

### Scope and Limitations

- Empirically validated for **single-group Bernoulli** data (conjugate Beta posterior)
- Theoretical extensions to continuous and two-group settings are in Appendices (not yet simulation-validated)
- Uses flat Beta(1,1) prior; informative priors can reduce N_goal
- MCMC-estimated HDIs introduce Monte Carlo error not studied here

## Commands

```bash
# Activate virtual environment (Python 3.10)
source .venv/bin/activate

# Run the app
streamlit run app.py

# Run all tests
pytest tests/ -v

# Run a single test file
pytest tests/test_stats.py -v

# Run a specific test
pytest tests/test_decision.py::test_epitg_decision_accept -v
```

## Architecture

### Data Flow

1. User inputs arrive via sidebar widgets → dict of values
2. Values stored in `st.session_state["committed_inputs"]` (live mode: on every change; analyze mode: on button click)
3. Example loading uses a `_pending_example` → `st.rerun()` → flush pattern at the top of `app.py` to avoid Streamlit's "cannot modify widget after instantiation" constraint
4. Tab module reads committed values, runs stats, renders results

### Key Modules

| Module | Role |
|--------|------|
| `app.py` | Streamlit entry point; session state management; routes to tab modules |
| `utils/decision.py` | ePitG algorithm (`epitg_decision()`); returns `DecisionResult` dataclass with `ACCEPT/REJECT/INCONCLUSIVE/NEEDS_MORE_DATA` |
| `utils/stats.py` | All statistical computation: HDI via `HDIofICDF()` (scipy numerical optimization), Beta/Student-t posteriors, difference HDIs, sample size estimation |
| `utils/viz.py` | Matplotlib figures: posterior plots, difference plots, forest plots; shared `_plot_posterior()` helper with color-coded HDI/ROPE regions |
| `utils/verdict.py` | `render_verdict_display()` — formats and renders the decision result in the UI |
| `utils/bayes_factor.py` | Analytical Beta-Binomial Bayes factors with standard priors |
| `utils/rope_advisor.py` | `@st.dialog` for guiding ROPE and precision goal selection; stages values into session state |
| `tabs/binary.py` | UI for binary (Bernoulli) data — single group and between groups |
| `tabs/continuous.py` | UI for continuous data — single group and between groups |
| `tabs/categorical.py` | UI for categorical data — one-vs-rest comparisons with forest plot |

### Tab Module Convention

Each tab module exposes:
- `sidebar_inputs()` → dict of user-entered values
- `render_results(inputs)` → display verdict, plots, and analysis summary
- `get_example_values()` → dict of pre-filled demo values

### Statistical Details

- **HDI**: Uses `scipy.optimize.fmin` over the ICDF to find the minimal-width credible interval. More accurate than equal-tailed CIs for skewed posteriors.
- **Binary single group**: Beta posterior; `successes_failures_to_hdi_ci_limits()`
- **Continuous single group**: Student-t posterior; `continuous_hdi_ci_limits()`
- **Binary between groups**: CLT approximation for proportion difference; validates with `check_clt_conditions()` (requires np ≥ 5)
- **Continuous between groups**: Welch's t approach (unequal variances)
- **Categorical**: One-vs-rest binary difference HDI; full Dirichlet posterior is a planned v2.0 improvement

### Session State Keys

- `variable_type` — "Binary", "Continuous", or "Categorical"
- `analysis_mode` — "Single Group" or "Between Groups"
- `live_update` — bool; real-time refresh vs. explicit Analyze click
- `committed_inputs` / `committed_key` — validated inputs used for computation
- `_pending_example` — staged example values (internal; flushed at top of `app.py`)
- `_force_commit` — triggers immediate commit on next render
