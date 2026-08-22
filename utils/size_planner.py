"""
Size planner — shared UI components for binary prospective sample-size planning.

Used by:
  - utils/rope_advisor.py  (inside @st.dialog wrappers)
  - tabs/prospective_binary.py  (as a first-class prospective page)

All render_* functions accept an optional `container` argument (default st)
so the same widgets can be placed in the main area or the sidebar.
"""
import math
import streamlit as st
from utils.constants import (
    BINARY_SINGLE_MIN_EFFECT_STR,
    BINARY_SINGLE_NULL_STR,
    BINARY_BG_NULL_STR,
    CONTINUOUS_NULL_STR,
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
    estimate_n_goal,
    CI_FRACTION,
)
from utils.viz import (
    plot_n_goal_by_parameter,
    plot_n_goal_by_parameter_between_groups,
    plot_n_goal_by_sigma,
)

# ── Single-group domain presets ───────────────────────────────────────────────
# TODO: narratives currently hard-code example rates (e.g. "around 3%").
#   Make them dynamic so they update if the user changes the preset values.
DOMAIN_PRESETS = {
    "🔧 Custom (I'll set my own)": None,
    "🛒 E-commerce / conversion rate": {
        "min_meaningful_effect": 0.005,
        "precision_pct": 70,
        "narrative": (
            "Your checkout conversion is around 3%. "
            "A shift of 0.005 (e.g. 0.030 → 0.035) is worth acting on. "
            "You want answers fast — being wrong occasionally just means running another test."
        ),
    },
    "🏥 Medical / clinical rate": {
        "min_meaningful_effect": 0.02,
        "precision_pct": 90,
        "narrative": (
            "You're tracking a treatment response rate around 0.70. "
            "A shift of 0.02 would change clinical practice. "
            "You need tight precision — wrong calls here affect patients."
        ),
    },
    "💻 Internal tooling / ops": {
        "min_meaningful_effect": 0.03,
        "precision_pct": 80,
        "narrative": (
            "Your pipeline success rate is around 0.95. "
            "Swings under 0.03 are normal noise. "
            "Data is cheap (every job run is a data point), so you'd rather collect more and be sure."
        ),
    },
    "🗳️ Election polling": {
        "min_meaningful_effect": 0.01,
        "precision_pct": 90,
        "narrative": (
            "You're polling whether a candidate crosses the 0.50 threshold. "
            "A shift of 0.01 in true support is meaningful in a tight race. "
            "Polling data is expensive (each response costs real fieldwork), "
            "but getting the call wrong is worse — you need high precision."
        ),
    },
}

# ── Continuous single-group domain presets ────────────────────────────────────
CONTINUOUS_SINGLE_DOMAIN_PRESETS = {
    "🔧 Custom (I'll set my own)": None,
    "🧪 Clinical biomarker": {
        "min_meaningful_effect": 5.0,
        "precision_pct": 80,
        "sigma_min": 10.0,
        "sigma_max": 30.0,
        "narrative": (
            "You're tracking a lab value such as blood pressure or cholesterol. "
            "A shift of 5 units would change clinical decisions. "
            "High precision is essential — wrong calls affect patient care."
        ),
    },
    "📚 Educational assessment": {
        "min_meaningful_effect": 5.0,
        "precision_pct": 80,
        "sigma_min": 10.0,
        "sigma_max": 25.0,
        "narrative": (
            "You're measuring test scores on a 0–100 scale. "
            "A shift of 5 points is the smallest educationally meaningful change. "
            "Precision matters but data is relatively cheap to collect."
        ),
    },
    "⚙️ Engineering / QC": {
        "min_meaningful_effect": 0.5,
        "precision_pct": 90,
        "sigma_min": 1.0,
        "sigma_max": 5.0,
        "narrative": (
            "You're measuring a manufacturing parameter such as diameter or weight. "
            "Deviations above 0.5 units exceed tolerance. "
            "Tight precision is required — process decisions are expensive to reverse."
        ),
    },
    "📊 Survey / Likert scale": {
        "min_meaningful_effect": 0.5,
        "precision_pct": 75,
        "sigma_min": 0.5,
        "sigma_max": 2.5,
        "narrative": (
            "You're averaging responses on a 5- or 7-point Likert scale. "
            "A shift of 0.5 scale points is the smallest perceptible change. "
            "Moderate precision is acceptable and data is relatively cheap."
        ),
    },
}

