"""
Are We There Yet? 🚗  Sequential Testing Advisor

A Streamlit app implementing the DPitG (Decisive Precision is the Goal)
stopping algorithm for sequential hypothesis testing.

Three views, controlled by _app_view in session state:
  "home"          — landing page: choose mode, variable type, and groups
  "prospective"   — sample-size planning (binary only)
  "retrospective" — stopping verdict for observed data (all variable types)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

st.set_page_config(
    page_title="Are We There Yet? 🚗",
    page_icon="🚗",
    layout="centered",
)

from tabs import binary, continuous, categorical
from tabs import prospective_binary
from utils.tutorials import GLOSSARY_TABLE, GLOSSARY_TABLE_BETWEEN_GROUPS
from utils.constants import (
    PREPRINT_URL, PREPRINT_CITE_INLINE, PREPRINT_APA, PREPRINT_BIBTEX, PREPRINT_ARXIV_ID,
)


# Putting here because for some reason
# when Streamlit hosts the `from utils.tutorials import get_package_versions`
# doesn't work, even though locally it does.
# Perhaps this is an __init__.py import issue?
def get_package_versions(packages=None):
    """Return a dict of package -> version for common app packages."""
    try:
        from importlib import metadata as importlib_metadata
    except Exception:
        import importlib_metadata

    if packages is None:
        packages = ["streamlit", "scipy", "numpy", "matplotlib"]

    versions = {}
    for pkg in packages:
        try:
            versions[pkg] = importlib_metadata.version(pkg)
        except Exception:
            versions[pkg] = "unknown"
    return versions


caption_str = "Sequential Hypothesis Testing Advisor"

# ── Flush pending example values BEFORE any widgets are instantiated ──────────
# Must happen before sidebar_inputs() so Streamlit sees new values as widget
# initial state rather than trying to modify already-instantiated widgets.
if "_pending_example" in st.session_state:
    for _k, _v in st.session_state.pop("_pending_example").items():
        st.session_state[_k] = _v

# ── Read routing state ────────────────────────────────────────────────────────
_app_view = st.session_state.get("_app_view", "home")
_app_variable_type = st.session_state.get("_app_variable_type", "Binary")
_app_analysis_mode = st.session_state.get("_app_analysis_mode", "Single Group")

# ── Sidebar header (always shown) ─────────────────────────────────────────────
st.sidebar.title("🚗 Are We There Yet?")
st.sidebar.caption(caption_str)

if _app_view != "home":
    if st.sidebar.button("← Home", key="_nav_home_btn", use_container_width=True):
        st.session_state["_app_view"] = "home"
        st.rerun()
    st.sidebar.divider()

# ── Sidebar watermark (always at bottom) — rendered last per view ─────────────
def _sidebar_watermark():
    try:
        _versions = get_package_versions()
    except Exception:
        _versions = {}
    _compact = (
        f"📦 streamlit {_versions.get('streamlit','?')} | "
        f"scipy {_versions.get('scipy','?')} | "
        f"numpy {_versions.get('numpy','?')} | "
        f"matplotlib {_versions.get('matplotlib','?')}"
    )
    st.sidebar.caption(_compact)
    st.sidebar.caption(f"📄 [{PREPRINT_CITE_INLINE}]({PREPRINT_URL})")


# ── About expander (shared across views) ─────────────────────────────────────
def _about_expander():
    with st.expander("ℹ️ About"):
        st.markdown(
            "This calculator implements the **DPitG** (Decisive Precision is the Goal) "
            "sequential testing algorithm. Use **Prospective** to plan your sample size, "
            "or **Retrospective** to check whether your collected data meets the stopping criterion."
        )
        st.divider()
        st.markdown(
            f"For full details on DPitG see: "
            f"[![arXiv](https://img.shields.io/badge/arXiv-{PREPRINT_ARXIV_ID}-b31b1b.svg)]({PREPRINT_URL})",
            unsafe_allow_html=False,
        )
        st.markdown("Citations (APA & BibTeX):")
        st.markdown(PREPRINT_APA)
        st.code(PREPRINT_BIBTEX, language="bibtex")


def _useful_expander():
    with st.expander("💡 When is this calculator most useful?"):
        st.info(
            "The **DPitG** stop criterion shines when data collection is relatively cheap and the budget "
            "comfortably covers the required sample. \n\n For expensive settings — clinical trials, longitudinal studies, "
            "costly policy evaluations — it still provides value as a diagnostic: it makes explicit what precision is "
            "achievable within the available budget, enabling an honest assessment of what the data can and cannot support. \n\n"
            "When precision is not met, within the 'Let Me Peek! 👀' tab you can find a 'Decide Now! 🎲' insert to assess decision risk. \n\n"
            "You can also examine results using ***p*-values** and **Bayes Factors** within dedicated tabs. \n\n"
        )

# ═══════════════════════════════════════════════════════════════════════════════
# HOME VIEW
# ═══════════════════════════════════════════════════════════════════════════════

def _render_home():
    st.title("Are We There Yet? 🚗")
    st.caption(caption_str)
    st.divider()

    st.markdown("### What would you like to do?")

    _mode_options = [
        "📐 Prospective — I'm planning a study",
        "🔍 Retrospective — I have data, is it enough?",
    ]
    _home_mode = st.radio(
        "Mode",
        _mode_options,
        index=0,
        key="_home_mode",
        label_visibility="collapsed",
    )
    is_prospective = _home_mode.startswith("📐")

    st.divider()
    st.markdown("### Variable type")

    if is_prospective:
        _var_options = ["Binary"]
        st.caption("Prospective planning is currently available for binary (Bernoulli) data.")
    else:
        _var_options = ["Binary", "Continuous", "Categorical"]

    _home_var_type = st.radio(
        "Variable type",
        _var_options,
        index=0,
        key="_home_var_type",
        horizontal=True,
        label_visibility="collapsed",
    )

    show_groups = _home_var_type != "Categorical"

    if show_groups:
        st.divider()
        st.markdown("### Groups")
        _home_analysis_mode = st.radio(
            "Groups",
            ["Single Group", "Between Groups"],
            index=0,
            key="_home_analysis_mode",
            horizontal=True,
            label_visibility="collapsed",
        )
    else:
        _home_analysis_mode = "N/A"

    st.divider()

    if st.button("Continue →", type="primary", key="_home_continue_btn"):
        st.session_state["_app_view"] = "prospective" if is_prospective else "retrospective"
        st.session_state["_app_variable_type"] = _home_var_type
        st.session_state["_app_analysis_mode"] = _home_analysis_mode
        st.rerun()

    st.divider()

    with st.expander("📖 Glossary"):
        st.markdown(GLOSSARY_TABLE, unsafe_allow_html=True)

    _useful_expander()
    _about_expander()

    _sidebar_watermark()


# ═══════════════════════════════════════════════════════════════════════════════
# PROSPECTIVE VIEW
# ═══════════════════════════════════════════════════════════════════════════════

def _render_prospective():
    # Sidebar context label
    st.sidebar.markdown(
        f"**📐 Prospective — {_app_variable_type}, {_app_analysis_mode}**"
    )
    st.sidebar.divider()

    inputs = prospective_binary.sidebar_inputs(_app_analysis_mode)

    _sidebar_watermark()

    # ── Main area ─────────────────────────────────────────────────────────────
    st.title("Sample Size Planning 📐")
    st.caption(f"{_app_variable_type} · {_app_analysis_mode}")

    prospective_binary.render_results(inputs)

    _glossary = GLOSSARY_TABLE_BETWEEN_GROUPS if _app_analysis_mode == "Between Groups" else GLOSSARY_TABLE
    with st.expander("📖 Glossary"):
        st.markdown(_glossary, unsafe_allow_html=True)

    _useful_expander()
    _about_expander()


# ═══════════════════════════════════════════════════════════════════════════════
# RETROSPECTIVE VIEW
# ═══════════════════════════════════════════════════════════════════════════════

def _render_retrospective():
    # Sidebar context label
    _mode_label = (
        f"**🔍 Retrospective — {_app_variable_type}"
        + (f", {_app_analysis_mode}**" if _app_variable_type != "Categorical" else "**")
    )
    st.sidebar.markdown(_mode_label)
    st.sidebar.divider()

    # ── Pending force-commit (set by Example button) ──────────────────────────
    _force_commit = st.session_state.pop("_force_commit", False)

    # ── Sidebar inputs ────────────────────────────────────────────────────────
    if _app_variable_type == "Binary":
        inputs = binary.sidebar_inputs(_app_analysis_mode)
    elif _app_variable_type == "Continuous":
        inputs = continuous.sidebar_inputs(_app_analysis_mode)
    else:  # Categorical
        inputs = categorical.sidebar_inputs()

    # ── Analysis controls ─────────────────────────────────────────────────────
    st.sidebar.divider()

    live_update = st.sidebar.checkbox(
        "⚡ Live update", value=False, key="live_update",
        help="When on, results refresh as you type. When off, click Analyze.",
    )

    _col_analyze, _col_example = st.sidebar.columns(2)
    with _col_analyze:
        _analyze_clicked = st.button(
            "🔍 Analyze", type="primary",
            disabled=live_update, use_container_width=True,
        )
    with _col_example:
        _example_clicked = st.button(
            "📋 Example", use_container_width=True,
        )

    _sidebar_watermark()

    # ── Commit logic ──────────────────────────────────────────────────────────
    _current_commit_key = (
        f"{_app_variable_type}_{inputs.get('analysis_mode', _app_analysis_mode)}"
    )

    if _example_clicked:
        _mode = inputs.get("analysis_mode", _app_analysis_mode)
        if _app_variable_type == "Binary":
            _ex = binary.get_example_values(_mode)
        elif _app_variable_type == "Continuous":
            _ex = continuous.get_example_values(_mode)
        else:
            _ex = categorical.get_example_values()
        st.session_state["_pending_example"] = _ex
        st.session_state["_force_commit"] = True
        st.rerun()

    if live_update or _force_commit:
        st.session_state["committed_inputs"] = inputs
        st.session_state["committed_key"] = _current_commit_key
    elif _analyze_clicked:
        st.session_state["committed_inputs"] = inputs
        st.session_state["committed_key"] = _current_commit_key

    # ── Main area ─────────────────────────────────────────────────────────────
    st.title("Are We There Yet? 🚗")
    _mode_disp = _app_analysis_mode if _app_variable_type != "Categorical" else ""
    st.caption(f"{_app_variable_type}" + (f" · {_mode_disp}" if _mode_disp else ""))

    _committed_inputs = st.session_state.get("committed_inputs")
    _committed_key = st.session_state.get("committed_key")

    if _committed_inputs is not None and _committed_key == _current_commit_key:
        if _app_variable_type == "Binary":
            binary.render_results(_committed_inputs)
        elif _app_variable_type == "Continuous":
            continuous.render_results(_committed_inputs)
        else:
            categorical.render_results(_committed_inputs)
    else:
        st.info(
            "👈 Fill in your data in the sidebar, then click **🔍 Analyze**.\n\n"
            "Or try **📋 Example** to load sample data instantly."
        )

        _is_binary_single = (
            _app_variable_type == "Binary"
            and _app_analysis_mode == "Single Group"
        )
        _rope_or_goal_missing = (
            inputs.get("rope_width") is None or inputs.get("precision_goal") is None
        )
        if _is_binary_single and _rope_or_goal_missing:
            st.warning(
                "👈 Need help determining ROPE & Precision Goal? "
                "Click the 🧭 button in the sidebar."
            )

    _glossary = GLOSSARY_TABLE_BETWEEN_GROUPS if _app_analysis_mode == "Between Groups" else GLOSSARY_TABLE
    with st.expander("📖 Glossary"):
        st.markdown(_glossary, unsafe_allow_html=True)

    _useful_expander()
    _about_expander()


# ═══════════════════════════════════════════════════════════════════════════════
# Route to active view
# ═══════════════════════════════════════════════════════════════════════════════

if _app_view == "home":
    _render_home()
elif _app_view == "prospective":
    _render_prospective()
else:  # retrospective
    _render_retrospective()
