"""
Binary variables — single-group analysis.

The user provides summary statistics for binary (Bernoulli) data
and receives an ePitG stopping decision.

Sidebar: all inputs
Main area: summary + verdict + plot
"""
import streamlit as st
import numpy as np

from utils.stats import successes_failures_to_hdi_ci_limits, CI_FRACTION
from utils.decision import epitg_decision
from utils.viz import plot_posterior_binary


def sidebar_inputs() -> dict:
    """Render all Binary inputs in the sidebar and return a dict of values."""

    # --- Sub-mode (single group now; A/B test later) ---
    analysis_mode = st.sidebar.radio(
        "Analysis",
        ["Single Group"],
        key="binary_analysis_mode",
    )

    if analysis_mode == "Single Group":
        return _sidebar_single_group()

    return {}


def _sidebar_single_group() -> dict:
    """Sidebar inputs for single-group binary data."""

    st.sidebar.markdown("### 📊 Data")

    input_mode = st.sidebar.radio(
        "Input format",
        ["Successes & Total", "Successes & Failures", "Success % & Total"],
        horizontal=True,
        key="binary_input_mode",
    )

    if input_mode == "Successes & Total":
        total = st.sidebar.number_input(
            "Total trials", min_value=2, value=100, step=1, key="binary_total",
        )
        successes = st.sidebar.number_input(
            "Successes", min_value=0, max_value=total, value=50, step=1,
            key="binary_successes",
        )
        failures = total - successes
    elif input_mode == "Success % & Total":
        total = st.sidebar.number_input(
            "Total trials", min_value=2, value=100, step=1, key="binary_total_pct",
        )
        success_pct = st.sidebar.number_input(
            "Success %", min_value=0.0, max_value=100.0, value=50.0, step=0.1,
            format="%.1f", key="binary_success_pct",
        )
        successes = int(round(success_pct / 100.0 * total))
        failures = total - successes
    else:
        successes = st.sidebar.number_input(
            "Successes", min_value=0, value=50, step=1, key="binary_successes_sf",
        )
        failures = st.sidebar.number_input(
            "Failures", min_value=0, value=50, step=1, key="binary_failures_sf",
        )
        total = successes + failures

    st.sidebar.markdown("### 🎯 Hypothesis & ROPE")

    theta_null = st.sidebar.number_input(
        "Null hypothesis (θ_null)", min_value=0.0, max_value=1.0,
        value=0.5, step=0.01, format="%.4f", key="binary_theta_null",
    )

    rope_mode = st.sidebar.radio(
        "ROPE specification",
        ["Full width (symmetric)", "Explicit min / max"],
        horizontal=True,
        key="binary_rope_mode",
    )

    if rope_mode == "Full width (symmetric)":
        rope_width = st.sidebar.number_input(
            "ROPE width (Δ_ROPE)", min_value=0.001, max_value=1.0,
            value=0.10, step=0.01, format="%.3f", key="binary_rope_width",
        )
        rope_min = theta_null - rope_width / 2
        rope_max = theta_null + rope_width / 2
    else:
        rope_min = st.sidebar.number_input(
            "ROPE min", min_value=0.0, max_value=1.0,
            value=0.45, step=0.01, format="%.4f", key="binary_rope_min",
        )
        rope_max = st.sidebar.number_input(
            "ROPE max", min_value=0.0, max_value=1.0,
            value=0.55, step=0.01, format="%.4f", key="binary_rope_max",
        )
        rope_width = rope_max - rope_min

    st.sidebar.markdown("### 🔬 Precision Goal")

    precision_goal = st.sidebar.number_input(
        "Goal (target HDI width)",
        min_value=0.001, max_value=1.0,
        value=0.08, step=0.01, format="%.3f", key="binary_precision_goal",
        help="Must be narrower than the ROPE width for the method to work.",
    )

    ci_fraction = CI_FRACTION
    with st.sidebar.expander("⚙️ Advanced"):
        ci_fraction = st.slider(
            "HDI mass", min_value=0.80, max_value=0.99,
            value=CI_FRACTION, step=0.01, format="%.2f",
            key="binary_ci_fraction",
        )

    return {
        "successes": successes,
        "failures": failures,
        "total": total,
        "theta_null": theta_null,
        "rope_min": rope_min,
        "rope_max": rope_max,
        "rope_width": rope_width,
        "precision_goal": precision_goal,
        "ci_fraction": ci_fraction,
    }


def render_results(inputs: dict):
    """Render the verdict and plot in the main area."""

    if not inputs:
        return

    successes = inputs["successes"]
    failures = inputs["failures"]
    total = inputs["total"]
    rope_min = inputs["rope_min"]
    rope_max = inputs["rope_max"]
    rope_width = inputs["rope_width"]
    precision_goal = inputs["precision_goal"]
    ci_fraction = inputs["ci_fraction"]

    # --- Validation ---
    if total < 2:
        st.warning("Need at least 2 observations.")
        return
    if rope_min >= rope_max:
        st.warning("ROPE min must be less than ROPE max.")
        return
    if rope_min < 0 or rope_max > 1:
        st.warning("ROPE bounds must be within [0, 1] for binary data.")
        return
    if precision_goal >= rope_width:
        st.warning("Precision goal must be narrower than the ROPE width.")
        return

    observed_rate = successes / total if total > 0 else 0.0

    # --- Input summary ---
    st.markdown("#### Binary — Single Group")

    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        st.markdown(
            f"**Data**  \n"
            f"{successes} successes / {total} total  \n"
            f"Rate = {observed_rate:.4f}"
        )
    with col_s2:
        st.markdown(
            f"**ROPE**  \n"
            f"[{rope_min:.4f}, {rope_max:.4f}]  \n"
            f"Width = {rope_width:.4f}"
        )
    with col_s3:
        st.markdown(
            f"**Precision Goal**  \n"
            f"{precision_goal:.3f}  \n"
            f"HDI mass = {ci_fraction:.0%}"
        )

    # --- Compute ---
    a = max(successes, 1)
    b = max(failures, 1)

    hdi_min, hdi_max = successes_failures_to_hdi_ci_limits(a, b, ci_fraction=ci_fraction)

    result = epitg_decision(
        hdi_min=hdi_min,
        hdi_max=hdi_max,
        rope_min=rope_min,
        rope_max=rope_max,
        precision_goal=precision_goal,
        point_estimate=observed_rate,
        ci_fraction=ci_fraction,
    )

    # --- Verdict ---
    st.divider()
    display = result.display

    st.markdown(f"### {display['emoji']}  {display['label']}")
    st.markdown(f"*{display['message']}*")

    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.metric("HDI width", f"{result.hdi_width:.4f}",
                   delta=f"Goal: {precision_goal:.4f}",
                   delta_color="normal" if result.precision_met else "inverse")
    with col_m2:
        st.metric("HDI", f"[{result.hdi_min:.4f}, {result.hdi_max:.4f}]")
    with col_m3:
        st.metric("Observed rate", f"{observed_rate:.4f}")

    # --- Plot ---
    fig = plot_posterior_binary(result, successes=a, failures=b)
    st.pyplot(fig)
