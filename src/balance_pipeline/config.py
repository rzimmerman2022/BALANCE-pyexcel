# -*- coding: utf-8 -*-
"""
==============================================================================
Module: config.py
Project: BALANCE-pyexcel
Description: Centralized configuration settings for the application.
             Loads settings from environment variables (via a .env file if present)
             with sensible defaults. Serves as the single source of truth for
             configurable parameters during the transition to config_v2.py.
             
Note: This module is being gradually replaced by config_v2.py. New code
      should prefer using PipelineConfig from config_v2.py. This module
      remains for backward compatibility with existing code.
==============================================================================

Version: 0.1.2
Last Modified: 2025-01-21
"""

# ==============================================================================
# 0. IMPORTS
# ==============================================================================
from __future__ import annotations
from pathlib import Path
import os
import sys
import logging
from typing import List, Dict, Final
from dotenv import load_dotenv

# Import the new centralized column definitions
from .foundation import CORE_FOUNDATION_COLUMNS

# ==============================================================================
# 1. ENVIRONMENT SETUP
# ==============================================================================
# Load environment variables before anything else
# This ensures all configuration has access to these values
load_dotenv()

# Set up module logger early so we can log configuration loading
logger = logging.getLogger(__name__)

# ==============================================================================
# 2. PATH RESOLUTION HELPERS
# ==============================================================================
def get_resource_path(relative_path: str | Path) -> Path:
    """
    Get absolute path to resource, works for dev and for PyInstaller.
    
    This function handles the complexity of finding resources whether
    the code is running from source or from a frozen executable.
    
    Args:
        relative_path: Path relative to the project root
        
    Returns:
        Absolute path to the resource
    """
    if hasattr(sys, "_MEIPASS"):
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = Path(getattr(sys, "_MEIPASS"))
        logger.debug(f"Running frozen (PyInstaller), base path: {base_path}")
    else:
        # Not frozen, running in normal Python environment
        base_path = Path(__file__).resolve().parents[2]
        logger.debug(f"Running from source, base path: {base_path}")
    
    return base_path / relative_path


# Determine project root for path resolution
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
logger.debug(f"Project root determined as: {PROJECT_ROOT}")

# ==============================================================================
# 3. CORE CONFIGURATION CONSTANTS
# ==============================================================================
# These are the fundamental settings that rarely change

# Application metadata
APP_NAME: Final[str] = "BALANCE-pyexcel"
APP_VERSION: Final[str] = "0.1.2"

# ==============================================================================
# 4. PATH CONFIGURATION
# ==============================================================================
# All paths should be configurable via environment variables
# with sensible defaults for development

# Input/Output Paths
CSV_INBOX_DEFAULT: Final[Path] = Path(
    os.getenv("CSV_INBOX", str(PROJECT_ROOT / "csv_inbox"))
).expanduser().resolve()

OUTPUT_DIR_DEFAULT: Final[Path] = Path(
    os.getenv("OUTPUT_DIR", str(PROJECT_ROOT / "output"))
).expanduser().resolve()

# Rule File Paths
SCHEMA_REGISTRY_PATH: Final[Path] = Path(
    os.getenv("SCHEMA_REGISTRY", str(get_resource_path("rules/schema_registry.yml")))
).resolve()

MERCHANT_LOOKUP_PATH: Final[Path] = Path(
    os.getenv("MERCHANT_LOOKUP", str(get_resource_path("rules/merchant_lookup.csv")))
).resolve()

# Output Filenames
BALANCE_FINAL_PARQUET_FILENAME: Final[str] = os.getenv(
    "BALANCE_FINAL_PARQUET_FILENAME", 
    "balance_final.parquet"
)

# ==============================================================================
# 5. DATA PROCESSING CONFIGURATION
# ==============================================================================
# Settings that control how data is processed

