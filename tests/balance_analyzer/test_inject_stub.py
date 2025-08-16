"""Unit test for the opening balance injection stub.

Verifies that the placeholder implementation is a no-op that returns an
identical DataFrame (values and index preserved).
"""

from __future__ import annotations

import pandas as pd
from baseline_analyzer import inject_opening_balance, load_config
from pandas.testing import assert_frame_equal


def test_inject_opening_balance_noop() -> None:
    """inject_opening_balance should return an unchanged copy of the input."""
    # tiny DataFrame with non-default index to catch index mismatches
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]}, index=[100, 101])

    cfg = load_config()  # type: ignore[arg-type]  # default settings object
    result = inject_opening_balance(df, cfg)

    # Ensure equality — allow dtype cast differences (e.g., int32 vs int64)
    assert_frame_equal(result, df, check_dtype=False)
    # Confirm we got a copy (not strictly required, but nice extra check)
    assert result is not df
