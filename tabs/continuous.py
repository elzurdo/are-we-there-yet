"""
Continuous variables — placeholder for future implementation.
"""
import streamlit as st


def sidebar_inputs() -> dict:
    """Placeholder sidebar inputs for continuous variables."""
    st.sidebar.info("🚧 Coming soon")
    return {}


def render_results(inputs: dict):
    """Placeholder main area for continuous variables."""
    st.markdown("#### Continuous Variables")
    st.info(
        "🚧 Continuous variables support coming soon!  \n"
        "This will support stopping decisions for continuous outcomes "
        "(e.g., means) using Student-t posteriors."
    )
