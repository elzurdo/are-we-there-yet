"""
Prospective planning for continuous data — single group.

Sidebar: domain preset only.
Main area: null value (μ_null), Steps 1 & 2, Step 3.
"""
import streamlit as st
from utils.constants import CONTINUOUS_NULL_STR, ROPE_WIDTH_STR
from utils.size_planner import (
    CONTINUOUS_SINGLE_DOMAIN_PRESETS,
    render_domain_preset,
    render_steps_1_and_2,
    render_step3_single_continuous,
)

_PFX_SG = "_prosp_cont_sg"


def sidebar_inputs(analysis_mode: str) -> dict:
    """Render domain preset into the sidebar; return it for the main area."""
    preset_name, preset = render_domain_preset(
        CONTINUOUS_SINGLE_DOMAIN_PRESETS, _PFX_SG, container=st.sidebar
    )
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
        st.info("🚧 Continuous between-groups prospective planning is coming soon.")


def _render_single(preset) -> None:
    pfx = _PFX_SG

    st.markdown("### 🎯 Null hypothesis")
    mu_null = st.number_input(
        f"Null value ({CONTINUOUS_NULL_STR})",
        value=0.0,
        step=0.1,
        format="%.2f",
        key=f"{pfx}_mu_null",
        help="The reference value around which the ROPE will be centred (e.g. 0 for a difference, or a known target).",
    )

    st.divider()
    st.markdown("### 📐 ROPE & Precision")

    learn_more = (
        "Enter the smallest change in your measurement that would trigger a decision.  \n"
        f"The **ROPE** (Region of Practical Equivalence) spans ±Δ_min around {CONTINUOUS_NULL_STR}, "
        f"giving {ROPE_WIDTH_STR} = 2 × Δ_min."
    )

    rope_width, precision_goal, all_ready, goal_too_wide = render_steps_1_and_2(
        advisor_prefix=pfx,
        presets=CONTINUOUS_SINGLE_DOMAIN_PRESETS,
        null_val=mu_null,
        null_label=CONTINUOUS_NULL_STR,
        effect_label="Δ_min",
        step1_caption=(
            "What's the smallest change in your measurement that your team would act on? "
            "This will determine the ROPE around the null value."
        ),
        step1_learn_more=learn_more,
        step1_help=f"The ROPE spans ±Δ_min around {CONTINUOUS_NULL_STR}. {ROPE_WIDTH_STR} = 2 × Δ_min.",
        preset=preset,
        min_effect_max=None,
        min_effect_step=0.1,
        min_effect_format="%.2f",
    )

    if not all_ready or goal_too_wide:
        return

    sigma_min_default = preset.get("sigma_min", rope_width) if preset else rope_width
    sigma_max_default = preset.get("sigma_max", rope_width * 5) if preset else rope_width * 5

    st.divider()
    render_step3_single_continuous(
        advisor_prefix=pfx,
        rope_width=rope_width,
        precision_goal=precision_goal,
        sigma_min_default=sigma_min_default,
        sigma_max_default=sigma_max_default,
    )