# ── Between-groups domain presets ─────────────────────────────────────────────
BETWEEN_GROUPS_DOMAIN_PRESETS = {
    "🔧 Custom (I'll set my own)": None,
    "🛒 E-commerce / A/B test": {
        "min_meaningful_effect": 0.005,
        "precision_pct": 70,
        "narrative": (
            "Your control group converts at ~0.030 and your treatment at ~0.035. "
            "A lift of 0.005 is the smallest difference worth deploying. "
            "Fast iteration matters — being wrong occasionally means running another test."
        ),
    },
    "🏥 Clinical trial": {
        "min_meaningful_effect": 0.02,
        "precision_pct": 90,
        "narrative": (
            "Your control arm has a ~0.70 response rate; treatment might shift it by 0.02 or more. "
            "A difference of 0.02 between arms would change clinical practice. "
            "High precision is essential — wrong calls affect patients."
        ),
    },
    "💻 Canary deployment / ops": {
        "min_meaningful_effect": 0.03,
        "precision_pct": 80,
        "narrative": (
            "Your baseline pipeline succeeds ~0.95 of the time. "
            "Differences under 0.03 between control and canary are normal noise. "
            "Each job run is a data point, so you'd rather collect more and be sure."
        ),
    },
    "🗳️ Survey / polling comparison": {
        "min_meaningful_effect": 0.01,
        "precision_pct": 90,
        "narrative": (
            "You're comparing support rates between two demographic groups. "
            "A difference of 0.01 in true support is meaningful. "
            "Fieldwork is expensive, but getting the comparison wrong matters more."
        ),
    },
}


# ── Shared helpers ─────────────────────────────────────────────────────────────

_PRESET_NOT_PROVIDED = object()  # sentinel: distinguish "no preset" from "Custom (None)"


