"""
Tests for the Unified Data Processing Pipeline (v2).

This module contains pytest test cases for the UnifiedPipeline,
its configuration, output adapters, and overall integration.
"""

import logging
import shutil  # For cleaning up test outputs
from pathlib import Path

import pandas as pd
import pytest
from balance_pipeline.config_v2 import PipelineConfig

# from balance_pipeline.outputs import ExcelOutput, PowerBIOutput  # These classes don't exist yet
# Modules to test
from balance_pipeline.pipeline_v2 import UnifiedPipeline

# Configure logging for tests
logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.DEBUG) # Or set via pytest config

# --- Fixtures ---


@pytest.fixture(scope="session")
def project_root_dir() -> Path:
    """Returns the project root directory."""
    return Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def sample_data_dir(project_root_dir: Path) -> Path:
    """Provides the path to the sample_data directory."""
    return project_root_dir / "sample_data"  # Adjust if your sample data is elsewhere


@pytest.fixture(scope="session")
def rules_dir(project_root_dir: Path) -> Path:
    """Provides the path to the rules directory."""
    return project_root_dir / "rules"


@pytest.fixture(scope="module")
def temp_output_dir(project_root_dir: Path) -> Path:
    """Creates a temporary directory for test outputs and cleans it up afterwards."""
    temp_dir = project_root_dir / "tests" / "temp_test_outputs"
    temp_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Created temporary output directory: {temp_dir}")
    yield temp_dir
    logger.info(f"Cleaning up temporary output directory: {temp_dir}")
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def default_pipeline_config(rules_dir: Path, temp_output_dir: Path) -> PipelineConfig:
    """Returns a default PipelineConfig instance for testing."""
    return PipelineConfig(
        rules_dir=rules_dir,
        schema_registry_path=rules_dir
        / "schema_registry.yml",  # Ensure this exists or mock
        merchant_lookup_path=rules_dir
        / "merchant_lookup.csv",  # Ensure this exists or mock
        default_output_dir=temp_output_dir,
    )


@pytest.fixture
def sample_csv_files(sample_data_dir: Path) -> list[str]:
    """
    Provides a list of sample CSV file paths for testing.
    This fixture needs to be adapted to your actual sample files.
    Ensure these files exist and are representative.
    """
    # Example: Create dummy CSV files for testing if real ones are not available/suitable
    # For now, assumes some CSVs exist in sample_data_dir.
    # Replace with actual paths to your test CSVs.
    # file1 = sample_data_dir / "ryan_monarch_v2.yaml" # This is a yaml, need CSVs
    # file2 = sample_data_dir / "jordyn_pdf_v1.yaml"   # This is a yaml, need CSVs

    # Placeholder: User needs to provide actual sample CSVs or create them in fixtures.
    # For the test to run, these files should exist.
    # Let's assume there's a "sample_input1.csv" and "sample_input2.csv"
    # in the sample_data_dir for demonstration.

    # Create minimal dummy CSVs for the sake of having files
    dummy_csv1_path = sample_data_dir / "dummy_test_input1.csv"
    dummy_csv2_path = sample_data_dir / "dummy_test_input2.csv"

    # Check if sample_data_dir exists, create if not (for dummy files)
    sample_data_dir.mkdir(parents=True, exist_ok=True)

    if not dummy_csv1_path.exists():
        pd.DataFrame(
            {"Date": ["2023-01-01"], "Description": ["Test A"], "Amount": [100]}
        ).to_csv(dummy_csv1_path, index=False)
    if not dummy_csv2_path.exists():
        pd.DataFrame(
            {
                "Transaction Date": ["01/02/2023"],
                "Details": ["Test B"],
                "Debit": [50.0],
                "Credit": [None],
            }
        ).to_csv(dummy_csv2_path, index=False)

    # This should point to actual, representative CSV files for proper testing.
    # For now, using the dummy files created above.
    # return [str(sample_data_dir / "actual_sample1.csv"), str(sample_data_dir / "actual_sample2.csv")]
    return [str(dummy_csv1_path), str(dummy_csv2_path)]


# --- Test Cases ---


def test_pipeline_config_initialization(default_pipeline_config: PipelineConfig):
    """Tests basic initialization of PipelineConfig."""
    assert default_pipeline_config.schema_mode == "flexible"  # Default
    assert default_pipeline_config.log_level == "INFO"  # Default
    assert default_pipeline_config.schema_registry_path.name == "schema_registry.yml"
    logger.info(f"PipelineConfig explain:\n{default_pipeline_config.explain()}")


def test_unified_pipeline_initialization(default_pipeline_config: PipelineConfig):
    """Tests initialization of UnifiedPipeline with different schema modes."""
    pipeline_flex = UnifiedPipeline(schema_mode="flexible")
    assert pipeline_flex.schema_mode == "flexible"

    pipeline_strict = UnifiedPipeline(schema_mode="strict")
    assert pipeline_strict.schema_mode == "strict"

    with pytest.raises(ValueError):
        UnifiedPipeline(schema_mode="invalid_mode")


