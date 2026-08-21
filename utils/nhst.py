"""
Null Hypothesis Significance Testing (NHST) utilities.

Provides p-value calculations for comparison with DPitG sequential testing.
These are provided as reference to show limitations of traditional NHST.
"""
import numpy as np
from scipy.stats import norm, t as student_t
from typing import Tuple


def nhst_test(
    observed: float,
    null_value: float,
    se: float,
    test_type: str = "z",
    df: float = None,
) -> Tuple[float, float, str]:
    """
    Perform a two-tailed NHST test.

    Parameters
    ----------
    observed : float
        Observed statistic (proportion, mean, or difference).
    null_value : float
        Null hypothesis value (e.g., 0 for difference tests).
    se : float
        Standard error of the statistic.
    test_type : str
        "z" for z-test (binary/large samples) or "t" for t-test (continuous).
    df : float, optional
        Degrees of freedom (required if test_type="t").

    Returns
    -------
    tuple
        (test_statistic, p_value, decision_at_05)
        - test_statistic: z or t value
        - p_value: two-tailed p-value
        - decision_at_05: "Reject H₀" or "Fail to Reject H₀" at α=0.05

    Raises
    ------
    ValueError
        If test_type="t" but df is not provided.
    """
    if se == 0:
        # Avoid division by zero (edge case with zero variance)
        return (np.nan, np.nan, "Undefined")

    test_stat = (observed - null_value) / se

    if test_type == "z":
        # Two-tailed z-test
        p_value = 2 * norm.cdf(-abs(test_stat))
    elif test_type == "t":
        if df is None:
            raise ValueError("Degrees of freedom (df) required for t-test")
        # Two-tailed t-test
        p_value = 2 * student_t.cdf(-abs(test_stat), df=df)
    else:
        raise ValueError(f"Unknown test_type: {test_type}. Use 'z' or 't'.")

    decision_at_05 = "Reject H₀" if p_value < 0.05 else "Fail to Reject H₀"

    return (test_stat, p_value, decision_at_05)
