from typing import List, Tuple
import pandas as pd
from balance_pipeline.errors import DataConsistencyError

def flip_if_positive(df: pd.DataFrame, amount_col: str) -> pd.DataFrame:
    """
    Flip positive amounts to negative in the specified column.
    Raises DataConsistencyError if df is not a DataFrame or column missing.
    """
    if not isinstance(df, pd.DataFrame):
        raise DataConsistencyError(f"Expected pandas DataFrame, got {type(df)}")
    if amount_col not in df.columns:
        raise DataConsistencyError(f"Column '{amount_col}' not found in DataFrame for flip_if_positive")
    # Ensure numeric
    df[amount_col] = pd.to_numeric(df[amount_col], errors='coerce')
    # Mask positive values and flip
    positive_mask = df[amount_col] > 0
    df.loc[positive_mask, amount_col] = -df.loc[positive_mask, amount_col].abs()
    return df

def flip_if_withdrawal(df: pd.DataFrame,
                       amount_col: str,
                       category_col: str = "Category") -> pd.DataFrame:
    """
    Flip amounts to negative where the category indicates withdrawal or payment.
    Raises DataConsistencyError if inputs are invalid.
    """
    if not isinstance(df, pd.DataFrame):
        raise DataConsistencyError(f"Expected pandas DataFrame, got {type(df)}")
    if amount_col not in df.columns:
        raise DataConsistencyError(f"Column '{amount_col}' not found in DataFrame for flip_if_withdrawal")
    if category_col not in df.columns:
        raise DataConsistencyError(f"Column '{category_col}' not found in DataFrame for flip_if_withdrawal")
    # Ensure numeric
    df[amount_col] = pd.to_numeric(df[amount_col], errors='coerce')
    # Identify withdrawal categories
    mask = (
        df[category_col].notna()
        & df[category_col].str.contains("Withdrawal|Payment", case=False, na=False, regex=True)
    )
    df.loc[mask, amount_col] = -df.loc[mask, amount_col].abs()
    return df
