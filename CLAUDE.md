# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Are We There Yet?** is a Streamlit web app implementing the **ePitG (Enhanced Precision is the Goal)** sequential hypothesis testing algorithm. It allows users to input summary statistics and receive a stopping verdict based on two combined criteria:
1. **Precision**: HDI width < precision goal
2. **Location**: HDI fully inside or outside the ROPE (Region of Practical Equivalence)

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