# Schema Configuration - Validate before making it final
# This is the key insight: we validate the value BEFORE declaring it as Final
_schema_mode_raw = os.getenv("SCHEMA_MODE", "strict").lower()
if _schema_mode_raw not in ["strict", "flexible"]:
    logger.warning(
        f"Invalid SCHEMA_MODE '{_schema_mode_raw}' specified. Defaulting to 'strict'."
    )
    _schema_mode_raw = "strict"

# Now we can safely declare it as a mutable value (not Final)
# This allows other parts of the code to modify it if needed
SCHEMA_MODE: str = _schema_mode_raw

# Column Definitions
# Using the centralized definitions from foundation.py
CORE_REQUIRED_COLUMNS: Final[List[str]] = CORE_FOUNDATION_COLUMNS

# Optional Column Groups - these are only included when they contain data
OPTIONAL_COLUMN_GROUPS: Final[Dict[str, List[str]]] = {
    "banking": [
        "AccountLast4",      # Last 4 digits of account
        "AccountType",       # Checking, Savings, etc.
        "Institution",       # Bank name
        "ReferenceNumber",   # Check numbers, transaction IDs
    ],
    "statements": [
        "StatementStart",    # Statement period start date
        "StatementEnd",      # Statement period end date
        "StatementPeriodDesc", # Human-readable period description
    ],
    "aggregator": [
        "OriginalDate",      # Date from aggregator if different
        "AccountNumber",     # Full account number from aggregator
        "Tags",              # User-defined tags from aggregator
    ],
    "descriptive": [
        "OriginalDescription", # Raw description from source
        "Description",         # Cleaned/shorter description
        "Category",           # Transaction category
        "Note",               # User notes
    ],
    "metadata": [
        "DataSourceName",    # Which source system
        "DataSourceDate",    # When data was extracted
        "Currency",          # Currency code
        "PostDate",          # Settlement date
        "Extras",            # JSON blob for unmapped fields
    ]
}

# ==============================================================================
# 6. OUTPUT FORMAT CONFIGURATION
# ==============================================================================
# This section is where we fix the Final assignment error
# The key is to validate BEFORE declaring as Final

# First, define the supported formats as a constant
SUPPORTED_OUTPUT_FORMATS: Final[Dict[str, str]] = {
    "parquet": ".parquet",
    "excel": ".xlsx",
    "csv": ".csv",
    "json": ".json",
}

# Now validate the default format BEFORE declaring it as Final
# This is the pattern: validate first, then declare as Final
_default_format_raw = os.getenv("DEFAULT_OUTPUT_FORMAT", "parquet")
if _default_format_raw not in SUPPORTED_OUTPUT_FORMATS:
    logger.warning(
        f"Invalid DEFAULT_OUTPUT_FORMAT '{_default_format_raw}'. "
        f"Defaulting to 'parquet'. Valid options: {list(SUPPORTED_OUTPUT_FORMATS.keys())}"
    )
    _default_format_raw = "parquet"

# NOW we can safely declare it as Final with the validated value
DEFAULT_OUTPUT_FORMAT: Final[str] = _default_format_raw

# Output-specific settings
EXCEL_SHEET_NAME: Final[str] = os.getenv("EXCEL_SHEET_NAME", "Transactions")
PARQUET_COMPRESSION: Final[str] = os.getenv("PARQUET_COMPRESSION", "snappy")

# ==============================================================================
# 7. LOGGING CONFIGURATION
# ==============================================================================
# Logging settings
LOG_LEVEL: Final[str] = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT: Final[str] = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"

# Configure basic logging only if it hasn't been configured yet
# This prevents multiple calls to basicConfig when modules are imported
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
    )

# ==============================================================================
# 8. FEATURE FLAGS
# ==============================================================================
# Flags to enable/disable features
# These use the same pattern: get the value, validate it, then declare as Final

