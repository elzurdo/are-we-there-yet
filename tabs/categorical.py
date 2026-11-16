"""
Categorical variables — one-vs-rest and one-vs-reference analysis.

Two analysis modes:

  One-vs-Rest (default):
    For each category i, the posterior on p_i is Beta(c_i+1, N−c_i+1) — the
    exact Dirichlet marginal. The null is θ_null = 1/K (uniform), overridable.
    ROPE and precision goal are on the proportion scale.

  One-vs-Reference (pairwise):
    Each non-reference category is compared to the chosen reference via the CLT
    Normal approximation for a difference of two proportions. Each group uses its
    own count (not the total N). ROPE and precision goal are on the difference scale.

TODO (v2.0): Full Dirichlet posterior with Monte Carlo HDI for joint uncertainty.
TODO (v2.0): Multiple comparisons correction (e.g., Bonferroni, FDR).
"""
import streamlit as st
import numpy as np

from utils.stats import successes_failures_to_hdi_ci_limits, binary_difference_hdi, CI_FRACTION
from utils.constants import ROPE_MODE_HELP
from utils.decision import dpitg_decision, DECISION_DISPLAY
from utils.viz import plot_categorical_forest
from utils.verdict import render_verdict_display
from utils.bayes_factor import (
    binary_single_group_bayes_factor, PRIOR_SPECS,
    interpret_bayes_factor_jeffreys, interpret_bayes_factor_kass_raftery,
)
from utils.tutorials import (
    NHST_LIMITATIONS,
    MATHS_CATEGORICAL,
    BAYES_FACTOR_INTRO_CATEGORICAL,
    BAYES_FACTOR_INTERPRETATION,
)


def get_example_values() -> dict:
    """Return session-state key/value pairs for a worked example."""
    return {
        "cat_n_categories": 3,
        "cat_count_0": 120,
        "cat_count_1": 95,
        "cat_count_2": 80,
        "cat_analysis_mode": "One-vs-Rest",
        "cat_rope_mode": "Full width (symmetric)",
        "cat_rope_width": 0.10,
        "cat_precision_goal": 0.08,
    }


