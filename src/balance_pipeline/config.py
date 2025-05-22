# -*- coding: utf-8 -*-
"""
==============================================================================
Module: config.py
Project: BALANCE-pyexcel
Description: Centralized configuration settings for the application.
             Loads settings from environment variables (via a .env file if present)
             with sensible defaults. Aims to be the single source of truth for
             configurable parameters like file paths, logging levels, etc.
==============================================================================

Version: 0.1.0
Last Modified: 2025-04-21 # Placeholder date
Author: Your Name / AI Assistant
"""

# ==============================================================================
# 0. IMPORTS
# ==============================================================================
from __future__ import annotations  # Allows using Path hint before full definition
from pathlib import Path  # For object-oriented path manipulation
import os  # For accessing environment variables
import sys  # For checking if running as frozen executable
import logging  # For configuring application logging
from dotenv import load_dotenv  # For loading .env files

# ==============================================================================
# 1. LOAD ENVIRONMENT VARIABLES
# ==============================================================================
# This command looks for a file named '.env' in the current working directory
# or parent directories and loads any variables defined within it into the
# environment. This allows overriding default settings without changing code.
# Make sure '.env' is listed in your .gitignore file!
load_dotenv()
logging.info(".env file loaded if present.")

# ==============================================================================
# 2. CORE CONSTANTS & RESOURCE PATH HELPER
# ==============================================================================


def get_resource_path(relative_path: str | Path) -> Path:
    """Get absolute path to resource, works for dev and for PyInstaller"""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        # The type of sys._MEIPASS is str, so cast it for Path
        base_path = Path(getattr(sys, '_MEIPASS'))
        logging.debug(f"Running frozen (PyInstaller), base path: {base_path}")
    else:
        # Not frozen, running in normal Python environment
        # Calculate PROJECT_ROOT relative to this file's location
        base_path = Path(__file__).resolve().parents[2]
        logging.debug(f"Running from source, base path: {base_path}")

    return base_path / relative_path


# --- Project Root Directory (for reference when not frozen) ---
# This is mainly for logging or non-frozen context now.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
logging.info(f"Project Root (source context) determined as: {PROJECT_ROOT}")


# ==============================================================================
# 3. FILE PATHS CONFIGURATION
# ==============================================================================

# --- CSV Input Folder ---
# Defines the *default* path where the application might look for input CSV files
# if not overridden by CLI arguments or other runtime configurations.
# It first checks if an environment variable 'CSV_INBOX' is set.
# If not, it defaults to a folder named 'csv_inbox' inside the PROJECT_ROOT.
# .expanduser() handles '~' notation (e.g., ~/Documents) if used in the path.
# REVIEW / TODO: The overall plan involves reading the *actual* inbox path
#                from the Excel 'Config' sheet during runtime when called from Excel.
#                This default path defined here might be used for standalone script runs,
#                testing, or as a fallback if the Excel read fails. We need to ensure
#                the Excel reading logic (in __init__.py or the =PY() cell) correctly
#                uses the path from the Excel sheet and potentially overrides this default.
CSV_INBOX_DEFAULT = Path(
    os.getenv("CSV_INBOX", PROJECT_ROOT / "csv_inbox")
).expanduser()
logging.info(f"Default CSV Inbox Path configured to: {CSV_INBOX_DEFAULT}")

# --- Schema Registry File Path ---
# Defines the location of the YAML file containing the rules for parsing CSVs.
# Uses get_resource_path to find it correctly whether frozen or not.
# Checks for 'SCHEMA_REGISTRY' environment variable first.
SCHEMA_REGISTRY_PATH = Path(
    os.getenv("SCHEMA_REGISTRY", get_resource_path("rules/schema_registry.yml"))
)
logging.info(f"Schema Registry Path configured to: {SCHEMA_REGISTRY_PATH}")

# --- Merchant Lookup File Path ---
# Defines the location of the CSV file used for merchant normalization rules.
# Uses get_resource_path to find it correctly whether frozen or not.
# Checks for 'MERCHANT_LOOKUP' environment variable first.
MERCHANT_LOOKUP_PATH = Path(
    os.getenv("MERCHANT_LOOKUP", get_resource_path("rules/merchant_lookup.csv"))
)
logging.info(f"Merchant Lookup Path configured to: {MERCHANT_LOOKUP_PATH}")

# --- Output Parquet Filename ---
# Defines the canonical name for the final Parquet output.
BALANCE_FINAL_PARQUET_FILENAME = os.getenv(
    "BALANCE_FINAL_PARQUET_FILENAME", "balance_final.parquet"
)
logging.info(f"Final Parquet Filename configured to: {BALANCE_FINAL_PARQUET_FILENAME}")


# Add other paths here as needed (e.g., output paths, database paths)
# OUTPUT_DIR = get_resource_path(os.getenv("OUTPUT_DIR", "output"))
# OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", PROJECT_ROOT / "output")).expanduser()

# ==============================================================================
# 4. LOGGING CONFIGURATION
# ==============================================================================

# --- Logging Level ---
# Sets the detail level for logging messages.
# Checks for 'LOG_LEVEL' environment variable, defaulting to 'INFO'.
# Common levels: DEBUG, INFO, WARNING, ERROR, CRITICAL.
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# --- Basic Logging Setup ---
# Configures the root logger for the application.
# This setup applies unless more specific logger configurations are made elsewhere.
# Format includes timestamp, log level, logger name, and the message.
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",  # Added specific date format
)
# Example of getting a logger specific to this module
# logger = logging.getLogger(__name__)
# logger.info("Logging configured.") # Use module-specific logger if preferred

# ==============================================================================
# 5. FEATURE FLAGS (Examples)
# ==============================================================================
# Used to enable/disable certain features, often for testing or phased rollout.

# --- Use Polars Library ---
# Example flag: Check 'USE_POLARS' environment variable (defaults to 'false').
# Converts the value to lowercase and checks if it's 'true'.
USE_POLARS = os.getenv("USE_POLARS", "false").lower() == "true"
logging.info(f"Feature Flag - Use Polars: {USE_POLARS}")


# ==============================================================================
# END OF FILE: config.py
# ==============================================================================
