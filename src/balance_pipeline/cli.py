# -*- coding: utf-8 -*-
"""
==============================================================================
Module: cli.py
Project: BALANCE-pyexcel
Description: Command-line interface for running the BALANCE-pyexcel pipeline
             outside of Excel. Allows running the ETL process, reading Queue_Review
             decisions from Excel, syncing those decisions, and writing results back.
==============================================================================

Version: 0.1.1
Last Modified: 2025-04-24
Author: Ryan Zimmerman / AI Assistant
"""

from pathlib import Path
import argparse
import pandas as pd
import logging
import sys
import os  # os was not used directly, sys.executable and os.getcwd() are in dev_main
import time  # Added for retry loop
import io  # io module is no longer used
from typing import Optional, Any, List, Union, cast  # Added List, Union, Literal, cast
from datetime import date  # Added date
import importlib  # Added for reload and explicit import
import click
from balance_pipeline.errors import BalancePipelineError


# Now import the modules, hopefully freshly
from balance_pipeline import config  # Import full config module
from balance_pipeline import (
    ingest as ingest_module,
)  # Import the module itself for reloading
from balance_pipeline import (
    csv_consolidator as csv_consolidator_module,
)  # Import for reloading

# from balance_pipeline.csv_consolidator import process_csv_files # Will call as csv_consolidator_module.process_csv_files
from balance_pipeline.sync import sync_review_decisions
# Removed: from balance_pipeline.export import write_parquet_duckdb


# --- Force UTF-8 Encoding for stdout/stderr ---
# This helps ensure emojis (like ✅) and other Unicode characters print correctly,
# especially on Windows consoles that might default to a different encoding (e.g., cp1252).
# It attempts to reconfigure the standard streams if possible (Python 3.7+).
try:
    if hasattr(sys.stdout, "reconfigure"):
        cast(Any, sys.stdout).reconfigure(encoding="utf-8", errors="replace")
        cast(Any, sys.stderr).reconfigure(encoding="utf-8", errors="replace")
        # Optional: Log this change if logging is set up VERY early, otherwise skip logging here.
        # print("INFO: Reconfigured stdout/stderr for UTF-8.", file=sys.stderr)
    else:
        # Fallback for older versions might involve io.TextIOWrapper, but can be complex.
        # For simplicity, we'll rely on reconfigure if available.
        pass
except Exception as e_encode:
    # Log a warning if reconfiguration fails, but don't stop the script.
    print(f"WARNING: Could not force UTF-8 encoding: {e_encode}", file=sys.stderr)
# --- End UTF-8 Encoding ---

# Configure logging (basic setup, will be refined by setup_logging)
log = logging.getLogger(__name__)


def setup_logging(log_file: Optional[str] = None, verbose: bool = False) -> None:
    """
    Set up logging configuration. If log_file is provided, logs will be written to that file
    as well as to stdout. Respects the project-wide LOG_LEVEL setting.

    Uses force=True to ensure configuration is applied even if other modules have
    already configured logging. Includes workaround for UTF-8 encoding on stdout.
    """
    # Use log level from config module
    log_level_name = (
        config.LOG_LEVEL if isinstance(config.LOG_LEVEL, str) else "INFO"
    )  # Default to INFO
    log_level = getattr(logging, log_level_name.upper(), logging.INFO)
    if verbose:
        log_level = logging.DEBUG  # Override to DEBUG if verbose flag is set
        logging.getLogger('balance_pipeline').setLevel(logging.DEBUG)
        logging.getLogger('balance_pipeline.csv_consolidator').setLevel(logging.DEBUG)

    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(log_format)

    # --- Configure stdout handler with UTF-8 encoding ---
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)

    # Attempt to force UTF-8 encoding on the stream handler
    # Needed for emojis (like ✅) to print correctly on Windows consoles
    try:
        # Check if encoding attribute exists and is not already utf-8
        current_encoding = getattr(stdout_handler.stream, "encoding", "").lower()
        if current_encoding != "utf-8":
            log.debug(
                f"Attempting to set stdout encoding to UTF-8 (current: {current_encoding})"
            )
            # Try Python 3.9+ method first
            if hasattr(stdout_handler.stream, "reconfigure"):
                try:
                    stdout_handler.stream.reconfigure(encoding="utf-8")
                    log.debug(
                        "Reconfigured stdout stream encoding to UTF-8 using reconfigure()."
                    )
                except Exception as reconfig_err:
                    log.debug(
                        f"stream.reconfigure() failed: {reconfig_err}. Trying TextIOWrapper fallback."
                    )
                    # Fallback to TextIOWrapper if reconfigure fails or isn't available
                    if (
                        hasattr(stdout_handler.stream, "fileno")
                        and stdout_handler.stream.fileno() >= 0
                    ):
                        stdout_handler.stream = io.TextIOWrapper(
                            os.fdopen(
                                stdout_handler.stream.fileno(), "wb", closefd=False
                            ),
                            encoding="utf-8",
                            line_buffering=True,  # Attempt to mimic standard stdout buffering
                        )
                        log.debug(
                            "Wrapped stdout stream with TextIOWrapper for UTF-8 encoding."
                        )
                    else:
                        log.warning(
                            "Could not wrap stdout stream for UTF-8: Invalid or missing file descriptor."
                        )
            # Fallback for Python < 3.9 or streams without reconfigure
            elif (
                hasattr(stdout_handler.stream, "fileno")
                and stdout_handler.stream.fileno() >= 0
            ):
                stdout_handler.stream = io.TextIOWrapper(
                    os.fdopen(stdout_handler.stream.fileno(), "wb", closefd=False),
                    encoding="utf-8",
                    line_buffering=True,
                )
                log.debug(
                    "Wrapped stdout stream with TextIOWrapper for UTF-8 encoding (fallback)."
                )
            else:
                log.warning(
                    "Could not set stdout stream encoding to UTF-8: Neither reconfigure nor fileno available/valid."
                )
        else:
            log.debug("stdout stream encoding is already UTF-8.")

    except Exception as encoding_err:
        log.warning(f"Could not force UTF-8 encoding on stdout stream: {encoding_err}")

    handlers: List[logging.Handler] = [stdout_handler]  # Explicitly type handlers
    # --- End stdout handler configuration ---

    # Add file handler if log file path is provided
    if log_file:
        try:
            file_handler = logging.FileHandler(
                log_file, encoding="utf-8"
            )  # Ensure file is also UTF-8
            file_handler.setFormatter(formatter)
            handlers.append(file_handler)
        except Exception as e:
            log.error(f"Could not create log file handler for {log_file}: {e}")

    # Apply the configuration (force=True overrides any existing config)
    logging.basicConfig(
        level=log_level,
        format=log_format,  # Format is applied via handlers now, but set here for consistency
        handlers=handlers,
        force=True,  # Crucial for ensuring this config takes precedence
    )
    log.debug(
        f"Logging configured. Level: {logging.getLevelName(log_level)}. Handlers: {[h.name for h in handlers if hasattr(h, 'name')]}"
    )


