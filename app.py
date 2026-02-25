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

st.title("Are We There Yet? 🚗")
st.caption("Sequential Testing Advisor  •  Enhanced Precision is the Goal (ePitG)")

st.markdown(
    "Input your experiment's summary statistics below to check whether "
    "you've collected enough data for a conclusive decision."
)

# --- Main tabs ---
from tabs import binary, continuous

tab_binary, tab_continuous = st.tabs(["Binary Variables", "Continuous Variables"])

with tab_binary:
    binary.render()

with tab_continuous:
    continuous.render()
