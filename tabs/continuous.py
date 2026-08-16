"""
Continuous variables — single-group analysis.

The user provides summary statistics for continuous data (mean, std, n)
and receives an ePitG stopping decision using a Student-t posterior.

NOTE: For ordinal data (e.g., star ratings, Likert scales), treating as continuous
      works well when n ≥ 30 and the distribution is roughly symmetric. For smaller
      samples or highly skewed ordinal data, consider the Categorical tab or wait
      for proper ordinal regression support.

TODO (v2.0): Add proper ordinal variable support with cumulative link models
             (proportional odds, probit) that respect the ordered nature of categories.
             This would require MCMC (PyMC/Stan) as there's no analytical HDI solution.

Sidebar: all inputs
Main area: summary + verdict + plot
"""
import streamlit as st
import numpy as np
from scipy.stats import t as student_t

from utils.stats import continuous_hdi_ci_limits, continuous_difference_hdi, continuous_overlap, CI_FRACTION, estimate_n_goal, estimate_n_goal_between_groups_continuous
from utils.decision import epitg_decision
from utils.viz import plot_posterior_continuous, plot_posterior_difference, plot_nhst_posterior, plot_two_continuous_posteriors
from utils.verdict import render_verdict_display
from utils.nhst import nhst_test
from utils.tutorials import (
    NHST_LIMITATIONS, MATHS_CONTINUOUS_SINGLE_GROUP, MATHS_CONTINUOUS_BETWEEN_GROUPS,
)


def get_example_values(mode: str = "Single Group") -> dict:
    """Return session-state key/value pairs for a worked example."""
    if mode == "Between Groups":
        return {
            "cont_bg_label_a": "Control",
            "cont_bg_label_b": "Treatment",
            "cont_bg_a_mean": 100.0,
            "cont_bg_a_std": 15.0,
            "cont_bg_a_n": 30,
            "cont_bg_b_mean": 107.0,
            "cont_bg_b_std": 15.0,
            "cont_bg_b_n": 30,
            "cont_bg_theta_null": 0.0,
            "cont_bg_rope_mode": "Full width (symmetric)",
            "cont_bg_rope_width": 5.0,
            "cont_bg_precision_goal": 4.0,
        }
    # Single Group
    return {
        "cont_mean": 100.0,
        "cont_std": 15.0,
        "cont_n": 30,
        "cont_theta_null": 100.0,
        "cont_rope_mode": "Full width (symmetric)",
        "cont_rope_width": 10.0,
        "cont_precision_goal": 8.0,
    }


def sidebar_inputs() -> dict:
    """Render all Continuous inputs in the sidebar and return a dict of values."""

    # --- Sub-mode (single group now; two-group later) ---
    analysis_mode = st.sidebar.radio(
        "Analysis",
        ["Single Group", "Between Groups"],
        key="cont_analysis_mode",
    )

    if analysis_mode == "Single Group":
        return _sidebar_single_group()
    elif analysis_mode == "Between Groups":
        return _sidebar_between_groups()

    return {}


