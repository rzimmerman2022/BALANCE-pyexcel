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
import os
import time
import io # <<< Added import for io module
from typing import Optional, Any
from balance_pipeline.config import LOG_LEVEL  # Import project-wide log level

# Import the pipeline modules
from balance_pipeline.ingest import load_folder
from balance_pipeline.normalize import normalize_df
from balance_pipeline.sync import sync_review_decisions
from balance_pipeline.export import write_parquet_duckdb # Added for DuckDB Parquet export

# --- Force UTF-8 Encoding for stdout/stderr ---
# This helps ensure emojis (like ✅) and other Unicode characters print correctly,
# especially on Windows consoles that might default to a different encoding (e.g., cp1252).
# It attempts to reconfigure the standard streams if possible (Python 3.7+).
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
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
    # Use project-wide log level if defined, otherwise use INFO (or DEBUG if verbose)
    log_level_name = LOG_LEVEL if isinstance(LOG_LEVEL, str) else 'INFO' # Default to INFO
    log_level = getattr(logging, log_level_name.upper(), logging.INFO)
    if verbose:
        log_level = logging.DEBUG # Override to DEBUG if verbose flag is set
    
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
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
            log.debug(f"Attempting to set stdout encoding to UTF-8 (current: {current_encoding})")
            # Try Python 3.9+ method first
            if hasattr(stdout_handler.stream, 'reconfigure'):
                try:
                    stdout_handler.stream.reconfigure(encoding='utf-8')
                    log.debug("Reconfigured stdout stream encoding to UTF-8 using reconfigure().")
                except Exception as reconfig_err:
                    log.debug(f"stream.reconfigure() failed: {reconfig_err}. Trying TextIOWrapper fallback.")
                    # Fallback to TextIOWrapper if reconfigure fails or isn't available
                    if hasattr(stdout_handler.stream, 'fileno') and stdout_handler.stream.fileno() >= 0:
                         stdout_handler.stream = io.TextIOWrapper(
                             os.fdopen(stdout_handler.stream.fileno(), "wb", closefd=False),
                             encoding="utf-8",
                             line_buffering=True # Attempt to mimic standard stdout buffering
                         )
                         log.debug("Wrapped stdout stream with TextIOWrapper for UTF-8 encoding.")
                    else:
                         log.warning("Could not wrap stdout stream for UTF-8: Invalid or missing file descriptor.")
            # Fallback for Python < 3.9 or streams without reconfigure
            elif hasattr(stdout_handler.stream, 'fileno') and stdout_handler.stream.fileno() >= 0:
                 stdout_handler.stream = io.TextIOWrapper(
                     os.fdopen(stdout_handler.stream.fileno(), "wb", closefd=False),
                     encoding="utf-8",
                     line_buffering=True
                 )
                 log.debug("Wrapped stdout stream with TextIOWrapper for UTF-8 encoding (fallback).")
            else:
                 log.warning("Could not set stdout stream encoding to UTF-8: Neither reconfigure nor fileno available/valid.")
        else:
            log.debug("stdout stream encoding is already UTF-8.")
            
    except Exception as encoding_err:
        log.warning(f"Could not force UTF-8 encoding on stdout stream: {encoding_err}")

    handlers = [stdout_handler]
    # --- End stdout handler configuration ---

    # Add file handler if log file path is provided
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file, encoding='utf-8') # Ensure file is also UTF-8
            file_handler.setFormatter(formatter)
            handlers.append(file_handler)
        except Exception as e:
            log.error(f"Could not create log file handler for {log_file}: {e}")
    
    # Apply the configuration (force=True overrides any existing config)
    logging.basicConfig(
        level=log_level,
        format=log_format, # Format is applied via handlers now, but set here for consistency
        handlers=handlers,
        force=True  # Crucial for ensuring this config takes precedence
    )
    log.debug(f"Logging configured. Level: {logging.getLevelName(log_level)}. Handlers: {[h.name for h in handlers if hasattr(h, 'name')]}")


