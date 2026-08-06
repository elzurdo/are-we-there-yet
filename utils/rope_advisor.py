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
    BINARY_SINGLE_NULL_STR,
    BINARY_SINGLE_OBSERVE_STR,
)

# ── Domain presets ────────────────────────────────────────────────────────────
# Each entry maps to a dict with:
#   min_meaningful_diff_pct  – smallest effect that matters, in pp
#   precision_mode           – "As a fraction of my negligible zone" | "As an absolute width"
#   precision_pct            – used when mode is fraction (0–100)
DOMAIN_PRESETS = {
    "Custom (I'll set my own)": None,
    "E-commerce / conversion rate": {
        "min_meaningful_diff_pct": 2.0,
        "precision_mode": "As a fraction of my negligible zone",
        "precision_pct": 80,
    },
    "Medical / clinical rate": {
        "min_meaningful_diff_pct": 5.0,
        "precision_mode": "As a fraction of my negligible zone",
        "precision_pct": 90,
    },
    "Internal tooling / ops": {
        "min_meaningful_diff_pct": 3.0,
        "precision_mode": "As a fraction of my negligible zone",
        "precision_pct": 75,
    },
}

# Radio option strings — defined as module-level constants so the comparison
# in Step 3 stays in sync with the widget options list.
_FRACTION_MODE = f"As a fraction of {ROPE_WIDTH_STR} (width of my null equivalence zone)"
_ABSOLUTE_MODE = "As an absolute width"


@st.dialog("🧭 Help me choose ROPE & Precision Goal", width="large")
def rope_advisor_dialog_binary_single(theta_null: float = 0.5) -> None:
    """Interactive 3-step guide for binary single-group ROPE & precision goal.

    On Apply, stages computed values into st.session_state['_pending_example']
    and calls st.rerun() so the flush block in app.py injects them safely.

    Parameters
    ----------
    theta_null : float
        The current null hypothesis value — used to compute ROPE bounds
        for the live preview.
    """

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

    st.divider()

    # ── Step 1 — Minimum meaningful difference ────────────────────────────────
    st.markdown(f"#### Step 1 — Smallest effect that matters ({BINARY_SINGLE_MIN_EFFECT_STR})")
    st.markdown(
        f"What's the smallest change in proportion your team would actually act on?  \n"
        f"*e.g. If your baseline is {BINARY_SINGLE_NULL_STR} = 0.50 and a shift to {BINARY_SINGLE_OBSERVE_STR} =0.52 would change a decision, enter **2** (percentage points) "
        f"({BINARY_SINGLE_MIN_EFFECT_STR} = 0.02 — the minimum meaningful shift around each side of the null).*  \n"
        f"The ROPE — **Region of Practical Equivalence** — spans ±{BINARY_SINGLE_MIN_EFFECT_STR} around "
        f"{BINARY_SINGLE_NULL_STR}, giving {ROPE_WIDTH_STR} = 2{BINARY_SINGLE_MIN_EFFECT_STR}."
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
    st.markdown("#### Step 2 — How do you want to express outcome precision?")
    st.markdown(
        f"Think of *precision* as the width of the bell curve (the posterior) that you'd be happy to stop the experiment under.  \n"
        f"A narrower curve means you're more confident about where the true effect lies but at a cost of more data collection.  \n"
        f"This is called the **Precision Goal** ({GOAL_STR}): the target for {HDI_WIDTH_STR} at stopping.  \n"
        f"It is independent of the ROPE location but dependent on width {GOAL_STR}≤{ROPE_WIDTH_STR}."
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
    st.markdown("#### Step 3 — How precise?")

    precision_goal = None

    if precision_mode == _FRACTION_MODE:
        default_pct = int(preset["precision_pct"]) if preset and "precision_pct" in preset else 80
        precision_pct = st.slider(
            f"{GOAL_STR} as % of {ROPE_WIDTH_STR}",
            min_value=50,
            max_value=99,
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

    # ── Apply ─────────────────────────────────────────────────────────────────
    if st.button(
        "✅ Apply",
        type="primary",
        disabled=not all_ready or goal_too_wide,
    ):
        st.session_state["_pending_example"] = {
            "binary_rope_mode": "Full width (symmetric)",
            "binary_rope_width": round(rope_width, 6),
            "binary_precision_goal": round(precision_goal, 6),
        }
        st.session_state["_force_commit"] = True
        st.rerun()