def _sidebar_single_group() -> dict:
    """Sidebar inputs for single-group continuous data."""

    st.sidebar.markdown("### 📊 Data")

    sample_mean = st.sidebar.number_input(
        "Sample mean (x̄)", value=None, step=0.1,
        format="%.4f", key="cont_mean",
    )
    sample_std = st.sidebar.number_input(
        "Sample std (s)", min_value=0.0001, value=None, step=0.1,
        format="%.4f", key="cont_std",
    )
    n = st.sidebar.number_input(
        "Sample size (n)", min_value=2, value=None, step=1,
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
        help="Must not exceed the ROPE width for the method to work.",
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
        "analysis_mode": "Single Group",
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

    analysis_mode = inputs.get("analysis_mode", "Single Group")

    if analysis_mode == "Between Groups":
        _render_between_groups(inputs)
    else:
        _render_single_group(inputs)


def _render_single_group(inputs: dict):
    """Render results for single-group continuous analysis."""

    sample_mean = inputs["sample_mean"]
    sample_std = inputs["sample_std"]
    n = inputs["n"]

    if any(v is None for v in [sample_mean, sample_std, n]):
        st.info("👈 Enter your data in the sidebar to begin.")
        return
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
    if precision_goal > rope_width:
        st.warning("Precision goal must not exceed the ROPE width.")
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

    # --- Sample size advice (shown only when precision not yet met) ---
    if not result.precision_met:
        variance = sample_std ** 2
        n_goal, n_additional = estimate_n_goal(variance, precision_goal, n, ci_fraction)
        st.info(
             f"📏 To achieve precision goal ω_goal={precision_goal:{fmt}}, based on the current sample standard deviation s={sample_std:{fmt}}: \n"
            f"You have sampled **{n:,}** data points.  \n"
            f"**{n_goal:,}** samples are recommended."
            f"That leaves at least **~{n_additional:,}** additional samples to collect."
        )

    peek_container = (
        st.container()
        if result.can_stop
        else st.expander("Let Me Peek! 👀", expanded=False)
    )
    with peek_container:
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

        # --- Alternative Methods ---
        with st.expander("⚖️ Alternative Methods", expanded=False):
            tab_nhst, = st.tabs(["NHST (p-value)"])

            with tab_nhst:
                alpha = st.slider(
                    "Significance level (α)", min_value=0.01, max_value=0.10,
                    value=0.05, step=0.01, format="%.2f", key="cont_sg_alpha"
                )

                # Compute NHST for single mean (one-sample t-test)
                theta_null = inputs["theta_null"]
                se_sample = sample_std / np.sqrt(n)
                df = n - 1
                test_stat, p_val, decision = nhst_test(
                    observed=sample_mean,
                    null_value=theta_null,
                    se=se_sample,
                    test_type="t",
                    df=df
                )

                col_n1, col_n2, col_n3 = st.columns(3)
                with col_n1:
                    st.metric("t-statistic", f"{test_stat:{fmt}}")
                with col_n2:
                    st.metric("p-value", f"{p_val:.4f}")
                with col_n3:
                    color = "🔴" if p_val < alpha else "🟢"
                    decision_at_alpha = "Reject H₀" if p_val < alpha else "Fail to Reject H₀"
                    st.metric(f"Decision (α={alpha:.2f})", f"{color} {decision_at_alpha}")

                # NHST plot
                dist_null = student_t(df=df, loc=theta_null, scale=se_sample)
                fig_nhst = plot_nhst_posterior(
                    observed=sample_mean,
                    null_value=theta_null,
                    se=se_sample,
                    test_stat=test_stat,
                    p_value=p_val,
                    dist=dist_null,
                    x_label="μ",
                    decimal_places=dp
                )
                st.pyplot(fig_nhst)

                st.markdown(NHST_LIMITATIONS)

    # --- Maths Tutorial ---
    with st.expander('🎓 "The Maths Behind the Curtain"', expanded=False):
        st.markdown(MATHS_CONTINUOUS_SINGLE_GROUP)

# ──────────────────────────────────────────────────────────────
# Between Groups
# ──────────────────────────────────────────────────────────────

def _sidebar_group_inputs(label: str, key_prefix: str) -> dict:
    """Reusable sidebar inputs for a single continuous group."""

    st.sidebar.markdown(f"#### {label}")

    sample_mean = st.sidebar.number_input(
        "Sample mean (x̄)", value=None, step=0.1,
        format="%.4f", key=f"{key_prefix}_mean",
    )
    sample_std = st.sidebar.number_input(
        "Sample std (s)", min_value=0.0001, value=None, step=0.1,
        format="%.4f", key=f"{key_prefix}_std",
    )
    n = st.sidebar.number_input(
        "Sample size (n)", min_value=2, value=None, step=1,
        key=f"{key_prefix}_n",
    )

    return {"mean": sample_mean, "std": sample_std, "n": n}


def _sidebar_between_groups() -> dict:
    """Sidebar inputs for between-groups continuous comparison."""

    st.sidebar.markdown("### 📊 Data")

    col_la, col_lb = st.sidebar.columns(2)
    with col_la:
        label_a = st.text_input("Label A", value="Group A", key="cont_bg_label_a")
    with col_lb:
        label_b = st.text_input("Label B", value="Group B", key="cont_bg_label_b")
    if not label_a.strip():
        label_a = "Group A"
    if not label_b.strip():
        label_b = "Group B"

    group_a = _sidebar_group_inputs(label_a, "cont_bg_a")
    group_b = _sidebar_group_inputs(label_b, "cont_bg_b")

    st.sidebar.markdown("### 🎯 Hypothesis & ROPE")

    theta_null = st.sidebar.number_input(
        "Null hypothesis (δ₀ = μ_A − μ_B)", value=0.0, step=0.1,
        format="%.4f", key="cont_bg_theta_null",
    )

    rope_mode = st.sidebar.radio(
        "ROPE specification",
        ["Full width (symmetric)", "Explicit min / max"],
        horizontal=True,
        key="cont_bg_rope_mode",
    )

    if rope_mode == "Full width (symmetric)":
        rope_width = st.sidebar.number_input(
            "ROPE width (Δ_ROPE)", min_value=0.001,
            value=5.0, step=0.1, format="%.3f", key="cont_bg_rope_width",
        )
        rope_min = theta_null - rope_width / 2
        rope_max = theta_null + rope_width / 2
    else:
        rope_min = st.sidebar.number_input(
            "ROPE min", value=-2.5, step=0.1,
            format="%.4f", key="cont_bg_rope_min",
        )
        rope_max = st.sidebar.number_input(
            "ROPE max", value=2.5, step=0.1,
            format="%.4f", key="cont_bg_rope_max",
        )
        rope_width = rope_max - rope_min

    st.sidebar.markdown("### 🔬 Precision Goal")

    precision_goal = st.sidebar.number_input(
        "Goal (target HDI width)",
        min_value=0.001,
        value=4.0, step=0.1, format="%.3f", key="cont_bg_precision_goal",
        help="Must not exceed the ROPE width for the method to work.",
    )

    ci_fraction = CI_FRACTION
    decimal_places = 3
    verdict_style = "Centered text"
    with st.sidebar.expander("⚙️ Advanced"):
        ci_fraction = st.slider(
            "HDI mass", min_value=0.80, max_value=0.99,
            value=CI_FRACTION, step=0.01, format="%.2f",
            key="cont_bg_ci_fraction",
        )
        decimal_places = st.number_input(
            "Decimal places", min_value=1, max_value=10,
            value=3, step=1, key="cont_bg_decimal_places",
        )
        verdict_style = st.radio(
            "Verdict display style",
            ["Centered text", "Info/Warning box"],
            key="cont_bg_verdict_style",
        )

    return {
        "analysis_mode": "Between Groups",
        "group_a": group_a,
        "group_b": group_b,
        "label_a": label_a,
        "label_b": label_b,
        "theta_null": theta_null,
        "rope_min": rope_min,
        "rope_max": rope_max,
        "rope_width": rope_width,
        "precision_goal": precision_goal,
        "ci_fraction": ci_fraction,
        "decimal_places": decimal_places,
        "verdict_style": verdict_style,
    }


def _render_between_groups(inputs: dict):
    """Render results for between-groups continuous comparison."""

    group_a = inputs["group_a"]
    group_b = inputs["group_b"]
    label_a = inputs.get("label_a", "Group A")
    label_b = inputs.get("label_b", "Group B")
    rope_min = inputs["rope_min"]
    rope_max = inputs["rope_max"]
    rope_width = inputs["rope_width"]
    precision_goal = inputs["precision_goal"]
    ci_fraction = inputs["ci_fraction"]
    dp = inputs["decimal_places"]
    verdict_style = inputs["verdict_style"]
    fmt = f".{dp}f"

    mean_a, std_a, n_a = group_a["mean"], group_a["std"], group_a["n"]
    mean_b, std_b, n_b = group_b["mean"], group_b["std"], group_b["n"]

    if any(v is None for v in [mean_a, std_a, n_a, mean_b, std_b, n_b]):
        st.info("👈 Enter data for both groups in the sidebar to begin.")
        return

    # --- Validation ---
    if n_a < 2 or n_b < 2:
        st.warning("Each group needs at least 2 observations.")
        return
    if rope_min >= rope_max:
        st.warning("ROPE min must be less than ROPE max.")
        return
    if precision_goal > rope_width:
        st.warning("Precision goal must not exceed the ROPE width.")
        return

    delta = mean_a - mean_b

    # --- Compute Welch's t ---
    hdi_min, hdi_max, se, df = continuous_difference_hdi(
        mean_a, std_a, n_a, mean_b, std_b, n_b, ci_fraction=ci_fraction
    )

    result = epitg_decision(
        hdi_min=hdi_min,
        hdi_max=hdi_max,
        rope_min=rope_min,
        rope_max=rope_max,
        precision_goal=precision_goal,
        point_estimate=delta,
        ci_fraction=ci_fraction,
    )

    # --- Input summary ---
    st.markdown("#### Continuous — Between Groups")

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(
            f"**{label_a}**  \n"
            f"x̄ = {mean_a:{fmt}}, s = {std_a:{fmt}}  \n"
            f"n = {n_a}"
        )
    with col_b:
        st.markdown(
            f"**{label_b}**  \n"
            f"x̄ = {mean_b:{fmt}}, s = {std_b:{fmt}}  \n"
            f"n = {n_b}"
        )

    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        st.markdown(
            f"**Difference (δ)**  \n"
            f"x̄_{label_a} − x̄_{label_b} = {delta:{fmt}}  \n"
            f"SE = {se:{fmt}}, ν = {df:.1f}"
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

    # --- Verdict ---
    st.divider()
    render_verdict_display(result, precision_goal, fmt, verdict_style)

    # --- Sample size advice (shown only when precision not yet met) ---
    if not result.precision_met:
        n_a_goal, n_b_goal, n_a_add, n_b_add = estimate_n_goal_between_groups_continuous(
            std_a, n_a, std_b, n_b, precision_goal, ci_fraction
        )
        st.info(
            f"📏 To achieve precision goal ω_goal={precision_goal:{fmt}}, based on the current sample standard deviations "
            f"s_{label_a}={std_a:{fmt}}, s_{label_b}={std_b:{fmt}} (preserving the current {n_a}/{n_b} group ratio):  \n"
            f"**{label_a}**: You have sampled {n_a:,} data points. ~{n_a_goal:,} total are recommended. "
            f"That leaves at least ~{n_a_add:,} additional samples to collect.  \n"
            f"**{label_b}**: You have sampled {n_b:,} data points. ~{n_b_goal:,} total are recommended. "
            f"That leaves at least ~{n_b_add:,} additional samples to collect."
        )

    peek_container = (
        st.container()
        if result.can_stop
        else st.expander("Let Me Peek! 👀", expanded=False)
    )
    with peek_container:
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.metric("HDI width", f"{result.hdi_width:{fmt}}",
                       delta=f"Goal: {precision_goal:{fmt}}",
                       delta_color="normal" if result.precision_met else "inverse")
        with col_m2:
            st.metric("HDI", f"[{result.hdi_min:{fmt}}, {result.hdi_max:{fmt}}]")
        with col_m3:
            st.metric("Difference (δ)", f"{delta:{fmt}}")

        # --- Difference posterior plot (Welch's t) ---
        st.markdown("##### Posterior of Difference (δ)")
        dist = student_t(df=df, loc=delta, scale=se)
        fig = plot_posterior_difference(result, delta=delta, se=se,
                                        decimal_places=dp, dist=dist)
        st.pyplot(fig)

        # --- Individual group posteriors ---
        st.markdown("##### Individual Group Posteriors")
        overlap = continuous_overlap(mean_a, std_a, n_a, mean_b, std_b, n_b)

        col_ov, _ = st.columns([1, 2])
        with col_ov:
            st.metric("Posterior Overlap", f"{overlap:{fmt}}")

        fig2 = plot_two_continuous_posteriors(
            mean_a, std_a, n_a, mean_b, std_b, n_b,
            overlap=overlap, decimal_places=dp,
            label_a=label_a, label_b=label_b,
        )
        st.pyplot(fig2)

        # --- Alternative Methods ---
        with st.expander("⚖️ Alternative Methods", expanded=False):
            tab_nhst, = st.tabs(["NHST (p-value)"])

            with tab_nhst:
                alpha = st.slider(
                    "Significance level (α)", min_value=0.01, max_value=0.10,
                    value=0.05, step=0.01, format="%.2f", key="cont_bg_alpha"
                )

                # Compute NHST for difference in means (Welch's t-test)
                theta_null = inputs["theta_null"]
                test_stat, p_val, decision = nhst_test(
                    observed=delta,
                    null_value=theta_null,
                    se=se,
                    test_type="t",
                    df=df
                )

                col_n1, col_n2, col_n3 = st.columns(3)
                with col_n1:
                    st.metric("t-statistic", f"{test_stat:{fmt}}")
                with col_n2:
                    st.metric("p-value", f"{p_val:.4f}")
                with col_n3:
                    color = "🔴" if p_val < alpha else "🟢"
                    decision_at_alpha = "Reject H₀" if p_val < alpha else "Fail to Reject H₀"
                    st.metric(f"Decision (α={alpha:.2f})", f"{color} {decision_at_alpha}")

                # NHST plot
                dist_null = student_t(df=df, loc=theta_null, scale=se)
                fig_nhst = plot_nhst_posterior(
                    observed=delta,
                    null_value=theta_null,
                    se=se,
                    test_stat=test_stat,
                    p_value=p_val,
                    dist=dist_null,
                    x_label="δ",
                    decimal_places=dp
                )
                st.pyplot(fig_nhst)

            # Tutorial
            with st.expander('📚 "Why We Don\'t Use p-values Alone"', expanded=False):
                st.markdown(NHST_LIMITATIONS)

    # --- Maths Tutorial ---
    with st.expander('🎓 "The Maths Behind the Curtain"', expanded=False):
        st.markdown(MATHS_CONTINUOUS_BETWEEN_GROUPS)

