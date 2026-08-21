"""
Prospective planning for binary (Bernoulli) data — single group and between groups.

Sidebar: domain preset + Steps 1 & 2 (ROPE width, precision goal).
Main area: Step 3 — N_goal estimation with exploration sliders and chart.
"""
import streamlit as st
from utils.constants import (
    BINARY_SINGLE_MIN_EFFECT_STR,
    BINARY_SINGLE_NULL_STR,
    BINARY_BG_NULL_STR,
    ROPE_HALF_WIDTH_STR,
    ROPE_WIDTH_STR,
    BINARY_SINGLE_OBSERVE_STR,
    theta_hat_label,
)
from utils.size_planner import (
    DOMAIN_PRESETS,
    BETWEEN_GROUPS_DOMAIN_PRESETS,
    render_steps_1_and_2,
    render_step3_single,
    render_step3_between,
)

# Prefix namespaces: separate from _advisor_sg/bg used by the dialog
_PFX_SG = "_prosp_sg"
_PFX_BG = "_prosp_bg"


def sidebar_inputs(analysis_mode: str) -> dict:
    """Render planning inputs into the sidebar and return current values."""
    if analysis_mode == "Single Group":
        return _sidebar_single()
    return _sidebar_between()


def _sidebar_single() -> dict:
    pfx = _PFX_SG

    st.sidebar.markdown("### 🎯 Null hypothesis")
    theta_null = st.sidebar.number_input(
        f"Null hypothesis ({BINARY_SINGLE_NULL_STR})",
        min_value=0.0,
        max_value=1.0,
        value=0.5,
        step=0.01,
        format="%.4f",
        key=f"{pfx}_theta_null",
    )

    st.sidebar.divider()
    st.sidebar.markdown("### 📐 ROPE & Precision")

    learn_more = (
        f"If your baseline is {BINARY_SINGLE_NULL_STR} = 0.50 and a shift to "
        f"{BINARY_SINGLE_OBSERVE_STR} = 0.52 would change a decision, enter **2** "
        f"(percentage points), meaning {BINARY_SINGLE_MIN_EFFECT_STR} = 0.02.  \n"
        f"The **ROPE** (Region of Practical Equivalence) spans "
        f"±{BINARY_SINGLE_MIN_EFFECT_STR} around {BINARY_SINGLE_NULL_STR}, "
        f"giving {ROPE_WIDTH_STR} = 2{BINARY_SINGLE_MIN_EFFECT_STR}."
    )

    rope_width, precision_goal, all_ready, goal_too_wide = render_steps_1_and_2(
        advisor_prefix=pfx,
        presets=DOMAIN_PRESETS,
        null_val=theta_null,
        step1_learn_more=learn_more,
        container=st.sidebar,
    )

    return {
        "analysis_mode": "Single Group",
        "theta_null": theta_null,
        "rope_width": rope_width,
        "precision_goal": precision_goal,
        "all_ready": all_ready,
        "goal_too_wide": goal_too_wide,
    }


def _sidebar_between() -> dict:
    pfx = _PFX_BG

    st.sidebar.markdown("### 🏷️ Group labels")
    col_a, col_b = st.sidebar.columns(2)
    with col_a:
        label_a = st.text_input("Group A label", value="Control", key=f"{pfx}_label_a")
    with col_b:
        label_b = st.text_input("Group B label", value="Treatment", key=f"{pfx}_label_b")

    st.sidebar.markdown("### 🎯 Null hypothesis")
    delta_null = st.sidebar.number_input(
        f"Null difference ({BINARY_BG_NULL_STR} = θ_A − θ_B)",
        min_value=-0.99,
        max_value=0.99,
        value=0.0,
        step=0.01,
        format="%.4f",
        key=f"{pfx}_delta_null",
    )

    st.sidebar.divider()
    st.sidebar.markdown("### 📐 ROPE & Precision")

    learn_more = (
        f"If {label_a}'s rate is {theta_hat_label(label_a)} = 0.50 "
        f"and {label_b}'s is {theta_hat_label(label_b)} = 0.52, "
        f"the difference Δ = {theta_hat_label(label_a)} − {theta_hat_label(label_b)} = −0.02 — a 2 pp effect.  \n"
        f"The **ROPE** (Region of Practical Equivalence) spans "
        f"±{ROPE_HALF_WIDTH_STR} around {BINARY_BG_NULL_STR}, "
        f"so {ROPE_WIDTH_STR} equals twice the value you enter below."
    )

    rope_width, precision_goal, all_ready, goal_too_wide = render_steps_1_and_2(
        advisor_prefix=pfx,
        presets=BETWEEN_GROUPS_DOMAIN_PRESETS,
        null_val=delta_null,
        null_label=BINARY_BG_NULL_STR,
        effect_label=ROPE_HALF_WIDTH_STR,
        step1_caption="What's the smallest difference in proportions between groups your team would act on?",
        step1_learn_more=learn_more,
        step1_help=(
            f"The ROPE spans ±{ROPE_HALF_WIDTH_STR} around {BINARY_BG_NULL_STR}. "
            f"Enter as a percentage — {ROPE_WIDTH_STR} will be twice this value."
        ),
        container=st.sidebar,
    )

    return {
        "analysis_mode": "Between Groups",
        "label_a": label_a,
        "label_b": label_b,
        "delta_null": delta_null,
        "rope_width": rope_width,
        "precision_goal": precision_goal,
        "all_ready": all_ready,
        "goal_too_wide": goal_too_wide,
    }


def render_results(inputs: dict) -> None:
    """Render Step 3 (N_goal estimation) in the main area."""
    if not inputs.get("all_ready") or inputs.get("goal_too_wide"):
        st.info(
            "Complete Steps 1 and 2 in the sidebar to see the sample size estimate."
        )
        return

    analysis_mode = inputs.get("analysis_mode", "Single Group")
    rope_width = inputs["rope_width"]
    precision_goal = inputs["precision_goal"]

    st.divider()

    if analysis_mode == "Single Group":
        render_step3_single(
            advisor_prefix=_PFX_SG,
            rope_width=rope_width,
            precision_goal=precision_goal,
            theta_null=inputs["theta_null"],
        )
    else:
        render_step3_between(
            advisor_prefix=_PFX_BG,
            rope_width=rope_width,
            precision_goal=precision_goal,
            delta_null=inputs["delta_null"],
            p_a_default=0.5,
            p_b_default=max(0.01, min(0.99, 0.5 - inputs["delta_null"])),
            label_a=inputs.get("label_a", "A"),
            label_b=inputs.get("label_b", "B"),
        )
