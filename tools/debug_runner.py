#!/usr/bin/env python3
###############################################################################
# BALANCE-pyexcel – Debug Runner
#
# Description : Standalone script to run the core balance calculations with
#               extensive logging. Useful when analyzer.py is too large to
#               debug directly.
# Key Concepts: - Modular data loading
#               - Detailed logging
#               - Path-independent execution
# Public API  : - main()
#               - setup_logging()
#               - run_debug_calculation()
# -----------------------------------------------------------------------------
# Change Log
# Date        Author      Type        Note
# 2025-06-09  Codex       add         Initial version
# 2025-06-09  Assistant   update      Added path handling, improved structure
###############################################################################
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from analyzer import AnalysisConfig

try:
    from core_calculations import CoreCalculator
    from data_loader_temp import load_all_data
except ImportError:  # pragma: no cover - optional modules
    CoreCalculator = None
    load_all_data = None


logger = logging.getLogger(__name__)

# Constants
DEFAULT_DATA_DIR = "data"
DEFAULT_OUTPUT_DIR = "output"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(log_dir: Path | None = None) -> None:
    """
    Configure logging with both file and console handlers.
    
    Args:
        log_dir: Directory for log files. Creates 'logs' directory if None.
    """
    if log_dir is None:
        log_dir = Path("logs")
    
    log_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"debug_run_{timestamp}.log"
    
    # Configure root logger
    logging.basicConfig(
        level=logging.DEBUG,
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    
    # Adjust third-party loggers if needed
    logging.getLogger("pandas").setLevel(logging.WARNING)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    
    logger.info("=== DEBUG RUN STARTED ===")
    logger.info("Log file: %s", log_file)


def validate_data_files(data_dir: Path) -> dict[str, Path]:
    """
    Validate that all required data files exist.
    
    Args:
        data_dir: Directory containing data files
        
    Returns:
        Dictionary mapping file type to Path object
        
    Raises:
        FileNotFoundError: If any required file is missing
    """
    required_files = {
        "expense": "Expense_History_20250527.csv",
        "ledger": "Transaction_Ledger_20250527.csv",
        "rent_alloc": "Rent_Allocation_20250527.csv",
        "rent_hist": "Rent_History_20250527.csv",
    }
    
    file_paths = {}
    missing_files = []
    
    for file_type, filename in required_files.items():
        file_path = data_dir / filename
        if not file_path.exists():
            missing_files.append(str(file_path))
        else:
            file_paths[file_type] = file_path
            size_kb = file_path.stat().st_size / 1024
            logger.info("Found %s file: %s (%.1f KB)", file_type, file_path, size_kb)
    
    if missing_files:
        error_msg = f"Missing required files: {', '.join(missing_files)}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)
    
    return file_paths


def load_and_validate_data(
    file_paths: dict[str, Path]
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Load all data files and perform basic validation.
    
    Args:
        file_paths: Dictionary mapping file type to Path
        
    Returns:
        Tuple of (expense_df, ledger_df, rent_alloc_df, rent_hist_df)
        
    Raises:
        ValueError: If data validation fails
    """
    logger.info("Loading data files...")
    
    try:
        expense_df, ledger_df, rent_alloc_df, rent_hist_df = load_all_data(
            file_paths["expense"],
            file_paths["ledger"],
            file_paths["rent_alloc"],
            file_paths["rent_hist"],
        )
    except Exception as e:
        logger.error("Failed to load data: %s", e)
        raise
    
    # Log basic statistics
    dataframes = {
        "Expenses": expense_df,
        "Ledger": ledger_df,
        "Rent Allocation": rent_alloc_df,
        "Rent History": rent_hist_df,
    }
    
    for name, df in dataframes.items():
        logger.info(
            "%s: %d rows, %d columns, columns=%s",
            name,
            len(df),
            len(df.columns),
            list(df.columns)[:5],  # Show first 5 columns
        )
        
        # Check for empty dataframes
        if df.empty:
            logger.warning("%s dataframe is empty!", name)
    
    return expense_df, ledger_df, rent_alloc_df, rent_hist_df


def run_debug_calculation(
    config: AnalysisConfig,
    expense_df: pd.DataFrame,
    ledger_df: pd.DataFrame,
    rent_alloc_df: pd.DataFrame,
    rent_hist_df: pd.DataFrame,
) -> dict[str, Any]:
    """
    Run the core balance calculation with detailed logging.
    
    Args:
        config: Analysis configuration
        expense_df: Expense history dataframe
        ledger_df: Transaction ledger dataframe
        rent_alloc_df: Rent allocation dataframe
        rent_hist_df: Rent history dataframe
        
    Returns:
        Dictionary containing calculation results
    """
    logger.info("Starting balance calculation...")
    
    # Using ledger_df directly as master_ledger
    master_ledger = ledger_df
    
    logger.debug("Master ledger shape: %s", master_ledger.shape)
    logger.debug("Master ledger columns: %s", list(master_ledger.columns))
    
    # Initialize calculator and run reconciliation
    calculator = CoreCalculator(config)
    
    try:
        result = calculator.triple_reconciliation(master_ledger)
    except Exception as e:
        logger.error("Calculation failed: %s", e, exc_info=True)
        raise
    
    # Log results
    logger.info("=== CALCULATION RESULTS ===")
    logger.info("Who owes whom: %s", result.get("who_owes_whom", "N/A"))
    logger.info("Amount owed: $%.2f", result.get("amount_owed", 0))
    logger.info(
        "Reconciliation status: %s",
        "PASSED" if result.get("reconciled") else "FAILED"
    )
    
    # Log any warnings or discrepancies
    if "warnings" in result:
        for warning in result["warnings"]:
            logger.warning("Reconciliation warning: %s", warning)
    
    return result


def save_results(result: dict[str, Any], output_dir: Path) -> Path:
    """
    Save calculation results to JSON file.
    
    Args:
        result: Calculation results dictionary
        output_dir: Directory for output files
        
    Returns:
        Path to saved file
    """
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"balance_result_{timestamp}.json"
    
    # Add metadata to results
    result_with_metadata = {
        "timestamp": timestamp,
        "version": "1.0",
        "results": result,
    }
    
    try:
        output_file.write_text(json.dumps(result_with_metadata, indent=2))
        logger.info("Results saved to: %s", output_file)
        return output_file
    except Exception as e:
        logger.error("Failed to save results: %s", e)
        raise


def main() -> None:
    """Execute the debug runner with comprehensive error handling."""
    try:
        # Setup logging
        setup_logging()
        
        # Initialize configuration
        config = AnalysisConfig()
        logger.info("Configuration loaded: %s", config.__dict__)
        
        # Validate data files
        data_dir = Path(DEFAULT_DATA_DIR)
        file_paths = validate_data_files(data_dir)
        
        # Load data
        expense_df, ledger_df, rent_alloc_df, rent_hist_df = load_and_validate_data(
            file_paths
        )
        
        # Run calculation
        result = run_debug_calculation(
            config, expense_df, ledger_df, rent_alloc_df, rent_hist_df
        )
        
        # Save results
        output_dir = Path(DEFAULT_OUTPUT_DIR)
        output_file = save_results(result, output_dir)
        
        logger.info("=== DEBUG RUN COMPLETED SUCCESSFULLY ===")
        logger.info("Check %s for detailed results", output_file)
        
    except FileNotFoundError as e:
        logger.error("File error: %s", e)
        sys.exit(1)
    except ImportError as e:
        logger.error("Import error: %s", e)
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        sys.exit(1)
    finally:
        logger.info("=== DEBUG RUN ENDED ===")


if __name__ == "__main__":
    main()