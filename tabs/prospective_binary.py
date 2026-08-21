"""
Prospective planning for binary (Bernoulli) data — single group and between groups.

Sidebar: domain preset only.
Main area: null hypothesis (+ group labels for between groups), Steps 1 & 2, Step 3.
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
    render_domain_preset,
    render_steps_1_and_2,
    render_step3_single,
    render_step3_between,
)

# Prefix namespaces: separate from _advisor_sg/bg used by the dialog
_PFX_SG = "_prosp_sg"
_PFX_BG = "_prosp_bg"


def sidebar_inputs(analysis_mode: str) -> dict:
    """Render only the domain preset into the sidebar; return it for the main area."""
    if analysis_mode == "Single Group":
        presets = DOMAIN_PRESETS
        pfx = _PFX_SG
    else:
        presets = BETWEEN_GROUPS_DOMAIN_PRESETS
        pfx = _PFX_BG

    preset_name, preset = render_domain_preset(presets, pfx, container=st.sidebar)
    return {
        "analysis_mode": analysis_mode,
        "preset_name": preset_name,
        "preset": preset,
    }


def render_results(inputs: dict) -> None:
    """Render null hypothesis, Steps 1–3 in the main area."""
    analysis_mode = inputs.get("analysis_mode", "Single Group")
    preset = inputs.get("preset")

    if analysis_mode == "Single Group":
        _render_single(preset)
    else:
        _render_between(preset)


def _render_single(preset) -> None:
    pfx = _PFX_SG

    st.markdown("### 🎯 Null hypothesis")
    theta_null = st.number_input(
        f"Null hypothesis ({BINARY_SINGLE_NULL_STR})",
        min_value=0.0,
        max_value=1.0,
        value=0.5,
        step=0.01,
        format="%.4f",
        key=f"{pfx}_theta_null",
    )

    st.divider()
    st.markdown("### 📐 ROPE & Precision")

    learn_more = (
        f"If your baseline is {BINARY_SINGLE_NULL_STR} = 0.50 and a shift to "
        f"{BINARY_SINGLE_OBSERVE_STR} = 0.52 would change a decision, enter **0.02**, "
        f"meaning {BINARY_SINGLE_MIN_EFFECT_STR} = 0.02.  \n"
        f"The **ROPE** (Region of Practical Equivalence) spans "
        f"±{BINARY_SINGLE_MIN_EFFECT_STR} around {BINARY_SINGLE_NULL_STR}, "
        f"giving {ROPE_WIDTH_STR} = 2{BINARY_SINGLE_MIN_EFFECT_STR}."
    )

    rope_width, precision_goal, all_ready, goal_too_wide = render_steps_1_and_2(
        advisor_prefix=pfx,
        presets=DOMAIN_PRESETS,
        null_val=theta_null,
        step1_learn_more=learn_more,
        preset=preset,
    )

    if not all_ready or goal_too_wide:
        return

    st.divider()
    render_step3_single(
        advisor_prefix=pfx,
        rope_width=rope_width,
        precision_goal=precision_goal,
        theta_null=theta_null,
    )


def _render_between(preset) -> None:
    pfx = _PFX_BG

    st.markdown("### 🏷️ Group labels")
    col_a, col_b = st.columns(2)
    with col_a:
        label_a = st.text_input("Group A label", value="Control", key=f"{pfx}_label_a")
    with col_b:
        label_b = st.text_input("Group B label", value="Treatment", key=f"{pfx}_label_b")

    st.markdown("### 🎯 Null hypothesis")
    delta_null = st.number_input(
        f"Null difference ({BINARY_BG_NULL_STR} = θ_A − θ_B)",
        min_value=-0.99,
        max_value=0.99,
        value=0.0,
        step=0.01,
        format="%.4f",
        key=f"{pfx}_delta_null",
    )

    st.divider()
    st.markdown("### 📐 ROPE & Precision")

    learn_more = (
        f"If {label_a}'s rate is {theta_hat_label(label_a)} = 0.50 "
        f"and {label_b}'s is {theta_hat_label(label_b)} = 0.52, "
        f"the difference Δ = {theta_hat_label(label_a)} − {theta_hat_label(label_b)} = −0.02.  \n"
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
        preset=preset,
    )

    if not all_ready or goal_too_wide:
        return

    st.divider()
    render_step3_between(
        advisor_prefix=pfx,
        rope_width=rope_width,
        precision_goal=precision_goal,
        delta_null=delta_null,
        p_a_default=0.5,
        p_b_default=max(0.01, min(0.99, 0.5 - delta_null)),
        label_a=label_a,
        label_b=label_b,
    )
