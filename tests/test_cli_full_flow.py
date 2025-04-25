# -*- coding: utf-8 -*-
"""
Integration tests for the full CLI workflow including Excel workbook interaction
"""
import os
import subprocess
import tempfile
import zipfile
from pathlib import Path
import shutil
import pytest
import pandas as pd


@pytest.fixture
def fake_xlsm(tmp_path):
    """
    Create a fake .xlsm file with minimal Excel structure
    An .xlsm file is essentially a zip file containing XML documents and metadata
    """
    xlsm_path = tmp_path / "test_workbook.xlsm"
    
    # Create a simple ZIP file with basic Excel structure
    with zipfile.ZipFile(xlsm_path, 'w') as zf:
        # Add required Excel components
        zf.writestr('[Content_Types].xml', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"></Types>')
        zf.writestr('_rels/.rels', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"></Relationships>')
        zf.writestr('xl/workbook.xml', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"></workbook>')
        
        # Add VBA project container (makes it a macro workbook)
        zf.writestr('xl/vbaProject.bin', b'This is a fake VBA project')
    
    return xlsm_path


@pytest.fixture
def sample_csv_dir(tmp_path):
    """Create a sample CSV directory with test CSV files representing different schemas"""
    ryan_dir = tmp_path / "csv_inbox" / "ryan"
    jordyn_dir = tmp_path / "csv_inbox" / "jordyn"
    ryan_dir.mkdir(parents=True)
    jordyn_dir.mkdir(parents=True)
    
    # Create Rocket Money sample
    rocket_csv = ryan_dir / "BALANCE - Rocket Money - test.csv"
    rocket_content = """Date,Account Name,Institution Name,Amount,Description,Category
2025-04-01,Checking,RocketBank,-50.00,Test Grocery Purchase,Groceries
2025-04-02,Savings,RocketBank,100.00,Test Deposit,Income
"""
    rocket_csv.write_text(rocket_content)
    
    # Create Monarch Money sample with different transaction to avoid duplicate TxnID
    monarch_csv = ryan_dir / "BALANCE - Monarch Money - test.csv"
    monarch_content = """Date,Merchant,Amount,Account,Institution,Category,Original Statement
2025-04-02,Test Grocery Store,-35.00,Checking,MonarchBank,Groceries,Original text
2025-04-03,Different Purchase,-25.00,Checking,MonarchBank,Shopping,Original text
"""
    monarch_csv.write_text(monarch_content)
    
    # Create a Wells Fargo sample
    wells_csv = jordyn_dir / "Jordyn - Wells Fargo - Active Cash Visa Signature Card x4296 - CSV.csv"
    wells_content = """Name,Institution,Account Description,Date,Amount,CheckNum,TransType,Description,Balance,Category
Jordyn Doe,Wells Fargo,Active Cash Card,04/01/2025,50.00,,CREDIT,Wells Fargo Test Transaction,,Shopping
"""
    wells_csv.write_text(wells_content)
    
    return tmp_path / "csv_inbox"


def test_full_cli_workflow(sample_csv_dir, fake_xlsm, tmp_path):
    """
    Test the entire CLI workflow:
    1. Run in dry-run mode first
    2. Run for real to generate .temp.xlsx
    3. Verify the temp file exists and lock file is cleaned up
    4. Check the content of the temp file
    """
    # Paths for testing
    python_path = Path(os.environ.get('VIRTUAL_ENV', '.')) / "Scripts" / "python.exe"
    if not python_path.exists():
        python_path = "python"  # Fallback to system Python
    
    # Copy the fake xlsm to the temp directory for modification
    test_xlsm = tmp_path / "BALANCE-test.xlsm"
    shutil.copy(fake_xlsm, test_xlsm)
    
    # Create a backup copy to verify VBA project preservation
    backup_xlsm = tmp_path / "original.xlsm"
    shutil.copy(fake_xlsm, backup_xlsm)
    
    # --- Phase 1: Dry run ---
    cmd_dry_run = [
        str(python_path),
        "-m", "balance_pipeline.cli",
        str(sample_csv_dir),
        str(test_xlsm),
        "--dry-run"
    ]
    
    result_dry = subprocess.run(cmd_dry_run, capture_output=True, text=True)
    
    # Check if dry run succeeded
    assert result_dry.returncode == 0, f"Dry run command failed with output: {result_dry.stderr}"
    
    # Check that dry run CSV was created
    dry_run_csv = test_xlsm.with_suffix(".dry-run.csv")
    assert dry_run_csv.exists(), "Dry run CSV should be created"
    
    # Check no lock file remains
    lock_file = test_xlsm.with_suffix(".lock")
    assert not lock_file.exists(), "Lock file should not exist after dry run"
    
    # --- Phase 2: Real run ---
    cmd_real = [
        str(python_path),
        "-m", "balance_pipeline.cli",
        str(sample_csv_dir),
        str(test_xlsm)
    ]
    
    result_real = subprocess.run(cmd_real, capture_output=True, text=True)
    
    # Check if command succeeded
    assert result_real.returncode == 0, f"Command failed with output: {result_real.stderr}"
    
    # Check that temp xlsx was created for .xlsm files
    temp_xlsx = test_xlsm.with_suffix(".temp.xlsx")
    assert temp_xlsx.exists(), "Temp XLSX should be created for .xlsm files"
    
    # Check no lock file remains
    assert not lock_file.exists(), "Lock file should be cleaned up after processing"
    
    # --- Phase 3: Verify content of temp file ---
    try:
        with pd.ExcelFile(temp_xlsx) as xls:
            # Check both expected sheets exist
            assert "Transactions" in xls.sheet_names, "Temp file should have Transactions sheet"
            assert "Queue_Review" in xls.sheet_names, "Temp file should have Queue_Review sheet"
            
            # Read the transactions sheet
            df = pd.read_excel(xls, sheet_name="Transactions")
            
            # Verify we have rows
            assert len(df) > 0, "Transactions sheet should contain data"
            
            # Check that key columns exist
            for col in ["TxnID", "Date", "Amount", "Description", "Owner"]:
                assert col in df.columns, f"Column {col} should exist in output"
                
            # Check that we have rows from both owners
            owners = set(df["Owner"].str.lower())
            assert "ryan" in owners, "Should have transactions from Ryan"
            assert "jordyn" in owners, "Should have transactions from Jordyn"
            
            # Check that we have groceries from both sources but no single duplicate transaction
            groceries_count = len(df[df["Description"].str.contains("Grocery", case=False)])
            assert groceries_count == 2, "Should have two different grocery transactions from different sources"
            
            # Make sure we didn't duplicate the same transaction
            grocery_txns = df[df["Description"].str.contains("Grocery", case=False)]["Description"].tolist()
            assert "Test Grocery Purchase" in grocery_txns, "Should have Rocket's grocery transaction"
            assert "Test Grocery Store" in grocery_txns, "Should have Monarch's grocery transaction"
            
    except Exception as e:
        pytest.fail(f"Failed to read temp XLSX file: {e}")
        
    # Verify original .xlsm still has vbaProject.bin (check the file is still a real .xlsm)
    with zipfile.ZipFile(test_xlsm, "r") as zf:
        file_list = zf.namelist()
        assert "xl/vbaProject.bin" in file_list, "VBA project should still exist in original .xlsm"


def test_cli_prefer_rocket_behavior(sample_csv_dir, fake_xlsm, tmp_path):
    """
    Test that the deduplication logic correctly handles different transactions from different sources
    """
    # Paths for testing
    python_path = Path(os.environ.get('VIRTUAL_ENV', '.')) / "Scripts" / "python.exe"
    if not python_path.exists():
        python_path = "python"  # Fallback to system Python
    
    # Set up a special test directory with actual duplicates
    duplicate_csv_dir = tmp_path / "duplicate_test"
    ryan_dir = duplicate_csv_dir / "ryan"
    ryan_dir.mkdir(parents=True)
    
    # Create Rocket Money sample with a specific transaction
    rocket_csv = ryan_dir / "BALANCE - Rocket Money - test.csv"
    rocket_content = """Date,Account Name,Institution Name,Amount,Description,Category
2025-04-01,Checking,RocketBank,-50.00,SAME EXACT TRANSACTION,Groceries
"""
    rocket_csv.write_text(rocket_content)
    
    # Create Monarch Money sample with the EXACT SAME transaction (same date, amount, desc, bank, account)
    # Need exact same values for TxnID generation fields to match
    monarch_csv = ryan_dir / "BALANCE - Monarch Money - test.csv"
    monarch_content = """Date,Merchant,Amount,Account,Institution,Category,Original Statement
2025-04-01,SAME EXACT TRANSACTION,-50.00,Checking,RocketBank,Groceries,Original text
"""
    monarch_csv.write_text(monarch_content)
    
    # Copy the fake xlsm to the temp directory
    test_xlsm = tmp_path / "BALANCE-source-test.xlsm"
    shutil.copy(fake_xlsm, test_xlsm)
    
    # Run the CLI on the duplicate directory
    cmd = [
        str(python_path),
        "-m", "balance_pipeline.cli",
        str(duplicate_csv_dir),
        str(test_xlsm),
        "--dry-run"  # Use dry-run for simpler CSV output
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0, "Command should succeed"
    
    # Read the output CSV
    csv_path = test_xlsm.with_suffix(".dry-run.csv")
    df = pd.read_csv(csv_path)
    
    # Find the transaction
    txn_rows = df[df["Description"] == "SAME EXACT TRANSACTION"]
    
    # Should only be one row - the duplicate should be removed
    assert len(txn_rows) == 1, "Should have deduplicated the identical transactions"
    
    # The remaining row should be from Rocket (our preferred source)
    assert txn_rows.iloc[0]["Source"] == "Rocket", "Should have kept the Rocket version"
