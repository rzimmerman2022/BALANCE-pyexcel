import pytest
import pandas as pd
from pathlib import Path
from balance_pipeline.csv_consolidator import process_csv_files
from balance_pipeline.errors import RecoverableFileError

def test_skip_bad_and_process_good(tmp_path):
    # Create a good CSV with required headers
    good = tmp_path / "good.csv"
    good.write_text("Date,Description,Amount\n2025-01-01,Test,100\n")
    # Create a bad CSV with invalid header
    bad = tmp_path / "bad.csv"
    bad.write_text("X,Y,Z\n1,2,3\n")
    # Process both, allowing registry override to a minimal valid registry
    # Create a minimal valid schema registry
    registry = tmp_path / "schema.yml"
    registry.write_text("""
- id: test
  match_filename: "*.csv"
  header_signature: ["Date","Description","Amount"]
  column_map: {}
""")
    # Call process_csv_files: bad file should raise RecoverableFileError and get skipped internally
    # Good file should succeed
    df = process_csv_files(
        [str(bad), str(good)],
        schema_registry_override_path=registry
    )
    # Only the good row should be in the output
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert df.iloc[0]["Description"] == "Test"
