# -*- coding: utf-8 -*-
"""
==============================================================================
Module: test_parquet_selective_load.py
Project: BALANCE-pyexcel
Description: Unit tests for verifying memory reduction from selective Parquet column loading.
==============================================================================
"""

import pytest
import pandas as pd
from pathlib import Path

# Assuming cli.py and its Parquet reading logic are the target.
# We are testing the effectiveness of pd.read_parquet(columns=[...])


def create_sample_parquet(file_path: Path, num_rows: int = 1000) -> pd.DataFrame:
    """Creates a sample Parquet file with diverse data types and more columns than needed."""
    data = {
        "TxnID": [f"id_{i}" for i in range(num_rows)],
        "SharedFlag": ["Y", "N", "S", "?"] * (num_rows // 4) + ["Y"] * (num_rows % 4),
        "SplitPercent": [float(i % 101) for i in range(num_rows)],
        "Amount": [float(i * 10.5) for i in range(num_rows)],
        "Description": [
            f"Transaction description {i} with extra details" for i in range(num_rows)
        ],
        "Date": pd.to_datetime([f"2023-01-{ (i % 28) + 1 }" for i in range(num_rows)]),
        "Category": [f"Category_{i % 10}" for i in range(num_rows)],
        "Merchant": [f"Merchant Name {i % 50}" for i in range(num_rows)],
        "Account": [f"Account_{i % 5}" for i in range(num_rows)],
        "Notes": [
            f"Some notes for transaction {i}, could be lengthy." * 5
            for i in range(num_rows)
        ],
    }
    df = pd.DataFrame(data)
    # Ensure data types are representative
    df["SplitPercent"] = df["SplitPercent"].astype(
        "float64"
    )  # Allow NA if needed, though not here
    df["Amount"] = df["Amount"].astype("float64")
    df["Date"] = pd.to_datetime(df["Date"])

    # Ensure string columns are actual strings, not objects if possible, for memory calculation
    for col in [
        "TxnID",
        "SharedFlag",
        "Description",
        "Category",
        "Merchant",
        "Account",
        "Notes",
    ]:
        df[col] = df[col].astype(pd.StringDtype())

    df.to_parquet(file_path, engine="pyarrow", index=False)
    return df


def test_selective_column_load_memory_reduction(tmp_path):
    """
    Tests that reading only specified columns from Parquet results in lower memory usage.
    """
    parquet_file = tmp_path / "sample_data.parquet"
    original_df = create_sample_parquet(
        parquet_file, num_rows=10000
    )  # Use a decent number of rows

    # 1. Read all columns
    df_full_load = pd.read_parquet(parquet_file)
    memory_full_load = df_full_load.memory_usage(deep=True).sum()

    # 2. Read only specified columns (as done in cli.py)
    columns_to_load_selectively = ["TxnID", "SharedFlag", "SplitPercent"]
    df_selective_load = pd.read_parquet(
        parquet_file, columns=columns_to_load_selectively
    )
    memory_selective_load = df_selective_load.memory_usage(deep=True).sum()

    # Assertions
    # Check that columns are correctly selected
    assert list(df_selective_load.columns) == columns_to_load_selectively
    assert all(
        col in df_full_load.columns for col in columns_to_load_selectively
    )  # Sanity check

    # Check that memory usage is reduced
    # The exact percentage can vary based on data, string content, etc.
    # A simple less-than check is robust.
    # For a more specific check like "> 50% reduction", it might be flaky.
    # Let's assert it's significantly less, e.g., less than half.
    # (memory_full_load / memory_selective_load) should be > some_factor

    print(f"Memory - Full Load: {memory_full_load} bytes")
    print(f"Memory - Selective Load: {memory_selective_load} bytes")

    assert (
        memory_selective_load < memory_full_load
    ), "Selective load should use less memory than full load."

    # Optional: More specific memory reduction assertion (can be sensitive to data)
    # For example, assert that selective load is less than 50% of full load memory.
    # This depends heavily on the relative size of the selected columns vs. others.
    # Given "Notes" and "Description" are large string columns, this should hold.
    assert (
        memory_selective_load < (memory_full_load * 0.5)
    ), f"Selective load memory ({memory_selective_load}) is not less than 50% of full load memory ({memory_full_load})."

    # Verify dtypes are preserved for loaded columns
    for col in columns_to_load_selectively:
        # Parquet read might change StringDtype to object if not careful,
        # but pandas usually handles this well.
        # We compare based on the original_df's dtypes for the selected columns.
        assert pd.api.types.is_dtype_equal(
            df_selective_load[col].dtype, original_df[col].dtype
        ), f"Dtype mismatch for column '{col}'. Selective: {df_selective_load[col].dtype}, Original: {original_df[col].dtype}"


def test_selective_load_handles_missing_columns_gracefully(tmp_path):
    """
    Tests how pd.read_parquet(columns=...) handles requests for columns not in the Parquet file.
    It should raise a KeyError or similar, which cli.py handles.
    """
    parquet_file = tmp_path / "sample_data_minimal.parquet"
    minimal_data = {
        "TxnID": ["id_1", "id_2"],
        # "SharedFlag" is missing
        "SplitPercent": [50.0, 25.0],
    }
    df_minimal = pd.DataFrame(minimal_data)
    df_minimal["TxnID"] = df_minimal["TxnID"].astype(pd.StringDtype())
    df_minimal.to_parquet(parquet_file, engine="pyarrow", index=False)

    columns_to_try_load = [
        "TxnID",
        "SharedFlag",
        "SplitPercent",
    ]  # "SharedFlag" is missing

    # PyArrow can raise ArrowInvalid if a requested column is not in the Parquet file's schema.
    # Pandas might sometimes wrap this as a KeyError. We'll catch the more specific one if pyarrow is used.
    import pyarrow  # Import for the exception type

    with pytest.raises((KeyError, pyarrow.lib.ArrowInvalid)) as excinfo:
        pd.read_parquet(parquet_file, columns=columns_to_try_load)

    # Check that the error message mentions the missing column
    # The exact error message can vary. Pyarrow might raise an ArrowInvalid error
    # that pandas translates or wraps.
    # A common pandas behavior is KeyError for missing columns in `columns` list.
    assert (
        "SharedFlag" in str(excinfo.value).replace("'", "").replace('"', "")
    ), f"Expected 'SharedFlag' to be mentioned in the KeyError, got: {str(excinfo.value)}"
    # Example error: "Column 'SharedFlag' not found in schema" or "['SharedFlag'] not in columns"
