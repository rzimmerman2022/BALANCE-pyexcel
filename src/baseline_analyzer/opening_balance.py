"""Opening balance injection stub for Baseline Analyzer.

Currently this is a no-op placeholder that simply returns a copy of the input
DataFrame.  Real logic will be implemented in a later sprint.
"""
from __future__ import annotations

import pandas as pd

from ._settings import Settings


def inject_opening_balance(df: pd.DataFrame, cfg: Settings) -> pd.DataFrame:  # noqa: D401
    """Return *df* unchanged (placeholder).

    Parameters
    ----------
    df
        Input baseline DataFrame.
    cfg
        Loaded :class:`~baseline_analyzer._settings.Settings` object, included
        here to lock-in the public signature expected by downstream callers.

    Returns
    -------
    pd.DataFrame
        A **copy** of *df* to avoid mutating the caller’s object.
    """
    return df.copy()  # no-op stub
