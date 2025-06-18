#!/usr/bin/env python
"""
Quick expense totals: all vs shared – NA-safe
"""

import pandas as pd
import re
from pathlib import Path

DATA_DIR  = Path(__file__).resolve().parent / "data"
csv_path  = DATA_DIR / "Expense_History_20250527.csv"

# -----------------------------
# 1) read & strip header spaces
# -----------------------------
expenses_df = pd.read_csv(csv_path)
expenses_df.columns = expenses_df.columns.str.strip()      # " Actual Amount " -> "Actual Amount"

# -----------------------------
# 2) helpers
# -----------------------------
CURRENCY_RE = re.compile(r"[^0-9.\-]")

def clean_money(series: pd.Series) -> pd.Series:
    """Strip $, commas, blanks → float (NaN for non-numbers)."""
    cleaned = (
        series.astype(str)
              .str.replace(CURRENCY_RE, "", regex=True)
              .replace({"": pd.NA, "nan": pd.NA})
    )
    return pd.to_numeric(cleaned, errors="coerce")         # <- immune to pd.NA

# -----------------------------
# 3) normalise amounts
# -----------------------------
expenses_df["ActualAmount"]  = clean_money(expenses_df["Actual Amount"])
expenses_df["AllowedAmount"] = clean_money(expenses_df["Allowed Amount"])

# -----------------------------
# 4) totals
# -----------------------------
total_all     = expenses_df["ActualAmount"].sum(skipna=True)
total_shared  = expenses_df.loc[expenses_df["AllowedAmount"] > 0, "AllowedAmount"].sum(skipna=True)
personal_only = total_all - total_shared

# -----------------------------
# 5) pretty-print
# -----------------------------
print(f"Total of ALL expenses   : ${total_all:,.2f}")
print(f"Total of SHARED expenses: ${total_shared:,.2f}")
print(f"Difference (personal)   : ${personal_only:,.2f}")
