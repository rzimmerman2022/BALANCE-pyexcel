"""
Rent Allocation CSV loader.
Handles format with monthly rent splits:
Month, Tax Base Rent , Tax Garage , Tax Trash , Tax Courtesy , Conservice , Gross Total , Ryan's Rent (43%) ,Jordyn's Rent (57%)
Jan-24,"$1,946.00 ",$100.00 ,$29.00 ,$15.00 ,$29.72 ,"$2,119.72 ",$911.48 ,"$1,208.24 "
[data rows]

Creates separate rows for Ryan and Jordyn with their respective amounts.
"""

import pathlib

import pandas as pd

from ..column_utils import normalize_cols


def find_latest_rent_alloc_file(data_dir: pathlib.Path) -> pathlib.Path:
    """Find the latest Rent_Allocation_*.csv file in data_dir."""
    pattern = "Rent_Allocation_*.csv"
    files = list(data_dir.glob(pattern))
    if not files:
        raise FileNotFoundError(f"No files matching {pattern} found in {data_dir}")
    # Return the latest by filename (lexicographic sort)
    return sorted(files)[-1]


def load_rent_alloc(data_dir: pathlib.Path) -> pd.DataFrame:
    """
    Load Rent Allocation CSV and split into Ryan/Jordyn rows.

    Args:
        data_dir: Directory containing Rent_Allocation_*.csv

    Returns:
        CTS-compliant DataFrame with separate rows for Ryan and Jordyn
    """
    try:
        rent_file = find_latest_rent_alloc_file(data_dir)
    except FileNotFoundError:
        return pd.DataFrame()

    try:
        # Load the rent allocation CSV
        df = pd.read_csv(rent_file)

        # Remove completely empty rows
        df = df.dropna(how="all")

        # Filter out rows where Month is empty/null (template rows)
        df = df[df.iloc[:, 0].notna() & (df.iloc[:, 0].astype(str).str.strip() != "")]

        if df.empty:
            return pd.DataFrame()

        # Normalize column names for easier access
        df.columns = [str(c).strip().lower() for c in df.columns]

        rent_rows = []

        # Process each month row
        for _, row in df.iterrows():
            month = row.iloc[0]  # First column is month

            # Skip if month is empty or looks like a template
            if pd.isna(month) or str(month).strip() == "":
                continue

            # Find the gross total and individual amounts
            gross_total = None
            ryan_amount = None
            jordyn_amount = None

            # Look for gross total column (various possible names)
            for col in df.columns:
                if "gross" in col and "total" in col:
                    gross_total = row[col]
                elif "ryan" in col and ("rent" in col or "43%" in col):
                    ryan_amount = row[col]
                elif "jordyn" in col and ("rent" in col or "57%" in col):
                    jordyn_amount = row[col]

            # Create Ryan's rent row
            ryan_row = {
                "date": month,
                "person": "Ryan",
                "merchant": "Rent",
                "description": "Monthly rent allocation",
                "actual_amount": gross_total if gross_total is not None else 0,
                "allowed_amount": ryan_amount if ryan_amount is not None else 0,
                "source_file": "Rent_Allocation",
            }
            rent_rows.append(ryan_row)

            # Create Jordyn's rent row
            jordyn_row = {
                "date": month,
                "person": "Jordyn",
                "merchant": "Rent",
                "description": "Monthly rent allocation",
                "actual_amount": 0,  # Jordyn doesn't pay actual, only owes allowed
                "allowed_amount": jordyn_amount if jordyn_amount is not None else 0,
                "source_file": "Rent_Allocation",
            }
            rent_rows.append(jordyn_row)

        if not rent_rows:
            return pd.DataFrame()

        # Create DataFrame from rent rows
        rent_df = pd.DataFrame(rent_rows)

        # Apply CTS normalization
        return normalize_cols(rent_df, "Rent_Allocation")

    except Exception as e:
        print(f"Warning: Failed to parse rent allocation {rent_file}: {e}")
        return pd.DataFrame()