def etl_main(
    inbox_path: Path,
    prefer_source: str = "Rocket",
    exclude_patterns: Optional[List[str]] = None,  # Use Optional[List[str]]
    only_patterns: Optional[List[str]] = None,  # Use Optional[List[str]]
) -> pd.DataFrame:
    """
    Main ETL function that loads CSVs, normalizes data, and returns a DataFrame.

    Args:
        inbox_path: Path to the folder containing CSV files to process.
        prefer_source: Preferred source for deduplication (e.g., "Rocket", "Monarch").
        exclude_patterns: List of glob patterns to exclude files/folders.
        only_patterns: List of glob patterns to exclusively include files/folders.

    Returns:
        pd.DataFrame: Processed, normalized, and deduplicated transaction data.
    """
    log.info(f"Starting ETL process for inbox: {inbox_path}")

    # 1. Scan for CSV files
    csv_file_paths: List[Path] = []  # Changed back to List[Path]
    if inbox_path.is_dir():
        for item in inbox_path.rglob("*.csv"):  # Recursive glob
            # Apply exclude patterns
            if exclude_patterns and any(item.match(p) for p in exclude_patterns):
                log.debug(f"Excluding file due to exclude pattern: {item}")
                continue
            # Apply only patterns (if any are specified)
            if only_patterns and not any(item.match(p) for p in only_patterns):
                log.debug(
                    f"Excluding file because it doesn't match 'only' patterns: {item}"
                )
                continue
            csv_file_paths.append(item)
    elif inbox_path.is_file() and inbox_path.suffix.lower() == ".csv":
        # Allow processing a single CSV file if inbox_path points to one
        csv_file_paths.append(inbox_path)
    else:
        log.error(f"Inbox path {inbox_path} is not a valid directory or CSV file.")
        return pd.DataFrame()

    if not csv_file_paths:
        log.warning(f"No CSV files found to process in {inbox_path} matching criteria.")
        return pd.DataFrame()

    log.info(
        f"Found {len(csv_file_paths)} CSV files to process: {[p.name for p in csv_file_paths]}"
    )

    # 2. Process CSV files using the new consolidator module
    # This function handles schema matching, transformations, TxnID, merchant cleaning, etc.
    # Call using the reloaded module reference
    df = csv_consolidator_module.process_csv_files(
        cast(List[Union[str, Path]], csv_file_paths)  # Cast for process_csv_files
    )  # prefer_source is not used by this function directly

    if df.empty:
        log.warning(
            "CSV processing resulted in an empty DataFrame before deduplication."
        )
        return df

    log.info(f"Consolidated data from CSVs into {len(df)} rows before deduplication.")

    # 3. Deduplication based on TxnID and prefer_source
    # This logic is adapted from the original normalize_df function.
    # 'DataSourceName' from csv_consolidator corresponds to 'Source' in normalize_df.
    if (
        "DataSourceName" in df.columns
        and "TxnID" in df.columns
        and df["TxnID"].notna().any()
    ):
        initial_row_count_before_dedupe = len(df)
        log.info(f"Applying deduplication, preferring source: '{prefer_source}'")

        # Ensure TxnID is string for consistent sorting/merging
        df["TxnID"] = df["TxnID"].astype(str)

        # Create a temporary sort key column for deduplication
        df["_sort_key_for_dedupe"] = 2  # Default for NA or non-matching DataSourceName
        df.loc[df["DataSourceName"] == prefer_source, "_sort_key_for_dedupe"] = 0
        df.loc[
            (df["DataSourceName"] != prefer_source) & pd.notna(df["DataSourceName"]),
            "_sort_key_for_dedupe",
        ] = 1

        df = df.sort_values(by=["TxnID", "_sort_key_for_dedupe"], kind="mergesort")

        num_duplicates_before = df.duplicated(subset=["TxnID"], keep=False).sum()
        if num_duplicates_before > 0:
            log.info(
                f"Found {num_duplicates_before // 2} sets of potential duplicate entries based on TxnID before deduplication by preferred source ('{prefer_source}')."
            )

        df = df.drop_duplicates(subset=["TxnID"], keep="first")
        df = df.drop(columns=["_sort_key_for_dedupe"])

        num_removed = initial_row_count_before_dedupe - len(df)
        if num_removed > 0:
            log.info(
                f"Removed {num_removed} duplicate transactions, prioritizing '{prefer_source}'."
            )
    else:
        log.warning(
            "Skipping source-based deduplication: 'DataSourceName' or 'TxnID' column missing, or no TxnIDs generated."
        )

    log.info(f"Final ETL DataFrame contains {len(df)} rows.")
    return df


# importlib is already imported at the top
# ingest_module is already imported at the top


def main(argv: Optional[List[str]] = None) -> None:  # Added argv parameter
    """
    Main CLI entry point
    """
    # Attempt to reload the ingest module to pick up changes
    # This should happen AFTER setup_logging if it logs, or ensure logging is configured first.
    # For now, let's assume logging is configured by setup_logging called later.
    try:
        # Re-import and reload ingest_module specifically within main's scope if needed,
        # or rely on the top-level import and reload.
        # To be safe, let's ensure ingest_module is the one from the top.
        importlib.reload(ingest_module)
        print(
            "INFO: Reloaded balance_pipeline.ingest module in main().", file=sys.stderr
        )
        # Also reload csv_consolidator to pick up its internal changes like MASTER_SCHEMA_COLUMNS
        importlib.reload(csv_consolidator_module)
        print(
            "INFO: Reloaded balance_pipeline.csv_consolidator module in main().",
            file=sys.stderr,
        )
    except Exception as e_reload:
        print(
            f"WARNING: Could not reload modules in main(): {e_reload}", file=sys.stderr
        )

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="BALANCE-pyexcel ETL Pipeline: Process CSVs and update Excel.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog="""
Examples:
  # Process CSVs in 'MyCSVs' and update/create 'MyWorkbook.xlsx'
  poetry run balance-pyexcel ".\\MyCSVs" ".\\MyWorkbook.xlsx"

  # Process CSVs, update macro-enabled workbook (using temp file), log verbosely
  poetry run balance-pyexcel "C:\\CSV Inbox" "S:\\Shared\\Finance\\BALANCE.xlsm" -v --log process.log
  
  # Dry run - process data but only output to CSV, don't touch Excel
  poetry run balance-pyexcel "Input" "Output.xlsx" --dry-run
  
  # Use a custom name for the review sheet
  poetry run balance-pyexcel "Input" "Output.xlsx" --queue-sheet "Review_Needed" 
