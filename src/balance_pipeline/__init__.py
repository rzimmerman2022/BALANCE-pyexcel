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
from __future__ import annotations # Allows type hint 'pd.DataFrame' before full definition

from pathlib import Path         # For handling file system paths robustly
import logging                   # For application logging
import pandas as pd              # For DataFrame operations (used in type hint)

# Import core processing functions from other modules within this package
from .ingest import load_folder    # Function to load data from CSVs
from .normalize import normalize_df # Function to clean and normalize the data
from .errors import BalancePipelineError

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
    # .expanduser() handles '~' correctly (e.g., on Linux/Mac).
    # .resolve() makes the path absolute and resolves any symlinks.
    inbox_path = Path(csv_inbox).expanduser().resolve()
    log.info("ETL process starting for inbox: %s", inbox_path)

    # --- Step 1: Ingest Data ---
    # Call the function from ingest.py to find, read, map, and combine CSVs.
    # This now handles multiple schemas and owner subfolders.
    # It returns a DataFrame with columns matching ingest.STANDARD_COLS.
    raw_df = load_folder(inbox_path)
    log.info("Ingestion complete. Loaded %s raw rows.", len(raw_df))

    # --- Step 2: Normalize Data ---
    # Call the function from normalize.py to perform further cleaning,
    # generate TxnID, add SharedFlag, select/order final columns.
    # REVIEW: Ensure the normalize_df function handles the columns produced by the new ingest.py
    clean_df = normalize_df(raw_df)
    log.info("Normalization complete. Result has %s rows.", len(clean_df))

    # --- Complete ---
    log.info("ETL process finished successfully.")
    return clean_df

# ==============================================================================
# END OF FILE: __init__.py
# ==============================================================================
