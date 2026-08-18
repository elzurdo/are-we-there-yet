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
    check_clt_conditions, beta_overlap, CI_FRACTION, estimate_n_goal,
    estimate_n_goal_between_groups,
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
from utils.rope_advisor import rope_advisor_dialog_binary_single
from utils.constants import BINARY_SINGLE_PARAMETER_ESTIMATE_STR, GOAL_STR, HDI_WIDTH_STR, ROPE_WIDTH_STR, BINARY_SINGLE_NULL_STR
from utils.forced_decision import (
    posterior_tail_probability, bayesian_expected_loss, FORCED_DECISION_REFERENCES,
)

def get_example_values(mode: str = "Single Group") -> dict:
    """Return session-state key/value pairs for a worked example."""
    if mode == "Between Groups":
        return {
            "bg_label_a": "Control",
            "bg_label_b": "Treatment",
            "bg_a_input_mode": "Successes & Total",
            "bg_a_total": 200,
            "bg_a_successes": 100,
            "bg_b_input_mode": "Successes & Total",
            "bg_b_total": 200,
            "bg_b_successes": 120,
            "bg_theta_null": 0.0,
            "bg_rope_mode": "Full width (symmetric)",
            "bg_rope_width": 0.10,
            "bg_precision_goal": 0.08,
        }
    # Single Group
    return {
        "binary_input_mode": "Successes & Total",
        "binary_total": 100,
        "binary_successes": 50,
        "binary_theta_null": 0.5,
        "binary_rope_mode": "Full width (symmetric)",
        "binary_rope_width": 0.10,
        "binary_precision_goal": 0.08,
    }


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
            "Total trials", min_value=2, value=None, step=1, key="binary_total",
        )
        successes = st.sidebar.number_input(
            "Successes", min_value=0, max_value=total, value=None, step=1,
            key="binary_successes",
        )
        failures = (total - successes) if (total is not None and successes is not None) else None
    elif input_mode == "Success % & Total":
        total = st.sidebar.number_input(
            "Total trials", min_value=2, value=None, step=1, key="binary_total_pct",
        )
        success_pct = st.sidebar.number_input(
            "Success %", min_value=0.0, max_value=100.0, value=None, step=0.1,
            format="%.1f", key="binary_success_pct",
        )
        successes = int(round(success_pct / 100.0 * total)) if (success_pct is not None and total is not None) else None
        failures = (total - successes) if (total is not None and successes is not None) else None
    else:
        successes = st.sidebar.number_input(
            "Successes", min_value=0, value=None, step=1, key="binary_successes_sf",
        )
        failures = st.sidebar.number_input(
            "Failures", min_value=0, value=None, step=1, key="binary_failures_sf",
        )
        total = (successes + failures) if (successes is not None and failures is not None) else None

    # Flush values committed by the ROPE advisor dialog's on_click callback
    # before ROPE / precision widgets render so they pick up the new values.
    if "_rope_advisor_result" in st.session_state:
        _r = st.session_state.pop("_rope_advisor_result")
        st.session_state["binary_rope_mode"] = _r["binary_rope_mode"]
        st.session_state["binary_rope_width"] = _r["binary_rope_width"]
        st.session_state["binary_precision_goal"] = _r["binary_precision_goal"]
        if "binary_theta_null" in _r:
            st.session_state["binary_theta_null"] = _r["binary_theta_null"]
        st.session_state["_force_commit"] = True

    st.sidebar.markdown("### 🎯 Hypothesis & ROPE")

    if "binary_theta_null" not in st.session_state:
        st.session_state["binary_theta_null"] = 0.5
    theta_null = st.sidebar.number_input(
        f"Null hypothesis ({BINARY_SINGLE_NULL_STR})", min_value=0.0, max_value=1.0,
        step=0.01, format="%.4f", key="binary_theta_null",
    )

    rope_mode = st.sidebar.radio(
        "ROPE specification",
        ["Full width (symmetric)", "Explicit min / max"],
        horizontal=True,
        key="binary_rope_mode",
    )

    if rope_mode == "Full width (symmetric)":
        rope_width = st.sidebar.number_input(
            rf"ROPE width {ROPE_WIDTH_STR}", min_value=0.001, max_value=1.0,
            value=None, step=0.01, format="%.3f", key="binary_rope_width",
        )
        rope_min = (theta_null - rope_width / 2) if rope_width is not None else None
        rope_max = (theta_null + rope_width / 2) if rope_width is not None else None
    else:
        rope_min = st.sidebar.number_input(
            "ROPE min", min_value=0.0, max_value=1.0,
            value=None, step=0.01, format="%.4f", key="binary_rope_min",
        )
        rope_max = st.sidebar.number_input(
            "ROPE max", min_value=0.0, max_value=1.0,
            value=None, step=0.01, format="%.4f", key="binary_rope_max",
        )
        rope_width = (rope_max - rope_min) if (rope_min is not None and rope_max is not None) else None

    st.sidebar.markdown("### 🔬 Precision Goal")

    precision_goal = st.sidebar.number_input(
        f"Precision Goal {GOAL_STR}",
        min_value=0.001, max_value=1.0,
        value=None, step=0.01, format="%.3f", key="binary_precision_goal",
        help=f"This is the target width of {HDI_WIDTH_STR}.\n Requires {GOAL_STR} ≤ {ROPE_WIDTH_STR}.",
    )

    if st.sidebar.button(
        "🧭 Help me choose",
        key="binary_rope_advisor_btn",
        help="Answer 3 short questions to get recommended ROPE & precision-goal values.",
        use_container_width=True,
    ):
        rope_advisor_dialog_binary_single(theta_null=theta_null)

    # TODO: more to just above the Analyze button
    if rope_width is None or precision_goal is None:
        st.sidebar.caption("⚠️ Set ROPE width and Precision Goal above to enable analysis.")

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

    if any(v is None for v in [successes, failures, total]):
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
    if total < 2:
        st.warning("Need at least 2 observations.")
        return
    if rope_min is None or rope_max is None or rope_width is None or precision_goal is None:
        return
    if rope_min >= rope_max:
        st.warning("ROPE min must be less than ROPE max.")
        return
    if rope_min < 0 or rope_max > 1:
        st.warning("ROPE bounds must be within [0, 1] for binary data.")
        return
    if precision_goal > rope_width:
        st.warning(f"Precision goal {GOAL_STR} must not exceed the ROPE width.")
        return

    observed_rate = successes / total if total > 0 else 0.0

    # --- Input summary ---
    st.markdown("#### Binary — Single Group")

    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        st.markdown(
            f"**Data**  \n"
            f"{successes} successes / {total} total  \n"
            f"Rate {BINARY_SINGLE_PARAMETER_ESTIMATE_STR} = {observed_rate:{fmt}}"
        )
    with col_s2:
        st.markdown(
            f"**ROPE**  \n"
            f"Range: [{rope_min:{fmt}}, {rope_max:{fmt}}]  \n"
            f"Width {ROPE_WIDTH_STR} = {rope_width:{fmt}}"
        )
    with col_s3:
        st.markdown(
            f"**Posterior Requirements**  \n"
            f"Precision Goal {GOAL_STR} = {precision_goal:{fmt}}  \n"
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

    # --- Sample size advice (shown only when precision not yet met) ---
    if not result.precision_met:
        variance = observed_rate * (1 - observed_rate)
        n_goal, n_additional = estimate_n_goal(variance, precision_goal, total, ci_fraction)
        st.info(
            f"📏 To achieve precision goal ω_goal={precision_goal:{fmt}}, based on the current observed rate θ̂={observed_rate:{fmt}}:  \n"
            f"You have sampled **{total:,}** data points.  \n"
            f"~**{n_goal:,}** samples are recommended.  \n"
            f"That leaves at least **~{n_additional:,}** additional samples to collect."
        )

    if result.can_stop:
        _render_single_group_peek(result, inputs, observed_rate, a, b)
    else:
        with st.expander("Let Me Peek! 👀", expanded=False):
            tab_peek, tab_decide = st.tabs(["🔍 Posterior Peek", "Decide Now! 🎲"])
            with tab_peek:
                _render_single_group_peek(result, inputs, observed_rate, a, b)
            with tab_decide:
                _render_forced_decision_single(result, inputs, observed_rate, successes, failures)

    # --- Maths Tutorial ---
    with st.expander('🎓 "The Maths Behind the Curtain"', expanded=False):
        st.markdown(MATHS_BINARY_SINGLE_GROUP)


def _render_single_group_peek(result, inputs, observed_rate, a, b):
    """Render metrics, posterior plot, and alternative methods for single-group binary."""
    dp = inputs["decimal_places"]
    fmt = f".{dp}f"
    precision_goal = inputs["precision_goal"]
    total = inputs["total"]
    theta_null = inputs["theta_null"]

    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m2:
        st.metric(f"HDI width {HDI_WIDTH_STR}", f"{result.hdi_width:{fmt}}",
                   delta=f"{GOAL_STR}: {precision_goal:{fmt}}",
                   delta_color="normal" if result.precision_met else "inverse")
    with col_m1:
        st.metric("HDI range", f"[{result.hdi_min:{fmt}}, {result.hdi_max:{fmt}}]")
    with col_m3:
        st.metric(r"Observed rate $\hat{\theta}$", f"{observed_rate:{fmt}}")

    fig = plot_posterior_binary(result, successes=a, failures=b, decimal_places=dp)
    st.pyplot(fig)

    with st.expander("⚖️ Alternative Methods", expanded=False):
        tab_nhst, tab_bf = st.tabs(["NHST (p-value)", "Bayes Factor"])

        with tab_nhst:
            alpha = st.slider(
                "Significance level (α)", min_value=0.01, max_value=0.10,
                value=0.05, step=0.01, format="%.2f", key="binary_sg_alpha"
            )

            se_null = np.sqrt(theta_null * (1 - theta_null) / total)
            test_stat, p_val, _ = nhst_test(
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

            interp_scale = st.radio(
                "Interpretation scale",
                options=["jeffreys", "kass_raftery"],
                format_func=lambda x: "Jeffreys (1961)" if x == "jeffreys" else "Kass & Raftery (1995)",
                horizontal=True,
                key="binary_sg_bf_scale"
            )

            prior_alpha = PRIOR_SPECS[prior_choice]["alpha"]
            prior_beta = PRIOR_SPECS[prior_choice]["beta"]

            bf10 = binary_single_group_bayes_factor(
                successes=a,
                n=total,
                theta_null=theta_null,
                prior_alpha=prior_alpha,
                prior_beta=prior_beta,
            )

            if interp_scale == "jeffreys":
                category, emoji = interpret_bayes_factor_jeffreys(bf10)
            else:
                category, emoji = interpret_bayes_factor_kass_raftery(bf10)

            col_b1, col_b2 = st.columns(2)
            with col_b1:
                st.metric("BF₁₀", f"{bf10:.3f}")
            with col_b2:
                st.metric("Interpretation", f"{emoji} {category}")

            bf01 = 1 / bf10
            st.caption(f"BF₀₁ (evidence for H₀) = {bf01:.3f}")

            st.markdown(BAYES_FACTOR_INTERPRETATION)

            show_savage_dickey = st.checkbox(
                "Show Savage-Dickey density ratio",
                value=False,
                key="binary_sg_bf_savage_dickey",
                help="Visualize BF as the ratio of prior/posterior density heights at θ₀"
            )

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


def _render_forced_decision_single(result, inputs, observed_rate, successes, failures):
    """Render the 'Decide Now! 🎲' tab content for single-group binary."""
    dp = inputs["decimal_places"]
    fmt = f".{dp}f"
    theta_null = inputs["theta_null"]
    rope_min = inputs["rope_min"]
    rope_max = inputs["rope_max"]

    st.info(
        "DPitG stopping criteria are not yet met. These methods allow a provisional decision "
        "based on the current posterior. Treat results with caution — the posterior is still imprecise."
    )

    # ──  Posterior Tail Probability ────────────────────────────────────────
    st.markdown("#### Posterior Tail Probability")

    prob, direction = posterior_tail_probability(successes, failures, theta_null, observed_rate)

    if direction == "above":
        prob_label = "P(θ > θ_null | data)"
        dir_caption = (
            f"Observed rate ({observed_rate:{fmt}}) ≥ θ_null ({theta_null:{fmt}}) "
            f"→ reporting P(θ > θ_null | data)"
        )
    else:
        prob_label = "P(θ < θ_null | data)"
        dir_caption = (
            f"Observed rate ({observed_rate:{fmt}}) < θ_null ({theta_null:{fmt}}) "
            f"→ reporting P(θ < θ_null | data)"
        )

    st.caption(dir_caption)

    col_prob, _ = st.columns([1, 2])
    with col_prob:
        st.metric(prob_label, f"{prob:.4f}")

    threshold = st.slider(
        "Decision threshold",
        min_value=0.80, max_value=0.99, value=0.95, step=0.01, format="%.2f",
        key="forced_threshold_slider",
    )

    if prob >= threshold:
        st.warning(
            f"⚠️ **Forced Decision: Reject θ_null** — "
            f"effect is {direction} null with {prob:.1%} posterior probability "
            f"(threshold {threshold:.2f} met)."
        )
    else:
        st.warning(
            f"⚠️ **Forced Decision: Insufficient evidence** — "
            f"posterior probability {prob:.3f} < threshold {threshold:.2f}. "
            f"No directional forced verdict."
        )

    # ── Bayesian Expected Loss ────────────────────────────────────────────
    with st.expander("⚖️ Account for decision costs (Bayesian Expected Loss)", expanded=False):
        loss_ratio = st.slider(
            "Cost ratio  L₀ / L₁",
            min_value=0.1, max_value=10.0, value=1.0, step=0.1, format="%.1f",
            key="forced_loss_ratio_slider",
            help=(
                "L₀ = cost of wrongly accepting H₀ (false positive).  "
                "L₁ = cost of wrongly rejecting H₀ (false negative).  "
                "Ratio = 1 → symmetric loss (majority-posterior rule)."
            ),
        )

        p_inside, p_outside, el_accept, el_reject, forced_accept = bayesian_expected_loss(
            successes, failures, rope_min, rope_max, loss_ratio
        )

        col1, col2 = st.columns(2)
        with col1:
            st.metric("P(θ inside ROPE | data)", f"{p_inside:.4f}")
            st.metric("EL(Accept H₀)", f"{el_accept:.4f}")
        with col2:
            st.metric("P(θ outside ROPE | data)", f"{p_outside:.4f}")
            st.metric("EL(Reject H₀)", f"{el_reject:.4f}")

        if forced_accept:
            st.warning(
                f"⚠️ **Forced Decision: Accept θ_null** — "
                f"expected loss favors Accept (EL={el_accept:.4f} < EL={el_reject:.4f})."
            )
        else:
            st.warning(
                f"⚠️ **Forced Decision: Reject θ_null** — "
                f"expected loss favors Reject (EL={el_reject:.4f} < EL={el_accept:.4f})."
            )

    # ── Methods & References ──────────────────────────────────────────────────
    with st.expander("📚 Methods & References", expanded=False):
        st.markdown(FORCED_DECISION_REFERENCES)


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
            "Total trials", min_value=2, value=None, step=1, key=f"{key_prefix}_total",
        )
        successes = st.sidebar.number_input(
            "Successes", min_value=0, max_value=total, value=None, step=1,
            key=f"{key_prefix}_successes",
        )
        failures = (total - successes) if (total is not None and successes is not None) else None
    elif input_mode == "Success % & Total":
        total = st.sidebar.number_input(
            "Total trials", min_value=2, value=None, step=1, key=f"{key_prefix}_total_pct",
        )
        success_pct = st.sidebar.number_input(
            "Success %", min_value=0.0, max_value=100.0, value=None, step=0.1,
            format="%.1f", key=f"{key_prefix}_success_pct",
        )
        successes = int(round(success_pct / 100.0 * total)) if (success_pct is not None and total is not None) else None
        failures = (total - successes) if (total is not None and successes is not None) else None
    else:
        successes = st.sidebar.number_input(
            "Successes", min_value=0, value=None, step=1, key=f"{key_prefix}_successes_sf",
        )
        failures = st.sidebar.number_input(
            "Failures", min_value=0, value=None, step=1, key=f"{key_prefix}_failures_sf",
        )
        total = (successes + failures) if (successes is not None and failures is not None) else None

    return {"successes": successes, "failures": failures, "total": total}


def _sidebar_between_groups() -> dict:
    """Sidebar inputs for between-groups binary comparison."""

    st.sidebar.markdown("### 📊 Data")

    for key, default in [("bg_label_a", "Group A"), ("bg_label_b", "Group B")]:
        if key not in st.session_state:
            st.session_state[key] = default
    col_la, col_lb = st.sidebar.columns(2)
    with col_la:
        label_a = st.text_input("Label A", key="bg_label_a")
    with col_lb:
        label_b = st.text_input("Label B", key="bg_label_b")
    if not label_a.strip():
        label_a = "Group A"
    if not label_b.strip():
        label_b = "Group B"

    group_a = _sidebar_group_inputs(label_a, "bg_a")
    group_b = _sidebar_group_inputs(label_b, "bg_b")

    st.sidebar.markdown("### 🎯 Hypothesis & ROPE")

    if "bg_theta_null" not in st.session_state:
        st.session_state["bg_theta_null"] = 0.0
    theta_null = st.sidebar.number_input(
        "Null hypothesis (δ₀ = p_A − p_B)", min_value=-1.0, max_value=1.0,
        step=0.01, format="%.4f", key="bg_theta_null",
    )

    rope_mode = st.sidebar.radio(
        "ROPE specification",
        ["Full width (symmetric)", "Explicit min / max"],
        horizontal=True,
        key="bg_rope_mode",
    )

    if rope_mode == "Full width (symmetric)":
        if "bg_rope_width" not in st.session_state:
            st.session_state["bg_rope_width"] = 0.10
        rope_width = st.sidebar.number_input(
            "ROPE width (Δ_ROPE)", min_value=0.001, max_value=2.0,
            step=0.01, format="%.3f", key="bg_rope_width",
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

    if "bg_precision_goal" not in st.session_state:
        st.session_state["bg_precision_goal"] = 0.08
    precision_goal = st.sidebar.number_input(
        "Goal (target HDI width)",
        min_value=0.001, max_value=2.0,
        step=0.01, format="%.3f", key="bg_precision_goal",
        help="Must not exceed the ROPE width for the method to work.",
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
    """Render results for between-groups binary comparison."""

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

    n_a, s_a = group_a["total"], group_a["successes"]
    n_b, s_b = group_b["total"], group_b["successes"]

    if any(v is None for v in [n_a, s_a, n_b, s_b]):
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
            f"**{label_a}**  \n"
            f"{s_a} successes / {n_a} total  \n"
            f"Rate = {p_a:{fmt}}"
        )
    with col_b:
        st.markdown(
            f"**{label_b}**  \n"
            f"{s_b} successes / {n_b} total  \n"
            f"Rate = {p_b:{fmt}}"
        )

    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        st.markdown(
            f"**Difference (δ)**  \n"
            f"p̂_{label_a} − p̂_{label_b} = {delta:{fmt}}  \n"
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

    # --- Sample size advice (shown only when precision not yet met) ---
    if not result.precision_met:
        n_a_goal, n_b_goal, n_a_add, n_b_add = estimate_n_goal_between_groups(
            p_a, n_a, p_b, n_b, precision_goal, ci_fraction
        )
        st.info(
            f"📏 To achieve precision goal ω_goal={precision_goal:{fmt}}, based on the current observed rates "
            f"θ̂_{label_a}={p_a:{fmt}}, θ̂_{label_b}={p_b:{fmt}} (preserving the current {n_a}/{n_b} group ratio):  \n"
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

        fig2 = plot_two_beta_posteriors(a_a, b_a, a_b, b_b, overlap=overlap, decimal_places=dp,
                                         label_a=label_a, label_b=label_b)
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
                test_stat, p_val, _ = nhst_test(
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
        st.markdown(MATHS_BINARY_BETWEEN_GROUPS, unsafe_allow_html=True)
