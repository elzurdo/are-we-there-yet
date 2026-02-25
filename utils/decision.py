"""
Decision logic for the Enhanced Precision is the Goal (ePitG) stopping algorithm.

The ePitG algorithm requires BOTH conditions to stop:
1. Precision:  HDI width < Goal
2. Location:   HDI fully inside or fully outside the ROPE (conclusive)

Decision outcomes (after stopping):
- Accept:  HDI fully inside ROPE
- Reject:  HDI fully outside ROPE

If either condition is not met, data collection should continue.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Decision(Enum):
    """Possible ePitG verdicts."""
    ACCEPT = "accept"
    REJECT = "reject"
    INCONCLUSIVE = "inconclusive"  # precision met, but HDI straddles ROPE
    NEEDS_MORE_DATA = "needs_more_data"  # precision not yet met


# Display configuration for each decision
DECISION_DISPLAY = {
    Decision.ACCEPT: {
        "emoji": "✅",
        "label": "Accept θ_null",
        "color": "green",
        "message": "Both precision and conclusiveness achieved. The HDI is fully within the ROPE — accept the null hypothesis.",
    },
    Decision.REJECT: {
        "emoji": "❌",
        "label": "Reject θ_null",
        "color": "red",
        "message": "Both precision and conclusiveness achieved. The HDI is fully outside the ROPE — reject the null hypothesis.",
    },
    Decision.INCONCLUSIVE: {
        "emoji": "⏳",
        "label": "Keep Collecting",
        "color": "orange",
        "message": "Precision goal reached, but the HDI straddles the ROPE boundary. Keep collecting data for a conclusive result.",
    },
    Decision.NEEDS_MORE_DATA: {
        "emoji": "👀",
        "label": "Let me Peek!",
        "color": "blue",
        "message": "Whoa there, eager beaver! 🦫 Your precision goal hasn't been met yet. Here's a sneak peek at where things stand — but no peeking-induced decisions, okay?",
    },
}


@dataclass
class DecisionResult:
    """Container for ePitG decision output."""
    decision: Decision
    hdi_min: float
    hdi_max: float
    hdi_width: float
    rope_min: float
    rope_max: float
    rope_width: float
    precision_goal: float
    precision_met: bool
    point_estimate: float
    ci_fraction: float

    @property
    def display(self) -> dict:
        return DECISION_DISPLAY[self.decision]

    @property
    def can_stop(self) -> bool:
        """Whether the ePitG criteria allow stopping."""
        return self.decision in (Decision.ACCEPT, Decision.REJECT)


def _decide_location(hdi_min: float, hdi_max: float,
                     rope_min: float, rope_max: float) -> Decision:
    """
    Apply the Decision Rule (Algorithm 1 in the paper).

    Determines the relationship between HDI and ROPE:
    - Accept:       HDI fully inside ROPE
    - Reject:       HDI fully outside ROPE
    - Inconclusive: HDI straddles ROPE boundary
    """
    if rope_min <= hdi_min and hdi_max <= rope_max:
        return Decision.ACCEPT
    if hdi_min > rope_max:
        return Decision.REJECT  # θ_null < θ_hat
    if hdi_max < rope_min:
        return Decision.REJECT  # θ_hat < θ_null
    return Decision.INCONCLUSIVE


def epitg_decision(
    hdi_min: float,
    hdi_max: float,
    rope_min: float,
    rope_max: float,
    precision_goal: float,
    point_estimate: float,
    ci_fraction: float = 0.95,
) -> DecisionResult:
    """
    Apply the Enhanced Precision is the Goal (ePitG) algorithm.

    Parameters
    ----------
    hdi_min, hdi_max : float
        Lower and upper bounds of the HDI.
    rope_min, rope_max : float
        Lower and upper bounds of the ROPE.
    precision_goal : float
        Target HDI width for stopping.
    point_estimate : float
        Observed rate or mean (for display purposes).
    ci_fraction : float
        HDI mass fraction used (default 0.95).

    Returns
    -------
    DecisionResult
        Full decision output including verdict and diagnostics.
    """
    hdi_width = hdi_max - hdi_min
    rope_width = rope_max - rope_min
    precision_met = hdi_width < precision_goal

    if precision_met:
        decision = _decide_location(hdi_min, hdi_max, rope_min, rope_max)
    else:
        decision = Decision.NEEDS_MORE_DATA

    return DecisionResult(
        decision=decision,
        hdi_min=hdi_min,
        hdi_max=hdi_max,
        hdi_width=hdi_width,
        rope_min=rope_min,
        rope_max=rope_max,
        rope_width=rope_width,
        precision_goal=precision_goal,
        precision_met=precision_met,
        point_estimate=point_estimate,
        ci_fraction=ci_fraction,
    )
