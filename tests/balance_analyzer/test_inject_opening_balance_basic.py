"""Unit tests for opening balance injection (Sprint #4 – basic happy path)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from baseline_analyzer import inject_opening_balance, load_config

FIXTURE_DIR = Path(__file__).parent / "fixtures"
CSV_PATH = FIXTURE_DIR / "mini.csv"


def _load_fixture() -> pd.DataFrame:
    """Load mini.csv with correct dtypes for tests."""
    return pd.read_csv(
        CSV_PATH,
        parse_dates=["Date"],
        dtype={"Merchant": "string", "Account": "string", "Amount": "float64"},
    )


def test_inject_opening_balance_rows_and_labels() -> None:
    """Verify row count increase, label, and date offset per account."""
    df = _load_fixture()
    cfg = load_config()  # default YAML/settings

    out = inject_opening_balance(df, cfg)

    # Row count increases by number of distinct accounts
    n_accounts = df["Account"].nunique()
    assert len(out) == len(df) + n_accounts

    for acct, grp in out.groupby("Account"):
        first_row = grp.iloc[0]
        # Label check
        assert first_row["Merchant"] == cfg.opening_balance_col

        # Date check: first original date - 1 day
        orig_first_date = df.loc[df["Account"] == acct, "Date"].min()
        assert first_row["Date"] == orig_first_date - pd.Timedelta(days=1)
