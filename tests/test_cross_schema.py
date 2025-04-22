# tests/test_cross_schema.py
from balance_pipeline.ingest import load_folder, STANDARD_COLS
# If normalize_df is tested here later, uncomment:
# from balance_pipeline.normalize import normalize_df
from pathlib import Path
import pandas as pd
import pytest # Import pytest for using fixtures and skip functionality

# Define the path to the multi-schema sample data directory
# Assumes it's directly inside the main project folder (where pyproject.toml is)
SAMPLE_DATA_MULTI_DIR = Path("sample_data_multi")

# Basic test function to load data using the schema-aware ingest
def test_multi_schema_load():
    """
    Tests that ingest.load_folder can process multiple CSV schemas
    from owner subfolders and produce a DataFrame with expected basic properties.

    Requires properly structured sample data in ./sample_data_multi/
    """
    # Pre-condition check: Ensure sample data directory exists before running test
    if not SAMPLE_DATA_MULTI_DIR.is_dir():
        # Skip this test gracefully if the sample data isn't set up yet
        pytest.skip(f"Sample data directory not found, skipping test: {SAMPLE_DATA_MULTI_DIR}")

    # --- Action: Call the function under test ---
    try:
        # Load data using the schema-aware ingest function
        df = load_folder(SAMPLE_DATA_MULTI_DIR)
    except ValueError as e:
         # If load_folder raises ValueError (e.g., no CSVs found or YAML empty), fail the test clearly
         pytest.fail(f"load_folder raised ValueError during test: {e}")
    except FileNotFoundError as e:
         # If the parent folder itself isn't found
         pytest.fail(f"load_folder raised FileNotFoundError during test: {e}")
    except Exception as e:
        # Catch any other unexpected exception during load
        pytest.fail(f"load_folder raised an unexpected exception during test: {e}")


    # --- Assertions: Check the output DataFrame ---

    # 1. Check that some data was actually loaded (most basic check)
    assert not df.empty, "Loaded DataFrame should not be empty (check sample data and paths)."

    # 2. Check if Owner column contains expected values (case-insensitive check)
    #    This assumes your sample_data_multi has 'jordyn' and 'ryan' subfolders containing valid CSVs.
    expected_owners = {"jordyn", "ryan"}
    # Get unique owners, convert to lowercase, handle potential NA values if any crept in
    actual_owners = set(df["Owner"].dropna().astype(str).str.lower().unique())
    assert expected_owners.issubset(actual_owners), \
           f"Expected owners {expected_owners} not found in 'Owner' column. Found: {actual_owners}"

    # 3. Check that all defined STANDARD_COLS from ingest module are present
    assert all(col in df.columns for col in STANDARD_COLS), \
           f"DataFrame missing one or more standard columns. Expected: {STANDARD_COLS}, Got: {df.columns.tolist()}"

    # 4. Check for unexpected null/NA values in critical columns after ingest
    #    These columns should always have a value after successful ingestion and mapping.
    critical_cols_for_null_check = ["Owner", "Date", "Amount", "Description", "Account"] # Amount/Date NAs should have been dropped by ingest
    for col in critical_cols_for_null_check:
         # Only assert if the column actually exists to avoid KeyError if step 3 failed subtly
         if col in df.columns:
              assert df[col].notna().all(), f"Column '{col}' contains unexpected NaN/NaT values after ingest."

    # 5. Check Amount sign convention (basic check: assumes *some* expenses exist)
    #    Asserts that at least one row has a negative amount, implying outflows are negative.
    #    NOTE: This test WILL FAIL if your sample data only contains deposits/inflows.
    #          Adjust or add more specific tests if needed based on your sample data.
    assert not df.empty and (df["Amount"] < 0).any(), \
           "Expected at least one negative 'Amount' (outflow) based on sign rules, but none found. Check sample data or sign rules."

    # Add more tests here later for specific mappings, data types, edge cases etc.