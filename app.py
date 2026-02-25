"""
Are We There Yet? 🚗  Sequential Testing Advisor

A Streamlit app implementing the Enhanced Precision is the Goal (ePitG)
stopping algorithm for sequential hypothesis testing.

Users input summary statistics and receive a verdict on whether
their experiment has met the stopping criteria.
"""
import streamlit as st

st.set_page_config(
    page_title="Are We There Yet? 🚗",
    page_icon="🚗",
    layout="centered",
)

from tabs import binary, continuous

# ── Sidebar ──────────────────────────────────────────────────────────
st.sidebar.title("🚗 Are We There Yet?")
st.sidebar.caption("Sequential Testing Advisor")

variable_type = st.sidebar.radio(
    "Variable type",
    ["Binary", "Continuous"],
    key="variable_type",
)

st.sidebar.divider()

# Collect inputs in sidebar (each module owns its own sidebar widgets)
if variable_type == "Binary":
    inputs = binary.sidebar_inputs()
else:
    inputs = continuous.sidebar_inputs()

# ── Main area ────────────────────────────────────────────────────────
st.title("Are We There Yet? 🚗")
st.caption("Enhanced Precision is the Goal (ePitG)  •  Sequential Testing Advisor")

if variable_type == "Binary":
    binary.render_results(inputs)
else:
    continuous.render_results(inputs)
