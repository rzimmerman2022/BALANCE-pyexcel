"""
Migration Validation Script for BALANCE-pyexcel Unified Pipeline.

This script processes the same input data through both the legacy pipeline
and the new UnifiedPipeline (v2) to compare their outputs and ensure consistency.
It helps validate that the refactoring maintains backward compatibility in terms
of data output.

**Setup:**
1. Ensure you have sample CSV data in a designated directory.
2. Configure the `SAMPLE_DATA_INBOX_PATH` variable below to point to this directory.
3. The script assumes the old CLI's etl_main and the new UnifiedPipeline can access
   necessary configurations (like schema registry, merchant lookup) from their
   default locations or that these are implicitly handled by the respective modules.

**Output:**
- Logs differences found between the DataFrames produced by the two pipelines.
- Optionally saves the two DataFrames to CSV/Parquet for manual inspection.
"""
import logging
import pandas as pd
from pathlib import Path
import sys
import time

# Ensure the src directory is in PYTHONPATH if running script directly from 'scripts' folder
# This allows importing from balance_pipeline
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import from both old and new pipeline structures
from balance_pipeline.cli import etl_main as legacy_cli_etl_main # Legacy pipeline entry point
# from balance_pipeline import etl_main as legacy_init_etl_main # Alternative legacy entry
from balance_pipeline.pipeline_v2 import UnifiedPipeline
from balance_pipeline.config_v2 import PipelineConfig, pipeline_config_v2 as global_v2_config

# --- Configuration for the Validation Script ---
# TODO: User needs to set this path to their representative sample CSV data inbox
SAMPLE_DATA_INBOX_PATH = Path("sample_data_multi") # Example: "CSVs/test_run_01" or "sample_data_multi"
                                                 # This path should contain CSVs that both pipelines can process.
                                                 # It should be relative to the project root or an absolute path.

OUTPUT_COMPARISON_FILES = True # If True, saves DataFrames to files for inspection
COMPARISON_OUTPUT_DIR = Path("scripts_validation_output")

# Configure logging for the validation script
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("MigrationValidator")


def run_legacy_pipeline(inbox_path: Path) -> pd.DataFrame:
    """Runs the legacy ETL pipeline (using cli.etl_main)."""
    logger.info(f"Running LEGACY pipeline on: {inbox_path}")
    # Note: legacy_cli_etl_main might have its own logging setup.
    # It expects specific exclude/only patterns if needed, and prefer_source.
    # For a basic comparison, we use defaults.
    try:
        # legacy_cli_etl_main uses the old config.py for some defaults.
        # It also uses csv_consolidator which now uses the new config.py for SCHEMA_MODE.
        # This might lead to mixed config states if not careful.
        # For this validation, we assume it will run "as is".
        df_legacy = legacy_cli_etl_main(
            inbox_path=inbox_path,
            prefer_source="Rocket", # Default from legacy CLI
            exclude_patterns=[],
            only_patterns=[]
        )
        logger.info(f"LEGACY pipeline completed. Output shape: {df_legacy.shape}")
        return df_legacy
    except Exception as e:
        logger.error(f"Error running LEGACY pipeline: {e}", exc_info=True)
        return pd.DataFrame()

