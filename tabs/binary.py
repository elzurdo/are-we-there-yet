"""
Binary variables tab — single-group analysis.

The user provides summary statistics for binary (Bernoulli) data
and receives an ePitG stopping decision.
"""
import streamlit as st
import numpy as np

from utils.stats import successes_failures_to_hdi_ci_limits, CI_FRACTION
from utils.decision import epitg_decision, DECISION_DISPLAY
from utils.viz import plot_posterior_binary


def render():
    """Render the Binary Variables tab content."""

    # --- Sub-tabs for future expansion (single group now, A/B later) ---
    sub_tabs = st.tabs(["Single Group"])

    with sub_tabs[0]:
        _render_single_group()


def _render_single_group():
    """Single-group binary data analysis."""

    st.markdown("#### Data Summary")

    # --- Input mode toggle ---
    input_mode = st.radio(
        "Input format",
        ["Successes & Total", "Successes & Failures"],
        horizontal=True,
        key="binary_input_mode",
    )

    col_data1, col_data2 = st.columns(2)

    if input_mode == "Successes & Total":
        with col_data1:
            total = st.number_input("Total trials", min_value=2, value=100, step=1,
                                    key="binary_total")
        with col_data2:
            successes = st.number_input("Successes", min_value=0, max_value=total,
                                        value=50, step=1, key="binary_successes")
        failures = total - successes
    else:
        with col_data1:
            successes = st.number_input("Successes", min_value=0, value=50, step=1,
                                        key="binary_successes_sf")
        with col_data2:
            failures = st.number_input("Failures", min_value=0, value=50, step=1,
                                       key="binary_failures_sf")
        total = successes + failures

    if total < 2:
        st.warning("Need at least 2 observations.")
        return

    observed_rate = successes / total if total > 0 else 0.0

    st.markdown(
        f"**Observed rate:** {observed_rate:.4f}  "
        f"({successes} successes, {failures} failures, {total} total)"
    )

    # --- Hypothesis & ROPE ---
    st.markdown("#### Hypothesis & ROPE")

    theta_null = st.number_input(
        "Null hypothesis (θ_null)", min_value=0.0, max_value=1.0,
        value=0.5, step=0.01, format="%.4f", key="binary_theta_null",
    )

    rope_mode = st.radio(
        "ROPE specification",
        ["Full width (symmetric)", "Explicit min / max"],
        horizontal=True,
        key="binary_rope_mode",
    )

    if rope_mode == "Full width (symmetric)":
        rope_width = st.number_input(
            "ROPE width (Δ_ROPE)", min_value=0.001, max_value=1.0,
            value=0.10, step=0.01, format="%.3f", key="binary_rope_width",
        )
        rope_min = theta_null - rope_width / 2
        rope_max = theta_null + rope_width / 2
    else:
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            rope_min = st.number_input(
                "ROPE min", min_value=0.0, max_value=1.0,
                value=0.45, step=0.01, format="%.4f", key="binary_rope_min",
            )
        with col_r2:
            rope_max = st.number_input(
                "ROPE max", min_value=0.0, max_value=1.0,
                value=0.55, step=0.01, format="%.4f", key="binary_rope_max",
            )
        rope_width = rope_max - rope_min

    if rope_min < 0 or rope_max > 1:
        st.warning("ROPE bounds must be within [0, 1] for binary data.")
        return
    if rope_min >= rope_max:
        st.warning("ROPE min must be less than ROPE max.")
        return

    st.markdown(f"**ROPE:** [{rope_min:.4f}, {rope_max:.4f}]  (width = {rope_width:.4f})")

    # --- Precision Goal & HDI ---
    st.markdown("#### Precision Goal")

    precision_goal = st.number_input(
        "Goal (target HDI width)",
        min_value=0.001, max_value=rope_width, value=min(0.08, rope_width * 0.8),
        step=0.01, format="%.3f", key="binary_precision_goal",
        help="Must be narrower than the ROPE width for the method to work.",
    )

    with st.expander("Advanced settings"):
        ci_fraction = st.slider(
            "HDI mass", min_value=0.80, max_value=0.99,
            value=CI_FRACTION, step=0.01, format="%.2f",
            key="binary_ci_fraction",
        )

    # === Compute ===
    # Guard against a=0 or b=0 (Beta undefined)
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

    # === Display verdict ===
    st.divider()
    display = result.display

    st.markdown(f"### {display['emoji']}  {display['label']}")
    st.markdown(f"*{display['message']}*")

    # Key metrics
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.metric("HDI width", f"{result.hdi_width:.4f}",
                   delta=f"Goal: {precision_goal:.4f}",
                   delta_color="normal" if result.precision_met else "inverse")
    with col_m2:
        st.metric("HDI", f"[{result.hdi_min:.4f}, {result.hdi_max:.4f}]")
    with col_m3:
        st.metric("Observed rate", f"{observed_rate:.4f}")

    # Plot
    fig = plot_posterior_binary(result, successes=a, failures=b)
    st.pyplot(fig)
