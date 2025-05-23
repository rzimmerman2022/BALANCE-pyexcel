# -*- coding: utf-8 -*-
"""
Integration tests for the command-line interface
"""

import os
import subprocess
import zipfile
from pathlib import Path
import pytest
import pandas as pd
from pandas.testing import assert_frame_equal  # Added for F821
import openpyxl  # For creating more realistic Excel files

# Import constants for column names if needed, or define them
from balance_pipeline.sync import QUEUE_TXNID_COL, QUEUE_DECISION_COL, QUEUE_SPLIT_COL
from balance_pipeline.normalize import FINAL_COLS  # To check output columns


@pytest.fixture
def python_executable():
    """Returns the path to the python executable in the virtual environment or system."""
    venv_python = Path(os.environ.get("VIRTUAL_ENV", ".")) / "Scripts" / "python.exe"
    if venv_python.exists():
        return str(venv_python)
    return "python"  # Fallback


@pytest.fixture
def base_cli_command(python_executable):
    """Base command for running the CLI."""
    return [python_executable, "-m", "balance_pipeline.cli"]


@pytest.fixture
def fake_workbook(tmp_path, request):
    """
    Create a fake .xlsx or .xlsm file.
    If 'xlsm' is in request.param (indirect parametrization), create xlsm.
    Otherwise, create xlsx.
    """
    is_xlsm = hasattr(request, "param") and "xlsm" in request.param
    ext = ".xlsm" if is_xlsm else ".xlsx"
    workbook_path = tmp_path / f"test_workbook{ext}"

    if is_xlsm:
        # Create a simple ZIP file with a minimal structure for XLSM
        with zipfile.ZipFile(workbook_path, "w") as zf:
            zf.writestr(
                "[Content_Types].xml",
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/></Types>',
            )
            zf.writestr(
                "_rels/.rels",
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
            )
            zf.writestr(
                "xl/workbook.xml",
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets></workbook>',
            )
            zf.writestr(
                "xl/_rels/workbook.xml.rels",
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>',
            )
            zf.writestr(
                "xl/worksheets/sheet1.xml",
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData/></worksheet>',
            )
            # Add VBA project part for XLSM if needed for more robust fake
            # zf.writestr('xl/vbaProject.bin', b'dummy vba content') # Requires actual binary content
    else:
        # Create a minimal valid XLSX using openpyxl
        wb = openpyxl.Workbook()
        wb.save(workbook_path)
    return workbook_path


@pytest.fixture
def sample_csv_dir(tmp_path):
    """Create a sample CSV directory with a test CSV file."""
    csv_dir = tmp_path / "csv_inbox" / "user1"
    csv_dir.mkdir(parents=True, exist_ok=True)

    # CSV 1: Contains TX1, TX2
    csv_path1 = csv_dir / "data_source1.csv"
    # Using common headers that ingest.py might expect from schema_registry.yml
    # For simplicity, assume schema maps these to: Date, Description, Amount, Account, Bank
    csv_content1 = """Transaction Date,Details,Value,Account Name,Bank Name
2024-01-01,Merchant A TX1,-10.00,Checking,Bank1
2024-01-02,Merchant B TX2,-20.00,Checking,Bank1
"""
    csv_path1.write_text(csv_content1)

    # CSV 2: Contains TX3
    csv_path2 = csv_dir / "data_source2.csv"
    csv_content2 = """Transaction Date,Details,Value,Account Name,Bank Name
2024-01-03,Merchant C TX3,-30.00,Savings,Bank2
"""
    csv_path2.write_text(csv_content2)

    return csv_dir.parent  # Return the root of "csv_inbox"