def run_new_pipeline(inbox_path: Path, schema_mode: str = "flexible") -> pd.DataFrame:
    """Runs the new UnifiedPipeline."""
    logger.info(f"Running NEW UnifiedPipeline (schema_mode='{schema_mode}') on: {inbox_path}")
    
    # Scan for CSV files in the inbox_path (similar to how legacy etl_main does)
    csv_file_paths: list[Path] = []
    if inbox_path.is_dir():
        for item in inbox_path.rglob("*.csv"):
            csv_file_paths.append(item)
    elif inbox_path.is_file() and inbox_path.suffix.lower() == ".csv":
        csv_file_paths.append(inbox_path)
    else:
        logger.error(f"New pipeline: Inbox path {inbox_path} is not valid.")
        return pd.DataFrame()

    if not csv_file_paths:
        logger.warning(f"New pipeline: No CSV files found in {inbox_path}.")
        return pd.DataFrame()

    csv_file_paths_str = [str(p) for p in csv_file_paths]

    # Use the global_v2_config for paths to schema_registry, merchant_lookup
    # The UnifiedPipeline's process_files will use these if overrides are None.
    pipeline = UnifiedPipeline(schema_mode=schema_mode)
    try:
        df_new = pipeline.process_files(
            file_paths=csv_file_paths_str,
            schema_registry_override_path=str(global_v2_config.schema_registry_path),
            merchant_lookup_override_path=str(global_v2_config.merchant_lookup_path)
        )
        logger.info(f"NEW UnifiedPipeline (mode: {schema_mode}) completed. Output shape: {df_new.shape}")
        return df_new
    except Exception as e:
        logger.error(f"Error running NEW UnifiedPipeline (mode: {schema_mode}): {e}", exc_info=True)
        return pd.DataFrame()

def compare_dataframes(df1: pd.DataFrame, df2: pd.DataFrame, df1_name: str = "df1", df2_name: str = "df2") -> bool:
    """
    Compares two DataFrames for equality, logging differences.
    Tries to sort columns and reset index for a more robust comparison.
    """
    if df1.empty and df2.empty:
        logger.info("Both DataFrames are empty. Considered equal.")
        return True
    if df1.empty or df2.empty:
        logger.warning(f"One DataFrame is empty, the other is not. {df1_name} empty: {df1.empty}, {df2_name} empty: {df2.empty}")
        return False

    # Pre-comparison normalization
    try:
        # Sort columns for consistent order
        df1_sorted = df1.reindex(sorted(df1.columns), axis=1).reset_index(drop=True)
        df2_sorted = df2.reindex(sorted(df2.columns), axis=1).reset_index(drop=True)
        
        # Attempt to sort by a common, stable key if possible (e.g., TxnID, Date, Amount)
        # This helps align rows for comparison if row order differs but content is same.
        # This is a heuristic and might need adjustment based on data.
        sort_keys = [key for key in ["TxnID", "Date", "Amount", "OriginalDescription"] if key in df1_sorted.columns and key in df2_sorted.columns]
        if sort_keys:
            logger.debug(f"Attempting to sort DataFrames by keys: {sort_keys} before comparison.")
            df1_sorted = df1_sorted.sort_values(by=sort_keys).reset_index(drop=True)
            df2_sorted = df2_sorted.sort_values(by=sort_keys).reset_index(drop=True)
            
    except Exception as e_sort:
        logger.warning(f"Could not fully normalize DataFrames for comparison (sorting/reindexing failed): {e_sort}. Proceeding with raw comparison.")
        df1_sorted = df1.reset_index(drop=True)
        df2_sorted = df2.reset_index(drop=True)


    try:
        pd.testing.assert_frame_equal(df1_sorted, df2_sorted, check_dtype=False, rtol=1e-5, atol=1e-8)
        logger.info(f"DataFrames '{df1_name}' and '{df2_name}' are EQUAL (after sorting columns/rows, ignoring dtype).")
        return True
    except AssertionError as e:
        logger.warning(f"DataFrames '{df1_name}' and '{df2_name}' are DIFFERENT.")
        logger.warning(f"AssertionError details: {str(e).splitlines()[0]}") # First line of error often most useful

        # Log column differences
        cols_df1 = set(df1.columns)
        cols_df2 = set(df2.columns)
        if cols_df1 != cols_df2:
            logger.warning(f"Column differences: ")
            logger.warning(f"  Only in {df1_name}: {cols_df1 - cols_df2}")
            logger.warning(f"  Only in {df2_name}: {cols_df2 - cols_df1}")
        
        # Further detailed comparison (e.g., row-by-row or using a diff tool) might be needed.
        # For now, this indicates a difference.
        return False

