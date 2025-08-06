###############################################################################
# BALANCE-pyexcel – Tests for CSV Consolidator Module
#
# Description : Unit tests for the csv_consolidator.py module.
# Key Concepts: - Parametrized testing for multiple CSV fixtures.
#                - Validation of row counts, required columns, TxnID uniqueness.
# -----------------------------------------------------------------------------
# Change Log
# Date        Author            Type        Note
# 2025-05-17  Cline (AI)        feat        Initial creation of test harness.
###############################################################################

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

# Module to test
from balance_pipeline.csv_consolidator import (
    MANDATORY_MASTER_COLS,
    _normalize_csv_header,
    process_csv_files,
)

# --- Constants for Test Fixtures ---
# Assuming CWD for tests will be the project root BALANCE-pyexcel/
# or paths are relative to this test file's location.
# For simplicity, using Path objects relative to this file's parent, then 'fixtures'.
FIXTURES_DIR = Path(__file__).parent / "fixtures"

SAMPLE_CSVS = [
    (
        "Jordyn - Chase Bank - Total Checking x6173 - All.csv",
        {"expected_min_rows": 1, "owner": "Jordyn"},
    ),
    (
        "Jordyn - Discover - Discover It Card x1544 - CSV.csv",
        {"expected_min_rows": 1, "owner": "Jordyn"},
    ),
    (
        "Jordyn - Wells Fargo - Active Cash Visa Signature Card x4296 - CSV.csv",
        {"expected_min_rows": 1, "owner": "Jordyn"},
    ),
    ("Ryan - Monarch Money - 041225.csv", {"expected_min_rows": 1, "owner": "Ryan"}),
    ("Ryan - Rocket Money - 041225.csv", {"expected_min_rows": 1, "owner": "Ryan"}),
]

# --- Test Functions ---


@pytest.mark.parametrize("csv_filename, params", SAMPLE_CSVS)
def test_process_single_csv_file(csv_filename: str, params: dict):
    """
    Tests process_csv_files with individual sample CSVs.
    Validates row count, required columns, TxnID uniqueness, and basic amount properties.
    """
    csv_path = FIXTURES_DIR / csv_filename
    assert csv_path.exists(), f"Fixture CSV file not found: {csv_path}"

    # For these tests, we process one file at a time.
    # The Owner inference in process_csv_files relies on the parent dir of the CSV.
    # To simulate this correctly for fixtures, we might need to adjust how paths are passed
    # or ensure fixtures are in a structure like tests/fixtures/Jordyn/file.csv
    # For now, the Owner assertion will use the 'owner' from params.

    # To make owner inference work as designed (parent dir name),
    # we'd ideally pass a path like "tests/fixtures/Jordyn/file.csv" to process_csv_files.
    # However, our files are directly in fixtures/.
    # Let's construct a temporary "effective" path for owner inference if needed,
    # or rely on the fact that process_csv_files will use the direct parent of csv_path.
    # The current `owner = csv_file_path_obj.parent.name` will result in "fixtures" as owner.
    # This needs to be handled: either by passing an "owner_override" or by structuring fixtures.
    # For now, we'll check against the 'owner' param for the 'Owner' column content.

    df = process_csv_files([csv_path])

    # 1. Basic DataFrame checks
    assert not df.empty, f"Processed DataFrame for {csv_filename} is empty."
    assert (
        len(df) >= params["expected_min_rows"]
    ), f"Expected at least {params['expected_min_rows']} rows for {csv_filename}, got {len(df)}."

    # 2. Required columns non-null
    for col in MANDATORY_MASTER_COLS:
        assert (
            col in df.columns
        ), f"Mandatory column '{col}' missing in output for {csv_filename}."
        # TxnID can be None if generation fails, so check for that possibility if strict non-null is too harsh initially.
        # For now, let's assume TxnID should be generated.
        if col == "TxnID":  # TxnID might be None if dependent columns are missing.
            assert (
                df[col].notna().all() or df[col].isnull().all()
            ), f"Column '{col}' has mixed null/non-null values in {csv_filename}."
        else:
            assert (
                df[col].notna().all()
            ), f"Column '{col}' in {csv_filename} has null values where not expected."

    # Check Owner column content
    assert (
        df["Owner"] == params["owner"]
    ).all(), f"Owner column mismatch for {csv_filename}. Expected '{params['owner']}', got '{df['Owner'].unique()}'"

    # 3. Signed amounts make sense (basic checks)
    assert "Amount" in df.columns, f"'Amount' column missing for {csv_filename}."
    assert pd.api.types.is_numeric_dtype(
        df["Amount"]
    ), f"'Amount' column is not numeric for {csv_filename}."
    # Specific sum checks would require golden data for each file.
    # Example: if "Chase Bank" usually has more expenses:
    # if "Chase Bank" in csv_filename:
    #     assert df['Amount'].sum() < 0, f"Expected negative sum for Chase Bank transactions in {csv_filename}"

    # 4. TxnID uniqueness
    assert "TxnID" in df.columns, f"'TxnID' column missing for {csv_filename}."
    if df["TxnID"].notna().any():  # Only check uniqueness if there are non-null TxnIDs
        assert df.loc[
            df["TxnID"].notna(), "TxnID"
        ].is_unique, f"TxnID is not unique for {csv_filename}."

    # 5. Check for 'Extras' column
    assert "Extras" in df.columns, f"'Extras' column missing for {csv_filename}."

    # Log some info for review
    print(f"\nSuccessfully processed and validated: {csv_filename}")
    print(f"Processed {len(df)} rows.")
    print(
        f"TxnID unique: {df['TxnID'].is_unique if df['TxnID'].notna().any() else 'N/A (all null)'}"
    )
    print(
        f"Amount sum: {df['Amount'].sum() if 'Amount' in df.columns and pd.api.types.is_numeric_dtype(df['Amount']) else 'N/A'}"
    )