def etl_main(inbox_path: Path, prefer_source: str = "Rocket") -> pd.DataFrame:
    """
    Main ETL function that loads CSVs, normalizes data, and returns a DataFrame.
    
    Args:
        inbox_path: Path to the folder containing CSV files to process
        prefer_source: Preferred source for deduplication (default: "Rocket")
        
    Returns:
        pd.DataFrame: Processed and normalized transaction data
    """
    # Load data from CSVs using the schema registry
    log.info(f"Loading CSVs from {inbox_path}")
    df = load_folder(inbox_path) # Assumes load_folder handles internal logging
    log.info(f"Loaded {len(df)} rows from CSVs")
    
    # Normalize the data
    log.info("Normalizing data")
    df = normalize_df(df, prefer_source=prefer_source) # Pass the preferred source parameter
    log.info(f"Normalized data contains {len(df)} rows")
    
    return df

def main():
    """
    Main CLI entry point
    """
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
""" 
    ) # End of ArgumentParser definition
    
    # Define arguments AFTER the ArgumentParser initialization
    parser.add_argument("inbox", help="Path to CSV inbox folder")
    parser.add_argument("workbook", help="Path to target Excel workbook (.xlsx or .xlsm)")
    parser.add_argument("--no-sync", action="store_true", help="Skip reading/syncing decisions from Queue_Review sheet")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging (DEBUG level)")
    parser.add_argument("--log", help="Path to log file (in addition to console output)")
    parser.add_argument("--dry-run", action="store_true", help="Process data but do not write to Excel")
    parser.add_argument("--queue-sheet", default="Queue_Review", 
                        help="Name of the sheet containing decisions (default: Queue_Review)")
    parser.add_argument("--prefer-source", default="Rocket", 
                        help="Preferred source when deduplicating transactions (default: Rocket)")
    args = parser.parse_args()
    
    # --- Setup Logging ---
    # Must happen before any significant logging calls
    setup_logging(args.log, args.verbose)
    log.info("="*50)
    log.info("Starting BALANCE-pyexcel CLI process...") 
    log.debug(f"Arguments received: {args}")
    
    # --- Path Validation and Resolution ---
    try:
        inbox = Path(args.inbox).expanduser().resolve(strict=True) # strict=True ensures inbox exists
        workbook = Path(args.workbook).expanduser().resolve() # Allow workbook to not exist yet
        log.debug(f"Resolved Inbox Path: {inbox}")
        log.debug(f"Resolved Workbook Path: {workbook}")
    except FileNotFoundError as e:
         log.error(f"Input path error: Inbox folder not found at '{args.inbox}'. Details: {e}")
         sys.exit(1)
    except Exception as e:
         log.error(f"Error resolving paths: {e}")
         sys.exit(1)

    # Validate Excel file extension
    if not workbook.name.lower().endswith((".xlsx", ".xlsm")):
        log.error(f"Invalid workbook file extension: '{workbook.suffix}'. Must be .xlsx or .xlsm.")
        sys.exit(1)
    
    # Check inbox path is actually a directory
    if not inbox.is_dir():
        log.error(f"Inbox path provided is not a valid directory: {inbox}")
        sys.exit(1)
    
    if not workbook.exists() and not args.dry_run:
        log.warning(f"Target workbook does not exist: {workbook}. Will attempt to create it.")
    
    # --- Lock File Handling ---
    lock_file = workbook.with_suffix(workbook.suffix + ".lock") 
    lock_file_created = False
    if not args.dry_run:
        if lock_file.exists():
            try:
                locktime = time.time() - lock_file.stat().st_mtime
                log.warning(f"Lock file exists for '{workbook.name}' (created {locktime:.1f} seconds ago).")
                if locktime < 300: # 5 minutes tolerance
                    log.warning("Another process may be accessing this file. Waiting up to 30 seconds...")
                    wait_start = time.time()
                    while lock_file.exists() and (time.time() - wait_start < 30):
                        time.sleep(1)
                    if lock_file.exists():
                        log.error("Lock file still exists after 30 seconds. Aborting.")
                        log.error(f"If you are sure no other process is running, delete the lock file manually: {lock_file}")
                        sys.exit(1)
                    else:
                        log.info("Lock file was released.")
                else:
                    log.warning("Lock file is older than 5 minutes. Assuming stale lock and attempting removal...")
                    try:
                        lock_file.unlink() 
                        log.info("Removed stale lock file.")
                    except Exception as e_unlink_stale:
                        log.error(f"Could not remove stale lock file {lock_file}: {e_unlink_stale}. Aborting.")
                        sys.exit(1)

            except Exception as e_lock_check:
                 log.error(f"Error checking lock file {lock_file}: {e_lock_check}. Aborting.")
                 sys.exit(1)
        
        # Attempt to create lock file
        try:
            lock_file.touch(exist_ok=False) # exist_ok=False raises error if file exists (race condition check)
            lock_file_created = True
            log.debug(f"Created lock file: {lock_file}")
        except FileExistsError:
             log.error(f"Lock file {lock_file} appeared unexpectedly after check. Another process likely started. Aborting.")
             sys.exit(1)
        except Exception as e_lock_create:
            log.warning(f"Could not create lock file {lock_file}: {e_lock_create}. Proceeding without lock (potential risk).")
            lock_file_created = False 
    # --- End Lock File Handling ---

    try:
        # Step 1: Run ETL pipeline
        df = etl_main(inbox, prefer_source=args.prefer_source)
        if df.empty and inbox.exists(): 
             log.warning("ETL process resulted in an empty DataFrame. Check source CSVs and logs.")
             # Continue to ensure sheets are created/cleared if needed.

        # Step 2: Read Queue_Review sheet
        queue_df = pd.DataFrame() 
        if not args.no_sync:
            if workbook.exists():
                log.info(f"Reading '{args.queue_sheet}' sheet from {workbook}")
                try:
                    with pd.ExcelFile(workbook, engine='openpyxl') as xls: 
                        if args.queue_sheet in xls.sheet_names:
                            queue_df = pd.read_excel(xls, sheet_name=args.queue_sheet, dtype=str).fillna('') 
                            log.info(f"Read {len(queue_df)} rows from '{args.queue_sheet}'")
                            
                            required_cols = ["TxnID", "Set Shared? (Y/N/S for Split)", "Set Split % (0-100)"]
                            missing_cols = [col for col in required_cols if col not in queue_df.columns]
                            if missing_cols:
                                log.warning(f"'{args.queue_sheet}' sheet missing required columns: {', '.join(missing_cols)}. Skipping sync.")
                                queue_df = pd.DataFrame() 
                            else:
                                queue_df = queue_df[required_cols].copy() 
                                queue_df["Set Shared? (Y/N/S for Split)"] = queue_df["Set Shared? (Y/N/S for Split)"].astype(str).str.strip().str.upper()
                                queue_df["Set Split % (0-100)"] = pd.to_numeric(queue_df["Set Split % (0-100)"], errors='coerce').fillna(0) 
                                log.info(f"Filtered and cleaned '{args.queue_sheet}' data.")
                        else:
                            log.warning(f"'{args.queue_sheet}' sheet not found in workbook. Skipping sync.")
                except Exception as e:
                    log.error(f"Error reading '{args.queue_sheet}' sheet: {e}. Skipping sync.")
            else:
                 log.info(f"Workbook '{workbook.name}' does not exist yet. Skipping Queue_Review read.")
        else:
             log.info("Sync from Queue_Review disabled via --no-sync flag.")

        # Step 3: Sync decisions
        if not queue_df.empty and not args.no_sync:
            log.info("Syncing decisions from Queue_Review...")
            df = sync_review_decisions(df, queue_df) 
            log.info("Decisions synced.")

        # --- Parquet snapshot (DuckDB) ---
        # Step 4: Save final DataFrame to Parquet via DuckDB for integration
        parquet_path = workbook.with_suffix(".parquet")
        write_parquet_duckdb(df, parquet_path) # Use the new helper function

        # Step 5: Write results to Excel (or dry run CSV)
        if args.dry_run:
            log.info(f"DRY RUN: Would write {len(df)} rows to Transactions sheet in {workbook}")
            temp_csv = workbook.with_suffix(".dry-run.csv")
            try:
                df.to_csv(temp_csv, index=False)
                log.info(f"Saved dry run results to {temp_csv}")
            except Exception as e:
                 log.error(f"Error saving dry run CSV: {e}")
        else:
            # --- Write to Excel (handling .xlsm) ---
            is_macro_workbook = workbook.name.lower().endswith(".xlsm")
            target_file_path = workbook.with_suffix(".temp.xlsx") if is_macro_workbook else workbook
            write_mode = 'w' # Always overwrite/create the temp file or the target xlsx

            if is_macro_workbook:
                 log.warning("Working with macro-enabled workbook (.xlsm). Using temporary file workaround.")
            
            log.info(f"Preparing to write output to: {target_file_path}")
            
            try:
                sheets_to_preserve = []
                # If XLSM and original exists, identify sheets to copy to temp file
                if is_macro_workbook and workbook.exists():
                    try:
                        import openpyxl
                        wb_check = openpyxl.load_workbook(workbook, read_only=True, keep_vba=True)
                        sheets_to_preserve = [
                            sheet for sheet in wb_check.sheetnames 
                            if sheet not in ["Transactions", args.queue_sheet]
                        ]
                        wb_check.close()
                        log.debug(f"Sheets to preserve from original XLSM: {sheets_to_preserve}")
                    except Exception as e:
                        log.error(f"Error reading original workbook sheets for preservation: {e}")

                # Write main data and Queue_Review template to target/temp file
                with pd.ExcelWriter(target_file_path, engine="openpyxl", mode=write_mode) as writer:
                    log.info(f"Writing {len(df)} rows to 'Transactions' sheet...")
                    df.to_excel(writer, sheet_name="Transactions", index=False)
                    
                    if not args.no_sync: 
                         _create_queue_review_template(df, writer, args.queue_sheet)
                    
                    # If XLSM and preserving sheets, copy them now to the temp file
                    if is_macro_workbook and workbook.exists() and sheets_to_preserve:
                         log.info(f"Attempting to preserve sheets in temp file: {sheets_to_preserve}")
                         try:
                             source_wb = pd.ExcelFile(workbook, engine='openpyxl') 
                             for sheet_name in sheets_to_preserve:
                                 try:
                                     preserve_df = pd.read_excel(source_wb, sheet_name=sheet_name)
                                     preserve_df.to_excel(writer, sheet_name=sheet_name, index=False)
                                     log.debug(f"Preserved sheet: {sheet_name}")
                                 except Exception as e_sheet:
                                     log.warning(f"Could not preserve sheet '{sheet_name}': {e_sheet}")
                             source_wb.close()
                         except Exception as e_preserve:
                             log.error(f"Error during sheet preservation: {e_preserve}")

                # Log success message 
                success_msg = "✅ Wrote data" # Using emoji again now that encoding is fixed
                if is_macro_workbook:
                    success_msg += f" to temporary XLSX file: {target_file_path.name}"
                else:
                     success_msg += f" directly to workbook: {target_file_path.name}"
                log.info(success_msg)

                # Provide XLSM instructions if needed
                if is_macro_workbook:
                    log.info("\n==================================================================")
                    log.info("IMPORTANT: To update your macro-enabled workbook:")
                    log.info(f"1. Ensure your main workbook is CLOSED: {workbook}")
                    log.info(f"2. Open the temporary file: {target_file_path}")
                    log.info(f"3. Open your main workbook: {workbook}")
                    log.info("4. In the temporary file, right-click the 'Transactions' sheet tab -> Move or Copy...")
                    log.info(f"5. In the dialog, select '{workbook.name}' in 'To book:', check 'Create a copy', click OK.")
                    log.info(f"6. Repeat steps 4-5 for the '{args.queue_sheet}' sheet.")
                    log.info("7. Close the temporary file WITHOUT saving.")
                    log.info("8. Save your main workbook.")
                    log.info(f"9. You can now delete the temporary file: {target_file_path}")
                    log.info("   (Or use the 'ImportFromTempFile' macro in Excel if available)")
                    log.info("==================================================================\n")

            except PermissionError as pe:
                log.error(f"PERMISSION ERROR writing output file {target_file_path}. Check file permissions or if it's open elsewhere.")
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
    
def _create_queue_review_template(df: pd.DataFrame, writer: Any, sheet_name: str) -> None:
    """
    Create a template Queue_Review sheet with sample rows that need decisions.
    
    Args:
        df: DataFrame containing ALL processed transactions (used to find samples).
        writer: Excel writer object (pandas ExcelWriter).
        sheet_name: Name for the queue review sheet.
    """
    log.debug(f"Attempting to create '{sheet_name}' template...")
    # Create template DataFrame with required columns
    template_df = pd.DataFrame(columns=[
        "TxnID", 
        "Set Shared? (Y/N/S for Split)", 
        "Set Split % (0-100)",
        # Add context columns for easier review
        "Date",
        "Description",
        "CanonMerchant", # Added Canonical Merchant
        "Amount",
        "Owner"
    ])
    
    # Find sample rows from transactions that have the default '?' SharedFlag
    # Ensure 'SharedFlag' column exists before filtering
    if "SharedFlag" in df.columns:
        need_review = df[df["SharedFlag"] == "?"].head(10) # Take top 10 needing review
        if not need_review.empty:
            log.debug(f"Found {len(need_review)} sample rows needing review for template.")
            template_rows = []
            for _, row in need_review.iterrows():
                # Ensure all context columns exist in the row before appending
                context_cols = ["Date", "Description", "CanonMerchant", "Amount", "Owner"] # Added CanonMerchant
                if all(col in row for col in context_cols):
                     template_rows.append({
                         "TxnID": row.get("TxnID", "MISSING_ID"), # Use .get for safety
                         "Set Shared? (Y/N/S for Split)": "", # Blank for user input
                         "Set Split % (0-100)": None,        # Blank for user input
                         "Date": row.get("Date"),
                         "Description": row.get("Description"),
                         "CanonMerchant": row.get("CanonMerchant"), # Added CanonMerchant
                         "Amount": row.get("Amount"),
                         "Owner": row.get("Owner")
                     })
                else:
                     log.warning(f"Skipping row for Queue_Review template due to missing context columns (TxnID: {row.get('TxnID')})")

            # Only concat if we have valid rows
            if template_rows:
                 template_df = pd.concat([template_df, pd.DataFrame(template_rows)], ignore_index=True)
        else:
             log.debug("No transactions found with SharedFlag='?' to populate template.")
    else:
        log.warning("'SharedFlag' column not found in DataFrame. Cannot populate Queue_Review template with samples.")

    # Write the template (even if empty) to the Excel file
    try:
        template_df.to_excel(writer, sheet_name=sheet_name, index=False)
        log.info(f"Created '{sheet_name}' template sheet (with {len(template_df)} sample rows).")
    except Exception as e:
        log.error(f"Failed to write '{sheet_name}' template sheet: {e}")


def dev_main():
    """
    Development version of the main entry point that automatically enables verbose logging
    and provides more debugging information. Registered as 'balance-pyexcel-dev'.
    """
    # Modify sys.argv to include the --verbose flag if not already present
    # This ensures dev mode always runs verbosely unless explicitly overridden later
    if '--verbose' not in sys.argv and '-v' not in sys.argv:
        # Insert it after the script name (index 0)
        sys.argv.insert(1, '--verbose') 
    
    # Insert a clear banner to indicate we're in dev mode
    print("=" * 80, file=sys.stderr) # Print banner to stderr to separate from logs
    print("BALANCE-pyexcel [DEVELOPMENT MODE]", file=sys.stderr)
    print("=" * 80, file=sys.stderr)
    print(f"Python Executable: {sys.executable}", file=sys.stderr)
    print(f"Working Directory: {os.getcwd()}", file=sys.stderr)
    print(f"Full Command Line: {' '.join(sys.argv)}", file=sys.stderr)
    print("=" * 80, file=sys.stderr)
    
    # Call the regular main function
    main()

if __name__ == "__main__":
    # This block executes when the script is run directly (python src/balance_pipeline/cli.py)
    main()