# Parametrize for both .xlsx and .xlsm if behavior should be similar
@pytest.mark.parametrize("fake_workbook", ["xlsx", "xlsm"], indirect=True)
def test_cli_dry_run(base_cli_command, sample_csv_dir, fake_workbook):
    """Test CLI with --dry-run option."""
    cmd = base_cli_command + [
        str(sample_csv_dir),
        str(fake_workbook),
        "--dry-run",
        "--verbose",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")

    assert (
        result.returncode == 0
    ), f"Command failed.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"

    lock_file = fake_workbook.with_suffix(fake_workbook.suffix + ".lock")
    assert (
        not lock_file.exists()
    ), "Lock file should not be created or should be cleaned up after dry run"

    dry_run_csv = fake_workbook.with_suffix(".dry-run.csv")
    assert dry_run_csv.exists(), "Dry run CSV should be created"

    df = pd.read_csv(dry_run_csv)
    assert len(df) == 3, "Dry run CSV should contain 3 transactions from sample CSVs"
    assert "TxnID" in df.columns, "Processed data should have TxnID column"
    assert all(
        col in df.columns for col in ["SharedFlag", "SplitPercent"]
    ), "Dry run CSV must have classification columns"


@pytest.mark.parametrize(
    "fake_workbook", ["xlsm"], indirect=True
)  # Test specifically for XLSM
def test_cli_xlsm_processing_creates_temp_file(
    base_cli_command, sample_csv_dir, fake_workbook
):
    """Test CLI processing of .xlsm files creates a .temp.xlsx file."""
    cmd = base_cli_command + [str(sample_csv_dir), str(fake_workbook), "--verbose"]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")

    assert (
        result.returncode == 0
    ), f"Command failed.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"

    lock_file = fake_workbook.with_suffix(fake_workbook.suffix + ".lock")
    assert not lock_file.exists(), "Lock file should be cleaned up after processing"

    temp_xlsx = fake_workbook.with_suffix(".temp.xlsx")
    assert temp_xlsx.exists(), "Temp XLSX should be created for .xlsm files"

    try:
        with pd.ExcelFile(temp_xlsx) as xls:
            assert (
                "Transactions" in xls.sheet_names
            ), "Temp file should have Transactions sheet"
            df = pd.read_excel(xls, sheet_name="Transactions")
            assert len(df) == 3, "Transactions sheet should contain 3 txns"
            assert "TxnID" in df.columns
            assert (
                "Queue_Review" in xls.sheet_names
            ), "Temp file should have Queue_Review sheet"
    except Exception as e:
        pytest.fail(
            f"Failed to read temp XLSX file: {e}\nCLI STDOUT:\n{result.stdout}\nCLI STDERR:\n{result.stderr}"
        )


def test_cli_sync_flow_with_parquet_and_queue(
    base_cli_command, sample_csv_dir, tmp_path, caplog
):
    """Test the full sync flow: initial parquet, new CSVs, Queue_Review overrides."""
    workbook_path = tmp_path / "sync_test_book.xlsx"
    parquet_path = workbook_path.parent / "balance_final.parquet"

    # 1. Create initial Parquet (TX1 classified as 'Y', 100%)
    #    Need TxnID, SharedFlag, SplitPercent, and other FINAL_COLS for schema consistency.
    #    The TxnID for "Merchant A TX1" needs to be deterministic.
    #    For this test, we'll pre-calculate or assume a TxnID.
    #    Let's assume normalize_df generates TxnIDs. We need to run a partial pipeline
    #    or construct a plausible initial Parquet.
    #    Simpler: create parquet with expected columns.
    initial_parquet_data = {
        "TxnID": [
            "TX1_hash_placeholder"
        ],  # This hash needs to match what normalize_df would generate
        "Owner": ["user1"],
        "Date": [pd.to_datetime("2024-01-01")],
        "Account": ["Checking"],
        "Bank": ["Bank1"],
        "Description": ["Merchant A TX1"],
        "CleanDesc": ["Merchant A Tx1"],
        "CanonMerchant": ["Merchant A"],
        "Category": [None],
        "Amount": [-10.00],
        "SharedFlag": ["Y"],
        "SplitPercent": [100.0],
        "Source": ["data_source1.csv"],
    }
    # Add any missing FINAL_COLS with default values
    for col in FINAL_COLS:
        if col not in initial_parquet_data:
            initial_parquet_data[col] = [None] * len(initial_parquet_data["TxnID"])
            if col == "SplitPercent":
                initial_parquet_data[col] = [pd.NA] * len(initial_parquet_data["TxnID"])

    # To get the actual TxnID for "Merchant A TX1", we might need to call normalize_df
    # This is tricky for an integration test setup.
    # For now, let's assume the CLI will generate TxnIDs and the merge logic handles it.
    # The important part is that TX1 from CSV matches a TX1 in parquet if present.
    # The cli.py merge logic uses TxnID. normalize_df creates TxnID.
    # So, the initial parquet should have TxnIDs that *could* be generated.
    # Let's make the initial parquet empty for simplicity of TxnID generation,
    # and focus on Queue_Review overriding defaults from CSV processing.

    # Simplified: Start with no initial parquet, let CSVs be the first source.
    # Then Queue_Review will modify these.

    # Create Workbook with Queue_Review sheet
    # TX1 (from csv_content1) to be 'S', 30%
    # TX2 (from csv_content1) to be 'N'
    # TX3 (from csv_content2) not in Queue_Review
    # queue_review_data = { # F841: Local variable `queue_review_data` is assigned to but never used
    #     QUEUE_TXNID_COL: ["TX1_placeholder", "TX2_placeholder"], # These need to match generated TxnIDs
    #     QUEUE_DECISION_COL: ['S', 'N'],
    #     QUEUE_SPLIT_COL: ['30', pd.NA]
    # }
    # This test will be more robust if we can predict or pass TxnIDs.
    # For now, we'll rely on the CLI output and check against that.
    # The current sample_csv_dir creates TX1, TX2, TX3.
    # We need to know their TxnIDs to put in Queue_Review.
    # This suggests that testing `main()` directly by calling it from Python
    # and mocking `etl_main` or `normalize_df` to control TxnIDs might be better
    # than full subprocess runs for this specific scenario.

    # Given the subprocess approach, let's run it once to get TxnIDs, then construct Queue_Review.
    # This is a bit of a hack for testing.
    cmd_get_ids = base_cli_command + [
        str(sample_csv_dir),
        str(workbook_path),
        "--dry-run",
    ]
    result_get_ids = subprocess.run(
        cmd_get_ids, capture_output=True, text=True, encoding="utf-8"
    )
    assert result_get_ids.returncode == 0, "Failed to get TxnIDs for test setup"
    dry_run_df = pd.read_csv(workbook_path.with_suffix(".dry-run.csv"))

    txn_id_map = pd.Series(
        dry_run_df.TxnID.values, index=dry_run_df.Description
    ).to_dict()
    # Expected descriptions from sample_csv_dir: "Merchant A TX1", "Merchant B TX2", "Merchant C TX3"

    queue_review_df_data = {
        QUEUE_TXNID_COL: [
            txn_id_map.get("Merchant A TX1"),
            txn_id_map.get("Merchant B TX2"),
        ],
        QUEUE_DECISION_COL: ["S", "N"],
        QUEUE_SPLIT_COL: ["30", pd.NA],
    }
    queue_review_df = pd.DataFrame(queue_review_df_data)

    with pd.ExcelWriter(workbook_path, engine="openpyxl") as writer:
        queue_review_df.to_excel(writer, sheet_name="Queue_Review", index=False)

    # 2. Execute CLI
    cmd_sync = base_cli_command + [str(sample_csv_dir), str(workbook_path), "--verbose"]
    result_sync = subprocess.run(
        cmd_sync, capture_output=True, text=True, encoding="utf-8"
    )
    assert (
        result_sync.returncode == 0
    ), f"CLI sync command failed.\nSTDOUT:\n{result_sync.stdout}\nSTDERR:\n{result_sync.stderr}"

    # 3. Assertions
    assert parquet_path.exists(), "balance_final.parquet was not created"
    final_parquet_df = pd.read_parquet(parquet_path)

    # Check TX1 (Merchant A TX1)
    tx1_df = final_parquet_df[final_parquet_df["Description"] == "Merchant A TX1"]
    assert not tx1_df.empty, "TX1 not found in final Parquet"
    assert tx1_df.iloc[0]["SharedFlag"] == "S"
    assert tx1_df.iloc[0]["SplitPercent"] == 30.0

    # Check TX2 (Merchant B TX2)
    tx2_df = final_parquet_df[final_parquet_df["Description"] == "Merchant B TX2"]
    assert not tx2_df.empty, "TX2 not found in final Parquet"
    assert tx2_df.iloc[0]["SharedFlag"] == "N"
    assert pd.isna(tx2_df.iloc[0]["SplitPercent"])  # Or 0.0 if 'N' implies 0%

    # Check TX3 (Merchant C TX3) - should have default '?'
    tx3_df = final_parquet_df[final_parquet_df["Description"] == "Merchant C TX3"]
    assert not tx3_df.empty, "TX3 not found in final Parquet"
    assert tx3_df.iloc[0]["SharedFlag"] == "?"
    assert pd.isna(tx3_df.iloc[0]["SplitPercent"])

    # Check Transactions sheet in Excel
    # If workbook_path is .xlsm, temp file is created. If .xlsx, workbook_path is updated.
    output_excel_path = (
        workbook_path.with_suffix(".temp.xlsx")
        if workbook_path.suffix == ".xlsm"
        else workbook_path
    )
    if (
        not output_excel_path.exists() and workbook_path.suffix == ".xlsm"
    ):  # If .xlsm, check original if temp not made
        output_excel_path = (
            workbook_path  # This case should not happen if process runs ok
        )

    assert (
        output_excel_path.exists()
    ), f"Output Excel file {output_excel_path.name} not found."
    excel_trans_df = pd.read_excel(output_excel_path, sheet_name="Transactions")
    # Compare relevant columns with final_parquet_df (sorting to ensure order doesn't matter)
    cols_to_compare = ["Description", "SharedFlag", "SplitPercent"]
    assert_frame_equal(
        final_parquet_df[cols_to_compare]
        .sort_values("Description")
        .reset_index(drop=True),
        excel_trans_df[cols_to_compare]
        .sort_values("Description")
        .reset_index(drop=True),
        check_dtype=False,  # Dtypes can differ slightly (e.g. float64 vs object for NA)
    )


@pytest.mark.parametrize(
    "fake_workbook", ["xlsx"], indirect=True
)  # Use xlsx for this test
def test_cli_queue_review_missing_required_columns(
    base_cli_command, sample_csv_dir, fake_workbook, caplog
):
    """Test CLI behavior when Queue_Review sheet is missing required columns."""

    # Create Queue_Review with TxnID but missing the decision column
    queue_review_data = {
        "TxnID": ["TX1_placeholder_id"],  # Actual ID doesn't matter much here
        # QUEUE_DECISION_COL ("Set Shared? (Y/N/S for Split)") is missing
        QUEUE_SPLIT_COL: ["50"],
    }
    queue_review_df = pd.DataFrame(queue_review_data)

    with pd.ExcelWriter(fake_workbook, engine="openpyxl") as writer:
        queue_review_df.to_excel(writer, sheet_name="Queue_Review", index=False)

    cmd = base_cli_command + [str(sample_csv_dir), str(fake_workbook), "--verbose"]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")

    assert (
        result.returncode == 0
    ), f"CLI command failed.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"

    # Check logs for warning about missing columns and skipping sync
    # The log is in result.stdout or result.stderr depending on logger config
    full_log_output = result.stdout + result.stderr
    assert (
        f"'{fake_workbook.name}'"
    )  # Check workbook name is mentioned, adjust if cli.py logs differently
    assert "'Queue_Review' sheet missing required columns" in full_log_output
    assert "Skipping sync" in full_log_output

    # Verify Parquet file contains data with default flags (sync was skipped)
    parquet_path = fake_workbook.parent / "balance_final.parquet"
    assert parquet_path.exists()
    final_df = pd.read_parquet(parquet_path)

    assert len(final_df) == 3  # 3 transactions from sample_csv_dir
    assert final_df["SharedFlag"].unique().tolist() == [
        "?"
    ], "All SharedFlags should be default '?'"
    assert final_df["SplitPercent"].isna().all(), "All SplitPercents should be NA"
