"""
Unit tests for the master Parquet appending functionality.
"""

import os
import sys
from pathlib import Path

import duckdb
import pandas as pd
import pytest

# Adjust sys.path to allow importing from the 'scripts' directory
# This assumes the test is run from the project root (e.g., via 'poetry run pytest')
# or that PYTHONPATH is configured appropriately.
# The 'BALANCE-pyexcel' directory itself should be in sys.path for 'scripts.process_pdfs' to work.
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

try:
    from scripts.process_pdfs import append_to_master
except ImportError as e:
    # Provide a more informative error if the import fails due to path issues
    pytest.fail(
        f"Failed to import append_to_master from scripts.process_pdfs. "
        f"Ensure 'BALANCE-pyexcel' directory is in PYTHONPATH or sys.path. Error: {e}\n"
        f"Current sys.path: {sys.path}"
    )


# Define the path to the test Parquet file
# This is the actual path the script will use.
# Tests should clean up this file.
PARQUET_FILE_PATH = (
    project_root / "data" / "processed" / "combined_transactions.parquet"
)
MASTER_COLS = [
    "TransDate",
    "PostDate",
    "RawMerchant",
    "Amount",
    "AccountLast4",
    "ReferenceNumber",
    "Owner",
]


@pytest.fixture(scope="function")
def cleanup_parquet_file():
    """Fixture to ensure the Parquet file is removed before and after a test."""
    if PARQUET_FILE_PATH.exists():
        os.remove(PARQUET_FILE_PATH)
    yield  # Test runs here
    if PARQUET_FILE_PATH.exists():
        os.remove(PARQUET_FILE_PATH)
    # Attempt to remove the 'data/processed' directory if it's empty
    try:
        if PARQUET_FILE_PATH.parent.exists() and not any(
            PARQUET_FILE_PATH.parent.iterdir()
        ):
            PARQUET_FILE_PATH.parent.rmdir()
        if PARQUET_FILE_PATH.parent.parent.exists() and not any(
            PARQUET_FILE_PATH.parent.parent.iterdir()
        ):  # data/
            PARQUET_FILE_PATH.parent.parent.rmdir()
    except OSError:
        pass  # Ignore errors if directory is not empty or cannot be removed


def test_append_to_master_parquet(cleanup_parquet_file):
    """
    Tests appending a dummy DataFrame to the master Parquet file.
    Verifies file creation, schema, and basic dtypes.
    """
    # 1. Create a tiny dummy DataFrame
    data = {
        "TransDate": ["01/01/2023", "01/02/2023"],
        "RawMerchant": ["Merchant A", "Merchant B"],
        "Amount": [100.50, -25.75],
        "AccountLast4": ["1234", "5678"],
        # PostDate and ReferenceNumber will be missing to test pd.NA filling
    }
    dummy_df = pd.DataFrame(data)
    # Convert TransDate to datetime to mimic typical input before append_to_master's own conversion
    dummy_df["TransDate"] = pd.to_datetime(dummy_df["TransDate"])

    owner_name = "TestOwner"

    # 2. Call the helper function (append_to_master)
    # append_to_master is imported from scripts.process_pdfs
    append_to_master(dummy_df, owner_name)

    # 3. Assertions
    # 3.1. Parquet file exists
    assert (
        PARQUET_FILE_PATH.exists()
    ), f"Parquet file was not created at {PARQUET_FILE_PATH}"

    # 3.2. Read the Parquet file and check schema and dtypes
    con = None
    try:
        con = duckdb.connect(database=str(PARQUET_FILE_PATH), read_only=True)
        result_df = con.execute("SELECT * FROM master").fetchdf()

        # 3.2.1. Has all 7 columns
        assert (
            len(result_df.columns) == len(MASTER_COLS)
        ), f"Expected {len(MASTER_COLS)} columns, got {len(result_df.columns)}. Columns: {result_df.columns.tolist()}"
        for col in MASTER_COLS:
            assert (
                col in result_df.columns
            ), f"Expected column '{col}' not found in Parquet table."

        # 3.2.2. Correct dtypes (Pandas dtypes after fetching from DuckDB)
        # DuckDB types: TIMESTAMP, VARCHAR, DOUBLE, VARCHAR, VARCHAR, VARCHAR
        # Pandas dtypes: datetime64[ns], object (string), float64, object, object, object

        # TransDate should be datetime
        assert pd.api.types.is_datetime64_any_dtype(
            result_df["TransDate"]
        ), f"TransDate column is not datetime. Dtype: {result_df['TransDate'].dtype}"

        # Amount should be numeric (float64 by default for pandas from DuckDB DOUBLE)
        assert pd.api.types.is_numeric_dtype(
            result_df["Amount"]
        ), f"Amount column is not numeric. Dtype: {result_df['Amount'].dtype}"

        # PostDate should be datetime (even if all NA, it should be coerced)
        # If all values are pd.NA, pandas might make it object. DuckDB will make it TIMESTAMP.
        # When fetched, if all are NaT, it will be datetime64[ns]
        assert pd.api.types.is_datetime64_any_dtype(
            result_df["PostDate"]
        ), f"PostDate column is not datetime. Dtype: {result_df['PostDate'].dtype}"

        # Check Owner column content
        assert (
            result_df["Owner"] == owner_name
        ).all(), "Owner column not correctly populated."

        # Check that missing columns were filled with NA (which become None/NaT in result_df)
        # For PostDate (datetime), it should be NaT
        assert (
            result_df["PostDate"].isna().all()
        ), "PostDate (missing in input) should be all NaT."
        # For ReferenceNumber (object/string), it should be None or NaN (pd.NA becomes float NaN sometimes)
        assert (
            result_df["ReferenceNumber"].isna().all()
        ), "ReferenceNumber (missing in input) should be all NA."

        # Check a second append to ensure INSERT INTO works
        data2 = {
            "TransDate": ["01/03/2023"],
            "RawMerchant": ["Merchant C"],
            "Amount": [50.00],
            "PostDate": ["01/04/2023"],  # Provide PostDate this time
        }
        dummy_df2 = pd.DataFrame(data2)
        dummy_df2["TransDate"] = pd.to_datetime(dummy_df2["TransDate"])
        dummy_df2["PostDate"] = pd.to_datetime(dummy_df2["PostDate"])

        # Close connection before append_to_master writes again
        con.close()
        con = None

        append_to_master(dummy_df2, "TestOwner2")

        con = duckdb.connect(database=str(PARQUET_FILE_PATH), read_only=True)
        result_df_after_append = con.execute("SELECT * FROM master").fetchdf()

        assert len(result_df_after_append) == len(dummy_df) + len(
            dummy_df2
        ), "Number of rows after second append is incorrect."

        # Check owner of new row
        assert result_df_after_append.iloc[-1]["Owner"] == "TestOwner2"
        # Check PostDate of new row (should not be NaT)
        assert pd.notna(result_df_after_append.iloc[-1]["PostDate"])

    finally:
        if con:
            con.close()


# Example of how to run this test:
# Ensure DuckDB and Pandas are installed in your environment.
# From the root of the BALANCE-pyexcel project:
# poetry run pytest tests/test_master_parquet.py
