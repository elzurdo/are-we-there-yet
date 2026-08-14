"""
ROPE & Precision Goal advisor — binary single-group.

Provides an @st.dialog that walks the user through 3 short questions
and stages the resulting ROPE width and precision-goal values into
_pending_example so the flush block in app.py injects them before
any widgets are re-instantiated.

Domain presets offer sensible starting points that the user can override.
Add new entries to DOMAIN_PRESETS to extend domain support without touching
the dialog logic.
"""
import streamlit as st
from utils.constants import (
    BINARY_SINGLE_MIN_EFFECT_STR,
    BINARY_SINGLE_NULL_STR,
    GOAL_STR,
    HDI_WIDTH_STR,
    ROPE_WIDTH_STR,
    BINARY_SINGLE_OBSERVE_STR,
)
from utils.stats import binomial_rate_ci_width_to_sample_size
from utils.viz import plot_n_goal_by_parameter

# ── Domain presets ────────────────────────────────────────────────────────────
# Each entry maps to a dict with:
#   min_meaningful_diff_pct  – smallest effect that matters, in pp
#   precision_mode           – "As a fraction of my negligible zone" | "As an absolute width"
#   precision_pct            – used when mode is fraction (0–100)
#   narrative               – plain-language explanation shown in the UI
# TODO: narratives currently hard-code example rates (e.g. "around 3%").
#   Make them dynamic so they update if the user changes the preset values.
DOMAIN_PRESETS = {
    "🔧 Custom (I'll set my own)": None,
    "🛒 E-commerce / conversion rate": {
        "min_meaningful_diff_pct": 0.5,
        "precision_mode": "As a fraction of my negligible zone",
        "precision_pct": 70,
        "narrative": (
            "Your checkout conversion is around 3%. "
            "A half-point shift (e.g. 3.0% → 3.5%) is worth acting on. "
            "You want answers fast — being wrong occasionally just means running another test."
        ),
    },
    "🏥 Medical / clinical rate": {
        "min_meaningful_diff_pct": 2.0,
        "precision_mode": "As a fraction of my negligible zone",
        "precision_pct": 90,
        "narrative": (
            "You're tracking a treatment response rate around 70%. "
            "A 2 percentage-point shift would change clinical practice. "
            "You need tight precision — wrong calls here affect patients."
        ),
    },
    "💻 Internal tooling / ops": {
        "min_meaningful_diff_pct": 3.0,
        "precision_mode": "As a fraction of my negligible zone",
        "precision_pct": 80,
        "narrative": (
            "Your pipeline success rate is around 95%. "
            "Swings under 3 percentage points are normal noise. "
            "Data is cheap (every job run is a data point), so you'd rather collect more and be sure."
        ),
    },
    "🗳️ Election polling": {
        "min_meaningful_diff_pct": 1.0,
        "precision_mode": "As a fraction of my negligible zone",
        "precision_pct": 90,
        "narrative": (
            "You're polling whether a candidate crosses the 50% threshold. "
            "A 1 percentage-point shift in true support is meaningful in a tight race. "
            "Polling data is expensive (each response costs real fieldwork), "
            "but getting the call wrong is worse — you need high precision."
        ),
    },
}

# Radio option strings — defined as module-level constants so the comparison
# in Step 3 stays in sync with the widget options list.
_FRACTION_MODE = f"As a fraction of {ROPE_WIDTH_STR} (width of my null equivalence zone)"
_ABSOLUTE_MODE = "As an absolute width"


def _on_apply_click() -> None:
    """on_click callback for the Apply button.

    on_click callbacks are committed to global session state before Streamlit
    triggers the next rerun, so this survives both fragment and app reruns.
    We read the dialog widget values from session state (they share the same
    session state object) and store the result under a non-widget key that
    the sidebar will consume before rendering its ROPE/precision widgets.
    """
    min_diff_pct = st.session_state.get("_advisor_min_diff_pct")
    if min_diff_pct is None:
        return
    rope_width_val = 2 * min_diff_pct / 100.0
    precision_mode = st.session_state.get("_advisor_precision_mode", _FRACTION_MODE)
    if precision_mode == _FRACTION_MODE:
        precision_pct = st.session_state.get("_advisor_precision_pct", 80)
        precision_goal_val = rope_width_val * precision_pct / 100.0
    else:
        precision_abs_pct = st.session_state.get("_advisor_precision_abs_pct")
        if precision_abs_pct is None:
            return
        precision_goal_val = precision_abs_pct / 100.0
    st.session_state["_rope_advisor_result"] = {
        "binary_rope_mode": "Full width (symmetric)",
        "binary_rope_width": round(rope_width_val, 6),
        "binary_precision_goal": round(precision_goal_val, 6),
    }


