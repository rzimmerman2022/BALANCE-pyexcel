"""
Lineage tracking utilities for the baseline analyzer.
Provides functions to inject step IDs and manage data lineage throughout the pipeline.
"""
from __future__ import annotations

import pandas as pd


def add_step_id(df: pd.DataFrame, step_id: str) -> pd.DataFrame:
    """
    Add a step ID to the lineage column of a DataFrame.
    
    Args:
        df: DataFrame to add step ID to
        step_id: Step identifier (e.g., "01a_raw", "02b_clean")
    
    Returns:
        DataFrame with updated lineage column
    """
    df = df.copy()
    
    if "lineage" not in df.columns:
        df["lineage"] = step_id
    else:
        # Append step ID to existing lineage with pipe separator
        df["lineage"] = df["lineage"].fillna("").apply(
            lambda x: f"{x}|{step_id}" if x else step_id
        )
    
    return df


def init_lineage(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
    """
    Initialize lineage tracking for a source DataFrame.
    
    Args:
        df: Source DataFrame
        source_name: Name of the source (e.g., "expenses", "ledger", "rent")
    
    Returns:
        DataFrame with initialized lineage column
    """
    df = df.copy()
    step_id = f"01a_{source_name}_raw"
    df["lineage"] = step_id
    return df


def merge_lineage(df1: pd.DataFrame, df2: pd.DataFrame, 
                  merge_step_id: str, **merge_kwargs) -> pd.DataFrame:
    """
    Merge two DataFrames while preserving lineage information.
    
    Args:
        df1: First DataFrame
        df2: Second DataFrame  
        merge_step_id: Step ID for the merge operation
        **merge_kwargs: Additional arguments passed to pd.merge()
    
    Returns:
        Merged DataFrame with combined lineage
    """
    # Perform the merge
    result = pd.merge(df1, df2, **merge_kwargs)
    
    # Combine lineage from both DataFrames
    if "lineage_x" in result.columns and "lineage_y" in result.columns:
        result["lineage"] = result.apply(
            lambda row: combine_lineage_values(
                row.get("lineage_x", ""), 
                row.get("lineage_y", "")
            ), axis=1
        )
        # Drop the temporary lineage columns
        result = result.drop(columns=["lineage_x", "lineage_y"], errors="ignore")
    
    # Add the merge step ID
    result = add_step_id(result, merge_step_id)
    
    return result


def combine_lineage_values(lineage1: str, lineage2: str) -> str:
    """
    Combine two lineage strings, removing duplicates while preserving order.
    
    Args:
        lineage1: First lineage string
        lineage2: Second lineage string
    
    Returns:
        Combined lineage string
    """
    if not lineage1 and not lineage2:
        return ""
    
    if not lineage1:
        return lineage2
    
    if not lineage2:
        return lineage1
    
    # Split both lineages and combine while preserving order
    steps1 = lineage1.split("|") if lineage1 else []
    steps2 = lineage2.split("|") if lineage2 else []
    
    # Use dict to preserve order while removing duplicates (Python 3.7+)
    combined_steps = list(dict.fromkeys(steps1 + steps2))
    
    return "|".join(combined_steps)


def validate_lineage(df: pd.DataFrame, expected_steps: list[str] | None = None) -> bool:
    """
    Validate that all rows have valid lineage information.
    
    Args:
        df: DataFrame to validate
        expected_steps: Optional list of expected step IDs
    
    Returns:
        True if all lineage is valid, False otherwise
    """
    if "lineage" not in df.columns:
        return False
    
    # Check for null or empty lineage
    if df["lineage"].isnull().any() or (df["lineage"] == "").any():
        return False
    
    # If expected steps provided, validate they're all present
    if expected_steps:
        for _, row in df.iterrows():
            lineage_steps = set(row["lineage"].split("|"))
            if not set(expected_steps).issubset(lineage_steps):
                return False
    
    return True


def get_lineage_summary(df: pd.DataFrame) -> dict:
    """
    Get a summary of lineage information in the DataFrame.
    
    Args:
        df: DataFrame to analyze
    
    Returns:
        Dictionary with lineage statistics
    """
    if "lineage" not in df.columns:
        return {"error": "No lineage column found"}
    
    lineage_counts = df["lineage"].value_counts()
    all_steps = set()
    
    for lineage in df["lineage"].dropna():
        all_steps.update(lineage.split("|"))
    
    return {
        "total_rows": len(df),
        "rows_with_lineage": df["lineage"].notna().sum(),
        "unique_lineage_paths": len(lineage_counts),
        "all_steps": sorted(list(all_steps)),
        "lineage_distribution": lineage_counts.to_dict()
    }
