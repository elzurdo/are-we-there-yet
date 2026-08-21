"""
Verdict display utilities for DPitG decision results.
"""
import streamlit as st
from utils.decision import Decision, DecisionResult

from utils.constants import GOAL_STR, HDI_WIDTH_STR, GOAL_STR_HTML, HDI_WIDTH_STR_HTML

def render_verdict_display(
    result: DecisionResult, 
    precision_goal: float, 
    fmt: str, 
    verdict_style: str
) -> None:
    """
    Render the verdict display for an DPitG decision result.
    
    Parameters
    ----------
    result : DecisionResult
        The decision result containing verdict, HDI, and display info
    precision_goal : float
        The target precision (HDI width)
    fmt : str
        Format string for displaying numbers (e.g., '.3f')
    verdict_style : str
        Display style: "Centered text" or "Info/Warning box"
    """
    display = result.display
    color = display["color"]
    
    # Display emoji and label
    st.markdown(f"### {display['emoji']}  {display['label']}")
    
    # Show HDI vs Goal comparison for NEEDS_MORE_DATA and INCONCLUSIVE
    if result.decision == Decision.NEEDS_MORE_DATA:
        if verdict_style == "Centered text":
            st.markdown(
                f"<div style='text-align: center; font-size: 1.2em; margin: 10px 0; "
                f"color: {color};'>"
                f"<strong>{HDI_WIDTH_STR_HTML} &gt; {GOAL_STR_HTML}</strong><br>"
                f"<code style='font-size: 1.1em; color: {color};'>{result.hdi_width:{fmt}} &gt; {precision_goal:{fmt}}</code>"
                f"</div>",
                unsafe_allow_html=True
            )
        else:  # Info/Warning box
            st.warning(
                f"**{HDI_WIDTH_STR} > {GOAL_STR}**  \n"
                f"`{result.hdi_width:{fmt}} > {precision_goal:{fmt}}`"
            )
    
    elif result.decision == Decision.INCONCLUSIVE:
        comparison = "=" if abs(result.hdi_width - precision_goal) < 1e-9 else "<"
        if verdict_style == "Centered text":
            st.markdown(
                f"<div style='text-align: center; font-size: 1.2em; margin: 10px 0; "
                f"color: {color};'>"
                f"<strong>{HDI_WIDTH_STR_HTML} {comparison} {GOAL_STR_HTML}</strong> (precision met)<br>"
                f"<code style='font-size: 1.1em; color: {color};'>{result.hdi_width:{fmt}} {comparison} {precision_goal:{fmt}}</code><br>"
                f"<em style='font-size: 0.9em;'>but HDI straddles ROPE</em>"
                f"</div>",
                unsafe_allow_html=True
            )
        else:  # Info/Warning box
            st.warning(
                f"**{HDI_WIDTH_STR} {comparison} {GOAL_STR}** (precision met)  \n"
                f"`{result.hdi_width:{fmt}} {comparison} {precision_goal:{fmt}}`  \n"
                f"*but HDI straddles ROPE*"
            )
    
    # Display message
    st.markdown(f"*{display['message']}*")
