# -*- coding: utf-8 -*-
"""
==============================================================================
Package: balance_pipeline
File:    __init__.py
Project: BALANCE-pyexcel
Description: Makes the 'balance_pipeline' directory a Python package and
             provides the main entry point function `etl_main` called by
             external interfaces (like the Excel =PY() cell) to run the
             full CSV ingestion and normalization pipeline.
==============================================================================

Version: 0.1.0
Last Modified: 2025-04-21 # Placeholder date
Author: Your Name / AI Assistant
"""

# ==============================================================================
# 0. IMPORTS
# ==============================================================================
from __future__ import (
    annotations,
)  # Allows type hint 'pd.DataFrame' before full definition

from pathlib import Path  # For handling file system paths robustly
import logging  # For application logging
import pandas as pd  # For DataFrame operations (used in type hint)

# Import core processing functions from other modules within this package
# from .ingest import load_folder # Replaced by UnifiedPipeline
# from .normalize import normalize_df # Replaced by UnifiedPipeline
from .pipeline_v2 import UnifiedPipeline # New import

# ==============================================================================
# 1. MODULE LEVEL SETUP (Logging)
# ==============================================================================

# Get a logger specific to this module (__name__ resolves to 'balance_pipeline')
# Using module-specific loggers helps trace where messages originate.
log = logging.getLogger(__name__)
# Set the minimum severity level for messages from THIS logger.
# Note: The overall root logger level is set in config.py
# log.setLevel(logging.INFO) # This might be redundant if root logger level is already INFO or lower

# ==============================================================================
# 2. PUBLIC FUNCTIONS (Entry Point)
# ==============================================================================


# ------------------------------------------------------------------------------
# Function: etl_main
# ------------------------------------------------------------------------------
def etl_main(csv_inbox: str | Path) -> pd.DataFrame:
    """
    Main entry point for the ETL (Extract, Transform, Load) process.
    Orchestrates the loading and normalization of transaction data from CSV files.
    Designed to be called directly, typically from the Excel interface.

    Parameters
    ----------
    csv_inbox : str | Path
        The path to the root folder containing owner-specific sub-folders
        (e.g., 'ryan/', 'jordyn/') which hold the *.csv transaction files.

    Returns
    -------
    pandas.DataFrame
        A single DataFrame containing the fully cleaned, normalized, and
        owner-tagged transactions from all successfully processed CSV files.
        Returns an empty DataFrame if no files are processed or errors occur.

    Raises
    ------
        FileNotFoundError: If the `csv_inbox` path doesn't exist or isn't a directory
                           (raised from within `load_folder`).
        ValueError: If the schema registry failed to load or no CSVs are found
                    (raised from within `load_folder`).
        Exception: Propagates other potential exceptions from `load_folder` or
                   `normalize_df` (e.g., critical CSV parsing errors, etc.).
    """
    # --- Prepare Input Path ---
    # Convert input string path to a Path object for robust handling.
    inbox_path = Path(csv_inbox).expanduser().resolve()
    log.info("Legacy etl_main (from __init__.py) process starting for inbox: %s", inbox_path)
    log.warning("This etl_main (from balance_pipeline/__init__.py) is a legacy interface. "
                "Consider using the new CLI 'balance-pipe' or directly using UnifiedPipeline for programmatic access.")

    # --- Step 1: Scan for CSV files ---
    # This logic is similar to what was in cli.py's etl_main or ingest.load_folder
    csv_file_paths: list[Path] = []
    if inbox_path.is_dir():
        for item in inbox_path.rglob("*.csv"):  # Recursive glob
            csv_file_paths.append(item)
    elif inbox_path.is_file() and inbox_path.suffix.lower() == ".csv":
        csv_file_paths.append(inbox_path)
    else:
        log.error(f"Inbox path {inbox_path} is not a valid directory or CSV file.")
        return pd.DataFrame()

    if not csv_file_paths:
        log.warning(f"No CSV files found to process in {inbox_path}.")
        return pd.DataFrame()

    log.info(
        f"Found {len(csv_file_paths)} CSV files to process: {[p.name for p in csv_file_paths]}"
    )

    # --- Step 2: Process files using UnifiedPipeline ---
    log.info("Initializing UnifiedPipeline for CSV processing (schema_mode='flexible' for legacy __init__.etl_main).")
    # For this legacy interface (e.g., Excel calls), default to "flexible" mode.
    # Schema registry and merchant lookup paths will be taken from config_v2.py defaults.
    pipeline = UnifiedPipeline(schema_mode="flexible")

    csv_file_paths_str = [str(p) for p in csv_file_paths]
    processed_df: pd.DataFrame = pd.DataFrame()

    try:
        processed_df = pipeline.process_files(
            file_paths=csv_file_paths_str,
            schema_registry_override_path=None, # Use config_v2 default
            merchant_lookup_override_path=None    # Use config_v2 default
        )
    except Exception as e_pipeline:
        log.error(f"UnifiedPipeline processing failed within __init__.etl_main: {e_pipeline}", exc_info=True)
        return pd.DataFrame() # Return empty DataFrame on error

    if processed_df.empty:
        log.warning(
            "UnifiedPipeline processing in __init__.etl_main resulted in an empty DataFrame."
        )
    else:
        log.info(f"UnifiedPipeline processing in __init__.etl_main complete. Result has {len(processed_df)} rows.")
    
    # The UnifiedPipeline (via csv_consolidator) now handles all normalization,
    # TxnID generation, deduplication (if configured within csv_consolidator's scope), etc.
    # The old normalize_df call is no longer needed here.
    # Deduplication based on 'prefer_source' as done in cli.py's etl_main is not part of this
    # __init__.py etl_main's original contract, so it's omitted here to maintain compatibility.
    # If that specific deduplication is needed for Excel calls, it would have to be added here.
    # For now, returning the direct output of UnifiedPipeline.

    # --- Complete ---
    log.info("Legacy etl_main (from __init__.py) finished successfully.")
    return processed_df


# ==============================================================================
# END OF FILE: __init__.py
# ==============================================================================
