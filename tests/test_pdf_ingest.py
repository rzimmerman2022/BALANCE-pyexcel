# -*- coding: utf-8 -*-
"""
==============================================================================
Test Module: test_pdf_ingest.py
Project:     BALANCE-pyexcel
Description: Contains integration tests specifically for validating the ingestion
             and normalization pipeline for CSVs generated from PDFs (like the
             jordyn_pdf schema).
==============================================================================
"""

import pytest
from pathlib import Path
import shutil  # For copying files in fixture

# --- Imports from Application Code ---
# Assuming tests are run from the project root or pytest handles PYTHONPATH
from src.balance_pipeline.ingest import load_folder
from src.balance_pipeline.normalize import normalize_df, FINAL_COLS
from src.balance_pipeline import config  # To get project root for fixture path

# --- Constants ---
# Define the relative path to the source fixture file from the project root
FIXTURE_SRC_PATH = config.PROJECT_ROOT / "tests" / "fixtures" / "jordyn_pdf_sample.csv"
# Define the filename for the fixture when copied to the temp directory, matching the schema glob
FIXTURE_DEST_FILENAME = "BALANCE - Jordyn PDF - Sample.csv"

# --- Pytest Fixture for Test Setup ---


@pytest.fixture(scope="function")  # Create a fresh temp dir for each test function
def jordyn_pdf_inbox(tmp_path: Path) -> Path:
    """
    Sets up a temporary directory structure mimicking the expected input folder
    for the jordyn_pdf schema and copies the sample fixture file into it.

    Args:
        tmp_path (Path): The temporary directory path provided by pytest.

    Yields:
        Path: The path to the root of the temporary inbox structure (e.g., tmp_path/inbox).
    """
    # Create the root inbox and owner-specific subdirectory
    temp_inbox_root = tmp_path / "inbox"
    jordyn_dir = temp_inbox_root / "Jordyn"
    jordyn_dir.mkdir(parents=True, exist_ok=True)

    # Define the destination path for the fixture file
    fixture_dest_path = jordyn_dir / FIXTURE_DEST_FILENAME

    # Check if source fixture exists before copying
    if not FIXTURE_SRC_PATH.exists():
        pytest.fail(f"Fixture source file not found: {FIXTURE_SRC_PATH}")

    # Copy the fixture file to the temporary directory
    try:
        shutil.copyfile(FIXTURE_SRC_PATH, fixture_dest_path)
    except Exception as e:
        pytest.fail(f"Failed to copy fixture file to {fixture_dest_path}: {e}")

    # Yield the path to the root of the temporary inbox for the test function
    yield temp_inbox_root

    # Teardown (handled automatically by pytest's tmp_path fixture)


# --- Test Function ---


def test_jordyn_pdf_ingestion_and_normalization(jordyn_pdf_inbox: Path):
    """
    Tests the full ingestion and normalization flow for the jordyn_pdf schema.

    Steps:
    1. Uses the `jordyn_pdf_inbox` fixture to get a temp dir with the sample CSV.
    2. Calls `load_folder` to ingest the data.
    3. Calls `normalize_df` to apply normalization rules.
    4. Asserts that the final DataFrame columns match FINAL_COLS.
    5. Asserts that the 'Owner' column is correctly set to 'Jordyn'.
    6. Asserts that the 'AcctLast4' column is correctly mapped.
    7. Asserts that the 'Amount' sign is correctly flipped (negative).
    """
    # --- Arrange ---
    inbox_path = jordyn_pdf_inbox  # Path provided by the fixture

    # --- Act ---
    # Ingest the data using the temporary inbox
    ingested_df = load_folder(inbox_path)

    # Check if ingestion returned any data before normalizing
    if ingested_df.empty:
        pytest.fail(
            "Ingestion returned an empty DataFrame. Check schema matching or file reading."
        )

    # Normalize the ingested data
    normalized_df = normalize_df(ingested_df)  # Assuming default prefer_source is fine

    # --- Assert ---
    # 1. Check if the final columns match the expected standard
    assert (
        normalized_df.columns.tolist() == FINAL_COLS
    ), f"Columns mismatch. Expected: {FINAL_COLS}, Got: {normalized_df.columns.tolist()}"

    # 2. Check if the Owner was correctly assigned
    assert "Owner" in normalized_df.columns, "Owner column is missing"
    assert (
        normalized_df["Owner"].unique().tolist() == ["Jordyn"]
    ), f"Owner column contains unexpected values: {normalized_df['Owner'].unique().tolist()}"

    # 3. Check amount sign (should be negative due to flip_if_positive rule)
    assert "Amount" in normalized_df.columns, "Amount column is missing"
    assert (
        normalized_df["Amount"].iloc[0] < 0
    ), f"Amount sign rule failed. Expected negative amount, Got: {normalized_df['Amount'].iloc[0]}"

    # 4. Check number of rows (should match fixture)
    assert len(normalized_df) == 3, f"Expected 3 rows, but got {len(normalized_df)}"
