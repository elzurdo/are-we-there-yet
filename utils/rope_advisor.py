"""
ROPE & Precision Goal advisor — binary single-group and between-groups.

Provides @st.dialog functions that walk the user through 3 short questions
and stage the resulting ROPE width and precision-goal values into session state
so the flush block in the relevant sidebar function injects them before any
widgets are re-instantiated.

Session state key conventions:
  _advisor_sg_*  — single-group dialog widgets and state
  _advisor_bg_*  — between-groups dialog widgets and state
  _rope_advisor_sg_result — result staged by single-group apply callback
  _rope_advisor_bg_result — result staged by between-groups apply callback

UI logic (presets, step renderers) lives in utils/size_planner.py and is
shared with the prospective planning page.
"""
import streamlit as st
from utils.constants import (
    BINARY_SINGLE_MIN_EFFECT_STR,
    BINARY_SINGLE_NULL_STR,
    BINARY_BG_NULL_STR,
    GOAL_STR,
    ROPE_WIDTH_STR,
    ROPE_HALF_WIDTH_STR,
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


def _on_apply_click(advisor_prefix: str, result_key: str) -> None:
    """Generic apply callback for both single-group and between-groups advisors.

    Reads widget values from session state using advisor_prefix, then writes a
    result dict to result_key. The sidebar flush block maps result keys to the
    mode-specific session state keys for ROPE / precision widgets.
    """
    min_effect = st.session_state.get(f"{advisor_prefix}_min_effect")
    if min_effect is None:
        return
    rope_width_val = 2 * min_effect

    precision_pct = st.session_state.get(f"{advisor_prefix}_precision_pct", 80)
    precision_goal_val = rope_width_val * precision_pct / 100.0
    explore_omega = st.session_state.get(f"{advisor_prefix}_explore_omega")
    if explore_omega is not None:
        precision_goal_val = explore_omega

    result = {
        "rope_mode": "Full width (symmetric)",
        "rope_width": round(rope_width_val, 6),
        "precision_goal": round(precision_goal_val, 6),
    }

    explore_theta = st.session_state.get(f"{advisor_prefix}_explore_theta")
    if explore_theta is not None:
        result["theta_null"] = round(explore_theta, 4)

    st.session_state[result_key] = result


# ── Single-group dialog ───────────────────────────────────────────────────────

@st.dialog("🧭 Help me choose ROPE & Precision Goal", width="large")
def rope_advisor_dialog_binary_single(theta_null: float = 0.5) -> None:
    """Interactive 3-step guide for binary single-group ROPE & precision goal.

    On Apply, _on_apply_click() commits the result to _rope_advisor_sg_result,
    then this dialog detects the key and calls st.rerun(scope="app") to close
    itself and let the sidebar flush the values before its widgets render.
    """
    if "_rope_advisor_sg_result" in st.session_state:
        st.rerun(scope="app")

    pfx = "_advisor_sg"

    learn_more_sg = (
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
        step1_learn_more=learn_more_sg,
    )

    if all_ready and not goal_too_wide:
        st.divider()
        explore_theta, explore_omega = render_step3_single(
            advisor_prefix=pfx,
            rope_width=rope_width,
            precision_goal=precision_goal,
            theta_null=theta_null,
        )

        # Show what will be applied when Step 3 has been touched
        theta_changed = abs(explore_theta - theta_null) > 1e-4
        omega_changed = abs(explore_omega - precision_goal) > 1e-6
        step3_ever_touched = st.session_state.get(f"{pfx}_step3_touched", False)
        if theta_changed or omega_changed:
            st.session_state[f"{pfx}_step3_touched"] = True
            step3_ever_touched = True

        if step3_ever_touched:
            theta_note = (
                f"{BINARY_SINGLE_NULL_STR} updated to **{explore_theta:.2f}** (was {theta_null:.2f})"
                if theta_changed
                else f"{BINARY_SINGLE_NULL_STR} remains **{theta_null:.2f}**"
            )
            omega_note = (
                f"{GOAL_STR} updated to **{explore_omega:.4f}** (was {precision_goal:.4f} from Step 2)"
                if omega_changed
                else f"{GOAL_STR} remains **{precision_goal:.4f}**"
            )
            st.success(
                f"**Values that will be applied:**  \n"
                f"- {theta_note}  \n"
                f"- {omega_note}  \n"
                f"- **ROPE:** [{explore_theta - rope_width/2:.4f}, "
                f"{explore_theta + rope_width/2:.4f}] "
                f"({ROPE_WIDTH_STR} = {rope_width:.4f})"
            )

    st.button(
        "✅ Apply",
        type="primary",
        disabled=not all_ready or goal_too_wide,
        on_click=_on_apply_click,
        kwargs={"advisor_prefix": pfx, "result_key": "_rope_advisor_sg_result"},
    )
    st.caption(
        "These values will fill in the sidebar — "
        "then enter your observed data to get a verdict."
    )


# ── Between-groups dialog ─────────────────────────────────────────────────────

@st.dialog("🧭 Help me choose ROPE & Precision Goal", width="large")
def rope_advisor_dialog_binary_between_groups(
    delta_null: float = 0.0,
    p_a_default: float = 0.5,
    p_b_default: float = 0.5,
    label_a: str = "A",
    label_b: str = "B",
) -> None:
    """Interactive 3-step guide for binary between-groups ROPE & precision goal.

    On Apply, stages result to _rope_advisor_bg_result, then reruns the app so
    the sidebar flush block in _sidebar_between_groups injects the values.
    """
    if "_rope_advisor_bg_result" in st.session_state:
        st.rerun(scope="app")

    pfx = "_advisor_bg"

    learn_more_bg = (
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
        step1_learn_more=learn_more_bg,
        step1_help=(
            f"The ROPE spans ±{ROPE_HALF_WIDTH_STR} around {BINARY_BG_NULL_STR}. "
            f"Enter this as a percentage — {ROPE_WIDTH_STR} will be twice this value."
        ),
    )

    if all_ready and not goal_too_wide:
        st.divider()
        _, _, explore_omega = render_step3_between(
            advisor_prefix=pfx,
            rope_width=rope_width,
            precision_goal=precision_goal,
            delta_null=delta_null,
            p_a_default=p_a_default,
            p_b_default=p_b_default,
            label_a=label_a,
            label_b=label_b,
        )

        omega_changed = abs(explore_omega - precision_goal) > 1e-6
        if omega_changed:
            st.success(
                f"**Values that will be applied:**  \n"
                f"- {GOAL_STR} updated to **{explore_omega:.4f}** "
                f"(was {precision_goal:.4f} from Step 2)  \n"
                f"- **ROPE:** [{delta_null - rope_width/2:.4f}, "
                f"{delta_null + rope_width/2:.4f}] "
                f"({ROPE_WIDTH_STR} = {rope_width:.4f})"
            )

    st.button(
        "✅ Apply",
        type="primary",
        disabled=not all_ready or goal_too_wide,
        on_click=_on_apply_click,
        kwargs={"advisor_prefix": pfx, "result_key": "_rope_advisor_bg_result"},
    )
    st.caption(
        "These values will fill in the sidebar — "
        "then enter your observed data to get a verdict."
    )