def render_domain_preset(presets: dict, advisor_prefix: str, container=None) -> tuple:
    """Render only the domain preset selectbox into `container` (default st).

    Handles state sync so that changing the preset pre-fills Step 1 & 2 values.
    Returns (preset_name, preset) where preset is None when Custom is selected.
    """
    if container is None:
        container = st

    preset_name = container.selectbox(
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

    prev_preset = st.session_state.get(f"{advisor_prefix}_prev_preset")
    if preset_name != prev_preset:
        st.session_state[f"{advisor_prefix}_prev_preset"] = preset_name
        if preset is not None:
            st.session_state[f"{advisor_prefix}_min_effect"] = float(preset["min_meaningful_effect"])
            if "precision_pct" in preset:
                st.session_state[f"{advisor_prefix}_precision_pct"] = int(preset["precision_pct"])
            if "sigma_min" in preset:
                st.session_state[f"{advisor_prefix}_sigma_min"] = float(preset["sigma_min"])
            if "sigma_max" in preset:
                st.session_state[f"{advisor_prefix}_sigma_max"] = float(preset["sigma_max"])

    return preset_name, preset


def sync_p_b_to_p_a(advisor_prefix: str, delta_null: float) -> None:
    """on_change callback: sets p_B = p_A - delta_null (clamped to [0.01, 0.99])."""
    p_a = st.session_state.get(f"{advisor_prefix}_explore_p_a", 0.5)
    p_b = max(0.01, min(0.99, p_a - delta_null))
    st.session_state[f"{advisor_prefix}_explore_p_b"] = p_b


def preview_box(
    null_val, rope_width, min_effect, precision_goal,
    null_label=None, effect_label=None, container=None,
):
    """Render ROPE bounds and precision goal as a success box."""
    if container is None:
        container = st
    if null_label is None:
        null_label = BINARY_SINGLE_NULL_STR
    if effect_label is None:
        effect_label = BINARY_SINGLE_MIN_EFFECT_STR
    container.success(
        f"**ROPE:** {null_label} ± {effect_label} ({min_effect:.4f}) "
        f"→ [{null_val - rope_width/2:.4f}, {null_val + rope_width/2:.4f}]"
        f"  ({ROPE_WIDTH_STR} = {rope_width:.4f})  \n"
        f"**Precision goal:** stop when {HDI_WIDTH_STR} < "
        f"{GOAL_STR} = **{precision_goal:.4f}**"
    )


def render_steps_1_and_2(
    advisor_prefix: str,
    presets: dict,
    null_val: float,
    null_label=None,
    effect_label=None,
    step1_caption: str = "What's the smallest change in proportion your team would actually act on?\n This will determine the ROPE (Region of Practical Equivalence) around the null value.",
    step1_learn_more: str = None,
    step1_help: str = None,
    container=None,
    preset=_PRESET_NOT_PROVIDED,
    min_effect_max: float = 0.50,
    min_effect_step: float = 0.001,
    min_effect_format: str = "%.4f",
) -> tuple:
    """Render Steps 1 and 2 into `container` (default st; pass st.sidebar for the sidebar).

    When `preset` is supplied (from render_domain_preset), the internal preset
    selectbox is skipped — caller owns the preset widget. Pass the sentinel
    _PRESET_NOT_PROVIDED (the default) to get the old self-contained behaviour,
    which is what rope_advisor.py uses.

    Returns (rope_width, precision_goal, all_ready, goal_too_wide).
    rope_width and precision_goal are None when inputs are incomplete.
    """
    if container is None:
        container = st
    if null_label is None:
        null_label = BINARY_SINGLE_NULL_STR
    if effect_label is None:
        effect_label = BINARY_SINGLE_MIN_EFFECT_STR

    # ── Optional domain preset ────────────────────────────────────────────────
    if preset is _PRESET_NOT_PROVIDED:
        # Self-contained mode: render the selectbox here (rope_advisor.py path)
        preset_name = container.selectbox(
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

        prev_preset = st.session_state.get(f"{advisor_prefix}_prev_preset")
        if preset_name != prev_preset:
            st.session_state[f"{advisor_prefix}_prev_preset"] = preset_name
            if preset is not None:
                st.session_state[f"{advisor_prefix}_min_effect"] = float(preset["min_meaningful_effect"])
                if "precision_pct" in preset:
                    st.session_state[f"{advisor_prefix}_precision_pct"] = int(preset["precision_pct"])

    if preset is not None and "narrative" in preset:
        container.info(preset["narrative"])

    container.divider()

    # ── Step 1 ────────────────────────────────────────────────────────────────
    container.markdown(f"#### Step 1 — Smallest effect ({effect_label})")
    container.caption(step1_caption)

    if step1_learn_more:
        with container.expander("ℹ️ Learn more"):
            st.markdown(step1_learn_more)

    _help = step1_help or f"The ROPE spans ±{effect_label} around {null_label}. {ROPE_WIDTH_STR} = 2{effect_label}."
    _diff_kwargs = {}
    if f"{advisor_prefix}_min_effect" not in st.session_state:
        _diff_kwargs["value"] = float(preset["min_meaningful_effect"]) if preset else None
    min_effect = container.number_input(
        f"Minimum meaningful {effect_label} around each side of {null_label}",
        min_value=0.0001,
        max_value=min_effect_max,
        step=min_effect_step,
        format=min_effect_format,
        help=_help,
        key=f"{advisor_prefix}_min_effect",
        **_diff_kwargs,
    )

    rope_width = (2 * min_effect) if min_effect is not None else None

    if rope_width is not None:
        container.caption(
            f"→ ROPE = [{null_val - rope_width/2:.4f}, {null_val + rope_width/2:.4f}]"
            f"  ({ROPE_WIDTH_STR} = {rope_width:.4f})"
        )

    container.divider()

    # ── Step 2 ────────────────────────────────────────────────────────────────
    container.markdown("#### Step 2 — How precise?")
    container.caption("More precision means collecting more data.")
    with container.expander("ℹ️ Learn more"):
        st.markdown(
            f"*Precision* is the width of your uncertainty about the true value — "
            f"narrower means more confidence, but requires more data.  \n"
            f"The **Precision Goal** ({GOAL_STR}) is the target width at stopping. "
            f"It must satisfy {GOAL_STR} ≤ {ROPE_WIDTH_STR}."
        )

    _pct_kwargs = {}
    if f"{advisor_prefix}_precision_pct" not in st.session_state:
        _pct_kwargs["value"] = int(preset["precision_pct"]) if preset and "precision_pct" in preset else 80
    precision_pct = container.slider(
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
        container.caption(
            f"→ {ROPE_WIDTH_STR} × {precision_pct}% = {GOAL_STR} = **{precision_goal:.4f}**"
        )

        explore_omega_ss = st.session_state.get(f"{advisor_prefix}_explore_omega")
        if explore_omega_ss is not None and abs(explore_omega_ss - precision_goal) > 1e-6:
            container.caption(
                f"→ overridden to {GOAL_STR} = **{explore_omega_ss:.4f}** in Step 3 below"
            )
    else:
        container.caption("→ Complete Step 1 first to see the computed value.")

    # ── Preview ───────────────────────────────────────────────────────────────
    all_ready = rope_width is not None and precision_goal is not None
    goal_too_wide = all_ready and precision_goal > rope_width

    if all_ready:
        if goal_too_wide:
            container.warning(
                f"⚠️ {GOAL_STR} ({precision_goal:.4f}) must **not exceed** "
                f"{ROPE_WIDTH_STR} ({rope_width:.4f}) for the stopping rule to be meaningful. "
                "Increase the fraction."
            )
        else:
            preview_box(
                null_val, rope_width, min_effect, precision_goal,
                null_label=null_label, effect_label=effect_label, container=container,
            )
    else:
        container.info("Complete Steps 1–2 above to see a preview.")

    return rope_width, precision_goal, all_ready, goal_too_wide


# ── Step 3 renderers (always render in the main area) ─────────────────────────

def render_step3_single(
    advisor_prefix: str,
    rope_width: float,
    precision_goal: float,
    theta_null: float,
) -> tuple:
    """Render Step 3 (N_goal estimation) for single-group binary in the main area.

    Returns (explore_theta, explore_omega).
    """
    st.markdown("#### Step 3 — Estimated Sample Size")
    st.caption(
        "How many observations would you need to reach this precision? "
        "Adjust θ and ω_goal below to explore."
    )

    w_goal_min = 0.5 * float(rope_width)
    w_goal_max = float(rope_width)

    col_theta, col_omega = st.columns(2)
    with col_theta:
        explore_theta = st.slider(
            "θ (expected rate)",
            min_value=0.01,
            max_value=0.99,
            value=float(theta_null),
            step=0.01,
            format="%.2f",
            key=f"{advisor_prefix}_explore_theta",
        )
    with col_omega:
        explore_omega = st.slider(
            "ω_goal (precision)",
            min_value=w_goal_min,
            max_value=w_goal_max,
            value=float(precision_goal),
            step=0.001,
            format="%.4f",
            key=f"{advisor_prefix}_explore_omega",
        )

    z_star = st.session_state.get(f"{advisor_prefix}_z_star", 1.96)
    n_goal_est = binomial_rate_ci_width_to_sample_size(explore_theta, explore_omega, z_star=z_star)
    n_goal_display = max(1, int(n_goal_est))
    st.latex(
        r"N_{\rm goal} \approx \left\lceil"
        r"\frac{4\,z_*^2\;\hat\theta\,(1-\hat\theta)}{\omega_{\rm goal}^2}"
        r"\right\rceil"
    )
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
            key=f"{advisor_prefix}_z_star",
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
                format="%.4f",
                key=f"{advisor_prefix}_w_min",
            )
        with adv_col2:
            st.number_input(
                "Background ω max",
                min_value=w_goal_min,
                max_value=2 * w_goal_max,
                value=w_goal_max,
                step=0.01,
                format="%.4f",
                key=f"{advisor_prefix}_w_max",
            )
        n_goal_adv = max(1, int(binomial_rate_ci_width_to_sample_size(explore_theta, explore_omega, z_star=adv_z)))
        st.metric(label="N_goal (with custom z*)", value=f"{n_goal_adv:,}")

    fig = plot_n_goal_by_parameter(
        omega_goal=explore_omega,
        theta_highlight=explore_theta,
        z_star=st.session_state.get(f"{advisor_prefix}_z_star", 1.96),
        w_goal_min=st.session_state.get(f"{advisor_prefix}_w_min", w_goal_min),
        w_goal_max=st.session_state.get(f"{advisor_prefix}_w_max", w_goal_max),
    )
    st.pyplot(fig)

    return explore_theta, explore_omega


def render_step3_between(
    advisor_prefix: str,
    rope_width: float,
    precision_goal: float,
    delta_null: float,
    p_a_default: float,
    p_b_default: float,
    label_a: str,
    label_b: str,
) -> tuple:
    """Render Step 3 (N_goal estimation) for between-groups binary in the main area.

    Returns (explore_p_a, explore_p_b, explore_omega).
    """
    st.markdown("#### Step 3 — Estimated Sample Size")
    st.caption(
        f"How many observations per group would you need? "
        f"Adjust {theta_label(label_a)}, {theta_label(label_b)}, and {GOAL_STR} below to explore."
    )

    w_goal_min = 0.5 * float(rope_width)
    w_goal_max = float(rope_width)

    linked = st.checkbox(
        f"🔗 Link θ_{label_b} = θ_{label_a} − Δ₀ ({delta_null:+.2f})",
        value=True,
        key=f"{advisor_prefix}_link_p_b",
        help="When checked, moving θ_A automatically updates θ_B to maintain the null difference.",
    )

    col_pa, col_pb, col_omega = st.columns(3)
    with col_pa:
        explore_p_a = st.slider(
            f"θ_{label_a} (expected rate)",
            min_value=0.01,
            max_value=0.99,
            value=float(p_a_default),
            step=0.01,
            format="%.2f",
            key=f"{advisor_prefix}_explore_p_a",
            on_change=sync_p_b_to_p_a if linked else None,
            kwargs={"advisor_prefix": advisor_prefix, "delta_null": delta_null} if linked else None,
        )
    with col_pb:
        explore_p_b = st.slider(
            f"θ_{label_b} (expected rate)",
            min_value=0.01,
            max_value=0.99,
            value=float(p_b_default),
            step=0.01,
            format="%.2f",
            key=f"{advisor_prefix}_explore_p_b",
            disabled=linked,
        )
    with col_omega:
        explore_omega = st.slider(
            "ω_goal (precision)",
            min_value=w_goal_min,
            max_value=w_goal_max,
            value=float(precision_goal),
            step=0.001,
            format="%.4f",
            key=f"{advisor_prefix}_explore_omega",
        )

    with st.expander("⚙️ Advanced"):
        adv_r = st.slider(
            "Group ratio r = n_A / (n_A + n_B)",
            min_value=0.1,
            max_value=0.9,
            value=0.5,
            step=0.05,
            format="%.2f",
            key=f"{advisor_prefix}_ratio",
            help="0.5 = equal group sizes (default). Adjust if you expect unequal allocation.",
        )
        adv_z = st.number_input(
            "z* (critical value)",
            min_value=1.0,
            max_value=4.0,
            value=1.96,
            step=0.01,
            format="%.2f",
            key=f"{advisor_prefix}_z_star",
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
                format="%.4f",
                key=f"{advisor_prefix}_w_min",
            )
        with adv_col2:
            st.number_input(
                "Background ω max",
                min_value=w_goal_min,
                max_value=2 * w_goal_max,
                value=w_goal_max,
                step=0.01,
                format="%.4f",
                key=f"{advisor_prefix}_w_max",
            )

    r = st.session_state.get(f"{advisor_prefix}_ratio", 0.5)
    z_star = st.session_state.get(f"{advisor_prefix}_z_star", 1.96)

    n_total_est = binomial_difference_ci_width_to_sample_size(
        explore_p_a, explore_p_b, r, explore_omega, z_star=z_star,
    )
    n_a_goal = max(1, math.ceil(r * n_total_est))
    n_b_goal = max(1, math.ceil((1 - r) * n_total_est))

    st.latex(
        r"N_{\rm goal,\,total} \approx \left\lceil"
        r"\frac{4\,z_*^2 \left["
        r"\dfrac{\hat\theta_A(1-\hat\theta_A)}{r}"
        r"+\dfrac{\hat\theta_B(1-\hat\theta_B)}{1-r}"
        r"\right]}{\omega_{\rm goal}^2}"
        r"\right\rceil"
    )
    col_na, col_nb = st.columns(2)
    with col_na:
        st.metric(label=f"N_{label_a} goal", value=f"{n_a_goal:,}")
    with col_nb:
        st.metric(label=f"N_{label_b} goal", value=f"{n_b_goal:,}")

    fig = plot_n_goal_by_parameter_between_groups(
        omega_goal=explore_omega,
        p_a_highlight=explore_p_a,
        p_b_fixed=explore_p_b,
        r=r,
        z_star=z_star,
        w_goal_min=st.session_state.get(f"{advisor_prefix}_w_min", w_goal_min),
        w_goal_max=st.session_state.get(f"{advisor_prefix}_w_max", w_goal_max),
        label_a=label_a,
        label_b=label_b,
    )
    st.pyplot(fig)

    return explore_p_a, explore_p_b, explore_omega


def render_step3_single_continuous(
    advisor_prefix: str,
    rope_width: float,
    precision_goal: float,
    sigma_min_default: float = 1.0,
    sigma_max_default: float = 10.0,
    ci_fraction: float = CI_FRACTION,
) -> tuple:
    """Render Step 3 (N_goal estimation) for single-group continuous in the main area.

    Returns (explore_sigma, explore_omega).
    """
    st.markdown("#### Step 3 — Estimated Sample Size")
    st.caption(
        "How many observations would you need to reach this precision? "
        "Set the σ range below, then adjust σ and ω_goal to explore."
    )

    w_goal_min = 0.5 * float(rope_width)
    w_goal_max = float(rope_width)

    # ── σ range ───────────────────────────────────────────────────────────────
    col_smin, col_smax = st.columns(2)
    with col_smin:
        sigma_min = st.number_input(
            "σ range — min",
            min_value=0.001,
            value=float(st.session_state.get(f"{advisor_prefix}_sigma_min", sigma_min_default)),
            step=max(0.001, float(sigma_min_default) * 0.1),
            format="%.4g",
            key=f"{advisor_prefix}_sigma_min",
        )
    with col_smax:
        sigma_max = st.number_input(
            "σ range — max",
            min_value=float(sigma_min) + 0.001,
            value=float(st.session_state.get(f"{advisor_prefix}_sigma_max", sigma_max_default)),
            step=max(0.001, float(sigma_max_default) * 0.1),
            format="%.4g",
            key=f"{advisor_prefix}_sigma_max",
        )

    sigma_min = float(sigma_min)
    sigma_max = max(sigma_max, sigma_min + 0.001)
    sigma_mid = 0.5 * (sigma_min + sigma_max)

    # Clamp persisted slider value to current range to avoid Streamlit errors.
    _sigma_val = float(st.session_state.get(f"{advisor_prefix}_explore_sigma", sigma_mid))
    _sigma_val = max(sigma_min, min(sigma_max, _sigma_val))

    col_sigma, col_omega = st.columns(2)
    with col_sigma:
        explore_sigma = st.slider(
            "σ (expected std dev)",
            min_value=sigma_min,
            max_value=sigma_max,
            value=_sigma_val,
            step=(sigma_max - sigma_min) / 100.0,
            format="%.4g",
            key=f"{advisor_prefix}_explore_sigma",
        )
    with col_omega:
        explore_omega = st.slider(
            "ω_goal (precision)",
            min_value=w_goal_min,
            max_value=w_goal_max,
            value=float(precision_goal),
            step=max(0.0001, (w_goal_max - w_goal_min) / 100.0),
            format="%.4g",
            key=f"{advisor_prefix}_explore_omega",
        )

    z_star = st.session_state.get(f"{advisor_prefix}_z_star", 1.96)
    n_goal, _ = estimate_n_goal(explore_sigma ** 2, explore_omega, 0, ci_fraction)

    st.latex(
        r"N_{\rm goal} \approx \left\lceil"
        r"\frac{4\,z_*^2\,\sigma^2}{\omega_{\rm goal}^2}"
        r"\right\rceil"
    )
    st.metric(label="N_goal (estimated minimum sample size)", value=f"{n_goal:,}")

    with st.expander("⚙️ Advanced"):
        adv_z = st.number_input(
            "z* (critical value)",
            min_value=1.0,
            max_value=4.0,
            value=1.96,
            step=0.01,
            format="%.2f",
            key=f"{advisor_prefix}_z_star",
            help="1.96 ≈ 95% HDI, 2.576 ≈ 99% HDI",
        )
        adv_col1, adv_col2 = st.columns(2)
        with adv_col1:
            st.number_input(
                "Background ω min",
                min_value=w_goal_min * 0.5,
                max_value=w_goal_max,
                value=w_goal_min,
                step=max(0.0001, (w_goal_max - w_goal_min) / 10.0),
                format="%.4g",
                key=f"{advisor_prefix}_w_min",
            )
        with adv_col2:
            st.number_input(
                "Background ω max",
                min_value=w_goal_min,
                max_value=w_goal_max * 2,
                value=w_goal_max,
                step=max(0.0001, (w_goal_max - w_goal_min) / 10.0),
                format="%.4g",
                key=f"{advisor_prefix}_w_max",
            )
        n_goal_adv = math.ceil(4 * adv_z ** 2 * explore_sigma ** 2 / explore_omega ** 2)
        st.metric(label="N_goal (with custom z*)", value=f"{n_goal_adv:,}")

    fig = plot_n_goal_by_sigma(
        omega_goal=explore_omega,
        sigma_highlight=explore_sigma,
        z_star=z_star,
        sigma_min=sigma_min,
        sigma_max=sigma_max,
        w_goal_min=st.session_state.get(f"{advisor_prefix}_w_min", w_goal_min),
        w_goal_max=st.session_state.get(f"{advisor_prefix}_w_max", w_goal_max),
    )
    st.pyplot(fig)

    return explore_sigma, explore_omega
