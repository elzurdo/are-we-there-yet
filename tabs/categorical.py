"""
Categorical variables — one-vs-rest analysis.

The user provides counts for multiple categories and receives ePitG decisions
for each category vs the reference category using binary proportion differences.

TODO (v2.0): Consider full Dirichlet posterior with Monte Carlo HDI for joint uncertainty
TODO (v2.0): Account for multiple comparisons correction (e.g., Bonferroni, FDR)

Sidebar: all inputs
Main area: summary + forest plot + individual verdicts
"""
import streamlit as st
import numpy as np

from utils.stats import binary_difference_hdi, CI_FRACTION
from utils.decision import epitg_decision, DECISION_DISPLAY
from utils.viz import plot_categorical_forest
from utils.verdict import render_verdict_display


def get_example_values() -> dict:
    """Return session-state key/value pairs for a worked example."""
    return {
        "cat_n_categories": 3,
        "cat_count_0": 120,
        "cat_count_1": 95,
        "cat_count_2": 80,
        "cat_theta_null": 0.0,
        "cat_rope_mode": "Full width (symmetric)",
        "cat_rope_width": 0.10,
        "cat_precision_goal": 0.08,
    }


def sidebar_inputs() -> dict:
    """Render all Categorical inputs in the sidebar and return a dict of values."""

    st.sidebar.markdown("### 📊 Data")

    # Number of categories
    n_categories = st.sidebar.number_input(
        "Number of categories",
        min_value=3,
        max_value=10,
        value=3,
        step=1,
        key="cat_n_categories",
        help="Minimum 3 categories required for meaningful one-vs-rest comparison"
    )

    # Category inputs
    categories = {}
    category_names = []
    
    st.sidebar.markdown("#### Category Counts")
    
    for i in range(n_categories):
        col1, col2 = st.sidebar.columns([2, 1])
        with col1:
            name = st.text_input(
                f"Category {i+1} name",
                value=chr(65+i),  # A, B, C, ...
                key=f"cat_name_{i}",
            )
        with col2:
            count = st.number_input(
                "Count",
                min_value=0,
                value=None,
                key=f"cat_count_{i}",
            )
        
        if name:  # Only add if name is provided
            categories[name] = count
            category_names.append(name)

    # Reference category selection
    st.sidebar.markdown("### 🎯 Reference Category")
    
    if category_names:
        reference_category = st.sidebar.selectbox(
            "Reference category",
            options=category_names,
            index=0,
            key="cat_reference",
            help="All other categories will be compared to this one"
        )
    else:
        reference_category = None

    st.sidebar.markdown("### 🎯 Hypothesis & ROPE")

    theta_null = st.sidebar.number_input(
        "Null hypothesis (δ₀)", min_value=-1.0, max_value=1.0,
        value=0.0, step=0.01, format="%.4f", key="cat_theta_null",
        help="Typically 0 (no difference from reference)"
    )

    rope_mode = st.sidebar.radio(
        "ROPE specification",
        ["Full width (symmetric)", "Explicit min / max"],
        horizontal=True,
        key="cat_rope_mode",
    )

    if rope_mode == "Full width (symmetric)":
        rope_width = st.sidebar.number_input(
            "ROPE width (Δ_ROPE)", min_value=0.001, max_value=2.0,
            value=0.10, step=0.01, format="%.3f", key="cat_rope_width",
        )
        rope_min = theta_null - rope_width / 2
        rope_max = theta_null + rope_width / 2
    else:
        rope_min = st.sidebar.number_input(
            "ROPE min", min_value=-1.0, max_value=1.0,
            value=-0.05, step=0.01, format="%.4f", key="cat_rope_min",
        )
        rope_max = st.sidebar.number_input(
            "ROPE max", min_value=-1.0, max_value=1.0,
            value=0.05, step=0.01, format="%.4f", key="cat_rope_max",
        )
        rope_width = rope_max - rope_min

    st.sidebar.markdown("### 🔬 Precision Goal")

    precision_goal = st.sidebar.number_input(
        "Goal (target HDI width)",
        min_value=0.001, max_value=2.0,
        value=0.08, step=0.01, format="%.3f", key="cat_precision_goal",
        help="Must be narrower than the ROPE width for the method to work.",
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


def render_results(inputs: dict):
    """Render the verdicts and forest plot in the main area."""

    if not inputs or not inputs.get("categories"):
        st.info("👈 Configure categorical data in the sidebar to begin")
        return

    if any(v is None for v in inputs["categories"].values()):
        st.info("👈 Enter counts for all categories in the sidebar to begin.")
        return

    categories = inputs["categories"]
    reference_category = inputs["reference_category"]
    rope_min = inputs["rope_min"]
    rope_max = inputs["rope_max"]
    rope_width = inputs["rope_width"]
    precision_goal = inputs["precision_goal"]
    ci_fraction = inputs["ci_fraction"]
    dp = inputs["decimal_places"]
    verdict_style = inputs["verdict_style"]
    fmt = f".{dp}f"

    # --- Validation ---
    if len(categories) < 2:
        st.warning("Need at least 2 categories.")
        return
    if reference_category not in categories:
        st.warning("Reference category not found in data.")
        return
    if rope_min >= rope_max:
        st.warning("ROPE min must be less than ROPE max.")
        return
    if precision_goal >= rope_width:
        st.warning("Precision goal must be narrower than the ROPE width.")
        return

    # --- Compute total and proportions ---
    total_count = sum(categories.values())
    proportions = {k: v / total_count for k, v in categories.items()}

    reference_count = categories[reference_category]
    reference_prop = proportions[reference_category]

    # --- Input summary ---
    st.markdown("#### Categorical — One-vs-Rest")

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        cat_summary = "  \n".join([f"**{k}**: {v} ({proportions[k]:{fmt}})" for k, v in categories.items()])
        st.markdown(
            f"**Categories (n={total_count})**  \n"
            f"{cat_summary}"
        )
    with col_s2:
        st.markdown(
            f"**Reference**: {reference_category}  \n"
            f"Count: {reference_count} ({reference_prop:{fmt}})  \n\n"
            f"**ROPE**: [{rope_min:{fmt}}, {rope_max:{fmt}}]  \n"
            f"**Precision Goal**: {precision_goal:{fmt}}  \n"
            f"**HDI mass**: {ci_fraction:.0%}"
        )

    # --- Compute all comparisons ---
    comparisons = []
    other_categories = [k for k in categories.keys() if k != reference_category]

    for category in other_categories:
        cat_count = categories[category]
        cat_prop = proportions[category]
        delta = cat_prop - reference_prop

        # Compute HDI using binary difference (CLT)
        hdi_min, hdi_max = binary_difference_hdi(
            cat_prop, total_count,  # Using total as "n" for proportions
            reference_prop, total_count,
            ci_fraction=ci_fraction
        )

        # Get ePitG decision
        result = epitg_decision(
            hdi_min=hdi_min,
            hdi_max=hdi_max,
            rope_min=rope_min,
            rope_max=rope_max,
            precision_goal=precision_goal,
            point_estimate=delta,
            ci_fraction=ci_fraction,
        )

        comparisons.append({
            'category': category,
            'count': cat_count,
            'proportion': cat_prop,
            'delta': delta,
            'hdi_min': hdi_min,
            'hdi_max': hdi_max,
            'point_estimate': delta,
            'result': result,
            'verdict': result.decision.name,
            'color': result.display['color'],
        })

    # --- Forest Plot ---
    st.divider()
    st.markdown("### 📊 Forest Plot: All Comparisons")

    forest_data = [
        {
            'category': c['category'],
            'hdi_min': c['hdi_min'],
            'hdi_max': c['hdi_max'],
            'point_estimate': c['delta'],
            'verdict': c['verdict'],
            'color': c['color'],
        }
        for c in comparisons
    ]

    fig_forest = plot_categorical_forest(
        comparisons=forest_data,
        reference_name=reference_category,
        rope_min=rope_min,
        rope_max=rope_max,
        decimal_places=dp,
    )
    st.pyplot(fig_forest)

    # --- Individual Verdicts ---
    st.divider()
    st.markdown("### 📋 Individual Comparisons")

    for i, comp in enumerate(comparisons):
        with st.expander(f"**{comp['category']} vs {reference_category}**", expanded=(i == 0)):
            result = comp['result']
            
            # Summary metrics
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            with col_m1:
                st.metric("Difference (δ)", f"{comp['delta']:{fmt}}")
            with col_m2:
                st.metric("HDI", f"[{comp['hdi_min']:{fmt}}, {comp['hdi_max']:{fmt}}]")
            with col_m3:
                st.metric("HDI width", f"{result.hdi_width:{fmt}}",
                         delta=f"Goal: {precision_goal:{fmt}}",
                         delta_color="normal" if result.precision_met else "inverse")
            with col_m4:
                emoji = result.display['emoji']
                label = result.display['label']
                st.metric("Verdict", f"{emoji} {label}")

            # Detailed verdict
            render_verdict_display(result, precision_goal, fmt, verdict_style)

    # --- Notes ---
    with st.expander("ℹ️ About One-vs-Rest Analysis"):
        st.markdown("""
**Approach:**
- Each non-reference category is compared independently to the reference category
- Uses binary proportion difference with CLT Normal approximation
- HDI computed for each difference: δᵢ = p_i - p_ref

**Interpretation:**
- **Positive δ**: Category has higher proportion than reference
- **Negative δ**: Category has lower proportion than reference
- **HDI overlaps ROPE**: Difference is practically negligible

**Limitations:**
- Treats each comparison independently (doesn't account for joint uncertainty)
- Multiple comparisons increase chance of false positives
- Assumes sufficient sample size for CLT validity (each category count ≥ 5)

**Future enhancements (v2.0):**
- Full Dirichlet posterior with Monte Carlo HDI
- Multiple comparisons correction (Bonferroni, FDR)
- Proper ordinal variable support with cumulative link models
        """)


def render_main():
    """Main entry point for categorical tab."""
    inputs = sidebar_inputs()
    render_results(inputs)