@st.dialog("🧭 Help me choose ROPE & Precision Goal", width="large")
def rope_advisor_dialog_binary_single(theta_null: float = 0.5) -> None:
    """Interactive 3-step guide for binary single-group ROPE & precision goal.

    On Apply, _on_apply_click() commits the result to session state, then this
    dialog detects the committed key and calls st.rerun(scope="app") to close
    itself and let the sidebar flush the values before its widgets render.

    Parameters
    ----------
    theta_null : float
        The current null hypothesis value — used to compute ROPE bounds
        for the live preview.
    """
    # If on_click already committed a result, close the dialog immediately so
    # the full-app rerun lets the sidebar read it before widgets are rendered.
    if "_rope_advisor_result" in st.session_state:
        st.rerun(scope="app")

    # ── Optional domain preset ────────────────────────────────────────────────
    preset_name = st.selectbox(
        "Start from a domain preset (optional)",
        options=list(DOMAIN_PRESETS.keys()),
        index=0,
        help=(
            "Pre-fills the questions below with typical values for that domain. "
            "You can still override anything."
        ),
        key="_advisor_preset",
    )
    preset = DOMAIN_PRESETS[preset_name]

    if preset is not None and "narrative" in preset:
        st.info(preset["narrative"])

    prev_preset = st.session_state.get("_advisor_prev_preset")
    if preset_name != prev_preset:
        st.session_state["_advisor_prev_preset"] = preset_name
        if preset is not None:
            st.session_state["_advisor_min_diff_pct"] = float(preset["min_meaningful_diff_pct"])
            if preset.get("precision_mode") == "As an absolute width":
                st.session_state["_advisor_precision_mode"] = _ABSOLUTE_MODE
            else:
                st.session_state["_advisor_precision_mode"] = _FRACTION_MODE
            if "precision_pct" in preset:
                st.session_state["_advisor_precision_pct"] = int(preset["precision_pct"])

    st.divider()

    # ── Step 1 — Minimum meaningful difference ────────────────────────────────
    st.markdown(f"#### Step 1 — Smallest effect that matters ({BINARY_SINGLE_MIN_EFFECT_STR})")
    st.caption("What's the smallest change in proportion your team would actually act on?")
    with st.expander("ℹ️ Learn more"):
        st.markdown(
            f"If your baseline is {BINARY_SINGLE_NULL_STR} = 0.50 and a shift to "
            f"{BINARY_SINGLE_OBSERVE_STR} = 0.52 would change a decision, enter **2** "
            f"(percentage points), meaning {BINARY_SINGLE_MIN_EFFECT_STR} = 0.02.  \n"
            f"The **ROPE** (Region of Practical Equivalence) spans "
            f"±{BINARY_SINGLE_MIN_EFFECT_STR} around {BINARY_SINGLE_NULL_STR}, "
            f"giving {ROPE_WIDTH_STR} = 2{BINARY_SINGLE_MIN_EFFECT_STR}."
        )

    default_diff = float(preset["min_meaningful_diff_pct"]) if preset else None
    min_diff_pct = st.number_input(
        f"Minimum meaningful {BINARY_SINGLE_MIN_EFFECT_STR} around each side of {BINARY_SINGLE_NULL_STR} (percentage points)",
        min_value=0.01,
        max_value=50.0,
        value=default_diff,
        step=0.5,
        format="%.2f",
        help=f"The ROPE spans ±{BINARY_SINGLE_MIN_EFFECT_STR} around {BINARY_SINGLE_NULL_STR}. {ROPE_WIDTH_STR} = 2{BINARY_SINGLE_MIN_EFFECT_STR}.",
        key="_advisor_min_diff_pct",
    )

    # ROPE width = 2 × one-sided shift (symmetric around the null).
    # The minimum effect size the user cares about maps to the half-width;
    # the full ROPE width is twice that.
    rope_width = (2 * min_diff_pct / 100.0) if min_diff_pct is not None else None

    if rope_width is not None:
        rope_min_preview = theta_null - rope_width / 2
        rope_max_preview = theta_null + rope_width / 2
        st.caption(
            f"→ ROPE = [{rope_min_preview:.4f}, {rope_max_preview:.4f}]"
            f"  ({ROPE_WIDTH_STR} = {rope_width:.4f})"
        )

    st.divider()

    # ── Step 2 — Precision goal framing ──────────────────────────────────────
    # TODO: consider defaulting to fraction mode and tucking absolute mode
    #   behind an "Advanced" toggle to reduce cognitive load for new users.
    st.markdown("#### Step 2 — How do you want to express outcome precision?")
    st.caption("How precise do you need your answer to be? More precision means collecting more data.")
    with st.expander("ℹ️ Learn more"):
        st.markdown(
            f"*Precision* is the width of your uncertainty about the true value — "
            f"narrower means more confidence, but requires more data.  \n"
            f"The **Precision Goal** ({GOAL_STR}) is the target width at stopping. "
            f"It must satisfy {GOAL_STR} ≤ {ROPE_WIDTH_STR}."
        )

    # Build captions with live numbers where possible
    _eg_rope = rope_width if rope_width is not None else 0.04
    _eg_pct = 80
    _eg_abs = round(_eg_rope * _eg_pct / 100, 4)

    fraction_caption = (
        f"*e.g. If {ROPE_WIDTH_STR} = {_eg_rope:.4f} and you choose {_eg_pct}%, "
        f"you'll stop when {HDI_WIDTH_STR} ≤ {_eg_abs:.4f}"
    )
    absolute_caption = (
        f"*e.g. \"I want {HDI_WIDTH_STR} to be no wider than 0.05 in absolute terms\" — "
        f"useful when you have a hard reporting requirement like ±2.5 pp. This requires {GOAL_STR} ≤ {ROPE_WIDTH_STR}.*"
    )

    default_mode_idx = 0
    if preset and preset.get("precision_mode") == "As an absolute width":
        default_mode_idx = 1

    precision_mode = st.radio(
        f"Express {GOAL_STR}:",
        options=[_FRACTION_MODE, _ABSOLUTE_MODE],
        index=default_mode_idx,
        captions=[fraction_caption, absolute_caption],
        key="_advisor_precision_mode",
    )

    st.divider()

    # ── Step 3 — Precision level ──────────────────────────────────────────────
    # TODO: add a caption with orientation, e.g. "70–80% is typical;
    #   above 90% requires substantially more data."
    st.markdown("#### Step 3 — How precise?")

    precision_goal = None

    if precision_mode == _FRACTION_MODE:
        default_pct = int(preset["precision_pct"]) if preset and "precision_pct" in preset else 80
        precision_pct = st.slider(
            f"{GOAL_STR} as % of {ROPE_WIDTH_STR}",
            min_value=50,
            max_value=100,
            value=default_pct,
            step=1,
            format="%d%%",
            key="_advisor_precision_pct",
        )
        if rope_width is not None:
            precision_goal = rope_width * precision_pct / 100.0
            st.caption(
                f"→ {ROPE_WIDTH_STR} × {precision_pct}% = {GOAL_STR} = **{precision_goal:.4f}**"
            )
        else:
            st.caption("→ Complete Step 1 first to see the computed value.")
    else:
        precision_abs_pct = st.number_input(
            f"Target {GOAL_STR} in percentage points. Requires {GOAL_STR} ≤ {ROPE_WIDTH_STR}.",
            min_value=0.01,
            max_value=50.0,
            value=None,
            step=0.5,
            format="%.2f",
            help=f"{HDI_WIDTH_STR} ≤ {GOAL_STR} for the experiment to stop.",
            key="_advisor_precision_abs_pct",
        )
        if precision_abs_pct is not None:
            precision_goal = precision_abs_pct / 100.0
            st.caption(f"→ {GOAL_STR} = **{precision_goal:.4f}**")

    st.divider()

    # ── Preview ───────────────────────────────────────────────────────────────
    all_ready = rope_width is not None and precision_goal is not None
    goal_too_wide = all_ready and precision_goal > rope_width

    if all_ready:
        if goal_too_wide:
            st.warning(
                f"⚠️ {GOAL_STR} ({precision_goal:.4f}) must **not exceed** "
                f"{ROPE_WIDTH_STR} ({rope_width:.4f}) for the stopping rule to be meaningful. "
                "Increase the fraction or reduce the absolute width."
            )
        else:
            st.success(
                f"**ROPE:** {BINARY_SINGLE_NULL_STR} ± {BINARY_SINGLE_MIN_EFFECT_STR} ({min_diff_pct:.2f} pp) "
                f"→ [{theta_null - rope_width/2:.4f}, {theta_null + rope_width/2:.4f}]"
                f"  ({ROPE_WIDTH_STR} = {rope_width:.4f})  \n"
                f"**Precision goal:** stop when {HDI_WIDTH_STR} < "
                f"{GOAL_STR} = **{precision_goal:.4f}** ({precision_goal * 100:.2f} pp)"
            )
    else:
        st.info("Complete Steps 1–3 above to see a preview.")

    # ── Estimated sample size ────────────────────────────────────────────────
    if all_ready and not goal_too_wide:
        st.divider()
        st.markdown("#### Estimated Sample Size")
        st.caption(
            "How many observations would you need to reach this precision? "
            "Adjust θ and ω below to explore."
        )

        col_theta, col_omega = st.columns(2)
        with col_theta:
            explore_theta = st.slider(
                "θ (expected rate)",
                min_value=0.01,
                max_value=0.99,
                value=float(theta_null),
                step=0.01,
                format="%.2f",
                key="_advisor_explore_theta",
            )
        with col_omega:
            w_goal_min = 0.5 * float(rope_width)
            w_goal_max = float(rope_width)
            explore_omega = st.slider(
                f"ω_goal (precision)",
                min_value=w_goal_min,
                max_value=w_goal_max,
                value=float(precision_goal),
                step=0.001,
                format="%.4f",
                key="_advisor_explore_omega",
            )

        n_goal_est = binomial_rate_ci_width_to_sample_size(
            explore_theta, explore_omega, z_star=1.96,
        )
        n_goal_display = max(1, int(n_goal_est))

        st.metric(label="N_goal (estimated minimum sample size)", value=f"{n_goal_display:,}")

        # TODO: update z_star to derive from a user-chosen confidence level
        with st.expander("⚙️ Advanced"):
            adv_z = st.number_input(
                "z* (critical value)",
                min_value=1.0,
                max_value=4.0,
                value=1.96,
                step=0.01,
                format="%.2f",
                key="_advisor_z_star",
                help="1.96 ≈ 95% HDI, 2.576 ≈ 99% HDI",
            )
            adv_col1, adv_col2 = st.columns(2)
            with adv_col1:
                adv_w_min = st.number_input(
                    "Background ω min",
                    min_value=0.5 * w_goal_min,
                    max_value=w_goal_max,
                    value=w_goal_min,
                    step=0.01,
                    format="%.2f",
                    key="_advisor_w_min",
                )
            with adv_col2:
                adv_w_max = st.number_input(
                    "Background ω max",
                    min_value=w_goal_min,
                    max_value=2 *w_goal_max,
                    value=w_goal_max,
                    step=0.01,
                    format="%.2f",
                    key="_advisor_w_max",
                )

            n_goal_est_adv = binomial_rate_ci_width_to_sample_size(
                explore_theta, explore_omega, z_star=adv_z,
            )
            n_goal_display = max(1, int(n_goal_est_adv))
            st.metric(label="N_goal (with custom z*)", value=f"{n_goal_display:,}")

        fig = plot_n_goal_by_parameter(
            omega_goal=explore_omega,
            theta_highlight=explore_theta,
            z_star=st.session_state.get("_advisor_z_star", 1.96),
            w_goal_min=st.session_state.get("_advisor_w_min", w_goal_min),
            w_goal_max=st.session_state.get("_advisor_w_max", w_goal_max),
        )
        st.pyplot(fig)

    # ── Apply ─────────────────────────────────────────────────────────────────
    # TODO: add a brief "what happens next" note, e.g.
    #   "These values will fill in the sidebar — then enter your observed data to get a verdict."
    st.button(
        "✅ Apply",
        type="primary",
        disabled=not all_ready or goal_too_wide,
        on_click=_on_apply_click,
    )
