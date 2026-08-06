"""
Tests for utils/decision.py — ePitG decision logic.
"""
import pytest

from utils.decision import (
    Decision,
    DecisionResult,
    _decide_location,
    epitg_decision,
)

# ── Shared ROPE / HDI helpers ─────────────────────────────────
# ROPE: [0.45, 0.55], precision_goal: 0.08
ROPE_MIN = 0.45
ROPE_MAX = 0.55
PRECISION_GOAL = 0.08  # narrower than ROPE width (0.10)


def _make_result(**kwargs) -> DecisionResult:
    """Build an epitg_decision result with sensible defaults, overriding via kwargs."""
    defaults = dict(
        hdi_min=0.46, hdi_max=0.54,   # inside ROPE, precision met
        rope_min=ROPE_MIN, rope_max=ROPE_MAX,
        precision_goal=PRECISION_GOAL,
        point_estimate=0.50,
        ci_fraction=0.95,
    )
    defaults.update(kwargs)
    return epitg_decision(**defaults)


# ──────────────────────────────────────────────────────────────


class TestDecideLocation:
    """Unit tests for the internal _decide_location function."""

    def test_hdi_inside_rope_is_accept(self):
        """HDI fully within ROPE → ACCEPT."""
        assert _decide_location(0.47, 0.53, ROPE_MIN, ROPE_MAX) == Decision.ACCEPT

    def test_hdi_above_rope_is_reject(self):
        """HDI fully above ROPE → REJECT."""
        assert _decide_location(0.60, 0.70, ROPE_MIN, ROPE_MAX) == Decision.REJECT

    def test_hdi_below_rope_is_reject(self):
        """HDI fully below ROPE → REJECT."""
        assert _decide_location(0.20, 0.30, ROPE_MIN, ROPE_MAX) == Decision.REJECT

    def test_hdi_straddles_rope_upper_is_inconclusive(self):
        """HDI partially above ROPE → INCONCLUSIVE."""
        assert _decide_location(0.47, 0.58, ROPE_MIN, ROPE_MAX) == Decision.INCONCLUSIVE

    def test_hdi_straddles_rope_lower_is_inconclusive(self):
        """HDI partially below ROPE → INCONCLUSIVE."""
        assert _decide_location(0.40, 0.50, ROPE_MIN, ROPE_MAX) == Decision.INCONCLUSIVE

    def test_hdi_spans_entire_rope_is_inconclusive(self):
        """HDI wider than ROPE and containing it → INCONCLUSIVE."""
        assert _decide_location(0.30, 0.70, ROPE_MIN, ROPE_MAX) == Decision.INCONCLUSIVE

    def test_hdi_touching_rope_boundary_is_accept(self):
        """HDI exactly at ROPE edges (inclusive) → ACCEPT."""
        assert _decide_location(ROPE_MIN, ROPE_MAX, ROPE_MIN, ROPE_MAX) == Decision.ACCEPT


# ──────────────────────────────────────────────────────────────


class TestEpitgDecisionOutcomes:
    """Integration tests: all four Decision outcomes from epitg_decision."""

    def test_accept(self):
        """Precision met + HDI inside ROPE → ACCEPT."""
        result = _make_result(hdi_min=0.47, hdi_max=0.53)
        assert result.decision == Decision.ACCEPT

    def test_reject_above(self):
        """Precision met + HDI above ROPE → REJECT."""
        result = _make_result(hdi_min=0.62, hdi_max=0.68, point_estimate=0.65)
        assert result.decision == Decision.REJECT

    def test_reject_below(self):
        """Precision met + HDI below ROPE → REJECT."""
        result = _make_result(hdi_min=0.20, hdi_max=0.26, point_estimate=0.23)
        assert result.decision == Decision.REJECT

    def test_inconclusive(self):
        """Precision met + HDI straddles ROPE → INCONCLUSIVE.

        HDI [0.50, 0.57]: width=0.07 < goal=0.08 (precision met),
        but hdi_max=0.57 > rope_max=0.55 → straddles upper boundary.
        """
        result = _make_result(hdi_min=0.50, hdi_max=0.57)
        assert result.decision == Decision.INCONCLUSIVE

    def test_needs_more_data(self):
        """Precision not met → NEEDS_MORE_DATA, regardless of location."""
        # HDI is inside ROPE but too wide
        result = _make_result(hdi_min=0.40, hdi_max=0.60)  # width=0.20 > goal=0.08
        assert result.decision == Decision.NEEDS_MORE_DATA

    def test_needs_more_data_even_if_outside_rope(self):
        """NEEDS_MORE_DATA even when HDI is outside ROPE, if precision not met."""
        result = _make_result(hdi_min=0.60, hdi_max=0.80, point_estimate=0.70)
        assert result.decision == Decision.NEEDS_MORE_DATA


# ──────────────────────────────────────────────────────────────


class TestDecisionResultFields:
    """Tests for DecisionResult computed fields and properties."""

    def test_hdi_width_computed_correctly(self):
        """hdi_width == hdi_max - hdi_min."""
        result = _make_result(hdi_min=0.46, hdi_max=0.54)
        assert result.hdi_width == pytest.approx(0.08, abs=1e-9)

    def test_rope_width_computed_correctly(self):
        """rope_width == rope_max - rope_min."""
        result = _make_result()
        assert result.rope_width == pytest.approx(ROPE_MAX - ROPE_MIN, abs=1e-9)

    def test_precision_met_true_when_width_less_than_goal(self):
        result = _make_result(hdi_min=0.47, hdi_max=0.53)  # width=0.06 < 0.08
        assert result.precision_met is True

    def test_precision_met_false_when_width_exceeds_goal(self):
        result = _make_result(hdi_min=0.43, hdi_max=0.57)  # width=0.14 > 0.08
        assert result.precision_met is False

    def test_precision_met_true_when_width_equals_goal(self):
        """Precision is met when HDI width equals the goal (≤)."""
        result = _make_result(hdi_min=0.0, hdi_max=0.08)  # width exactly == 0.08
        assert result.precision_met is True

    def test_can_stop_true_for_accept(self):
        result = _make_result(hdi_min=0.47, hdi_max=0.53)
        assert result.can_stop is True

    def test_can_stop_true_for_reject(self):
        result = _make_result(hdi_min=0.62, hdi_max=0.68, point_estimate=0.65)
        assert result.can_stop is True

    def test_can_stop_false_for_inconclusive(self):
        # HDI [0.50, 0.57]: width=0.07 < goal=0.08, but straddles rope_max=0.55
        result = _make_result(hdi_min=0.50, hdi_max=0.57)
        assert result.can_stop is False

    def test_can_stop_false_for_needs_more_data(self):
        result = _make_result(hdi_min=0.40, hdi_max=0.60)
        assert result.can_stop is False

    def test_display_has_expected_keys(self):
        """display property must expose emoji, label, color, message."""
        result = _make_result(hdi_min=0.47, hdi_max=0.53)
        display = result.display
        for key in ("emoji", "label", "color", "message"):
            assert key in display, f"Missing key: {key}"

    def test_point_estimate_stored(self):
        result = _make_result(point_estimate=0.61)
        assert result.point_estimate == pytest.approx(0.61)

    def test_ci_fraction_stored(self):
        result = _make_result(ci_fraction=0.90)
        assert result.ci_fraction == pytest.approx(0.90)
