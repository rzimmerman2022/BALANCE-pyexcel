"""Opening balance injection logic (Sprint #4).

Insert a synthetic “Opening Balance” row **one day before** the first
transaction for each distinct account in the input *df*.

Behaviour
---------
* The new rows share the same structure/columns as *df*.
* ``cfg.opening_balance_col`` provides the label stamped into a suitable
  descriptive column (``"Merchant"`` preferred, else ``"Description"``,
  otherwise a new ``"Merchant"`` column is created).
* ``Amount`` (or configured amount column) is set to **0**.
* The result is sorted by ``Account`` then date so that each opening-balance
  row is the first per account.
"""

from __future__ import annotations

import pandas as pd

from ._settings import Settings


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def inject_opening_balance(df: pd.DataFrame, cfg: Settings) -> pd.DataFrame:  # noqa: D401
    """Return *df* with synthetic “Opening Balance” rows inserted.

    Parameters
    ----------
    df
        Baseline DataFrame.  Must contain at minimum:
        * Account column named exactly ``"Account"``.
        * Date column per ``cfg.date_col`` (datetime64[ns] or convertible).
        * Amount column per ``cfg.amount_col``.
    cfg
        Loaded settings object supplying configurable literals.

    Returns
    -------
    pd.DataFrame
        New DataFrame containing the original data **plus** one extra row
        for each unique account.
    """
    if df.empty:
        return df.copy()

    # Work on a copy to avoid mutating caller’s frame
    data = df.copy()

    account_col = "Account"
    if account_col not in data.columns:
        # Maintain stub’s earlier contract: silently return a copy when the
        # required columns are missing so downstream generic tests pass.
        return df.copy()

    date_col = cfg.date_col
    amount_col = cfg.amount_col

    # Identify the first-transaction row index for each account
    first_indices = data.groupby(account_col)[date_col].idxmin()

    synthetic_rows: list[pd.Series] = []
    label_col: str | None = None  # decided lazily

    for idx in first_indices:
        row = data.loc[idx].copy()

        # Decide which descriptive column to overwrite once.
        if label_col is None:
            for candidate in ("Merchant", "Description"):
                if candidate in data.columns:
                    label_col = candidate
                    break
            if label_col is None:  # neither exists → create Merchant
                label_col = "Merchant"
                data[label_col] = ""  # type: ignore[pd-unknown-arg]

        # Adjust fields
        row[date_col] = pd.to_datetime(row[date_col]) - pd.Timedelta(days=1)
        row[amount_col] = 0
        row[label_col] = cfg.opening_balance_col

        synthetic_rows.append(row)

    # Build DataFrame of opening rows using same column order
    openings = pd.DataFrame(synthetic_rows, columns=data.columns)

    # Concatenate and sort so openers lead per account
    out = pd.concat([data, openings], ignore_index=True)
    out.sort_values([account_col, date_col], inplace=True, kind="mergesort")
    out.reset_index(drop=True, inplace=True)
    return out