def main_validation():
    """Main function to run the validation."""
    logger.info("Starting Migration Validation Script...")
    
    project_root = Path(__file__).resolve().parent.parent
    abs_inbox_path = (project_root / SAMPLE_DATA_INBOX_PATH).resolve()

    if not abs_inbox_path.exists():
        logger.error(f"Sample data inbox path does not exist: {abs_inbox_path}")
        logger.error("Please configure SAMPLE_DATA_INBOX_PATH in this script.")
        return

    logger.info(f"Using sample data from: {abs_inbox_path}")

    # --- Run Legacy Pipeline ---
    start_time_legacy = time.time()
    df_legacy = run_legacy_pipeline(abs_inbox_path)
    duration_legacy = time.time() - start_time_legacy
    logger.info(f"Legacy pipeline execution time: {duration_legacy:.2f} seconds.")

    # --- Run New Pipeline (Flexible Mode - for closer comparison to legacy) ---
    start_time_new_flex = time.time()
    df_new_flexible = run_new_pipeline(abs_inbox_path, schema_mode="flexible")
    duration_new_flex = time.time() - start_time_new_flex
    logger.info(f"New pipeline (flexible) execution time: {duration_new_flex:.2f} seconds.")

    # --- Run New Pipeline (Strict Mode - for completeness) ---
    start_time_new_strict = time.time()
    df_new_strict = run_new_pipeline(abs_inbox_path, schema_mode="strict")
    duration_new_strict = time.time() - start_time_new_strict
    logger.info(f"New pipeline (strict) execution time: {duration_new_strict:.2f} seconds.")

    # --- Save outputs if enabled ---
    if OUTPUT_COMPARISON_FILES:
        COMPARISON_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"Saving comparison files to: {COMPARISON_OUTPUT_DIR}")
        if not df_legacy.empty:
            df_legacy.to_csv(COMPARISON_OUTPUT_DIR / "output_legacy.csv", index=False)
            df_legacy.to_parquet(COMPARISON_OUTPUT_DIR / "output_legacy.parquet", index=False)
        if not df_new_flexible.empty:
            df_new_flexible.to_csv(COMPARISON_OUTPUT_DIR / "output_new_flexible.csv", index=False)
            df_new_flexible.to_parquet(COMPARISON_OUTPUT_DIR / "output_new_flexible.parquet", index=False)
        if not df_new_strict.empty:
            df_new_strict.to_csv(COMPARISON_OUTPUT_DIR / "output_new_strict.csv", index=False)
            df_new_strict.to_parquet(COMPARISON_OUTPUT_DIR / "output_new_strict.parquet", index=False)

    # --- Compare Legacy vs New (Flexible) ---
    logger.info("\n--- Comparing Legacy Pipeline vs New UnifiedPipeline (Flexible Mode) ---")
    are_flex_equal = compare_dataframes(df_legacy, df_new_flexible, "Legacy", "New_Flexible")
    if are_flex_equal:
        logger.info("SUCCESS: Legacy and New (Flexible) pipeline outputs are consistent.")
    else:
        logger.warning("DIFFERENCES FOUND: Legacy and New (Flexible) pipeline outputs differ.")

    # --- Compare New (Flexible) vs New (Strict) ---
    # This comparison is more about understanding the modes than strict equality.
    logger.info("\n--- Comparing New UnifiedPipeline (Flexible Mode) vs New UnifiedPipeline (Strict Mode) ---")
    # This comparison might not be 'equal' by design due to schema differences.
    # The goal here is to observe, not necessarily assert equality.
    compare_dataframes(df_new_flexible, df_new_strict, "New_Flexible", "New_Strict")
    
    logger.info("\nMigration Validation Script Finished.")
    if not are_flex_equal:
        logger.warning("Please review the differences logged and the output files (if saved).")

if __name__ == "__main__":
    main_validation()