USE_POLARS: Final[bool] = os.getenv("USE_POLARS", "false").lower() == "true"
ENABLE_DEBUG_TRACES: Final[bool] = os.getenv("ENABLE_DEBUG_TRACES", "false").lower() == "true"
USE_COMPREHENSIVE_CLEANER: Final[bool] = os.getenv("USE_COMPREHENSIVE_CLEANER", "true").lower() == "true"

# ==============================================================================
# 9. VALIDATION AND HEALTH CHECKS
# ==============================================================================
def validate_configuration() -> List[str]:
    """
    Validates the configuration and returns a list of any issues found.
    
    This helps catch configuration problems early, before they cause
    runtime errors deep in the code.
    
    Returns:
        List of warning/error messages. Empty list means configuration is valid.
    """
    issues = []
    
    # Check critical paths exist
    if not SCHEMA_REGISTRY_PATH.exists():
        issues.append(f"Schema registry not found at: {SCHEMA_REGISTRY_PATH}")
    
    if not MERCHANT_LOOKUP_PATH.exists():
        issues.append(f"Merchant lookup not found at: {MERCHANT_LOOKUP_PATH}")
    
    # Check output directory is writable
    try:
        OUTPUT_DIR_DEFAULT.mkdir(parents=True, exist_ok=True)
        test_file = OUTPUT_DIR_DEFAULT / ".write_test"
        test_file.touch()
        test_file.unlink()
    except Exception as e:
        issues.append(f"Cannot write to output directory {OUTPUT_DIR_DEFAULT}: {e}")
    
    # Warn about deprecated features
    if USE_POLARS:
        issues.append("USE_POLARS is experimental and may not be fully supported")
    
    return issues

# ==============================================================================
# 10. CONFIGURATION SUMMARY
# ==============================================================================
def print_configuration(show_all: bool = False) -> None:
    """
    Prints the current configuration for debugging purposes.
    
    Args:
        show_all: If True, shows all configuration values. 
                  If False, only shows the most important ones.
    """
    print("\n=== BALANCE-pyexcel Configuration ===")
    print(f"Project Root: {PROJECT_ROOT}")
    print(f"Schema Mode: {SCHEMA_MODE}")
    print(f"Default Output Format: {DEFAULT_OUTPUT_FORMAT}")
    print(f"Log Level: {LOG_LEVEL}")
    
    if show_all:
        print("\nPaths:")
        print(f"  CSV Inbox: {CSV_INBOX_DEFAULT}")
        print(f"  Output Dir: {OUTPUT_DIR_DEFAULT}")
        print(f"  Schema Registry: {SCHEMA_REGISTRY_PATH}")
        print(f"  Merchant Lookup: {MERCHANT_LOOKUP_PATH}")
        
        print("\nFeature Flags:")
        print(f"  Use Polars: {USE_POLARS}")
        print(f"  Debug Traces: {ENABLE_DEBUG_TRACES}")
        print(f"  Comprehensive Cleaner: {USE_COMPREHENSIVE_CLEANER}")
    
    # Run validation
    issues = validate_configuration()
    if issues:
        print("\nConfiguration Issues:")
        for issue in issues:
            print(f"  ⚠️  {issue}")
    else:
        print("\n✅ Configuration is valid")

# ==============================================================================
# 11. MODULE INITIALIZATION
# ==============================================================================
# Run validation when module is imported, but don't fail the import
# This allows the module to load even if some paths don't exist yet
_validation_issues = validate_configuration()
if _validation_issues:
    for issue in _validation_issues:
        logger.warning(f"Configuration issue: {issue}")
else:
    logger.debug("Configuration validated successfully")

# Log key configuration values at module import
logger.info(f"Loaded {APP_NAME} configuration v{APP_VERSION}")
logger.debug(f"Schema mode: {SCHEMA_MODE}, Output format: {DEFAULT_OUTPUT_FORMAT}")

# ==============================================================================
# 12. BACKWARDS COMPATIBILITY
# ==============================================================================
# If other modules expect certain attributes that we've reorganized,
# we can provide them here for compatibility
# This section can be removed once all code is updated to use the new structure