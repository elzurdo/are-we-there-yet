"""
Binary variables — single-group analysis.

The user provides summary statistics for binary (Bernoulli) data
and receives an ePitG stopping decision.

Sidebar: all inputs
Main area: summary + verdict + plot
"""
import streamlit as st
import numpy as np

from utils.stats import (
    successes_failures_to_hdi_ci_limits, binary_difference_hdi,
    check_clt_conditions, beta_overlap, CI_FRACTION,
)
from utils.decision import epitg_decision
from utils.viz import (
    plot_posterior_binary, plot_posterior_difference, plot_two_beta_posteriors, 
    plot_nhst_posterior, plot_bayes_factor_prior_posterior,
)
from utils.verdict import render_verdict_display
from utils.nhst import nhst_test
from utils.bayes_factor import (
    binary_single_group_bayes_factor, PRIOR_SPECS,
    interpret_bayes_factor_jeffreys, interpret_bayes_factor_kass_raftery,
)
from utils.tutorials import (
    NHST_LIMITATIONS, MATHS_BINARY_SINGLE_GROUP, MATHS_BINARY_BETWEEN_GROUPS,
    BAYES_FACTOR_INTRO, BAYES_FACTOR_INTERPRETATION,
)


def sidebar_inputs() -> dict:
    """Render all Binary inputs in the sidebar and return a dict of values."""

    # --- Sub-mode (single group now; A/B test later) ---
    analysis_mode = st.sidebar.radio(
        "Analysis",
        ["Single Group", "Between Groups"],
        key="binary_analysis_mode",
    )

    if analysis_mode == "Single Group":
        return _sidebar_single_group()
    elif analysis_mode == "Between Groups":
        return _sidebar_between_groups()

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
    decimal_places = 3
    verdict_style = "Centered text"
    with st.sidebar.expander("⚙️ Advanced"):
        ci_fraction = st.slider(
            "HDI mass", min_value=0.80, max_value=0.99,
            value=CI_FRACTION, step=0.01, format="%.2f",
            key="binary_ci_fraction",
        )
        decimal_places = st.number_input(
            "Decimal places", min_value=1, max_value=10,
            value=3, step=1, key="binary_decimal_places",
        )
        verdict_style = st.radio(
            "Verdict display style",
            ["Centered text", "Info/Warning box"],
            key="binary_verdict_style",
        )

    return {
        "analysis_mode": "Single Group",
        "successes": successes,
        "failures": failures,
        "total": total,
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
    """Render results for single-group binary analysis."""

    successes = inputs["successes"]
    failures = inputs["failures"]
    total = inputs["total"]
    rope_min = inputs["rope_min"]
    rope_max = inputs["rope_max"]
    rope_width = inputs["rope_width"]
    precision_goal = inputs["precision_goal"]
    ci_fraction = inputs["ci_fraction"]
    dp = inputs["decimal_places"]
    verdict_style = inputs["verdict_style"]
    fmt = f".{dp}f"

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
            f"Rate = {observed_rate:{fmt}}"
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
    render_verdict_display(result, precision_goal, fmt, verdict_style)

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
            st.metric("Observed rate", f"{observed_rate:{fmt}}")

        # --- Plot ---
        fig = plot_posterior_binary(result, successes=a, failures=b, decimal_places=dp)
        st.pyplot(fig)

        # --- Alternative Methods ---
        with st.expander("⚖️ Alternative Methods", expanded=False):
            tab_nhst, tab_bf = st.tabs(["NHST (p-value)", "Bayes Factor"])

            with tab_nhst:
                alpha = st.slider(
                    "Significance level (α)", min_value=0.01, max_value=0.10,
                    value=0.05, step=0.01, format="%.2f", key="binary_sg_alpha"
                )

                # Compute NHST for single proportion
                theta_null = inputs["theta_null"]
                se_null = np.sqrt(theta_null * (1 - theta_null) / total)
                test_stat, p_val, decision = nhst_test(
                    observed=observed_rate,
                    null_value=theta_null,
                    se=se_null,
                    test_type="z"
                )

                col_n1, col_n2, col_n3 = st.columns(3)
                with col_n1:
                    st.metric("z-statistic", f"{test_stat:{fmt}}")
                with col_n2:
                    st.metric("p-value", f"{p_val:.4f}")
                with col_n3:
                    color = "🔴" if p_val < alpha else "🟢"
                    decision_at_alpha = "Reject H₀" if p_val < alpha else "Fail to Reject H₀"
                    st.metric(f"Decision (α={alpha:.2f})", f"{color} {decision_at_alpha}")

                # NHST plot
                from scipy.stats import norm
                dist_null = norm(loc=theta_null, scale=se_null)
                fig_nhst = plot_nhst_posterior(
                    observed=observed_rate,
                    null_value=theta_null,
                    se=se_null,
                    test_stat=test_stat,
                    p_value=p_val,
                    dist=dist_null,
                    x_label="p",
                    decimal_places=dp
                )
                st.pyplot(fig_nhst)

                st.markdown(NHST_LIMITATIONS)

            with tab_bf:
                st.markdown(BAYES_FACTOR_INTRO)

                # Prior selection
                col_p1, col_p2 = st.columns([1, 2])
                with col_p1:
                    prior_choice = st.selectbox(
                        "Prior for H₁",
                        options=list(PRIOR_SPECS.keys()),
                        format_func=lambda x: x.replace("_", " ").title(),
                        key="binary_sg_bf_prior"
                    )
                with col_p2:
                    st.caption(PRIOR_SPECS[prior_choice]["description"])

                # Interpretation scale
                interp_scale = st.radio(
                    "Interpretation scale",
                    options=["jeffreys", "kass_raftery"],
                    format_func=lambda x: "Jeffreys (1961)" if x == "jeffreys" else "Kass & Raftery (1995)",
                    horizontal=True,
                    key="binary_sg_bf_scale"
                )

                # Compute Bayes Factor
                prior_alpha = PRIOR_SPECS[prior_choice]["alpha"]
                prior_beta = PRIOR_SPECS[prior_choice]["beta"]
                theta_null = inputs["theta_null"]

                bf10 = binary_single_group_bayes_factor(
                    successes=a,
                    n=total,
                    theta_null=theta_null,
                    prior_alpha=prior_alpha,
                    prior_beta=prior_beta,
                )

                # Interpret
                if interp_scale == "jeffreys":
                    category, emoji = interpret_bayes_factor_jeffreys(bf10)
                else:
                    category, emoji = interpret_bayes_factor_kass_raftery(bf10)

                # Display
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    st.metric("BF₁₀", f"{bf10:.3f}")
                with col_b2:
                    st.metric("Interpretation", f"{emoji} {category}")

                # Optional: show BF₀₁
                bf01 = 1 / bf10
                st.caption(f"BF₀₁ (evidence for H₀) = {bf01:.3f}")

                st.markdown(BAYES_FACTOR_INTERPRETATION)

                # Visualization toggle
                show_savage_dickey = st.checkbox(
                    "Show Savage-Dickey density ratio",
                    value=False,
                    key="binary_sg_bf_savage_dickey",
                    help="Visualize BF as the ratio of prior/posterior density heights at θ₀"
                )

                # Plot prior vs posterior
                fig_bf = plot_bayes_factor_prior_posterior(
                    successes=a,
                    failures=b,
                    prior_alpha=prior_alpha,
                    prior_beta=prior_beta,
                    theta_null=theta_null,
                    bf_10=bf10,
                    show_density_ratio=show_savage_dickey,
                    decimal_places=dp,
                )
                st.pyplot(fig_bf)


                

    # --- Maths Tutorial ---
    with st.expander('🎓 "The Maths Behind the Curtain"', expanded=False):
        st.markdown(MATHS_BINARY_SINGLE_GROUP)

# ──────────────────────────────────────────────────────────────
# Between Groups
# ──────────────────────────────────────────────────────────────

def _sidebar_group_inputs(label: str, key_prefix: str) -> dict:
    """Reusable sidebar inputs for a single group (A or B)."""

    st.sidebar.markdown(f"#### {label}")

    input_mode = st.sidebar.radio(
        "Input format",
        ["Successes & Total", "Successes & Failures", "Success % & Total"],
        horizontal=True,
        key=f"{key_prefix}_input_mode",
    )

    if input_mode == "Successes & Total":
        total = st.sidebar.number_input(
            "Total trials", min_value=2, value=100, step=1, key=f"{key_prefix}_total",
        )
        successes = st.sidebar.number_input(
            "Successes", min_value=0, max_value=total, value=50, step=1,
            key=f"{key_prefix}_successes",
        )
        failures = total - successes
    elif input_mode == "Success % & Total":
        total = st.sidebar.number_input(
            "Total trials", min_value=2, value=100, step=1, key=f"{key_prefix}_total_pct",
        )
        success_pct = st.sidebar.number_input(
            "Success %", min_value=0.0, max_value=100.0, value=50.0, step=0.1,
            format="%.1f", key=f"{key_prefix}_success_pct",
        )
        successes = int(round(success_pct / 100.0 * total))
        failures = total - successes
    else:
        successes = st.sidebar.number_input(
            "Successes", min_value=0, value=50, step=1, key=f"{key_prefix}_successes_sf",
        )
        failures = st.sidebar.number_input(
            "Failures", min_value=0, value=50, step=1, key=f"{key_prefix}_failures_sf",
        )
        total = successes + failures

    return {"successes": successes, "failures": failures, "total": total}


def _sidebar_between_groups() -> dict:
    """Sidebar inputs for between-groups binary comparison."""

    st.sidebar.markdown("### 📊 Data")

    group_a = _sidebar_group_inputs("Group A", "bg_a")
    group_b = _sidebar_group_inputs("Group B", "bg_b")

    st.sidebar.markdown("### 🎯 Hypothesis & ROPE")

    theta_null = st.sidebar.number_input(
        "Null hypothesis (δ₀ = p_A − p_B)", min_value=-1.0, max_value=1.0,
        value=0.0, step=0.01, format="%.4f", key="bg_theta_null",
    )

    rope_mode = st.sidebar.radio(
        "ROPE specification",
        ["Full width (symmetric)", "Explicit min / max"],
        horizontal=True,
        key="bg_rope_mode",
    )

    if rope_mode == "Full width (symmetric)":
        rope_width = st.sidebar.number_input(
            "ROPE width (Δ_ROPE)", min_value=0.001, max_value=2.0,
            value=0.10, step=0.01, format="%.3f", key="bg_rope_width",
        )
        rope_min = theta_null - rope_width / 2
        rope_max = theta_null + rope_width / 2
    else:
        rope_min = st.sidebar.number_input(
            "ROPE min", min_value=-1.0, max_value=1.0,
            value=-0.05, step=0.01, format="%.4f", key="bg_rope_min",
        )
        rope_max = st.sidebar.number_input(
            "ROPE max", min_value=-1.0, max_value=1.0,
            value=0.05, step=0.01, format="%.4f", key="bg_rope_max",
        )
        rope_width = rope_max - rope_min

    st.sidebar.markdown("### 🔬 Precision Goal")

    precision_goal = st.sidebar.number_input(
        "Goal (target HDI width)",
        min_value=0.001, max_value=2.0,
        value=0.08, step=0.01, format="%.3f", key="bg_precision_goal",
        help="Must be narrower than the ROPE width for the method to work.",
    )

    ci_fraction = CI_FRACTION
    decimal_places = 3
    verdict_style = "Centered text"
    with st.sidebar.expander("⚙️ Advanced"):
        ci_fraction = st.slider(
            "HDI mass", min_value=0.80, max_value=0.99,
            value=CI_FRACTION, step=0.01, format="%.2f",
            key="bg_ci_fraction",
        )
        decimal_places = st.number_input(
            "Decimal places", min_value=1, max_value=10,
            value=3, step=1, key="bg_decimal_places",
        )
        verdict_style = st.radio(
            "Verdict display style",
            ["Centered text", "Info/Warning box"],
            key="bg_verdict_style",
        )

    return {
        "analysis_mode": "Between Groups",
        "group_a": group_a,
        "group_b": group_b,
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
    """Render results for between-groups binary comparison."""

    group_a = inputs["group_a"]
    group_b = inputs["group_b"]
    rope_min = inputs["rope_min"]
    rope_max = inputs["rope_max"]
    rope_width = inputs["rope_width"]
    precision_goal = inputs["precision_goal"]
    ci_fraction = inputs["ci_fraction"]
    dp = inputs["decimal_places"]
    verdict_style = inputs["verdict_style"]
    fmt = f".{dp}f"

    n_a, s_a = group_a["total"], group_a["successes"]
    n_b, s_b = group_b["total"], group_b["successes"]

    # --- Validation ---
    if n_a < 2 or n_b < 2:
        st.warning("Each group needs at least 2 observations.")
        return
    if rope_min >= rope_max:
        st.warning("ROPE min must be less than ROPE max.")
        return
    if precision_goal >= rope_width:
        st.warning("Precision goal must be narrower than the ROPE width.")
        return

    p_a = s_a / n_a if n_a > 0 else 0.0
    p_b = s_b / n_b if n_b > 0 else 0.0
    delta = p_a - p_b
    se = np.sqrt(p_a * (1 - p_a) / n_a + p_b * (1 - p_b) / n_b)

    # --- CLT validity check ---
    conditions = check_clt_conditions(p_a, n_a, p_b, n_b)
    all_pass = all(c["passed"] for c in conditions)

    if not all_pass:
        st.warning("⚠️ **CLT approximation may be unreliable**")
        cond_table = "| Condition | Value | Status |\n|-----------|------:|--------|\n"
        for c in conditions:
            status = "✅" if c["passed"] else "❌"
            cond_table += f"| {c['label']} ≥ 5 | {c['value']:.1f} | {status} |\n"
        st.markdown(cond_table)

    # --- Input summary ---
    st.markdown("#### Binary — Between Groups")

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(
            f"**Group A**  \n"
            f"{s_a} successes / {n_a} total  \n"
            f"Rate = {p_a:{fmt}}"
        )
    with col_b:
        st.markdown(
            f"**Group B**  \n"
            f"{s_b} successes / {n_b} total  \n"
            f"Rate = {p_b:{fmt}}"
        )

    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        st.markdown(
            f"**Difference (δ)**  \n"
            f"p̂_A − p̂_B = {delta:{fmt}}  \n"
            f"SE = {se:{fmt}}"
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
    hdi_min, hdi_max = binary_difference_hdi(p_a, n_a, p_b, n_b, ci_fraction=ci_fraction)

    result = epitg_decision(
        hdi_min=hdi_min,
        hdi_max=hdi_max,
        rope_min=rope_min,
        rope_max=rope_max,
        precision_goal=precision_goal,
        point_estimate=delta,
        ci_fraction=ci_fraction,
    )

    # --- Verdict ---
    st.divider()
    render_verdict_display(result, precision_goal, fmt, verdict_style)

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

        # --- Difference posterior plot ---
        st.markdown("##### Posterior of Difference (δ)")
        fig = plot_posterior_difference(result, delta=delta, se=se, decimal_places=dp)
        st.pyplot(fig)

        # --- Individual group posteriors ---
        st.markdown("##### Individual Group Posteriors")
        a_a, b_a = max(s_a, 1), max(n_a - s_a, 1)
        a_b, b_b = max(s_b, 1), max(n_b - s_b, 1)
        overlap = beta_overlap(a_a, b_a, a_b, b_b)

        col_ov, _ = st.columns([1, 2])
        with col_ov:
            st.metric("Posterior Overlap", f"{overlap:{fmt}}")

        fig2 = plot_two_beta_posteriors(a_a, b_a, a_b, b_b, overlap=overlap, decimal_places=dp)
        st.pyplot(fig2)

        # --- Alternative Methods ---
        with st.expander("⚖️ Alternative Methods", expanded=False):
            tab_nhst, = st.tabs(["NHST (p-value)"])

            with tab_nhst:
                alpha = st.slider(
                    "Significance level (α)", min_value=0.01, max_value=0.10,
                    value=0.05, step=0.01, format="%.2f", key="binary_bg_alpha"
                )

                # Compute NHST for difference in proportions
                theta_null = inputs["theta_null"]
                test_stat, p_val, decision = nhst_test(
                    observed=delta,
                    null_value=theta_null,
                    se=se,
                    test_type="z"
                )

                col_n1, col_n2, col_n3 = st.columns(3)
                with col_n1:
                    st.metric("z-statistic", f"{test_stat:{fmt}}")
                with col_n2:
                    st.metric("p-value", f"{p_val:.4f}")
                with col_n3:
                    color = "🔴" if p_val < alpha else "🟢"
                    decision_at_alpha = "Reject H₀" if p_val < alpha else "Fail to Reject H₀"
                    st.metric(f"Decision (α={alpha:.2f})", f"{color} {decision_at_alpha}")

                # NHST plot
                from scipy.stats import norm
                dist_null = norm(loc=theta_null, scale=se)
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
        st.markdown(MATHS_BINARY_BETWEEN_GROUPS)