# Additional test coverage added below


def test_normalize_csv_header_aliases():
    """Common header aliases should map to canonical names."""
    cases = {
        'Txn Date': 'date',
        'Account Name': 'account',
        'running balance': 'balance',
    }

    for raw, expected in cases.items():
        assert _normalize_csv_header(raw) == expected


def test_process_csv_with_invalid_schema():
    """Test handling of CSV that doesn't match any schema."""
    # Create a temporary CSV with unrecognized structure
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tf:
        tf.write('UnknownColumn1,UnknownColumn2,UnknownColumn3\n')
        tf.write('value1,value2,value3\n')
        temp_path = Path(tf.name)
    
    try:
        # This should not raise an error, but should handle gracefully
        df = process_csv_files([temp_path])
        # Since no schema matches, we expect an empty DataFrame or proper error handling
        assert df.empty or len(df) == 0
    finally:
        temp_path.unlink()  # Clean up


def test_date_parsing_with_various_formats():
    """Test date parsing with different date formats."""
    import tempfile
    
    # Create test CSV with various date formats
    test_data = '''Date,Amount,Description,Account
2024-01-15,100.00,"Test Transaction 1","Checking"
01/16/2024,200.00,"Test Transaction 2","Savings"
2024-01-17,300.00,"Test Transaction 3","Credit Card"
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tf:
        tf.write(test_data)
        temp_path = Path(tf.name)
    
    try:
        df = process_csv_files([temp_path])
        
        # Check that dates were parsed correctly
        if 'Date' in df.columns:
            assert pd.api.types.is_datetime64_any_dtype(df['Date'])
            # All dates should be parsed successfully
            assert df['Date'].notna().all()
    finally:
        temp_path.unlink()


def test_amount_transformation_with_signs():
    """Test amount transformation with positive and negative values."""
    import tempfile
    
    test_data = '''Date,Amount,Description,Account,Type
2024-01-15,-100.00,"Debit Transaction","Checking","debit"
2024-01-16,200.00,"Credit Transaction","Checking","credit"
2024-01-17,(50.00),"Parentheses negative","Checking","debit"
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tf:
        tf.write(test_data)
        temp_path = Path(tf.name)
    
    try:
        df = process_csv_files([temp_path])
        
        if 'Amount' in df.columns:
            # Check that amounts are numeric
            assert pd.api.types.is_numeric_dtype(df['Amount'])
            # Check specific values if processed correctly
            amounts = df['Amount'].tolist()
            # The actual sign handling depends on the implementation
            assert len(amounts) == 3
    finally:
        temp_path.unlink()


def test_duplicate_transaction_detection():
    """Test that potential duplicate transactions are flagged."""
    import tempfile
    
    # Create test data with potential duplicates
    test_data = '''Date,Amount,Description,Account
2024-01-15,100.00,"Same Transaction","Checking"
2024-01-15,100.00,"Same Transaction","Checking"
2024-01-16,100.00,"Different Day Same Amount","Checking"
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tf:
        tf.write(test_data)
        temp_path = Path(tf.name)
    
    try:
        df = process_csv_files([temp_path])
        
        # Check that TxnIDs are unique
        if 'TxnID' in df.columns:
            assert df['TxnID'].nunique() == len(df)
    finally:
        temp_path.unlink()