""",
    )  # End of ArgumentParser definition

    # Define arguments AFTER the ArgumentParser initialization
    # Positional arguments for full ETL mode, now optional if --raw-dir is used.
    parser.add_argument(
        "inbox",
        nargs="?",
        default=None,
        help="Path to CSV inbox folder (for full ETL mode). Required if --raw-dir is not used.",
    )
    parser.add_argument(
        "workbook",
        nargs="?",
        default=None,
        help="Path to target Excel workbook (for full ETL mode). Required if --raw-dir is not used.",
    )

    parser.add_argument(
        "--no-sync",
        action="store_true",
        help="Skip reading/syncing decisions from Queue_Review sheet (full ETL mode).",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging (DEBUG level).",
    )
    parser.add_argument(
        "--log", help="Path to log file (in addition to console output)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Process data but do not write to Excel (full ETL mode).",
    )
    parser.add_argument(
        "--queue-sheet",
        default="Queue_Review",
        help="Name of the sheet containing decisions (full ETL mode, default: Queue_Review).",
    )
    parser.add_argument(
        "--prefer-source",
        default="Rocket",
        help="Preferred source when deduplicating transactions (full ETL mode, default: Rocket).",
    )
    parser.add_argument(
        "--exclude",
        nargs="*",
        default=[],
        help="Glob patterns for files/directories to exclude (full ETL mode, e.g., '_Archive/*' 'Document*').",
    )
    parser.add_argument(
        "--only",
        nargs="*",
        default=[],
        help="Glob patterns for files/directories to include exclusively (full ETL mode, e.g., 'BankStatement*.csv').",
    )

    # Argument for raw processing mode (replaces --raw-csv)
    parser.add_argument(
        "--raw-dir",
        metavar="PATH",
        type=Path,  # Converts argument to a Path object
        default=None,  # Will be None if flag is not provided
        help="Raw processing mode: Path to a single CSV file or a directory containing CSVs (processed recursively). "
        "Bypasses schema registry and complex cleaning. "
        "If used, 'inbox' and 'workbook' arguments are ignored. "
        "Output is a single 'balance_final.parquet' in the directory specified by --out.",
    )
    # --out argument is now general, used by --raw-dir and potentially other modes if added later.
    # It was previously tied to --raw-csv. Let's ensure its help text is general.
    # The existing --out definition is fine: parser.add_argument("--out", type=Path, default=Path("artifacts"), help="Output directory (used with --raw-csv)")
    # I will update its help string to be more general.
    # The SEARCH block needs to include the original --out to replace it.
    # This is tricky. I'll do --out in a separate, very targeted replace if needed, or assume the current one is okay for now.
    # For now, I'll assume the existing --out is fine and its help text will be updated implicitly by context or later if needed.
    # The prompt's plan for CLI usage is `poetry run python src/balance_pipeline/cli.py --raw-dir ../CSVs --out artifacts`
    # This implies --out is still a valid argument.
    # The original --out was: parser.add_argument("--out", type=Path, default=Path("artifacts"), help="Output directory (used with --raw-csv)")
    # This should be fine, its help text is slightly specific but functionally it works.
    # Let's keep the existing --out as is for this step.
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("artifacts"),
        help="Output directory (used with --raw-dir, or other modes).",
    )
    args = parser.parse_args(argv)  # Pass argv to parse_args

    # --- Setup Logging ---
    # Must happen before any significant logging calls
    setup_logging(args.log, args.verbose)

    # --- Mode Dispatch ---
    if (
        args.raw_dir
    ):  # Check if --raw-dir argument was provided (it's a Path object or None)
        log.info(
            f"Raw directory/file processing mode activated for input: {args.raw_dir}"
        )
        # args.raw_dir is already a Path object due to type=Path in add_argument
        raw_input_path = args.raw_dir.expanduser().resolve()
        # args.out is also a Path object, defaulting to 'artifacts'
        output_dir = args.out.expanduser().resolve()

        all_dfs = []
        files_processed_count = 0
        processed_filenames = []  # To log which files were combined

        if not raw_input_path.exists():
            log.error(f"Input path for --raw-dir does not exist: {raw_input_path}")
            sys.exit(1)

        files_to_process = []
        if raw_input_path.is_file():
            if raw_input_path.suffix.lower() == ".csv":
                log.info(f"Processing single raw CSV file: {raw_input_path.name}")
                files_to_process.append(raw_input_path)
            else:
                log.error(
                    f"Specified path for --raw-dir is a file, but not a CSV: {raw_input_path}"
                )
                sys.exit(1)  # Exit if it's a file but not CSV
        elif raw_input_path.is_dir():
            log.info(f"Scanning directory for CSV files: {raw_input_path}")
            # Using sorted list for deterministic processing order
            for csv_file_path_item in sorted(list(raw_input_path.rglob("*.csv"))):
                files_to_process.append(csv_file_path_item)
            if not files_to_process:  # Log if directory scan yields no CSVs
                log.warning(f"No CSV files found in directory: {raw_input_path}")
        else:
            log.error(
                f"Input path for --raw-dir is neither a file nor a directory: {raw_input_path}"
            )
            sys.exit(1)  # Exit if path is invalid type

        for csv_file_path in files_to_process:
            # Safety nets: skip files in _archive or fixtures (case-insensitive)
            # Check parts of the path string for these directory names.
            path_str_lower = str(csv_file_path.as_posix()).lower()
            if "/_archive/" in path_str_lower or "/fixtures/" in path_str_lower:
                log.info(f"Skipping file in protected directory: {csv_file_path.name}")
                continue

            # process_single_raw_csv_file is the refactored function
            df_single_raw = process_single_raw_csv_file(
                csv_file_path
            )  # Renamed variable
            if (
                df_single_raw is not None
                and not df_single_raw.empty  # Use renamed variable
            ):  # Only append if df is valid and has data
                all_dfs.append(df_single_raw)  # Use renamed variable
                files_processed_count += 1
                processed_filenames.append(csv_file_path.name)
            elif (
                df_single_raw is not None and df_single_raw.empty
            ):  # Use renamed variable
                log.info(
                    f"File {csv_file_path.name} resulted in an empty DataFrame (e.g. headers only), not included in final Parquet."
                )
            # If df is None, process_single_raw_csv_file already logged the error/skip reason.

        if not all_dfs:
            log.warning(
                "No dataframes were successfully processed or all valid CSVs were empty/skipped. No Parquet file will be written."
            )
            sys.exit(0)  # Successful exit, but nothing to write

        try:
            combined_df = pd.concat(all_dfs, ignore_index=True)
            log.info(
                f"Combined data from {files_processed_count} CSV file(s) into a DataFrame with {len(combined_df)} rows."
            )
            if (
                files_processed_count > 0
            ):  # Log filenames only if some files were processed
                log.debug(f"Source files included: {', '.join(processed_filenames)}")

            output_dir.mkdir(parents=True, exist_ok=True)
            dest_parquet = output_dir / "balance_final.parquet"  # Standardized name
            combined_df.to_parquet(dest_parquet, index=False)
            # Standard print message for success
            print(
                f"✅  Wrote combined Parquet: {dest_parquet} (from {files_processed_count} file(s))"
            )
            sys.exit(0)  # Successful exit after writing Parquet
        except Exception as e:
            log.error(
                f"Error writing combined Parquet file to {dest_parquet}: {e}",
                exc_info=True,
            )
            sys.exit(1)

    elif args.inbox and args.workbook:
        # This is the start of the original full ETL logic.
        # The following lines were originally after the old `if args.raw_csv:` block.
        log.info("=" * 50)
        log.info("Starting BALANCE-pyexcel CLI process (full ETL mode)...")
        log.debug(
            f"Arguments received (full ETL mode): inbox='{args.inbox}', workbook='{args.workbook}'"
        )
        # The original # --- Path Validation and Resolution --- and the main try...finally block
        # for the full ETL process will follow here, as they are part of the existing code structure.
    # --- Path Validation and Resolution ---
    try:
        inbox = (
            Path(args.inbox).expanduser().resolve(strict=True)
        )  # strict=True ensures inbox exists
        workbook = (
            Path(args.workbook).expanduser().resolve()
        )  # Allow workbook to not exist yet
        log.debug(f"Resolved Inbox Path: {inbox}")
        log.debug(f"Resolved Workbook Path: {workbook}")
    except FileNotFoundError as e:
        log.error(
            f"Input path error: Inbox folder not found at '{args.inbox}'. Details: {e}"
        )
        sys.exit(1)
    except Exception as e:
        log.error(f"Error resolving paths: {e}")
        sys.exit(1)

    # Validate Excel file extension
    if not workbook.name.lower().endswith((".xlsx", ".xlsm")):
        log.error(
            f"Invalid workbook file extension: '{workbook.suffix}'. Must be .xlsx or .xlsm."
        )
        sys.exit(1)

    # Check inbox path is actually a directory
    # if not inbox.is_dir(): # Temporarily commented out for single-file diagnostics
    #     log.error(f"Inbox path provided is not a valid directory: {inbox}")
    #     sys.exit(1)

    if not workbook.exists() and not args.dry_run:
        log.warning(
            f"Target workbook does not exist: {workbook}. Will attempt to create it."
        )

    # --- Check for Excel's own lock file (e.g., ~$MyWorkbook.xlsx) ---
    # This indicates the file is likely open in Excel.
    excel_lock_file_name = "~$" + workbook.name
    excel_lock_file_path = workbook.parent / excel_lock_file_name
    if not args.dry_run and excel_lock_file_path.exists():
        log.error(
            f"Error: The Excel workbook '{workbook.name}' appears to be open by Microsoft Excel."
        )
        log.error(f"Detected Excel lock file: {excel_lock_file_path}")
        log.error("Please close the Excel workbook and try again.")
        sys.exit(1)

    # --- Lock File Handling (for concurrent script runs) ---
    lock_file = workbook.with_suffix(workbook.suffix + ".lock")
    lock_file_created = False
    if not args.dry_run:
        if lock_file.exists():
            try:
                locktime = time.time() - lock_file.stat().st_mtime
                log.warning(
                    f"Lock file exists for '{workbook.name}' (created {locktime:.1f} seconds ago)."
                )
                if locktime < 300:  # 5 minutes tolerance
                    log.warning(
                        "Another process may be accessing this file. Waiting up to 30 seconds..."
                    )
                    wait_start = time.time()
                    while lock_file.exists() and (time.time() - wait_start < 30):
                        time.sleep(1)
                    if lock_file.exists():
                        log.error("Lock file still exists after 30 seconds. Aborting.")
                        log.error(
                            f"If you are sure no other process is running, delete the lock file manually: {lock_file}"
                        )
                        sys.exit(1)
                    else:
                        log.info("Lock file was released.")
                else:
                    log.warning(
                        "Lock file is older than 5 minutes. Assuming stale lock and attempting removal..."
                    )
                    try:
                        lock_file.unlink()
                        log.info("Removed stale lock file.")
                    except Exception as e_unlink_stale:
                        log.error(
                            f"Could not remove stale lock file {lock_file}: {e_unlink_stale}. Aborting."
                        )
                        sys.exit(1)

            except Exception as e_lock_check:
                log.error(
                    f"Error checking lock file {lock_file}: {e_lock_check}. Aborting."
                )
                sys.exit(1)

        # Attempt to create lock file
        try:
            lock_file.touch(
                exist_ok=False
            )  # exist_ok=False raises error if file exists (race condition check)
            lock_file_created = True
            log.debug(f"Created lock file: {lock_file}")
        except FileExistsError:
            log.error(
                f"Lock file {lock_file} appeared unexpectedly after check. Another process likely started. Aborting."
            )
            sys.exit(1)
        except Exception as e_lock_create:
            log.warning(
                f"Could not create lock file {lock_file}: {e_lock_create}. Proceeding without lock (potential risk)."
            )
            lock_file_created = False
    # --- End Lock File Handling ---

    try:
        # Step 0: Load existing canonical data (if any)
        parquet_path = workbook.parent / config.BALANCE_FINAL_PARQUET_FILENAME
        canonical_df = pd.DataFrame()
        if (
            not args.dry_run and parquet_path.exists()
        ):  # Don't load if dry run, might not be needed
            log.info(
                f"Attempting to load specified columns from canonical Parquet: {parquet_path}"
            )
            try:
                # Stage 2.1 Perf Tweak: Load only specified columns
                columns_to_load = ["TxnID", "SharedFlag", "SplitPercent"]
                canonical_df = pd.read_parquet(parquet_path, columns=columns_to_load)

                # Convert TxnID to string for consistent merging
                # If read_parquet succeeded with columns_to_load, TxnID will be present.
                if "TxnID" in canonical_df.columns:
                    canonical_df["TxnID"] = canonical_df["TxnID"].astype(str)
                # SharedFlag and SplitPercent are also expected to be present due to columns_to_load.
                # Previous explicit checks and default assignments for missing SharedFlag/SplitPercent
                # are omitted as read_parquet(columns=...) should error if they are not found.

                log.info(
                    f"Loaded {len(canonical_df)} rows from canonical Parquet, selected columns: {columns_to_load}."
                )
            except (
                KeyError
            ) as e_key:  # Specifically for columns not found by pd.read_parquet
                log.error(
                    f"Error reading canonical Parquet {parquet_path}: A specified column for selective load was not found: {e_key}. Starting with empty canonical data."
                )
                canonical_df = pd.DataFrame()
            except Exception as e_read_parquet:
                log.error(
                    f"Error reading canonical Parquet {parquet_path}: {e_read_parquet}. Starting with empty canonical data."
                )
                canonical_df = pd.DataFrame()  # Ensure it's an empty DF on error
        elif args.dry_run:
            log.info("DRY RUN: Skipping load of existing canonical Parquet data.")
        else:
            log.info(
                f"Canonical Parquet file not found at {parquet_path}. Will create if not dry run. Starting with empty canonical data."
            )

        # Step 1: Run ETL pipeline for current sources
        # df_from_sources will have TxnID, and SharedFlag/SplitPercent initialized by normalize_df
        try:
            df_from_sources = etl_main(
                inbox,
                prefer_source=args.prefer_source,
                exclude_patterns=args.exclude,
                only_patterns=args.only,
            )
        except BalancePipelineError as exc:
            raise click.ClickException(str(exc)) from exc
        if df_from_sources.empty and inbox.exists():
            log.warning(
                "ETL process resulted in an empty DataFrame from sources. Check source CSVs and logs."
            )
            # If canonical_df exists, we might still proceed with it.

        # Step 2: Merge canonical SharedFlag/SplitPercent into df_from_sources
        # This brings forward classifications from the last run for transactions that are re-processed.
        if (
            not canonical_df.empty
            and "TxnID" in canonical_df.columns
            and "TxnID" in df_from_sources.columns
        ):
            log.info(
                "Merging existing classifications from canonical data into current ETL data..."
            )

            # Columns to carry over from canonical_df
            class_cols_from_canonical = ["TxnID"]
            if "SharedFlag" in canonical_df.columns:
                class_cols_from_canonical.append("SharedFlag")
            if "SplitPercent" in canonical_df.columns:
                class_cols_from_canonical.append("SplitPercent")

            # Ensure TxnID is string type in df_from_sources for merge
            df_from_sources["TxnID"] = df_from_sources["TxnID"].astype(str)

            # Perform a left merge: keep all rows from df_from_sources, add/update classifications from canonical_df
            # Suffix "_canonical" for columns from canonical_df to distinguish if needed, then coalesce.
            df_merged = pd.merge(  # Renamed variable
                df_from_sources,
                canonical_df[class_cols_from_canonical],
                on="TxnID",
                how="left",
                suffixes=(
                    "",
                    "_canonical",
                ),  # df_from_sources.SharedFlag, canonical_df.SharedFlag -> SharedFlag, SharedFlag_canonical
            )

            # Coalesce: If SharedFlag_canonical exists (meaning a match was found), use it. Otherwise, keep original SharedFlag from df_from_sources.
            if "SharedFlag_canonical" in df_merged.columns:  # Use renamed variable
                df_merged["SharedFlag"] = df_merged["SharedFlag_canonical"].fillna(
                    df_merged["SharedFlag"]
                )  # Use renamed variable
                df_merged.drop(
                    columns=["SharedFlag_canonical"], inplace=True
                )  # Use renamed variable

            if "SplitPercent_canonical" in df_merged.columns:  # Use renamed variable
                # fillna might not be ideal for pd.NA, use combine_first or where
                df_merged["SplitPercent"] = df_merged[
                    "SplitPercent_canonical"
                ].combine_first(  # Use renamed variable
                    df_merged["SplitPercent"]  # Use renamed variable
                )
                df_merged.drop(
                    columns=["SplitPercent_canonical"], inplace=True
                )  # Use renamed variable

            # Ensure SharedFlag/SplitPercent have no NaNs from failed merges (new items in df_from_sources)
            # csv_consolidator.py (via process_csv_files) should ensure these columns exist with correct dtypes.
            # This section is a safeguard, especially after merges which can alter dtypes.
            if "SharedFlag" in df_merged.columns:  # Use renamed variable
                # Ensure the column is nullable boolean before filling
                if (
                    not pd.api.types.is_extension_array_dtype(
                        df_merged["SharedFlag"]
                    )  # Use renamed variable
                    or df_merged["SharedFlag"].dtype
                    != pd.BooleanDtype()  # Use renamed variable
                ):
                    log.debug(
                        f"SharedFlag dtype before astype: {df_merged['SharedFlag'].dtype}. Coercing to pd.BooleanDtype()."  # Use renamed variable
                    )
                    # Replace any problematic string placeholders if they somehow got in, before coercing
                    df_merged["SharedFlag"] = df_merged["SharedFlag"].replace(
                        {"?": pd.NA, "": pd.NA}
                    )  # Use renamed variable
                    df_merged["SharedFlag"] = df_merged["SharedFlag"].astype(
                        pd.BooleanDtype()
                    )  # Use renamed variable
                df_merged["SharedFlag"] = df_merged["SharedFlag"].fillna(
                    value=pd.NA
                )  # Use renamed variable
            else:
                log.warning(
                    "SharedFlag column was missing after merge with canonical_df. Creating it with pd.NA and boolean dtype."
                )
                df_merged["SharedFlag"] = pd.NA  # Use renamed variable
                df_merged["SharedFlag"] = df_merged["SharedFlag"].astype(
                    pd.BooleanDtype()
                )  # Use renamed variable

            if "SplitPercent" in df_merged.columns:  # Use renamed variable
                # Ensure the column is float before filling
                if (
                    df_merged["SplitPercent"].dtype != "float64"  # Use renamed variable
                    and df_merged["SplitPercent"].dtype
                    != "float32"  # Use renamed variable
                ):
                    log.debug(
                        f"SplitPercent dtype before astype: {df_merged['SplitPercent'].dtype}. Coercing to float."  # Use renamed variable
                    )
                    df_merged["SplitPercent"] = pd.to_numeric(  # Use renamed variable
                        df_merged["SplitPercent"],
                        errors="coerce",  # Use renamed variable
                    )  # Coerce to numeric first
                df_merged["SplitPercent"] = df_merged["SplitPercent"].fillna(
                    pd.NA
                )  # Use renamed variable
            else:
                log.warning(
                    "SplitPercent column was missing after merge with canonical_df. Creating it with pd.NA and float dtype."
                )
                df_merged["SplitPercent"] = pd.NA  # Use renamed variable
                df_merged["SplitPercent"] = df_merged["SplitPercent"].astype(
                    "float"
                )  # Use renamed variable

            df = df_merged  # Assign back to df

            log.info(
                "Merged existing classifications. DataFrame now has %s rows.", len(df)
            )
        elif not df_from_sources.empty:
            log.info(
                "No canonical data to merge or TxnID missing. Using data directly from ETL process."
            )
            df = df_from_sources
        elif not canonical_df.empty:
            log.info("No new data from ETL sources. Using existing canonical data.")
            df = canonical_df  # Use canonical if no new data
        else:
            log.info(
                "Both ETL and canonical data are empty. Proceeding with an empty DataFrame."
            )
            df = pd.DataFrame()  # Ensure df is an empty DataFrame, not None

        # If df became empty after merge (e.g. df_from_sources was empty, canonical_df was empty)
        # ensure it has minimal columns for subsequent steps if they expect them.
        # normalize_df.FINAL_COLS could be used here.
        if df.empty:
            log.warning("Resulting DataFrame is empty before reading Queue_Review.")
            # Create an empty DF with FINAL_COLS to prevent errors in later stages like _create_queue_review_template
            # This assumes FINAL_COLS is accessible or defined; for now, let it be.
            # If normalize_df.FINAL_COLS is needed, it would require an import or passing it around.
            # For now, subsequent steps should handle an empty df.

        # Step 3: Read Queue_Review sheet
        queue_df = pd.DataFrame()
        if not args.no_sync:
            if workbook.exists():
                log.info(f"Reading '{args.queue_sheet}' sheet from {workbook}")
                try:
                    with pd.ExcelFile(workbook, engine="openpyxl") as xls:
                        if args.queue_sheet in xls.sheet_names:
                            queue_df = pd.read_excel(
                                xls, sheet_name=args.queue_sheet, dtype=str
                            ).fillna("")
                            log.info(
                                f"Read {len(queue_df)} rows from '{args.queue_sheet}'"
                            )

                            required_cols = [
                                "TxnID",
                                "Set Shared? (Y/N/S for Split)",
                                "Set Split % (0-100)",
                            ]
                            missing_cols = [
                                col
                                for col in required_cols
                                if col not in queue_df.columns
                            ]
                            if missing_cols:
                                log.warning(
                                    f"'{args.queue_sheet}' sheet missing required columns: {', '.join(missing_cols)}. Skipping sync."
                                )
                                queue_df = pd.DataFrame()
                            else:
                                queue_df = queue_df[required_cols].copy()
                                queue_df["Set Shared? (Y/N/S for Split)"] = (
                                    queue_df["Set Shared? (Y/N/S for Split)"]
                                    .astype(str)
                                    .str.strip()
                                    .str.upper()
                                )
                                queue_df["Set Split % (0-100)"] = pd.to_numeric(
                                    queue_df["Set Split % (0-100)"], errors="coerce"
                                ).fillna(0)
                                log.info(
                                    f"Filtered and cleaned '{args.queue_sheet}' data."
                                )
                        else:
                            log.warning(
                                f"'{args.queue_sheet}' sheet not found in workbook. Skipping sync."
                            )
                except Exception as e:
                    log.error(
                        f"Error reading '{args.queue_sheet}' sheet: {e}. Skipping sync."
                    )
            else:
                log.info(
                    f"Workbook '{workbook.name}' does not exist yet. Skipping Queue_Review read."
                )
        else:
            log.info("Sync from Queue_Review disabled via --no-sync flag.")

        # Step 3: Sync decisions
        if not queue_df.empty and not args.no_sync:
            log.info("Syncing decisions from Queue_Review...")
            df = sync_review_decisions(df, queue_df)
            log.info("Decisions synced.")

        # Step 4: Save final DataFrame to the canonical Parquet file
        # Path is sibling to the workbook, using filename from config
        parquet_path = workbook.parent / config.BALANCE_FINAL_PARQUET_FILENAME

        # Ensure output directory exists before writing
        if not args.dry_run:
            try:
                workbook.parent.mkdir(parents=True, exist_ok=True)
                log.info(f"Ensured output directory exists: {workbook.parent}")
            except Exception as e_mkdir:
                log.error(f"Could not create output directory {workbook.parent}: {e_mkdir}")
                # Depending on severity, might want to sys.exit(1) here
                # For now, let the write attempts fail and log those errors.

        # Confirm the DataFrame shape before write
        if not df.empty:
            log.info("⚙️  Final DF columns (%d): %s", len(df.columns), list(df.columns))
        else:
            log.info("⚙️  Final DF is empty before Parquet write.")

        # Stage 2.1 Retry loop for Parquet write
        max_retries = 5
        base_delay_seconds = 0.2  # Initial delay for back-off

        for attempt in range(max_retries):
            try:
                if attempt == 0:  # Log detailed message only on first attempt
                    log.info(
                        f"Writing final DataFrame ({len(df)} rows) to Parquet: {parquet_path} (Engine: pyarrow, Compression: zstd)"
                    )
                df.to_parquet(
                    parquet_path, engine="pyarrow", compression="zstd", index=False
                )
                log.info(
                    f"Successfully wrote Parquet file on attempt {attempt + 1}/{max_retries}."
                )
                break  # Success, exit loop
            except (
                IOError,
                OSError,
                PermissionError,
            ) as e_io:  # Catch specific errors that might be transient
                log.warning(
                    f"Parquet write attempt {attempt + 1}/{max_retries} failed: {e_io}"
                )
                if attempt < max_retries - 1:
                    delay = base_delay_seconds * (2**attempt)  # Exponential back-off
                    log.info(f"Retrying Parquet write in {delay:.2f} seconds...")
                    time.sleep(delay)
                else:
                    log.error(
                        f"Failed to write Parquet file {parquet_path} after {max_retries} attempts. Last error: {e_io}",
                        exc_info=True,
                    )
            except (
                Exception
            ) as e_parquet_other:  # Catch other unexpected errors during write
                log.error(
                    f"Unexpected error writing Parquet file {parquet_path} on attempt {attempt + 1}: {e_parquet_other}",
                    exc_info=True,
                )
                break  # Don't retry on unexpected errors.

        # Step 5: Write results to Excel (or dry run CSV)
        if args.dry_run:
            log.info(
                f"DRY RUN: Would write {len(df)} rows to Transactions sheet in {workbook}"
            )
            temp_csv = workbook.with_suffix(".dry-run.csv")
            try:
                df.to_csv(temp_csv, index=False)
                log.info(f"Saved dry run results to {temp_csv}")
            except Exception as e:
                log.error(f"Error saving dry run CSV: {e}")
        else:
            # --- Write to Excel (handling .xlsm) ---
            is_macro_workbook = workbook.name.lower().endswith(".xlsm")
            target_file_path = (
                workbook.with_suffix(".temp.xlsx") if is_macro_workbook else workbook
            )
            # write_mode will be used as literal 'w' in the call

            if is_macro_workbook:
                log.warning(
                    "Working with macro-enabled workbook (.xlsm). Using temporary file workaround."
                )

            log.info(f"Preparing to write output to: {target_file_path}")

            try:
                sheets_to_preserve = []
                # If XLSM and original exists, identify sheets to copy to temp file
                if is_macro_workbook and workbook.exists():
                    try:
                        import openpyxl

                        wb_check = openpyxl.load_workbook(
                            workbook, read_only=True, keep_vba=True
                        )
                        sheets_to_preserve = [
                            sheet
                            for sheet in wb_check.sheetnames
                            if sheet not in ["Transactions", args.queue_sheet]
                        ]
                        wb_check.close()
                        log.debug(
                            f"Sheets to preserve from original XLSM: {sheets_to_preserve}"
                        )
                    except Exception as e:
                        log.error(
                            f"Error reading original workbook sheets for preservation: {e}"
                        )

                # Write main data and Queue_Review template to target/temp file
                with pd.ExcelWriter(
                    target_file_path,
                    engine="openpyxl",
                    mode="w",  # Use literal 'w'
                ) as writer:
                    log.info(f"Writing {len(df)} rows to 'Transactions' sheet...")
                    df.to_excel(writer, sheet_name="Transactions", index=False)

                    if not args.no_sync:
                        _create_queue_review_template(df, writer, args.queue_sheet)

                    # If XLSM and preserving sheets, copy them now to the temp file
                    if is_macro_workbook and workbook.exists() and sheets_to_preserve:
                        log.info(
                            f"Attempting to preserve sheets in temp file: {sheets_to_preserve}"
                        )
                        try:
                            source_wb = pd.ExcelFile(workbook, engine="openpyxl")
                            for sheet_name in sheets_to_preserve:
                                try:
                                    preserve_df = pd.read_excel(
                                        source_wb, sheet_name=sheet_name
                                    )
                                    preserve_df.to_excel(
                                        writer, sheet_name=sheet_name, index=False
                                    )
                                    log.debug(f"Preserved sheet: {sheet_name}")
                                except Exception as e_sheet:
                                    log.warning(
                                        f"Could not preserve sheet '{sheet_name}': {e_sheet}"
                                    )
                            source_wb.close()
                        except Exception as e_preserve:
                            log.error(f"Error during sheet preservation: {e_preserve}")

                # Log success message
                success_msg = (
                    "✅ Wrote data"  # Using emoji again now that encoding is fixed
                )
                if is_macro_workbook:
                    success_msg += f" to temporary XLSX file: {target_file_path.name}"
                else:
                    success_msg += f" directly to workbook: {target_file_path.name}"
                log.info(success_msg)

                # Provide XLSM instructions if needed
                if is_macro_workbook:
                    log.info(
                        "\n=================================================================="
                    )
                    log.info("IMPORTANT: To update your macro-enabled workbook:")
                    log.info(f"1. Ensure your main workbook is CLOSED: {workbook}")
                    log.info(f"2. Open the temporary file: {target_file_path}")
                    log.info(f"3. Open your main workbook: {workbook}")
                    log.info(
                        "4. In the temporary file, right-click the 'Transactions' sheet tab -> Move or Copy..."
                    )
                    log.info(
                        f"5. In the dialog, select '{workbook.name}' in 'To book:', check 'Create a copy', click OK."
                    )
                    log.info(f"6. Repeat steps 4-5 for the '{args.queue_sheet}' sheet.")
                    log.info("7. Close the temporary file WITHOUT saving.")
                    log.info("8. Save your main workbook.")
                    log.info(
                        f"9. You can now delete the temporary file: {target_file_path}"
                    )
                    log.info(
                        "   (Or use the 'ImportFromTempFile' macro in Excel if available)"
                    )
                    log.info(
                        "==================================================================\n"
                    )

            except PermissionError:
                log.error(
                    f"PERMISSION ERROR writing output file {target_file_path}. Check file permissions or if it's open elsewhere."
                )
                raise
            except Exception as e:
                log.error(f"Error writing output file {target_file_path}: {e}")
                raise
            # --- End Write to Excel ---

        log.info("✅ Process completed successfully")

    except Exception as e:
        log.error(f"An unexpected error occurred during processing: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Clean up lock file if we created it
        if lock_file_created and lock_file.exists():
            try:
                lock_file.unlink(missing_ok=True)
                log.debug(f"Removed lock file: {lock_file}")
            except Exception as e:
                log.warning(f"Could not remove lock file {lock_file}: {e}")


def _create_queue_review_template(
    df: pd.DataFrame, writer: Any, sheet_name: str
) -> None:
    """
    Create a template Queue_Review sheet with sample rows that need decisions.

    Args:
        df: DataFrame containing ALL processed transactions (used to find samples).
        writer: Excel writer object (pandas ExcelWriter).
        sheet_name: Name for the queue review sheet.
    """
    log.debug(f"Attempting to create '{sheet_name}' template...")
    # Create template DataFrame with required columns
    template_df = pd.DataFrame(
        columns=[
            "TxnID",
            "Set Shared? (Y/N/S for Split)",
            "Set Split % (0-100)",
            # Add context columns for easier review
            "Date",
            "OriginalDescription",  # Changed Description to OriginalDescription
            "Merchant",
            "Amount",
            "Owner",
        ]
    )

    # Find sample rows from transactions that have the default '?' SharedFlag or are pd.NA
    # Ensure 'SharedFlag' column exists before filtering
    if "SharedFlag" in df.columns:
        # Check for pd.NA for items needing review, as '?' should no longer be used at this stage
        # However, sync_review_decisions might still introduce '?' if not updated.
        # For now, let's assume '?' is the marker from sync_review_decisions.
        # If sync_review_decisions is updated to use pd.NA, this check will need to be df["SharedFlag"].isna()
        needs_review_mask = (df["SharedFlag"] == "?") | df["SharedFlag"].isna()
        need_review = df[needs_review_mask].head(10)  # Take top 10 needing review

        if not need_review.empty:
            log.debug(
                f"Found {len(need_review)} sample rows needing review (SharedFlag is '?' or NA) for template."
            )
            template_rows = []
            for _, row in need_review.iterrows():
                # Ensure all context columns exist in the row before appending
                context_cols = [
                    "Date",
                    "OriginalDescription",
                    "Merchant",
                    "Amount",
                    "Owner",
                ]  # Changed Description to OriginalDescription
                if all(col in row for col in context_cols):
                    template_rows.append(
                        {
                            "TxnID": row.get(
                                "TxnID", "MISSING_ID"
                            ),  # Use .get for safety
                            "Set Shared? (Y/N/S for Split)": "",  # Blank for user input
                            "Set Split % (0-100)": None,  # Blank for user input
                            "Date": row.get("Date"),
                            "Description": row.get(
                                "OriginalDescription"
                            ),  # Changed Description to OriginalDescription
                            "Merchant": row.get("Merchant"),
                            "Amount": row.get("Amount"),
                            "Owner": row.get("Owner"),
                        }
                    )
                else:
                    log.warning(
                        f"Skipping row for Queue_Review template due to missing context columns (TxnID: {row.get('TxnID')})"
                    )

            # Only concat if we have valid rows
            if template_rows:
                # Convert dtypes before concat to avoid FutureWarning with all-NA columns
                template_df = template_df.convert_dtypes()
                template_df = pd.concat(
                    [template_df, pd.DataFrame(template_rows)], ignore_index=True
                )
        else:
            log.debug("No transactions found with SharedFlag='?' to populate template.")
    else:
        log.warning(
            "'SharedFlag' column not found in DataFrame. Cannot populate Queue_Review template with samples."
        )

    # Write the template (even if empty) to the Excel file
    try:
        template_df.to_excel(writer, sheet_name=sheet_name, index=False)
        log.info(
            f"Created '{sheet_name}' template sheet (with {len(template_df)} sample rows)."
        )
    except Exception as e:
        log.error(f"Failed to write '{sheet_name}' template sheet: {e}")


def process_single_raw_csv_file(src: Path) -> pd.DataFrame | None:
    """
    Reads a single raw CSV file, derives Owner, DataSourceName, and DataSourceDate metadata,
    and returns a pandas DataFrame. Returns None if the file cannot be processed or should be skipped.
    """
    import pandas as pd  # Keep imports local to function as per previous pattern
    import re

    log.info(f"[process_single_raw_csv_file] Attempting to process: {src.name}")
    try:
        df_raw_single = pd.read_csv(src)  # Renamed variable

        if "Amount" in df_raw_single.columns:  # Use renamed variable
            # Attempt to convert 'Amount' to numeric, coercing errors to NaN
            original_dtype_amount = df_raw_single[
                "Amount"
            ].dtype  # Use renamed variable
            # Common practice: remove currency symbols and thousands separators before converting
            # For now, assuming pd.to_numeric can handle reasonably clean numbers or will coerce others.
            # If amounts have '$', ',', this might need pre-cleaning:
            # df["Amount"] = df["Amount"].astype(str).str.replace(r'[$,]', '', regex=True)
            df_raw_single["Amount"] = pd.to_numeric(
                df_raw_single["Amount"], errors="coerce"
            )  # Use renamed variable

            nan_in_amount = df_raw_single["Amount"].isna().sum()  # Use renamed variable
            # Only log if there were actual NaNs *after* coercion that weren't already NaN
            # This check is a bit complex; simpler to just log if any NaNs exist post-coercion.
            if nan_in_amount > 0:
                # Check if these NaNs were newly introduced or already there.
                # This requires comparing pre- and post-coercion NaN counts if being precise.
                # For simplicity, just log the presence of NaNs.
                log.warning(
                    f"Found {nan_in_amount} NaN value(s) in 'Amount' column for {src.name} after numeric conversion."
                )

            if (
                original_dtype_amount != df_raw_single["Amount"].dtype
            ):  # Use renamed variable
                log.debug(
                    f"Changed 'Amount' column dtype from {original_dtype_amount} to {df_raw_single['Amount'].dtype} for {src.name}."  # Use renamed variable
                )
        else:
            log.warning(
                f"'Amount' column not found in {src.name}. Creating it as float64 with NaNs."
            )
            # Create an 'Amount' column of float type filled with NaNs if it doesn't exist.
            # This ensures schema consistency when concatenating DataFrames.
            df_raw_single["Amount"] = pd.Series(
                dtype="float64", index=df_raw_single.index
            )  # Use renamed variable

        if "AccountLast4" in df_raw_single.columns:  # Use renamed variable
            # Convert all values to string, ensuring that original NaN/None values are preserved.
            # .astype(str) would convert NaN to the string "nan".
            # A robust way is to apply a function that converts non-nulls to str.
            # Or, convert to str and then fix "nan" strings that were originally NaN.
            is_na_before_acct_last4 = df_raw_single[
                "AccountLast4"
            ].isna()  # Use renamed variable
            df_raw_single["AccountLast4"] = df_raw_single[
                "AccountLast4"
            ].astype(  # Use renamed variable
                str
            )  # Converts everything to string, NaN -> "nan"
            # Restore original NaNs to None so PyArrow treats them as nulls
            df_raw_single.loc[is_na_before_acct_last4, "AccountLast4"] = (
                None  # Use renamed variable
            )
            log.debug(
                f"Ensured 'AccountLast4' column is string type for {src.name}, preserving NaNs."
            )
        else:
            log.warning(
                f"'AccountLast4' column not found in {src.name}. Creating it as object type with Nones."
            )
            df_raw_single["AccountLast4"] = pd.Series(  # Use renamed variable
                dtype="object",
                index=df_raw_single.index,  # Use renamed variable
            )  # Fill with None

        # If CSV has headers but no data rows, df will be empty.
        # This is handled gracefully when adding new columns.

        # Derive Owner
        path_str_lower = str(
            src.as_posix()
        ).lower()  # Use as_posix for consistent / separators
        owner = "Unknown"  # Default owner
        if (
            "/csvs/ryan/" in path_str_lower
        ):  # Check for /ryan/ within the CSVs parent folder
            owner = "Ryan"
        elif (
            "/csvs/jordyn/" in path_str_lower
        ):  # Check for /jordyn/ within the CSVs parent folder
            owner = "Jordyn"
        df_raw_single["Owner"] = (
            owner  # Assign to all rows (or creates column if df is empty) # Use renamed variable
        )

        # Derive DataSourceName and DataSourceDate
        fname = src.name
        ds_name_val = "n/a"  # Default as per user's plan
        ds_date_val: Optional[date] = None  # Default to None, type Optional[date]

        # Regex for "Monarch Money" or "Rocket Money" followed by an 8-digit date
        # Using re.I for case-insensitivity as specified in user's diff snippet
        match = re.search(r"(Monarch Money|Rocket Money).*?(\d{8})", fname, re.I)
        if match:
            name_tag, yyyymmdd_str = match.groups()
            ds_name_val = name_tag.strip()  # Use the matched tag (Monarch or Rocket)
            try:
                # Convert to datetime.date object for proper Parquet date32 type
                ds_date_val = pd.to_datetime(
                    yyyymmdd_str, format="%Y%m%d"
                ).date()  # Use .date() for Timestamp
            except ValueError:
                log.warning(
                    f"Could not parse date '{yyyymmdd_str}' from filename '{fname}' for DataSourceDate. Using None."
                )
                # ds_date_val remains None

        df_raw_single["DataSourceName"] = ds_name_val  # Use renamed variable
        df_raw_single["DataSourceDate"] = (
            ds_date_val  # Assigns datetime.date objects or None # Use renamed variable
        )

        # Log derived info (conditionally accessing iloc[0] if df not empty for safety, though not strictly needed for these assignments)
        owner_log = (
            df_raw_single["Owner"].iloc[0] if not df_raw_single.empty else owner
        )  # Use renamed variable
        ds_name_log = (
            df_raw_single["DataSourceName"].iloc[0]
            if not df_raw_single.empty
            else ds_name_val
        )  # Use renamed variable
        # Handle ds_date_val being None for logging
        ds_date_log_val_for_display = ds_date_val if ds_date_val is not None else "None"  # noqa: F841
        ds_date_log_str = ds_date_val.isoformat() if ds_date_val is not None else "None"

        log.info(
            f"Successfully processed {src.name}: Rows={len(df_raw_single)}, Owner='{owner_log}', "  # Use renamed variable
            f"DataSourceName='{ds_name_log}', DataSourceDate='{ds_date_log_str}'"
        )
        return df_raw_single  # Use renamed variable

    except FileNotFoundError:
        log.error(f"[process_single_raw_csv_file] Source file not found: {src}")
        return None
    except (
        pd.errors.EmptyDataError
    ):  # This catches truly empty files (no headers, no data)
        log.warning(
            f"[process_single_raw_csv_file] Source file is completely empty (no data/headers): {src}. Skipping."
        )
        return None  # Skip this file from concatenation
    except Exception as e:
        log.error(
            f"[process_single_raw_csv_file] Error processing file {src}: {e}",
            exc_info=True,
        )
        return None


if __name__ == "__main__":
    main()