def sidebar_inputs() -> dict:
    """Render all Categorical inputs in the sidebar and return a dict of values."""

    st.sidebar.markdown("### 📊 Data")

    n_categories = st.sidebar.number_input(
        "Number of categories",
        min_value=3,
        max_value=10,
        value=3,
        step=1,
        key="cat_n_categories",
        help="Minimum 3 categories required.",
    )

    categories = {}
    category_names = []

    st.sidebar.markdown("#### Category Counts")

    for i in range(n_categories):
        col1, col2 = st.sidebar.columns([2, 1])
        with col1:
            name = st.text_input(
                f"Category {i+1} name",
                value=chr(65 + i),
                key=f"cat_name_{i}",
            )
        with col2:
            count = st.number_input(
                "Count",
                min_value=0,
                value=None,
                key=f"cat_count_{i}",
            )
        if name:
            categories[name] = count
            category_names.append(name)

    # ── Analysis mode ──────────────────────────────────────────
    st.sidebar.markdown("### 🔄 Analysis Mode")
    analysis_mode = st.sidebar.radio(
        "Compare each category against",
        options=["One-vs-Rest", "One-vs-Reference"],
        index=0,
        key="cat_analysis_mode",
        help=(
            "**One-vs-Rest**: each category vs. the whole population (Dirichlet marginal — recommended).  \n"
            "**One-vs-Reference**: each non-reference category vs. a chosen reference (CLT difference)."
        ),
    )

    # Reference category — only shown in one-vs-reference mode
    reference_category = None
    if analysis_mode == "One-vs-Reference":
        st.sidebar.markdown("### 🎯 Reference Category")
        if category_names:
            reference_category = st.sidebar.selectbox(
                "Reference category",
                options=category_names,
                index=0,
                key="cat_reference",
                help="All other categories are compared to this one.",
            )

    # ── Hypothesis & ROPE ──────────────────────────────────────
    st.sidebar.markdown("### 🎯 Hypothesis & Effect Size")

    k = n_categories
    default_theta_null = round(1.0 / k, 6)

    if analysis_mode == "One-vs-Rest":
        theta_null = st.sidebar.number_input(
            "Null proportion (θ_null)",
            min_value=0.0, max_value=1.0,
            value=default_theta_null,
            step=0.01, format="%.4f",
            key="cat_theta_null_ovr",
            help=f"Null proportion for each category. Defaults to 1/K = {default_theta_null:.4f} (uniform).",
        )
        rope_help = "ROPE centred on the null proportion (proportion scale)."
    else:
        theta_null = st.sidebar.number_input(
            "Null difference (Δ₀)",
            min_value=-1.0, max_value=1.0,
            value=0.0,
            step=0.01, format="%.4f",
            key="cat_theta_null_ref",
            help="Typically 0 (no difference between categories).",
        )
        rope_help = "ROPE centred on the null difference (difference scale)."

    rope_mode = st.sidebar.radio(
        "ROPE specification",
        ["Full width (symmetric)", "Explicit min / max"],
        horizontal=True,
        key="cat_rope_mode",
        help=ROPE_MODE_HELP,
    )

    if rope_mode == "Full width (symmetric)":
        rope_width = st.sidebar.number_input(
            "ROPE width (ω_ROPE)",
            min_value=0.001, max_value=2.0,
            value=0.10, step=0.01, format="%.3f",
            key="cat_rope_width",
            help=rope_help,
        )
        rope_min = theta_null - rope_width / 2
        rope_max = theta_null + rope_width / 2
    else:
        rope_min = st.sidebar.number_input(
            "ROPE min", min_value=-1.0, max_value=1.0,
            value=theta_null - 0.05, step=0.01, format="%.4f",
            key="cat_rope_min",
        )
        rope_max = st.sidebar.number_input(
            "ROPE max", min_value=-1.0, max_value=1.0,
            value=theta_null + 0.05, step=0.01, format="%.4f",
            key="cat_rope_max",
        )
        rope_width = rope_max - rope_min

    # ── Precision goal ─────────────────────────────────────────
    st.sidebar.markdown("### 🔬 Precision Goal")

    precision_goal = st.sidebar.number_input(
        "Goal (target HDI width)",
        min_value=0.001, max_value=2.0,
        value=0.08, step=0.01, format="%.3f",
        key="cat_precision_goal",
        help="Must not exceed the ROPE width.",
    )

    ci_fraction = CI_FRACTION
    decimal_places = 3
    verdict_style = "Centered text"
    with st.sidebar.expander("⚙️ Advanced"):
        ci_fraction = st.slider(
            "HDI mass", min_value=0.80, max_value=0.99,
            value=CI_FRACTION, step=0.01, format="%.2f",
            key="cat_ci_fraction",
        )
        decimal_places = st.number_input(
            "Decimal places", min_value=1, max_value=10,
            value=3, step=1, key="cat_decimal_places",
        )
        verdict_style = st.radio(
            "Verdict display style",
            ["Centered text", "Info/Warning box"],
            key="cat_verdict_style",
        )

    return {
        "categories": categories,
        "analysis_mode": analysis_mode,
        "reference_category": reference_category,
        "theta_null": theta_null,
        "rope_min": rope_min,
        "rope_max": rope_max,
        "rope_width": rope_width,
        "precision_goal": precision_goal,
        "ci_fraction": ci_fraction,
        "decimal_places": decimal_places,
        "verdict_style": verdict_style,
    }


def _compute_one_vs_rest(categories, total_count, theta_null, rope_min, rope_max,
                         precision_goal, ci_fraction):
    """Beta-posterior HDI for each category's proportion vs the whole population."""
    comparisons = []
    for name, count in categories.items():
        failures = total_count - count
        hdi_min, hdi_max = successes_failures_to_hdi_ci_limits(count, failures, ci_fraction)
        point_estimate = count / total_count
        result = dpitg_decision(
            hdi_min=hdi_min,
            hdi_max=hdi_max,
            rope_min=rope_min,
            rope_max=rope_max,
            precision_goal=precision_goal,
            point_estimate=point_estimate,
            ci_fraction=ci_fraction,
        )
        comparisons.append({
            "category": name,
            "count": count,
            "proportion": point_estimate,
            "point_estimate": point_estimate,
            "hdi_min": hdi_min,
            "hdi_max": hdi_max,
            "result": result,
            "verdict": result.decision.name,
            "color": result.display["color"],
        })
    return comparisons


def _compute_one_vs_reference(categories, total_count, reference_category,
                              rope_min, rope_max, precision_goal, ci_fraction):
    """CLT Normal HDI for the difference p_i − p_ref, using each group's own count."""
    ref_count = categories[reference_category]
    ref_prop = ref_count / total_count
    comparisons = []
    for name, count in categories.items():
        if name == reference_category:
            continue
        cat_prop = count / total_count
        delta = cat_prop - ref_prop
        hdi_min, hdi_max = binary_difference_hdi(
            cat_prop, count,        # group i: proportion, count
            ref_prop, ref_count,    # reference: proportion, count
            ci_fraction=ci_fraction,
        )
        result = dpitg_decision(
            hdi_min=hdi_min,
            hdi_max=hdi_max,
            rope_min=rope_min,
            rope_max=rope_max,
            precision_goal=precision_goal,
            point_estimate=delta,
            ci_fraction=ci_fraction,
        )
        comparisons.append({
            "category": name,
            "count": count,
            "proportion": cat_prop,
            "point_estimate": delta,
            "hdi_min": hdi_min,
            "hdi_max": hdi_max,
            "result": result,
            "verdict": result.decision.name,
            "color": result.display["color"],
        })
    return comparisons


