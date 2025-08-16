"""
Transaction Ledger CSV loader.
Handles format with header on 3rd row:
"July 4th, 2024 - October 1st, 2024",,,,,,,,
Ryan Expenses,,,,,,,,
Name,Date of Purchase,Account,Merchant, Merchant Description , Actual Amount , Description ,Category,Running Balance
[data rows]
"""

import pathlib

import pandas as pd

from ..column_utils import normalize_cols


def find_latest_ledger_file(data_dir: pathlib.Path) -> pathlib.Path:
    """Find the latest Transaction_Ledger_*.csv file in data_dir."""
    pattern = "Transaction_Ledger_*.csv"
    files = list(data_dir.glob(pattern))
    if not files:
        raise FileNotFoundError(f"No files matching {pattern} found in {data_dir}")
    # Return the latest by filename (lexicographic sort)
    return sorted(files)[-1]


def find_header_row(file_path: pathlib.Path) -> int:
    """
    Scan first 10 rows to find the header row containing transaction columns.
    Look for patterns like 'date', 'name', 'actual', 'merchant'
    """
    with open(file_path, encoding="utf-8", errors="ignore") as f:
        for i, line in enumerate(f):
            if i >= 10:  # Only check first 10 rows
                break

            line_lower = line.lower()
            # Look for key column indicators
            if (
                "date" in line_lower
                and "name" in line_lower
                and ("actual" in line_lower or "amount" in line_lower)
            ):
                return i

    # Default fallback - assume row 2 (0-indexed)
    return 2


def load_transaction_ledger(data_dir: pathlib.Path) -> pd.DataFrame:
    """
    Load Transaction Ledger CSV with header detection.

    Args:
        data_dir: Directory containing Transaction_Ledger_*.csv

    Returns:
        CTS-compliant DataFrame
    """
    try:
        ledger_file = find_latest_ledger_file(data_dir)
    except FileNotFoundError:
        return pd.DataFrame()

    # Find the actual header row
    header_row = find_header_row(ledger_file)

    try:
        # Load CSV with detected header row
        df = pd.read_csv(ledger_file, skiprows=header_row, on_bad_lines="skip")

        # Remove completely empty rows
        df = df.dropna(how="all")

        if df.empty:
            return pd.DataFrame()

        # Apply CTS normalization
        return normalize_cols(df, "Transaction_Ledger")

    except Exception as e:
        print(f"Warning: Failed to parse transaction ledger {ledger_file}: {e}")
        return pd.DataFrame()
