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

from tabs import binary, continuous, categorical, goal_planner

caption_str = "Sequential HypothesisTesting Advisor"
# ── Sidebar ──────────────────────────────────────────────────────────
st.sidebar.title("🚗 Are We There Yet?")
st.sidebar.caption(caption_str)

# Main navigation
page = st.sidebar.radio(
    "Navigation",
    ["🎯 Goal Planner", "📊 Analysis"],
    key="page_navigation",
)

st.sidebar.divider()

# If on Analysis page, show variable type selector and collect inputs
if page == "📊 Analysis":
    variable_type = st.sidebar.radio(
        "Variable type",
        ["Binary", "Continuous", "Categorical"],
        key="variable_type",
    )
    
    st.sidebar.divider()
    
    # Collect inputs in sidebar (each module owns its own sidebar widgets)
    if variable_type == "Binary":
        inputs = binary.sidebar_inputs()
    elif variable_type == "Continuous":
        inputs = continuous.sidebar_inputs()
    else:  # Categorical
        inputs = categorical.sidebar_inputs()

# ── Main area ────────────────────────────────────────────────────────
st.title("Are We There Yet? 🚗")
st.caption(caption_str)

# Route to appropriate page
if page == "🎯 Goal Planner":
    goal_planner.render_main()
else:  # Analysis
    if variable_type == "Binary":
        binary.render_results(inputs)
    elif variable_type == "Continuous":
        continuous.render_results(inputs)
    else:  # Categorical
        categorical.render_results(inputs)