def render_results(inputs: dict):
    """Render the verdicts and forest plot in the main area."""

    if not inputs or not inputs.get("categories"):
        st.info("👈 Configure categorical data in the sidebar to begin")
        return

    if any(v is None for v in inputs["categories"].values()):
        st.info("👈 Enter counts for all categories in the sidebar to begin.")
        return

    categories = inputs["categories"]
    analysis_mode = inputs["analysis_mode"]
    reference_category = inputs["reference_category"]
    theta_null = inputs["theta_null"]
    rope_min = inputs["rope_min"]
    rope_max = inputs["rope_max"]
    rope_width = inputs["rope_width"]
    precision_goal = inputs["precision_goal"]
    ci_fraction = inputs["ci_fraction"]
    dp = inputs["decimal_places"]
    verdict_style = inputs["verdict_style"]
    fmt = f".{dp}f"

    # ── Validation ─────────────────────────────────────────────
    if len(categories) < 2:
        st.warning("Need at least 2 categories.")
        return
    if analysis_mode == "One-vs-Reference" and reference_category not in categories:
        st.warning("Reference category not found in data.")
        return
    if rope_min >= rope_max:
        st.warning("ROPE min must be less than ROPE max.")
        return
    if precision_goal > rope_width:
        st.warning("Precision goal must not exceed the ROPE width.")
        return

    total_count = sum(categories.values())
    proportions = {k: v / total_count for k, v in categories.items()}
    k = len(categories)

    # ── Input summary ──────────────────────────────────────────
    mode_label = ("One-vs-Rest" if analysis_mode == "One-vs-Rest"
                  else f"One-vs-Reference (ref: {reference_category})")
    st.markdown(f"#### Categorical — {mode_label}")

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        cat_summary = "  \n".join(
            [f"**{k}**: {v} ({proportions[k]:{fmt}})" for k, v in categories.items()]
        )
        st.markdown(f"**Categories (n={total_count})**  \n{cat_summary}")
    with col_s2:
        null_label = "θ_null" if analysis_mode == "One-vs-Rest" else "Δ₀"
        st.markdown(
            f"**{null_label}**: {theta_null:{fmt}}  \n"
            f"**ROPE**: [{rope_min:{fmt}}, {rope_max:{fmt}}]  \n"
            f"**Precision Goal**: {precision_goal:{fmt}}  \n"
            f"**HDI mass**: {ci_fraction:.0%}"
        )

    # ── Compute comparisons ────────────────────────────────────
    if analysis_mode == "One-vs-Rest":
        comparisons = _compute_one_vs_rest(
            categories, total_count, theta_null,
            rope_min, rope_max, precision_goal, ci_fraction,
        )
    else:
        comparisons = _compute_one_vs_reference(
            categories, total_count, reference_category,
            rope_min, rope_max, precision_goal, ci_fraction,
        )

    # ── Forest Plot ────────────────────────────────────────────
    st.divider()
    st.markdown("### 📊 Forest Plot: All Comparisons")

    forest_data = [
        {
            "category": c["category"],
            "hdi_min": c["hdi_min"],
            "hdi_max": c["hdi_max"],
            "point_estimate": c["point_estimate"],
            "verdict": c["verdict"],
            "color": c["color"],
        }
        for c in comparisons
    ]

    fig_forest = plot_categorical_forest(
        comparisons=forest_data,
        rope_min=rope_min,
        rope_max=rope_max,
        decimal_places=dp,
        mode="one_vs_rest" if analysis_mode == "One-vs-Rest" else "one_vs_reference",
        theta_null=theta_null,
        reference_name=reference_category,
    )
    st.pyplot(fig_forest)

    # ── Individual Verdicts ────────────────────────────────────
    st.divider()
    st.markdown("### 📋 Individual Comparisons")

    # Bayes Factor settings — shared across all comparisons
    # BF always uses the single-group binary formula with θ_null = 1/K
    theta_null_uniform = 1.0 / k

    with st.expander("⚖️ Bayes Factor Settings", expanded=False):
        st.markdown(BAYES_FACTOR_INTRO_CATEGORICAL)
        col_p1, col_p2 = st.columns([1, 2])
        with col_p1:
            bf_prior_choice = st.selectbox(
                "Prior for H₁",
                options=list(PRIOR_SPECS.keys()),
                format_func=lambda x: x.replace("_", " ").title(),
                key="cat_bf_prior",
            )
        with col_p2:
            st.caption(PRIOR_SPECS[bf_prior_choice]["description"])

        bf_interp_scale = st.radio(
            "Interpretation scale",
            options=["jeffreys", "kass_raftery"],
            format_func=lambda x: "Jeffreys (1961)" if x == "jeffreys" else "Kass & Raftery (1995)",
            horizontal=True,
            key="cat_bf_scale",
        )
        st.caption(f"Uniform null: θ_null = 1/K = 1/{k} = {theta_null_uniform:.4f}")
        st.markdown(BAYES_FACTOR_INTERPRETATION)

    bf_prior_alpha = PRIOR_SPECS[bf_prior_choice]["alpha"]
    bf_prior_beta = PRIOR_SPECS[bf_prior_choice]["beta"]

    for i, comp in enumerate(comparisons):
        if analysis_mode == "One-vs-Rest":
            expander_label = f"**{comp['category']}** (proportion vs uniform null)"
        else:
            expander_label = f"**{comp['category']} vs {reference_category}**"

        with st.expander(expander_label, expanded=(i == 0)):
            result = comp["result"]

            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            with col_m1:
                est_label = "Proportion (p̂)" if analysis_mode == "One-vs-Rest" else "Difference (δ)"
                st.metric(est_label, f"{comp['point_estimate']:{fmt}}")
            with col_m2:
                st.metric("HDI", f"[{comp['hdi_min']:{fmt}}, {comp['hdi_max']:{fmt}}]")
            with col_m3:
                st.metric(
                    "HDI width", f"{result.hdi_width:{fmt}}",
                    delta=f"Goal: {precision_goal:{fmt}}",
                    delta_color="normal" if result.precision_met else "inverse",
                )
            with col_m4:
                st.metric("Verdict", f"{result.display['emoji']} {result.display['label']}")

            render_verdict_display(result, precision_goal, fmt, verdict_style)

            # Bayes Factor (always single-group binary vs uniform null 1/K)
            cat_count = comp["count"]
            bf10 = binary_single_group_bayes_factor(
                successes=max(cat_count, 1),
                n=total_count,
                theta_null=theta_null_uniform,
                prior_alpha=bf_prior_alpha,
                prior_beta=bf_prior_beta,
            )
            if bf_interp_scale == "jeffreys":
                bf_category, bf_emoji = interpret_bayes_factor_jeffreys(bf10)
            else:
                bf_category, bf_emoji = interpret_bayes_factor_kass_raftery(bf10)

            col_bf1, col_bf2 = st.columns(2)
            with col_bf1:
                st.metric(
                    f"BF₁₀ vs uniform (θ={theta_null_uniform:.3f})",
                    f"{bf10:.3f}",
                )
            with col_bf2:
                st.metric("Interpretation", f"{bf_emoji} {bf_category}")

    # TODO (viz): Add a log-scale BF₁₀ bar chart per category. See TODO.md § 10e.

    # ── Tutorial expanders ─────────────────────────────────────
    st.divider()

    with st.expander('🎓 "The Maths Behind the Curtain"', expanded=False):
        st.markdown(MATHS_CATEGORICAL)

    with st.expander('📚 "Why We Don\'t Use p-values Alone"', expanded=False):
        st.markdown(NHST_LIMITATIONS)

    with st.expander("ℹ️ About This Analysis", expanded=False):
        if analysis_mode == "One-vs-Rest":
            st.markdown("""
**One-vs-Rest approach (Dirichlet marginal):**
- For each category $i$ with count $c_i$ out of $N$ total, the posterior is
  $p_i \\mid \\text{data} \\sim \\text{Beta}(c_i+1,\\; N-c_i+1)$.
- This is the exact marginal of the Dirichlet posterior — no approximation.
- The null is $\\theta_{\\rm null} = 1/K$ (uniform). The ROPE and precision goal
  are on the proportion scale.
- All $K$ categories are analysed symmetrically; no reference is required.

**Limitations:**
- Marginals are analysed independently; the Dirichlet correlation structure is ignored.
- Multiple comparisons: $K$ independent tests increase the chance of false positives.
- Full joint inference requires a Dirichlet posterior (v2.0 planned).
            """)
        else:
            st.markdown(f"""
**One-vs-Reference approach (CLT Normal approximation):**
- Each non-reference category is compared to **{reference_category}** via
  $\\delta_i = p_i - p_{{\\rm ref}}$.
- The SE uses each group's own count:
  $\\text{{SE}} = \\sqrt{{\\hat p_i(1-\\hat p_i)/c_i + \\hat p_{{\\rm ref}}(1-\\hat p_{{\\rm ref}})/c_{{\\rm ref}}}}$.
- The ROPE and precision goal are on the difference scale.

**Limitations:**
- CLT approximation requires each group count $\\geq 5$ for reliable HDIs.
- Only $K-1$ comparisons shown; the reference category has no verdict.
- Multiple comparisons: $K-1$ tests increase the chance of false positives.
            """)


def render_main():
    """Main entry point for categorical tab."""
    inputs = sidebar_inputs()
    render_results(inputs)
