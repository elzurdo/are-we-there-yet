"""
Continuous variables — single-group analysis.

The user provides summary statistics for continuous data (mean, std, n)
and receives an ePitG stopping decision using a Student-t posterior.

Sidebar: all inputs
Main area: summary + verdict + plot
"""
import streamlit as st

from utils.stats import continuous_hdi_ci_limits, CI_FRACTION
from utils.decision import epitg_decision
from utils.viz import plot_posterior_continuous
from utils.verdict import render_verdict_display


def sidebar_inputs() -> dict:
    """Render all Continuous inputs in the sidebar and return a dict of values."""

    # --- Sub-mode (single group now; two-group later) ---
    analysis_mode = st.sidebar.radio(
        "Analysis",
        ["Single Group"],
        key="cont_analysis_mode",
    )

    if analysis_mode == "Single Group":
        return _sidebar_single_group()

    return {}


def _sidebar_single_group() -> dict:
    """Sidebar inputs for single-group continuous data."""

    st.sidebar.markdown("### 📊 Data")

    sample_mean = st.sidebar.number_input(
        "Sample mean (x̄)", value=100.0, step=0.1,
        format="%.4f", key="cont_mean",
    )
    sample_std = st.sidebar.number_input(
        "Sample std (s)", min_value=0.0001, value=15.0, step=0.1,
        format="%.4f", key="cont_std",
    )
    n = st.sidebar.number_input(
        "Sample size (n)", min_value=2, value=30, step=1,
        key="cont_n",
    )

    st.sidebar.markdown("### 🎯 Hypothesis & ROPE")

    theta_null = st.sidebar.number_input(
        "Null hypothesis (μ_null)", value=100.0, step=0.1,
        format="%.4f", key="cont_theta_null",
    )

    rope_mode = st.sidebar.radio(
        "ROPE specification",
        ["Full width (symmetric)", "Explicit min / max"],
        horizontal=True,
        key="cont_rope_mode",
    )

    if rope_mode == "Full width (symmetric)":
        rope_width = st.sidebar.number_input(
            "ROPE width (Δ_ROPE)", min_value=0.001,
            value=10.0, step=0.1, format="%.3f", key="cont_rope_width",
        )
        rope_min = theta_null - rope_width / 2
        rope_max = theta_null + rope_width / 2
    else:
        rope_min = st.sidebar.number_input(
            "ROPE min", value=95.0, step=0.1,
            format="%.4f", key="cont_rope_min",
        )
        rope_max = st.sidebar.number_input(
            "ROPE max", value=105.0, step=0.1,
            format="%.4f", key="cont_rope_max",
        )
        rope_width = rope_max - rope_min

    st.sidebar.markdown("### 🔬 Precision Goal")

    precision_goal = st.sidebar.number_input(
        "Goal (target HDI width)",
        min_value=0.001,
        value=8.0, step=0.1, format="%.3f", key="cont_precision_goal",
        help="Must be narrower than the ROPE width for the method to work.",
    )

    ci_fraction = CI_FRACTION
    decimal_places = 3
    verdict_style = "Centered text"
    with st.sidebar.expander("⚙️ Advanced"):
        ci_fraction = st.slider(
            "HDI mass", min_value=0.80, max_value=0.99,
            value=CI_FRACTION, step=0.01, format="%.2f",
            key="cont_ci_fraction",
        )
        decimal_places = st.number_input(
            "Decimal places", min_value=1, max_value=10,
            value=3, step=1, key="cont_decimal_places",
        )
        verdict_style = st.radio(
            "Verdict display style",
            ["Centered text", "Info/Warning box"],
            key="cont_verdict_style",
        )

    return {
        "sample_mean": sample_mean,
        "sample_std": sample_std,
        "n": n,
        "theta_null": theta_null,
        "rope_min": rope_min,
        "rope_max": rope_max,
        "rope_width": rope_width,
        "precision_goal": precision_goal,
        "ci_fraction": ci_fraction,
        "decimal_places": decimal_places,
        "verdict_style": verdict_style,
    }


def render_results(inputs: dict):
    """Render the verdict and plot in the main area."""

    if not inputs:
        return

    sample_mean = inputs["sample_mean"]
    sample_std = inputs["sample_std"]
    n = inputs["n"]
    rope_min = inputs["rope_min"]
    rope_max = inputs["rope_max"]
    rope_width = inputs["rope_width"]
    precision_goal = inputs["precision_goal"]
    ci_fraction = inputs["ci_fraction"]
    dp = inputs["decimal_places"]
    verdict_style = inputs["verdict_style"]
    fmt = f".{dp}f"

    # --- Validation ---
    if rope_min >= rope_max:
        st.warning("ROPE min must be less than ROPE max.")
        return
    if precision_goal >= rope_width:
        st.warning("Precision goal must be narrower than the ROPE width.")
        return

    # --- Input summary ---
    st.markdown("#### Continuous — Single Group")

    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        st.markdown(
            f"**Data**  \n"
            f"x̄ = {sample_mean:{fmt}}  \n"
            f"s = {sample_std:{fmt}}, n = {n}"
        )
    with col_s2:
        st.markdown(
            f"**ROPE**  \n"
            f"[{rope_min:{fmt}}, {rope_max:{fmt}}]  \n"
            f"Width = {rope_width:{fmt}}"
        )
    with col_s3:
        st.markdown(
            f"**Precision Goal**  \n"
            f"{precision_goal:{fmt}}  \n"
            f"HDI mass = {ci_fraction:.0%}"
        )

    # --- Compute ---
    hdi_min, hdi_max = continuous_hdi_ci_limits(
        sample_mean, sample_std, n, ci_fraction=ci_fraction,
    )

    result = epitg_decision(
        hdi_min=hdi_min,
        hdi_max=hdi_max,
        rope_min=rope_min,
        rope_max=rope_max,
        precision_goal=precision_goal,
        point_estimate=sample_mean,
        ci_fraction=ci_fraction,
    )

    # --- Verdict ---
    st.divider()
    render_verdict_display(result, precision_goal, fmt, verdict_style)

    with st.expander("Let Me Peek! 👀", expanded=False):


        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.metric("HDI width", f"{result.hdi_width:{fmt}}",
                       delta=f"Goal: {precision_goal:{fmt}}",
                       delta_color="normal" if result.precision_met else "inverse")
        with col_m2:
            st.metric("HDI", f"[{result.hdi_min:{fmt}}, {result.hdi_max:{fmt}}]")
        with col_m3:
            st.metric("Sample mean", f"{sample_mean:{fmt}}")

        # --- Plot ---
        fig = plot_posterior_continuous(result, sample_mean=sample_mean,
                                        sample_std=sample_std, n=n,
                                        decimal_places=dp)
        st.pyplot(fig)
