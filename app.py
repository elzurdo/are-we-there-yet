"""
Are We There Yet? 🚗  Sequential Testing Advisor

A Streamlit app implementing the Enhanced Precision is the Goal (ePitG)
stopping algorithm for sequential hypothesis testing.

Users input summary statistics and receive a verdict on whether
their experiment has met the stopping criteria.
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
from utils.tutorials import GLOSSARY_TABLE
from utils.constants import (
    PREPRINT_URL, PREPRINT_CITE_INLINE, PREPRINT_APA, PREPRINT_BIBTEX, PREPRINT_ARXIV_ID,
)


# Putting here because for some reason
# when Streamlit hosts the `from utils.tutorials import get_package_versions`
# doesn't work, even though locally it does.
# Perhaps this is an __init__.py import issue?
def get_package_versions(packages=None):
   """Return a dict of package -> version for common app packages.

   Uses importlib.metadata if available. Returns 'unknown' when a
   package is not installed or the version cannot be determined.
   """
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

# ── Flush pending example values BEFORE any widgets are instantiated ─────────
# This must happen before st.sidebar.radio / sidebar_inputs() so that
# Streamlit sees the new values as the initial state for each widget.
if "_pending_example" in st.session_state:
    for _k, _v in st.session_state.pop("_pending_example").items():
        st.session_state[_k] = _v

# ── Sidebar ──────────────────────────────────────────────────────────
st.sidebar.title("🚗 Are We There Yet?")
st.sidebar.caption(caption_str)

variable_type = st.sidebar.radio(
    "Variable type",
    ["Binary", "Continuous", "Categorical"],
    key="variable_type",
)

st.sidebar.divider()

# Check for pending force-commit (set when "📋 Example" is clicked)
_force_commit = st.session_state.pop("_force_commit", False)

# Collect inputs in sidebar (each module owns its own sidebar widgets)
if variable_type == "Binary":
    inputs = binary.sidebar_inputs()
elif variable_type == "Continuous":
    inputs = continuous.sidebar_inputs()
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

# ── Commit logic ──────────────────────────────────────────────────────────
_current_commit_key = f"{variable_type}_{inputs.get('analysis_mode', '')}"

if _example_clicked:
    _mode = inputs.get("analysis_mode", "Single Group")
    if variable_type == "Binary":
        _ex = binary.get_example_values(_mode)
    elif variable_type == "Continuous":
        _ex = continuous.get_example_values(_mode)
    else:
        _ex = categorical.get_example_values()
    # Stage values — they will be flushed into widget keys at the very top
    # of the next run, before any widgets are instantiated (avoiding the
    # "cannot be modified after widget is instantiated" error).
    st.session_state["_pending_example"] = _ex
    st.session_state["_force_commit"] = True
    st.rerun()

if live_update or _force_commit:
    st.session_state["committed_inputs"] = inputs
    st.session_state["committed_key"] = _current_commit_key
elif _analyze_clicked:
    st.session_state["committed_inputs"] = inputs
    st.session_state["committed_key"] = _current_commit_key

# ── Sidebar watermark (package versions) ─────────────────────────────────
try:
    _versions = get_package_versions()
except Exception:
    _versions = {"streamlit": "unknown", "scipy": "unknown", "numpy": "unknown", "matplotlib": "unknown"}

_compact = f"📦 Built with: streamlit {_versions.get('streamlit','unknown')} | scipy {_versions.get('scipy','unknown')} | numpy {_versions.get('numpy','unknown')} | matplotlib {_versions.get('matplotlib','unknown')}"
st.sidebar.caption(_compact)
st.sidebar.caption(f"📄 [{PREPRINT_CITE_INLINE}]({PREPRINT_URL})")
# ── Main area ────────────────────────────────────────────────────────
st.title("Are We There Yet? 🚗")
st.caption(caption_str)

# TODO: rename all ePitG → DPitG throughout the codebase (separate task)
with st.expander("ℹ️ About"):
    st.markdown(
        "This calculator helps you decide when to stop your experiment using the **DPitG** "
        "(Decisive Precision is the Goal) sequential testing algorithm. "
        "Enter your summary statistics, define the expected effect size (via the ROPE: Region of Practical Equivalence) and Precision Goal, "
        "and get an empirical stopping verdict."
    )

    st.divider()

    # ── Citation: Option A — inline hyperlinked text ──────────────────────────
    # st.markdown(
    #     f"For full details on DPitG see: [{PREPRINT_CITE_INLINE}]({PREPRINT_URL})"
    # )

    # ── Citation: Option B — arXiv shield badge ───────────────────────────────
    st.markdown(
        f"For full details on DPitG see: [![arXiv](https://img.shields.io/badge/arXiv-{PREPRINT_ARXIV_ID}-b31b1b.svg)]({PREPRINT_URL})",
        unsafe_allow_html=False,
    )

    # ── Citation: Option C — APA + BibTeX block ───────────────────────────────
    st.markdown("Citations (APA & BibTeX):")
    st.markdown(PREPRINT_APA)
    st.code(PREPRINT_BIBTEX, language="bibtex")

_committed_inputs = st.session_state.get("committed_inputs")
_committed_key = st.session_state.get("committed_key")

if _committed_inputs is not None and _committed_key == _current_commit_key:
    if variable_type == "Binary":
        binary.render_results(_committed_inputs)
    elif variable_type == "Continuous":
        continuous.render_results(_committed_inputs)
    else:  # Categorical
        categorical.render_results(_committed_inputs)
else:
    st.info(
        "👈 Fill in your data in the sidebar, then click **🔍 Analyze**.\n\n"
        "Or try **📋 Example** to load sample data instantly."
    )
    
    _is_binary_single = (
        variable_type == "Binary"
        and inputs.get("analysis_mode") == "Single Group"
    )
    _rope_or_goal_missing = (
        inputs.get("rope_width") is None or inputs.get("precision_goal") is None
    )
    if _is_binary_single and _rope_or_goal_missing:
        st.warning(
            "👈 Need help determining ROPE & Precision Goal? Click the 🧭 button in the sidebar."
        )

with st.expander("📖 Glossary"):
    st.markdown(GLOSSARY_TABLE, unsafe_allow_html=True)

with st.expander("💡 When is this calculator most useful?"):
    st.info(
        "The **DPitG** stop criterion shines when data collection is relatively cheap and the budget "
        "comfortably covers the required sample. For expensive settings — clinical trials, longitudinal studies, "
        "costly policy evaluations — it still provides value as a diagnostic: it makes explicit what precision is "
        "achievable within the available budget, enabling an honest assessment of what the data can and cannot support. "
        "You can also examine results using ***p*-values** and **Bayes Factors** within dedicated tabs."
    )
