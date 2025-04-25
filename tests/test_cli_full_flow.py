"""
End-to-end integration test for the BALANCE-pyexcel CLI.

Checks the following workflow:
- Running the CLI on sample CSV data.
- Targeting a macro-enabled workbook (.xlsm).
- Verifying the CLI completes successfully.
- Verifying the temporary XLSX file (.temp.xlsx) is created as expected.
- Verifying the lock file (.lock) is cleaned up after execution.
- Verifying the temporary XLSX contains the expected sheets ('Transactions', 'Queue_Review').
- Verifying the 'Transactions' sheet in the temporary file contains data rows.
"""
import subprocess
import shutil
import pathlib
import sys
import pytest # Import pytest for skipping if dependencies missing
import time # Import time for potential waits

# --- Test Configuration ---

# Define project root relative to this test file's location (tests/test_cli_...)
# Assuming this file is in tests/, ROOT will be the parent directory.
ROOT = pathlib.Path(__file__).resolve().parents[1]

# Define the command prefix for running poetry commands
# Handles potential differences in how poetry is invoked on different OS/setups
POETRY_CMD = ["poetry"] 
# Note: Adjust POETRY_CMD if 'poetry' isn't directly on PATH 
# e.g., ["python", "-m", "poetry"] or provide full path

# Define the base CLI command list
CLI_BASE_COMMAND = POETRY_CMD + ["run", "balance-pyexcel"]

# Define relative paths to sample data and the template workbook within the project
SAMPLE_DATA_FOLDER = ROOT / "sample_data_multi"
TEMPLATE_XLSM_FILE = ROOT / "BALANCE-template.xlsm" # The .xlsm with VBA macros

# --- Test Function ---

