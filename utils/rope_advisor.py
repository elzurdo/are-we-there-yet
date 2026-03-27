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
    st.markdown("#### Step 1 — Smallest effect that matters")
    st.markdown(
        "What's the smallest change in proportion your team would actually act on?  \n"
        "*e.g. If your baseline is 50% and a shift to 52% would change a decision, enter **2** (the minimum meaningful shift around each side of the null).*  \n"
        "The ROPE — **Region of Practical Equivalence** — spans ±this value around your null, "
        "giving a **total ROPE width of twice this amount**."
    )

    default_diff = float(preset["min_meaningful_diff_pct"]) if preset else None
    min_diff_pct = st.number_input(
        "Minimum meaningful shift around each side of the null (percentage points)",
        min_value=0.01,
        max_value=50.0,
        value=default_diff,
        step=0.5,
        format="%.2f",
        help="The ROPE spans ±this value around your null. Total ROPE width = 2 × this value.",
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
            f"  (width = {rope_width:.4f})"
        )

    st.divider()

    # ── Step 2 — Precision goal framing ──────────────────────────────────────
    st.markdown("#### Step 2 — How do you want to express outcome precision?")
    st.markdown("Think of *precision* as the width of the bell curve (the posterior) that you'd be happy to stop the experiment under.  \n"
                 "A narrower curve means you're more confident about where the true effect lies but at a cost of more data collection.  \n"
                "This is called the **Precision Goal**: the posterior width for stopping.  \n"
                "It is independent of the ROPE location but must be narrower than the ROPE width."
                )

    # Build captions with live numbers where possible
    _eg_rope = rope_width if rope_width is not None else 0.04
    _eg_pct = 80
    _eg_abs = round(_eg_rope * _eg_pct / 100, 4)

    fraction_caption = (
        f"*e.g. If your ROPE width is {_eg_rope:.4f} and you choose {_eg_pct}%, "
        f"you'll stop when the posterior width is narrower than {_eg_abs:.4f} — "
        f"you know the true effect to within {_eg_pct}% of what you'd consider practically equivalent to the null.*"
    )
    absolute_caption = (
        "*e.g. \"I want the posterior width to be no wider than 0.05 in absolute terms\" — "
        "useful when you have a hard reporting requirement like ±2.5 pp. This must be smaller than the ROPE width.*"
    )

    default_mode_idx = 0
    if preset and preset.get("precision_mode") == "As an absolute width":
        default_mode_idx = 1

    precision_mode = st.radio(
        "Express the precision goal:",
        options=[
            "As a fraction of the ROPE width (with of my null equivalence zone)",  # rephrase to avoid repeating "ROPE" in the caption
            "As an absolute width",
        ],
        index=default_mode_idx,
        captions=[fraction_caption, absolute_caption],
        key="_advisor_precision_mode",
    )

    st.divider()

    # ── Step 3 — Precision level ──────────────────────────────────────────────
    st.markdown("#### Step 3 — How precise?")

    precision_goal = None

    if precision_mode == "As a fraction of the ROPE width (with of my null equivalence zone)":
        default_pct = int(preset["precision_pct"]) if preset and "precision_pct" in preset else 80
        precision_pct = st.slider(
            "Precision as % of ROPE width",
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
                f"→ {rope_width:.4f} × {precision_pct}% = **{precision_goal:.4f}**"
            )
        else:
            st.caption("→ Complete Step 1 first to see the computed value.")
    else:
        precision_abs_pct = st.number_input(
            "Target HDI width (percentage points)",
            min_value=0.01,
            max_value=50.0,
            value=None,
            step=0.5,
            format="%.2f",
            help="The posterior width must be narrower than this for the experiment to stop.",
            key="_advisor_precision_abs_pct",
        )
        if precision_abs_pct is not None:
            precision_goal = precision_abs_pct / 100.0
            st.caption(f"→ Precision goal = **{precision_goal:.4f}**")

    st.divider()

    # ── Preview ───────────────────────────────────────────────────────────────
    all_ready = rope_width is not None and precision_goal is not None
    goal_too_wide = all_ready and precision_goal >= rope_width

    if all_ready:
        if goal_too_wide:
            st.warning(
                f"⚠️ Precision goal ({precision_goal:.4f}) must be **narrower** than the "
                f"ROPE width ({rope_width:.4f}) for the stopping rule to be meaningful. "
                "Increase the fraction or reduce the absolute width."
            )
        else:
            st.success(
                f"**ROPE:** ±{min_diff_pct:.2f} pp around your null "
                f"→ [{theta_null - rope_width/2:.4f}, {theta_null + rope_width/2:.4f}]"
                f"  (width = {rope_width:.4f})  \n"
                f"**Precision goal:** stop when 95% HDI is narrower than "
                f"**{precision_goal:.4f}** ({precision_goal * 100:.2f} pp)"
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