def test_unified_pipeline_process_files_flexible_mode(
    default_pipeline_config: PipelineConfig, sample_csv_files: list[str]
):
    """Tests the process_files method in 'flexible' schema_mode."""
    # This test requires sample_csv_files and a schema_registry.yml that can process them.
    # Ensure your default_pipeline_config points to a valid schema_registry.yml
    # and merchant_lookup.csv, or mock them.

    pipeline = UnifiedPipeline(schema_mode="flexible")

    # Override config paths for the pipeline instance if needed, or ensure fixture is correct
    # For now, assuming UnifiedPipeline will use the global config_v2 which should be
    # similar to default_pipeline_config if env vars aren't heavily used.
    # Better: Pass config paths directly if UnifiedPipeline is updated to take them,
    # or ensure the global config_v2 is set up for tests.
    # The current UnifiedPipeline.process_files takes overrides.

    df_processed = pipeline.process_files(
        file_paths=sample_csv_files,
        schema_registry_override_path=str(default_pipeline_config.schema_registry_path),
        merchant_lookup_override_path=str(default_pipeline_config.merchant_lookup_path),
    )

    assert isinstance(df_processed, pd.DataFrame)
    assert not df_processed.empty  # Assuming sample files produce some data
    # Add more specific assertions based on expected output for flexible mode
    # e.g., check for presence/absence of certain columns based on data.
    logger.info(f"Flexible mode processed DataFrame shape: {df_processed.shape}")
    logger.debug(f"Flexible mode DataFrame columns: {df_processed.columns.tolist()}")


def test_unified_pipeline_process_files_strict_mode(
    default_pipeline_config: PipelineConfig, sample_csv_files: list[str]
):
    """Tests the process_files method in 'strict' schema_mode."""
    pipeline = UnifiedPipeline(schema_mode="strict")

    df_processed = pipeline.process_files(
        file_paths=sample_csv_files,
        schema_registry_override_path=str(default_pipeline_config.schema_registry_path),
        merchant_lookup_override_path=str(default_pipeline_config.merchant_lookup_path),
    )

    assert isinstance(df_processed, pd.DataFrame)
    assert not df_processed.empty
    # In strict mode, all MASTER_SCHEMA_COLUMNS should be present
    # from balance_pipeline.constants import MASTER_SCHEMA_COLUMNS # Import if needed
    # assert all(col in df_processed.columns for col in MASTER_SCHEMA_COLUMNS)
    # assert len(df_processed.columns) == len(MASTER_SCHEMA_COLUMNS) # Or check exact number
    logger.info(f"Strict mode processed DataFrame shape: {df_processed.shape}")
    logger.debug(f"Strict mode DataFrame columns: {df_processed.columns.tolist()}")


def test_powerbi_output_adapter(temp_output_dir: Path):
    """Tests the PowerBIOutput adapter."""
    output_file = temp_output_dir / "test_powerbi_output.parquet"
    adapter = PowerBIOutput(output_file)

    sample_data = pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})
    adapter.write(sample_data)

    assert output_file.exists()
    df_read = pd.read_parquet(output_file)
    pd.testing.assert_frame_equal(df_read, sample_data)


def test_excel_output_adapter(temp_output_dir: Path):
    """Tests the ExcelOutput adapter."""
    output_file = temp_output_dir / "test_excel_output.xlsx"
    adapter = ExcelOutput(output_file)

    sample_data = pd.DataFrame(
        {
            "col1": [1, 2],
            "col2": ["a", "b"],
            "col_dt": pd.to_datetime(["2023-01-01", "2023-01-02"]),
        }
    )
    adapter.write(sample_data, sheet_name="TestData")

    assert output_file.exists()
    df_read = pd.read_excel(output_file, sheet_name="TestData")
    # Excel might change types (e.g., int to float if NaNs involved, datetimes)
    # For robust comparison, might need to cast or compare carefully.
    pd.testing.assert_frame_equal(
        df_read, sample_data, check_dtype=False
    )  # check_dtype=False for flexibility


# --- Placeholder for more tests ---

# test_backward_compatibility_cli():
#   - Use subprocess to call the old cli.py with sample data.
#   - Compare its output (e.g., a generated parquet/excel file) with the output
#     from the new main.py (balance-pipe) using the same data and equivalent settings.

# test_backward_compatibility_init_etl_main():
#   - Call src.balance_pipeline.etl_main() with sample data.
#   - Compare its output DataFrame with one generated by directly using
#     UnifiedPipeline with equivalent settings.

# test_output_adapter_excel_with_template():
#   - (Future) If ExcelOutput supports writing to a template.

# test_integration_with_sample_data_all_sources():
#   - A more comprehensive test using a variety of your actual sample CSVs
#     representing different financial institutions and data structures.
#   - Verify data integrity, correct schema mapping, TxnID generation, etc.

# test_error_handling_bad_csv():
#   - Test how the pipeline handles malformed or unreadable CSV files.

# test_error_handling_missing_schema():
#   - Test behavior when a CSV cannot be matched to any schema.

# test_logging_output():
#   - Capture log output during a pipeline run and verify key messages
#     are present or that log levels are respected.
