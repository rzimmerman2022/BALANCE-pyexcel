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

@pytest.fixture
def fake_xlsm(tmp_path):
    """Create a fake .xlsm file (which is essentially a zip file)"""
    xlsm_path = tmp_path / "test_workbook.xlsm"
    
    # Create a simple ZIP file with a minimal structure
    with zipfile.ZipFile(xlsm_path, 'w') as zf:
        # Add a dummy file to the archive
        zf.writestr('dummy.txt', 'This is a fake Excel file')
    
    return xlsm_path

@pytest.fixture
def sample_csv_dir(tmp_path):
    """Create a sample CSV directory with a test CSV file"""
    csv_dir = tmp_path / "csv_inbox" / "ryan"
    csv_dir.mkdir(parents=True)
    
    # Create a simple CSV file
    csv_path = csv_dir / "BALANCE - Rocket Money - test.csv"
    csv_content = """Date,Account Name,Institution Name,Amount,Description,Category
2025-04-01,Checking,TestBank,-50.00,Test Transaction,Groceries
2025-04-02,Savings,TestBank,100.00,Deposit,Income
"""
    csv_path.write_text(csv_content)
    
    return csv_dir.parent

def test_cli_dry_run(sample_csv_dir, fake_xlsm):
    """Test CLI with --dry-run option to ensure lock file cleanup works"""
    # Construct the command
    python_path = Path(os.environ.get('VIRTUAL_ENV', '.')) / "Scripts" / "python.exe"
    if not python_path.exists():
        python_path = "python"  # Fallback to system Python
    
    cmd = [
        str(python_path),
        "-m", "balance_pipeline.cli",
        str(sample_csv_dir),
        str(fake_xlsm),
        "--dry-run"
    ]
    
    # Run the command
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Check if it ran successfully
    assert result.returncode == 0, f"Command failed with output: {result.stderr}"
    
    # Check that the lock file doesn't exist
    lock_file = fake_xlsm.with_suffix(".lock")
    assert not lock_file.exists(), "Lock file should be cleaned up after dry run"
    
    # Check that the dry-run CSV was created
    dry_run_csv = fake_xlsm.with_suffix(".dry-run.csv")
    assert dry_run_csv.exists(), "Dry run CSV should be created"
    
    # Verify the CSV contains expected data
    df = pd.read_csv(dry_run_csv)
    assert len(df) > 0, "Dry run CSV should contain data"
    assert "TxnID" in df.columns, "Processed data should have TxnID column"

def test_cli_xlsm_processing(sample_csv_dir, fake_xlsm):
    """Test CLI processing of .xlsm files to ensure temp file creation"""
    # Construct the command
    python_path = Path(os.environ.get('VIRTUAL_ENV', '.')) / "Scripts" / "python.exe"
    if not python_path.exists():
        python_path = "python"  # Fallback to system Python
    
    cmd = [
        str(python_path),
        "-m", "balance_pipeline.cli",
        str(sample_csv_dir),
        str(fake_xlsm)
    ]
    
    # Run the command
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Check if it ran successfully
    assert result.returncode == 0, f"Command failed with output: {result.stderr}"
    
    # Check that the lock file doesn't exist (should be cleaned up)
    lock_file = fake_xlsm.with_suffix(".lock")
    assert not lock_file.exists(), "Lock file should be cleaned up after processing"
    
    # Check that the temp xlsx was created
    temp_xlsx = fake_xlsm.with_suffix(".temp.xlsx")
    assert temp_xlsx.exists(), "Temp XLSX should be created for .xlsm files"
    
    # Try to read the temp xlsx to verify it contains expected data
    try:
        with pd.ExcelFile(temp_xlsx) as xls:
            assert "Transactions" in xls.sheet_names, "Temp file should have Transactions sheet"
            df = pd.read_excel(xls, sheet_name="Transactions")
            assert len(df) > 0, "Transactions sheet should contain data"
            assert "TxnID" in df.columns, "Processed data should have TxnID column"
    except Exception as e:
        pytest.fail(f"Failed to read temp XLSX file: {e}")
