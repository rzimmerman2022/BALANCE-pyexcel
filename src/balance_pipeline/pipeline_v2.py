"""
Unified Data Processing Pipeline for BALANCE-pyexcel.

This module provides the UnifiedPipeline class, which serves as the central
engine for ingesting, processing, and standardizing financial data from various
CSV sources. It aims to consolidate the logic previously split between
the legacy pipeline (ingest.py, normalize.py) and the current pipeline
(cli.py, csv_consolidator.py).

The UnifiedPipeline class:
- Wraps the core functionality of csv_consolidator.py.
- Offers a clean, object-oriented interface.
- Handles business rules consistently.
- Supports both "strict" and "flexible" schema modes.
- Includes logging and error handling.
- Returns a standardized pandas DataFrame.
"""
import logging
from typing import List, Optional
from pathlib import Path # Added

import pandas as pd

# Imports from existing modules
from . import config as bp_config # Added for setting SCHEMA_MODE
from .csv_consolidator import process_csv_files as csv_consolidator_process_files # Added
# from .schema_types import SchemaMode # SchemaMode is just str for now
# from .config_v2 import PipelineConfig # Will be created in Phase 3

logger = logging.getLogger(__name__)

class UnifiedPipeline:
    """
    A unified pipeline for processing financial CSV files.

    This class orchestrates the reading, consolidation, and standardization
    of data from multiple CSV files, applying consistent business rules
    and schema validation.
    """

    def __init__(self, schema_mode: str = "flexible"):
        """
        Initializes the UnifiedPipeline.

        Args:
            schema_mode (str): The schema mode to use for processing.
                Can be "strict" (all 25 columns required) or
                "flexible" (only columns with data are included).
                Defaults to "flexible".
        """
        if schema_mode not in ["strict", "flexible"]:
            raise ValueError("schema_mode must be either 'strict' or 'flexible'")
        self.schema_mode = schema_mode
        logger.info(f"UnifiedPipeline initialized with schema_mode: {self.schema_mode}")

    def process_files(
        self,
        file_paths: List[str],
        schema_registry_override_path: Optional[str] = None,
        merchant_lookup_override_path: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Processes a list of CSV files and returns a consolidated DataFrame.

        This method encapsulates the core logic from csv_consolidator.py.
        It sets the schema_mode in the global config for the duration of the call.

        Args:
            file_paths (List[str]): A list of paths to the CSV files to process.
            schema_registry_override_path (Optional[str]): Path to override the default schema registry YAML.
            merchant_lookup_override_path (Optional[str]): Path to override the default merchant lookup CSV.

        Returns:
            pd.DataFrame: A DataFrame containing the consolidated and processed data.
        """
        logger.info(f"Starting UnifiedPipeline processing for {len(file_paths)} files with schema_mode: {self.schema_mode}.")
        if not file_paths:
            logger.warning("No file paths provided for processing.")
            return pd.DataFrame()

        # Store original config values to restore them later
        original_schema_mode = bp_config.SCHEMA_MODE
        # In the future, a PipelineConfig object will manage these overrides more cleanly.
        # For now, csv_consolidator_process_files uses its defaults from bp_config
        # if override paths are not provided.

        try:
            # Set schema_mode in the shared config module for csv_consolidator to pick up
            bp_config.SCHEMA_MODE = self.schema_mode
            logger.debug(f"Temporarily set bp_config.SCHEMA_MODE to: {bp_config.SCHEMA_MODE}")

            # Convert string paths to Path objects
            input_files_paths = [Path(fp) for fp in file_paths]
            schema_reg_override = Path(schema_registry_override_path) if schema_registry_override_path else None
            merchant_lkp_override = Path(merchant_lookup_override_path) if merchant_lookup_override_path else None

            # TODO: Integrate core logic from csv_consolidator.process_csv_files.
            # This involves calling csv_consolidator_process_files with the correct parameters.
            # The parameters for csv_consolidator_process_files are:
            # - csv_files: List[Union[str, Path]]
            # - schema_registry_override_path: Optional[Path] = None
            # - merchant_lookup_override_path: Optional[Path] = None
            # Other configurations (like RULES_DIR_PATH) are read from bp_config by csv_consolidator.
            
            df_consolidated = csv_consolidator_process_files(
                csv_files=input_files_paths,
                schema_registry_override_path=schema_reg_override,
                merchant_lookup_override_path=merchant_lkp_override,
            )
            
            if df_consolidated.empty:
                logger.info("UnifiedPipeline processing resulted in an empty DataFrame.")
            else:
                logger.info(f"UnifiedPipeline successfully processed files. Resulting DataFrame shape: {df_consolidated.shape}")
            
            return df_consolidated

        except Exception as e:
            logger.error(f"Error during UnifiedPipeline file processing: {e}", exc_info=True)
            raise # Re-raise for now
        finally:
            # Restore original config values
            bp_config.SCHEMA_MODE = original_schema_mode
            logger.debug(f"Restored bp_config.SCHEMA_MODE to: {bp_config.SCHEMA_MODE}")

if __name__ == "__main__":
    # Example usage (for basic testing, will be expanded)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    
    pipeline_flex = UnifiedPipeline(schema_mode="flexible")
    logger.info(f"Created pipeline with mode: {pipeline_flex.schema_mode}")

    pipeline_strict = UnifiedPipeline(schema_mode="strict")
    logger.info(f"Created pipeline with mode: {pipeline_strict.schema_mode}")

    # Example of how process_files might be called (files don't exist yet)
    # try:
    #     df = pipeline_flex.process_files(
    #         file_paths=["dummy1.csv", "dummy2.csv"],
    #         schema_registry_override_path="path/to/your/schema_registry.yml", # Placeholder
    #         merchant_lookup_override_path="path/to/your/merchant_lookup.csv" # Placeholder
    #     )
    #     if not df.empty:
    #         print("Processed DataFrame head:")
    #         print(df.head())
    # except Exception as e:
    #     logger.error(f"Example usage failed: {e}")

    try:
        pipeline_invalid = UnifiedPipeline(schema_mode="invalid_mode")
    except ValueError as e:
        logger.error(f"Caught expected error for invalid schema mode: {e}")