# Mark test to skip if pandas or openpyxl are not installed in the environment
# This prevents test failures due to missing optional dependencies needed just for the test
@pytest.mark.skipif(
    not shutil.which(POETRY_CMD[0]) or 
    subprocess.run(POETRY_CMD + ["show", "pandas"], capture_output=True, text=True, cwd=ROOT).returncode != 0 or
    subprocess.run(POETRY_CMD + ["show", "openpyxl"], capture_output=True, text=True, cwd=ROOT).returncode != 0,
    reason="Requires poetry, pandas, and openpyxl to be installed in the environment"
)
def test_xlsm_roundtrip(tmp_path):
    """
    Tests the full CLI workflow using an XLSM template and sample data.
    Verifies temporary file creation, lock file cleanup, and basic output structure.

    Args:
        tmp_path (pathlib.Path): Pytest fixture providing a temporary directory unique to this test run.
    """
    print(f"\n--- Starting test_xlsm_roundtrip in temporary directory: {tmp_path} ---")
    
    # ---- Arrange: Set up the test environment ----
    
    # Define paths for files used within the temporary directory
    test_xlsm = tmp_path / "BALANCE-test-runtime.xlsm" # Workbook copy for the test run
    expected_temp_xlsx = test_xlsm.with_suffix(".temp.xlsx") # Expected temp file
    expected_lock_file = test_xlsm.with_suffix(".lock") # Expected lock file

    # Verify necessary source files/folders exist before proceeding
    assert SAMPLE_DATA_FOLDER.exists(), f"Sample data folder not found: {SAMPLE_DATA_FOLDER}"
    assert TEMPLATE_XLSM_FILE.exists(), f"Template XLSM file not found: {TEMPLATE_XLSM_FILE}"
    
    # Copy the master XLSM template into the temporary directory for the test run
    print(f"Copying template {TEMPLATE_XLSM_FILE} to {test_xlsm}")
    shutil.copy(TEMPLATE_XLSM_FILE, test_xlsm)
    assert test_xlsm.exists(), "Failed to copy template XLSM to temporary directory"

    # Ensure expected output/lock files don't exist before running the CLI
    if expected_temp_xlsx.exists(): expected_temp_xlsx.unlink()
    if expected_lock_file.exists(): expected_lock_file.unlink()
    print(f"Ensured temporary file does not exist: {expected_temp_xlsx}")
    print(f"Ensured lock file does not exist: {expected_lock_file}")
    
    # Construct the full CLI command to execute
    command_to_run = CLI_BASE_COMMAND + [
        str(SAMPLE_DATA_FOLDER), # Input CSV folder path
        str(test_xlsm),          # Output/Target XLSM path
        "--verbose"              # Enable detailed logging output
    ]
    
    # ---- Act: Run the CLI command ----
    print(f"Running CLI command: {' '.join(command_to_run)}")
    
    # Execute the command using subprocess.run
    # - capture_output=True: Captures stdout and stderr
    # - text=True: Decodes stdout/stderr as text
    # - check=True: Raises CalledProcessError if the command returns a non-zero exit code (i.e., fails)
    # - cwd=ROOT: Ensures the command runs from the project root directory, important for poetry to find the virtual environment
    try:
        result = subprocess.run(
            command_to_run,
            capture_output=True, 
            text=True, 
            check=True, 
            cwd=ROOT,
            timeout=60 # Add a timeout (e.g., 60 seconds) to prevent hangs
        )
    except subprocess.CalledProcessError as e:
        # If check=True causes an error, print details before failing
        print("\n--- CLI Execution Failed ---")
        print(f"Return Code: {e.returncode}")
        print("\n--- STDOUT ---")
        print(e.stdout)
        print("\n--- STDERR ---")
        print(e.stderr)
        pytest.fail(f"CLI command failed with return code {e.returncode}")
    except subprocess.TimeoutExpired as e:
        print("\n--- CLI Execution Timed Out ---")
        print(e.stdout)
        print(e.stderr)
        pytest.fail("CLI command timed out")


    # Print stdout/stderr for debugging purposes, even on success
    print("\n--- CLI STDOUT ---")
    print(result.stdout)
    print("--- END CLI STDOUT ---")
    if result.stderr:
        print("\n--- CLI STDERR ---")
        print(result.stderr)
        print("--- END CLI STDERR ---")

    # ---- Assert: Verify the results ----
    
    # 1. Check for the success message in the CLI's standard output
    print("Asserting successful completion message in stdout...")
    assert "✅ Process completed successfully" in result.stdout, "Success message not found in stdout"

    # 2. Check that the temporary XLSX file was created (expected behavior for .xlsm input)
    print(f"Asserting temporary file exists: {expected_temp_xlsx}")
    assert expected_temp_xlsx.exists(), f"Temporary file '{expected_temp_xlsx.name}' was not created"

    # 3. Check that the lock file was automatically removed after execution
    print(f"Asserting lock file does not exist: {expected_lock_file}")
    # Add a small delay in case file system operations are slow
    time.sleep(0.5) 
    assert not expected_lock_file.exists(), f"Lock file '{expected_lock_file.name}' was not removed"

    # 4. Perform basic content validation on the temporary XLSX file
    print(f"Performing content validation on temporary file: {expected_temp_xlsx}")
    try:
        # Use pandas (requires pandas and openpyxl installed in the test environment)
        # to read the temporary Excel file and check its structure/content.
        import pandas as pd 
        with pd.ExcelFile(expected_temp_xlsx) as xls:
            print(f"Sheets found in temp file: {xls.sheet_names}")
            # Check for essential sheets
            assert "Transactions" in xls.sheet_names, "'Transactions' sheet missing in temp file"
            assert "Queue_Review" in xls.sheet_names, "'Queue_Review' sheet missing in temp file"
            
            # Check if 'Transactions' sheet has data rows
            transactions_df = pd.read_excel(xls, sheet_name="Transactions")
            row_count = transactions_df.shape[0]
            print(f"'Transactions' sheet has {row_count} rows.")
            assert row_count > 0, "'Transactions' sheet has no data rows" 
            # Note: You could add a more specific check, e.g., assert row_count == 40 
            # if you know exactly how many rows your sample data should produce.

            # Check if 'Queue_Review' sheet has the correct columns
            queue_df = pd.read_excel(xls, sheet_name="Queue_Review")
            expected_queue_cols = ["TxnID", "Set Shared? (Y/N/S for Split)", "Set Split % (0-100)", "Date", "Description", "Amount", "Owner"]
            print(f"Queue_Review columns found: {queue_df.columns.tolist()}")
            assert all(col in queue_df.columns for col in expected_queue_cols), "Queue_Review sheet missing expected columns"

    except ImportError:
         pytest.skip("Skipping content validation because 'pandas' or 'openpyxl' is not installed.")
    except Exception as e:
        pytest.fail(f"Error reading or validating temporary Excel file {expected_temp_xlsx}: {e}")

    print("--- test_xlsm_roundtrip PASSED ---")

