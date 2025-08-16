"""
Canonical Transaction Schema (CTS) utilities for balance pipeline.
Ensures all DataFrames conform to a single schema before concatenation.
"""

import re

import pandas as pd

# Canonical Transaction Schema - all loaders must return this exact schema
CTS = [
    "date",
    "person",
    "merchant",
    "description",
    "actual_amount",
    "allowed_amount",
    "source_file",
]

# Money columns that need special parsing and dtype enforcement
CTS_MONEY_COLS: set[str] = {"actual_amount", "allowed_amount"}

# Central column alias mapping - all variants map to CTS names
COLUMN_ALIASES: dict[str, str] = {
    # Date variants
    "date of purchase": "date",
    "month": "date",
    # Person variants
    "name": "person",
    # Description variants
    "merchant description": "description",
    # Money variants - note the spaces in original column names
    " actual amount ": "actual_amount",
    " allowed amount ": "allowed_amount",
    "actual amount": "actual_amount",
    "allowed amount": "allowed_amount",
    "gross total": "actual_amount",
    "ryan's rent (43%)": "allowed_amount",
    "jordyn's rent (57%)": "allowed_amount",
    # Additional merchant variants
    "merchant description": "description",
}


def parse_money(value) -> float:
    """
    Parse money values from various string formats to float.
    Handles: $1,234.56, (1234.56), $--, empty strings, etc.
    """
    if pd.isna(value) or value == "":
        return 0.0

    value_str = str(value).strip()

    # Handle special cases
    if value_str in ("", "-", "$ -", "$ -   ", "$--"):
        return 0.0

    # Remove all non-numeric characters except decimal point and minus sign
    cleaned = re.sub(r"[^0-9.\-]", "", value_str)

    if cleaned in ("", "-"):
        return 0.0

    try:
        return round(float(cleaned), 2)
    except ValueError:
        return 0.0


def normalize_cols(df: pd.DataFrame, source_file: str) -> pd.DataFrame:
    """
    Normalize any DataFrame to conform to Canonical Transaction Schema (CTS).

    Args:
        df: Input DataFrame with any column structure
        source_file: Source identifier for tracking

    Returns:
        DataFrame with exactly CTS columns and proper dtypes
    """
    if df.empty:
        # Return empty DataFrame with CTS structure
        empty_df = pd.DataFrame(columns=CTS)
        for col in CTS_MONEY_COLS:
            empty_df[col] = empty_df[col].astype("float64")
        return empty_df

    # Make a copy to avoid modifying original
    result = df.copy()

    # Step 1: Normalize column names (lowercase, strip whitespace)
    result.columns = [str(c).strip().lower() for c in result.columns]

    # Step 2: Apply column aliases
    result = result.rename(columns=COLUMN_ALIASES)

    # Step 3: Ensure all CTS columns exist
    for col in CTS:
        if col not in result.columns:
            if col in CTS_MONEY_COLS:
                result[col] = 0.0
            elif col == "source_file":
                result[col] = source_file
            else:
                result[col] = ""

    # Step 4: Parse money columns
    for col in CTS_MONEY_COLS:
        if col in result.columns:
            result[col] = result[col].apply(parse_money)

    # Step 5: Parse date column
    if "date" in result.columns:
        result["date"] = pd.to_datetime(result["date"], errors="coerce")

    # Step 6: Set source_file
    result["source_file"] = source_file

    # Step 7: Handle duplicate columns by keeping only the first occurrence
    # This can happen when multiple source columns map to the same CTS column
    result = result.loc[:, ~result.columns.duplicated()]

    # Step 8: Return only CTS columns in correct order
    return result[CTS].copy()


def validate_cts_compliance(df: pd.DataFrame) -> bool:
    """
    Validate that a DataFrame conforms to CTS.

    Returns:
        True if compliant, False otherwise
    """
    if df.empty:
        return True

    # Check column names
    if list(df.columns) != CTS:
        return False

    # Check money column dtypes
    for col in CTS_MONEY_COLS:
        if not pd.api.types.is_numeric_dtype(df[col]):
            return False

    # Check date column dtype
    if not pd.api.types.is_datetime64_any_dtype(df["date"]):
        return False

    return True
