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

Domain presets offer sensible starting points that the user can override.
Add new entries to DOMAIN_PRESETS / BETWEEN_GROUPS_DOMAIN_PRESETS to extend
domain support without touching the dialog logic.
"""
import math
import streamlit as st
from utils.constants import (
    BINARY_SINGLE_MIN_EFFECT_STR,
    BINARY_SINGLE_NULL_STR,
    BINARY_BG_NULL_STR,
    GOAL_STR,
    HDI_WIDTH_STR,
    ROPE_WIDTH_STR,
    ROPE_HALF_WIDTH_STR,
    BINARY_SINGLE_OBSERVE_STR,
    theta_label,
    theta_hat_label,
)
from utils.stats import (
    binomial_rate_ci_width_to_sample_size,
    binomial_difference_ci_width_to_sample_size,
)
from utils.viz import (
    plot_n_goal_by_parameter,
    plot_n_goal_by_parameter_between_groups,
)

# ── Single-group domain presets ───────────────────────────────────────────────
# TODO: narratives currently hard-code example rates (e.g. "around 3%").
#   Make them dynamic so they update if the user changes the preset values.
DOMAIN_PRESETS = {
    "🔧 Custom (I'll set my own)": None,
    "🛒 E-commerce / conversion rate": {
        "min_meaningful_diff_pct": 0.5,
        "precision_pct": 70,
        "narrative": (
            "Your checkout conversion is around 3%. "
            "A half-point shift (e.g. 3.0% → 3.5%) is worth acting on. "
            "You want answers fast — being wrong occasionally just means running another test."
        ),
    },
    "🏥 Medical / clinical rate": {
        "min_meaningful_diff_pct": 2.0,
        "precision_pct": 90,
        "narrative": (
            "You're tracking a treatment response rate around 70%. "
            "A 2 percentage-point shift would change clinical practice. "
            "You need tight precision — wrong calls here affect patients."
        ),
    },
    "💻 Internal tooling / ops": {
        "min_meaningful_diff_pct": 3.0,
        "precision_pct": 80,
        "narrative": (
            "Your pipeline success rate is around 95%. "
            "Swings under 3 percentage points are normal noise. "
            "Data is cheap (every job run is a data point), so you'd rather collect more and be sure."
        ),
    },
    "🗳️ Election polling": {
        "min_meaningful_diff_pct": 1.0,
        "precision_pct": 90,
        "narrative": (
            "You're polling whether a candidate crosses the 50% threshold. "
            "A 1 percentage-point shift in true support is meaningful in a tight race. "
            "Polling data is expensive (each response costs real fieldwork), "
            "but getting the call wrong is worse — you need high precision."
        ),
    },
}

# ── Between-groups domain presets ─────────────────────────────────────────────
BETWEEN_GROUPS_DOMAIN_PRESETS = {
    "🔧 Custom (I'll set my own)": None,
    "🛒 E-commerce / A/B test": {
        "min_meaningful_diff_pct": 0.5,
        "precision_pct": 70,
        "narrative": (
            "Your control group converts at ~3% and your treatment at ~3.5%. "
            "A 0.5 percentage-point lift is the smallest difference worth deploying. "
            "Fast iteration matters — being wrong occasionally means running another test."
        ),
    },
    "🏥 Clinical trial": {
        "min_meaningful_diff_pct": 2.0,
        "precision_pct": 90,
        "narrative": (
            "Your control arm has a ~70% response rate; treatment might shift it by 2+ pp. "
            "A 2 percentage-point difference between arms would change clinical practice. "
            "High precision is essential — wrong calls affect patients."
        ),
    },
    "💻 Canary deployment / ops": {
        "min_meaningful_diff_pct": 3.0,
        "precision_pct": 80,
        "narrative": (
            "Your baseline pipeline succeeds ~95% of the time. "
            "Differences under 3 pp between control and canary are normal noise. "
            "Each job run is a data point, so you'd rather collect more and be sure."
        ),
    },
    "🗳️ Survey / polling comparison": {
        "min_meaningful_diff_pct": 1.0,
        "precision_pct": 90,
        "narrative": (
            "You're comparing support rates between two demographic groups. "
            "A 1 percentage-point difference in true support is meaningful. "
            "Fieldwork is expensive, but getting the comparison wrong matters more."
        ),
    },
}


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _sync_p_b_to_p_a(advisor_prefix: str, delta_null: float) -> None:
    """on_change callback for the p_A slider when p_B linking is active.

    Computes p_B = p_A - delta_null (clamped to [0.01, 0.99]) and writes it
    to session state so the p_B slider picks it up on the next render.
    """
    p_a = st.session_state.get(f"{advisor_prefix}_explore_p_a", 0.5)
    p_b = max(0.01, min(0.99, p_a - delta_null))
    st.session_state[f"{advisor_prefix}_explore_p_b"] = p_b


def _on_apply_click(advisor_prefix: str, result_key: str) -> None:
    """Generic apply callback for both single-group and between-groups advisors.

    Reads widget values from session state using advisor_prefix, then writes a
    result dict to result_key. The sidebar flush block maps result keys to the
    mode-specific session state keys for ROPE / precision widgets.

    Note: explore_theta (single-group only) is included in the result only when
    the key exists in session state; between-groups uses explore_p_a / explore_p_b
    instead and does not set explore_theta, so it is naturally excluded.
    """
    min_diff_pct = st.session_state.get(f"{advisor_prefix}_min_diff_pct")
    if min_diff_pct is None:
        return
    rope_width_val = 2 * min_diff_pct / 100.0

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


def _preview_box(
    null_val, rope_width, min_diff_pct, precision_goal,
    null_label=None, effect_label=None,
):
    """Render ROPE bounds and precision goal as a success box."""
    if null_label is None:
        null_label = BINARY_SINGLE_NULL_STR
    if effect_label is None:
        effect_label = BINARY_SINGLE_MIN_EFFECT_STR
    st.success(
        f"**ROPE:** {null_label} ± {effect_label} ({min_diff_pct:.2f} pp) "
        f"→ [{null_val - rope_width/2:.4f}, {null_val + rope_width/2:.4f}]"
        f"  ({ROPE_WIDTH_STR} = {rope_width:.4f})  \n"
        f"**Precision goal:** stop when {HDI_WIDTH_STR} < "
        f"{GOAL_STR} = **{precision_goal:.4f}** ({precision_goal * 100:.2f} pp)"
    )


def _steps_1_and_2(
    advisor_prefix: str,
    presets: dict,
    null_val: float,
    null_label=None,
    effect_label=None,
    step1_caption: str = "What's the smallest change in proportion your team would actually act on?",
    step1_learn_more: str = None,
    step1_help: str = None,
):
    """Render Steps 1 and 2 (ROPE width and precision goal) and return computed values.

    Returns (rope_width, precision_goal, all_ready, goal_too_wide).
    rope_width and precision_goal are None when inputs are incomplete.
    """
    if null_label is None:
        null_label = BINARY_SINGLE_NULL_STR
    if effect_label is None:
        effect_label = BINARY_SINGLE_MIN_EFFECT_STR

    # ── Optional domain preset ────────────────────────────────────────────────
    preset_name = st.selectbox(
        "Start from a domain preset (optional)",
        options=list(presets.keys()),
        index=0,
        help=(
            "Pre-fills the questions below with typical values for that domain. "
            "You can still override anything."
        ),
        key=f"{advisor_prefix}_preset",
    )
    preset = presets[preset_name]

    if preset is not None and "narrative" in preset:
        st.info(preset["narrative"])

    prev_preset = st.session_state.get(f"{advisor_prefix}_prev_preset")
    if preset_name != prev_preset:
        st.session_state[f"{advisor_prefix}_prev_preset"] = preset_name
        if preset is not None:
            st.session_state[f"{advisor_prefix}_min_diff_pct"] = float(preset["min_meaningful_diff_pct"])
            if "precision_pct" in preset:
                st.session_state[f"{advisor_prefix}_precision_pct"] = int(preset["precision_pct"])

    st.divider()

    # ── Step 1 ────────────────────────────────────────────────────────────────
    st.markdown(f"#### Step 1 — Smallest effect that matters ({effect_label})")
    st.caption(step1_caption)

    if step1_learn_more:
        with st.expander("ℹ️ Learn more"):
            st.markdown(step1_learn_more)

    _help = step1_help or f"The ROPE spans ±{effect_label} around {null_label}. {ROPE_WIDTH_STR} = 2{effect_label}."
    _diff_kwargs = {}
    if f"{advisor_prefix}_min_diff_pct" not in st.session_state:
        _diff_kwargs["value"] = float(preset["min_meaningful_diff_pct"]) if preset else None
    min_diff_pct = st.number_input(
        f"Minimum meaningful {effect_label} around each side of {null_label} (percentage points)",
        min_value=0.01,
        max_value=50.0,
        step=0.5,
        format="%.2f",
        help=_help,
        key=f"{advisor_prefix}_min_diff_pct",
        **_diff_kwargs,
    )

    rope_width = (2 * min_diff_pct / 100.0) if min_diff_pct is not None else None

    if rope_width is not None:
        st.caption(
            f"→ ROPE = [{null_val - rope_width/2:.4f}, {null_val + rope_width/2:.4f}]"
            f"  ({ROPE_WIDTH_STR} = {rope_width:.4f})"
        )

    st.divider()

    # ── Step 2 ────────────────────────────────────────────────────────────────
    st.markdown("#### Step 2 — How precise?")
    st.caption("How precise do you need your answer to be? More precision means collecting more data.")
    with st.expander("ℹ️ Learn more"):
        st.markdown(
            f"*Precision* is the width of your uncertainty about the true value — "
            f"narrower means more confidence, but requires more data.  \n"
            f"The **Precision Goal** ({GOAL_STR}) is the target width at stopping. "
            f"It must satisfy {GOAL_STR} ≤ {ROPE_WIDTH_STR}."
        )

    _pct_kwargs = {}
    if f"{advisor_prefix}_precision_pct" not in st.session_state:
        _pct_kwargs["value"] = int(preset["precision_pct"]) if preset and "precision_pct" in preset else 80
    precision_pct = st.slider(
        f"{GOAL_STR} as % of {ROPE_WIDTH_STR}",
        min_value=50,
        max_value=100,
        step=1,
        format="%d%%",
        key=f"{advisor_prefix}_precision_pct",
        help="70–80% is typical; above 90% requires substantially more data.",
        **_pct_kwargs,
    )

    precision_goal = None
    if rope_width is not None:
        precision_goal = rope_width * precision_pct / 100.0
        st.caption(
            f"→ {ROPE_WIDTH_STR} × {precision_pct}% = {GOAL_STR} = **{precision_goal:.4f}**"
        )

        explore_omega_ss = st.session_state.get(f"{advisor_prefix}_explore_omega")
        if explore_omega_ss is not None and abs(explore_omega_ss - precision_goal) > 1e-6:
            st.caption(
                f"→ overridden to {GOAL_STR} = **{explore_omega_ss:.4f}** in Step 3 below"
            )
    else:
        st.caption("→ Complete Step 1 first to see the computed value.")

    # ── Step 2 preview ────────────────────────────────────────────────────────
    all_ready = rope_width is not None and precision_goal is not None
    goal_too_wide = all_ready and precision_goal > rope_width

    if all_ready:
        if goal_too_wide:
            st.warning(
                f"⚠️ {GOAL_STR} ({precision_goal:.4f}) must **not exceed** "
                f"{ROPE_WIDTH_STR} ({rope_width:.4f}) for the stopping rule to be meaningful. "
                "Increase the fraction."
            )
        else:
            _preview_box(null_val, rope_width, min_diff_pct, precision_goal,
                         null_label=null_label, effect_label=effect_label)
    else:
        st.info("Complete Steps 1–2 above to see a preview.")

    return rope_width, precision_goal, all_ready, goal_too_wide


# ── Single-group dialog ───────────────────────────────────────────────────────

@st.dialog("🧭 Help me choose ROPE & Precision Goal", width="large")
def rope_advisor_dialog_binary_single(theta_null: float = 0.5) -> None:
    """Interactive 3-step guide for binary single-group ROPE & precision goal.

    On Apply, _on_apply_click() commits the result to _rope_advisor_sg_result,
    then this dialog detects the key and calls st.rerun(scope="app") to close
    itself and let the sidebar flush the values before its widgets render.

    Parameters
    ----------
    theta_null : float
        Current null hypothesis value — used to compute ROPE bounds for the preview.
    """
    if "_rope_advisor_sg_result" in st.session_state:
        st.rerun(scope="app")

    pfx = "_advisor_sg"

    learn_more_sg = (
        f"If your baseline is {BINARY_SINGLE_NULL_STR} = 0.50 and a shift to "
        f"{BINARY_SINGLE_OBSERVE_STR} = 0.52 would change a decision, enter **2** "
        f"(percentage points), meaning {BINARY_SINGLE_MIN_EFFECT_STR} = 0.02.  \n"
        f"The **ROPE** (Region of Practical Equivalence) spans "
        f"±{BINARY_SINGLE_MIN_EFFECT_STR} around {BINARY_SINGLE_NULL_STR}, "
        f"giving {ROPE_WIDTH_STR} = 2{BINARY_SINGLE_MIN_EFFECT_STR}."
    )

    rope_width, precision_goal, all_ready, goal_too_wide = _steps_1_and_2(
        advisor_prefix=pfx,
        presets=DOMAIN_PRESETS,
        null_val=theta_null,
        step1_learn_more=learn_more_sg,
    )

    # ── Step 3 — Estimated sample size ────────────────────────────────────────
    if all_ready and not goal_too_wide:
        st.divider()
        st.markdown("#### Step 3 — Estimated Sample Size")
        st.caption(
            "How many observations would you need to reach this precision? "
            "Adjust θ and ω below to explore. Changes here will be applied."
        )

        col_theta, col_omega = st.columns(2)
        with col_theta:
            # Streamlit widget labels do not render LaTeX; using Unicode/ASCII notation
            explore_theta = st.slider(
                "θ (expected rate)",
                min_value=0.01,
                max_value=0.99,
                value=float(theta_null),
                step=0.01,
                format="%.2f",
                key=f"{pfx}_explore_theta",
            )
        with col_omega:
            w_goal_min = 0.5 * float(rope_width)
            w_goal_max = float(rope_width)
            # Streamlit widget labels do not render LaTeX; using Unicode/ASCII notation
            explore_omega = st.slider(
                "ω_goal (precision)",
                min_value=w_goal_min,
                max_value=w_goal_max,
                value=float(precision_goal),
                step=0.001,
                format="%.4f",
                key=f"{pfx}_explore_omega",
            )

        n_goal_est = binomial_rate_ci_width_to_sample_size(
            explore_theta, explore_omega, z_star=1.96,
        )
        n_goal_display = max(1, int(n_goal_est))
        st.metric(label="N_goal (estimated minimum sample size)", value=f"{n_goal_display:,}")

        # TODO: update z_star to derive from a user-chosen confidence level
        # TODO: add absolute-width precision mode as an advanced option (removed
        #   from Step 2 to reduce cognitive load; see git history for prior UI).
        with st.expander("⚙️ Advanced"):
            adv_z = st.number_input(
                "z* (critical value)",
                min_value=1.0,
                max_value=4.0,
                value=1.96,
                step=0.01,
                format="%.2f",
                key=f"{pfx}_z_star",
                help="1.96 ≈ 95% HDI, 2.576 ≈ 99% HDI",
            )
            adv_col1, adv_col2 = st.columns(2)
            with adv_col1:
                st.number_input(
                    "Background ω min",
                    min_value=0.5 * w_goal_min,
                    max_value=w_goal_max,
                    value=w_goal_min,
                    step=0.01,
                    format="%.2f",
                    key=f"{pfx}_w_min",
                )
            with adv_col2:
                st.number_input(
                    "Background ω max",
                    min_value=w_goal_min,
                    max_value=2 * w_goal_max,
                    value=w_goal_max,
                    step=0.01,
                    format="%.2f",
                    key=f"{pfx}_w_max",
                )

            n_goal_est_adv = binomial_rate_ci_width_to_sample_size(
                explore_theta, explore_omega, z_star=adv_z,
            )
            n_goal_display_adv = max(1, int(n_goal_est_adv))
            st.metric(label="N_goal (with custom z*)", value=f"{n_goal_display_adv:,}")

        fig = plot_n_goal_by_parameter(
            omega_goal=explore_omega,
            theta_highlight=explore_theta,
            z_star=st.session_state.get(f"{pfx}_z_star", 1.96),
            w_goal_min=st.session_state.get(f"{pfx}_w_min", w_goal_min),
            w_goal_max=st.session_state.get(f"{pfx}_w_max", w_goal_max),
        )
        st.pyplot(fig)

        # ── Step 3 preview ────────────────────────────────────────────────────
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
                else f"{BINARY_SINGLE_NULL_STR} remains the same at **{theta_null:.2f}**"
            )
            omega_note = (
                f"{GOAL_STR} updated to **{explore_omega:.4f}** "
                f"(was {precision_goal:.4f} from Step 2)"
                if omega_changed
                else f"{GOAL_STR} remains the same at **{precision_goal:.4f}**"
            )
            effective_theta = explore_theta
            st.success(
                f"**Values that will be applied:**  \n"
                f"- {theta_note}  \n"
                f"- {omega_note}  \n"
                f"- **ROPE:** [{effective_theta - rope_width/2:.4f}, "
                f"{effective_theta + rope_width/2:.4f}] "
                f"({ROPE_WIDTH_STR} = {rope_width:.4f})"
            )

    # ── Apply ─────────────────────────────────────────────────────────────────
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

    Parameters
    ----------
    delta_null : float
        Current null hypothesis for the difference (Δ₀ = θ_A − θ_B).
    p_a_default : float
        Expected rate for Group A — pre-populates the Step 3 θ_A slider.
    p_b_default : float
        Expected rate for Group B — pre-populates the Step 3 θ_B slider.
    label_a : str
        Display name for Group A (e.g. "Control").
    label_b : str
        Display name for Group B (e.g. "Treatment").
    """
    if "_rope_advisor_bg_result" in st.session_state:
        st.rerun(scope="app")

    pfx = "_advisor_bg"

    learn_more_bg = (
        f"If {label_a}'s rate is {theta_hat_label(label_a)} = 0.50 "
        f"and {label_b}'s is {theta_hat_label(label_b)} = 0.52, "
        f"the difference Δ = {theta_hat_label(label_a)} − {theta_hat_label(label_b)} = −0.02 — a 2 pp effect.  \n"
        f"The **ROPE** (Region of Practical Equivalence) spans "
        f"±{ROPE_HALF_WIDTH_STR} around {BINARY_BG_NULL_STR}, "
        f"so {ROPE_WIDTH_STR} equals twice the value you enter below."
    )

    rope_width, precision_goal, all_ready, goal_too_wide = _steps_1_and_2(
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

    # ── Step 3 — Estimated sample size ────────────────────────────────────────
    if all_ready and not goal_too_wide:
        st.divider()
        st.markdown("#### Step 3 — Estimated Sample Size")
        st.caption(
            f"How many observations per group would you need? "
            f"Adjust {theta_label(label_a)}, {theta_label(label_b)}, and {GOAL_STR} below to explore."
        )

        w_goal_min = 0.5 * float(rope_width)
        w_goal_max = float(rope_width)

        # Streamlit widget labels do not render LaTeX; using Unicode/ASCII notation
        linked = st.checkbox(
            f"🔗 Link θ_{label_b} = θ_{label_a} − Δ₀ ({delta_null:+.2f})",
            value=True,
            key=f"{pfx}_link_p_b",
            help="When checked, moving θ_A automatically updates θ_B to maintain the null difference.",
        )

        col_pa, col_pb, col_omega = st.columns(3)
        with col_pa:
            # Streamlit widget labels do not render LaTeX; using Unicode/ASCII notation
            explore_p_a = st.slider(
                f"θ_{label_a} (expected rate)",
                min_value=0.01,
                max_value=0.99,
                value=float(p_a_default),
                step=0.01,
                format="%.2f",
                key=f"{pfx}_explore_p_a",
                on_change=_sync_p_b_to_p_a if linked else None,
                kwargs={"advisor_prefix": pfx, "delta_null": delta_null} if linked else None,
            )
        with col_pb:
            # Streamlit widget labels do not render LaTeX; using Unicode/ASCII notation
            explore_p_b = st.slider(
                f"θ_{label_b} (expected rate)",
                min_value=0.01,
                max_value=0.99,
                value=float(p_b_default),
                step=0.01,
                format="%.2f",
                key=f"{pfx}_explore_p_b",
                disabled=linked,
            )
        with col_omega:
            # Streamlit widget labels do not render LaTeX; using Unicode/ASCII notation
            explore_omega = st.slider(
                "ω_goal (precision)",
                min_value=w_goal_min,
                max_value=w_goal_max,
                value=float(precision_goal),
                step=0.001,
                format="%.4f",
                key=f"{pfx}_explore_omega",
            )

        with st.expander("⚙️ Advanced"):
            adv_r = st.slider(
                "Group ratio r = n_A / (n_A + n_B)",
                min_value=0.1,
                max_value=0.9,
                value=0.5,
                step=0.05,
                format="%.2f",
                key=f"{pfx}_ratio",
                help="0.5 = equal group sizes (default). Adjust if you expect unequal allocation.",
            )
            adv_z = st.number_input(
                "z* (critical value)",
                min_value=1.0,
                max_value=4.0,
                value=1.96,
                step=0.01,
                format="%.2f",
                key=f"{pfx}_z_star",
                help="1.96 ≈ 95% HDI, 2.576 ≈ 99% HDI",
            )
            adv_col1, adv_col2 = st.columns(2)
            with adv_col1:
                st.number_input(
                    "Background ω min",
                    min_value=0.5 * w_goal_min,
                    max_value=w_goal_max,
                    value=w_goal_min,
                    step=0.01,
                    format="%.2f",
                    key=f"{pfx}_w_min",
                )
            with adv_col2:
                st.number_input(
                    "Background ω max",
                    min_value=w_goal_min,
                    max_value=2 * w_goal_max,
                    value=w_goal_max,
                    step=0.01,
                    format="%.2f",
                    key=f"{pfx}_w_max",
                )

        r = st.session_state.get(f"{pfx}_ratio", 0.5)
        z_star = st.session_state.get(f"{pfx}_z_star", 1.96)

        n_total_est = binomial_difference_ci_width_to_sample_size(
            explore_p_a, explore_p_b, r, explore_omega, z_star=z_star,
        )
        n_a_goal = max(1, math.ceil(r * n_total_est))
        n_b_goal = max(1, math.ceil((1 - r) * n_total_est))

        col_na, col_nb = st.columns(2)
        with col_na:
            # Streamlit metric labels do not render LaTeX; using Unicode/ASCII notation
            st.metric(label=f"N_{label_a} goal", value=f"{n_a_goal:,}")
        with col_nb:
            # Streamlit metric labels do not render LaTeX; using Unicode/ASCII notation
            st.metric(label=f"N_{label_b} goal", value=f"{n_b_goal:,}")

        fig = plot_n_goal_by_parameter_between_groups(
            omega_goal=explore_omega,
            p_a_highlight=explore_p_a,
            p_b_fixed=explore_p_b,
            r=r,
            z_star=z_star,
            w_goal_min=st.session_state.get(f"{pfx}_w_min", w_goal_min),
            w_goal_max=st.session_state.get(f"{pfx}_w_max", w_goal_max),
            label_a=label_a,
            label_b=label_b,
        )
        st.pyplot(fig)

        # ── Step 3 preview (shown when ω_goal deviates from Step 2 default) ──
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

    # ── Apply ─────────────────────────────────────────────────────────────────
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
