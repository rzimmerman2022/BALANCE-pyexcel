# -*- coding: utf-8 -*-
"""
==============================================================================
Script: process_pdfs.py
Project: BALANCE-pyexcel
Description: Processes PDF bank statements found in an input directory using
             Tabula, extracts tables, and saves them as CSV files in an
             output directory. Includes error handling for problematic PDFs.
==============================================================================

Version: 0.1.1
Last Modified: 2025-05-04
Author: AI Assistant (Cline)
"""

import tabula # Changed from camelot
import pandas as pd
from pathlib import Path
import argparse
import logging
import sys
# import os # os is no longer used directly

# --- Configure Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# --- Define Schema ID ---
# Note: SCHEMA_ID is no longer used for filename generation directly
# SCHEMA_ID = "jordyn_pdf" # As suggested in the review

def read_with_fallback(pdf_path: Path):
    """Try UTF-8 first, then CP-1252, finally ignore bad bytes."""
    base_kwargs = dict(
        pages="all",
        multiple_tables=True,
        stream=True,
        guess=True,
        pandas_options={"dtype": str}, # Keep data as strings initially via pandas
    )
    try:
        log.debug(f"Attempting to read {pdf_path.name} with UTF-8")
        # Pass encoding directly to tabula.read_pdf for subprocess decoding
        return tabula.read_pdf(str(pdf_path), encoding='utf-8', **base_kwargs)
    except UnicodeDecodeError:
        log.warning(f"UTF-8 failed for {pdf_path.name} → retry CP-1252")
        # Fallback to CP-1252 for subprocess decoding
        # No need for a third try-except here if CP-1252 handles the known issue
        return tabula.read_pdf(str(pdf_path), encoding='cp1252', **base_kwargs)
        # Note: If other errors occur, they will propagate up from here

def process_pdf(pdf_path: Path, owner_output_dir: Path, owner_name: str) -> bool:
    """
    Extracts tables from a single PDF using Tabula (with encoding fallbacks), concatenates them,
    and saves the result as a single CSV in the specified owner's directory.

    Args:
        pdf_path (Path): Path to the input PDF file.
        owner_output_dir (Path): Directory for the specific owner within the main inbox.
        owner_name (str): Name of the owner.

    Returns:
        bool: True if processing and saving were successful, False otherwise.
    """
    log.info(f"Processing PDF: {pdf_path.name} for owner: {owner_name}")
    valid_tables_df = []
    try:
        # Use the helper function with encoding fallbacks - pass Path object directly
        tables = read_with_fallback(pdf_path)

        if not tables:
            log.warning(f"No tables found by Tabula (with fallbacks) in {pdf_path.name}. Skipping.")
            return False # Indicate failure/skip

        log.info(f"Found {len(tables)} table(s) in {pdf_path.name}. Filtering and attempting to concatenate.")

        # Filter out empty tables or tables with only headers before concatenation
        for i, df in enumerate(tables):
            if not df.empty and len(df) > 1:
                valid_tables_df.append(df)
                log.debug(f"Added table {i+1} (shape: {df.shape}) to concatenation list.")
            else:
                log.debug(f"Skipping empty or header-only table {i+1}.")

        if not valid_tables_df:
            log.warning(f"No valid tables found to concatenate in {pdf_path.name}. Skipping.")
            return False # Indicate failure/skip

        # Concatenate the list of valid DataFrames
        combined_df = pd.concat(valid_tables_df, ignore_index=True)
        log.info(f"Concatenated {len(valid_tables_df)} valid table(s) into a single DataFrame with shape {combined_df.shape}.")

        # --- Filter out non-transaction rows (Simplified Approach) ---
        # Assume transaction data has a valid date-like string in index 10 (MM/DD)
        # and a valid numeric amount in index 14.
        initial_rows = len(combined_df)
        if combined_df.shape[1] >= 15:
            try:
                # Check for MM/DD format (allows 1/1, 01/01, 12/31 etc.)
                date_col_idx = 10
                amount_col_idx = 14
                date_pattern = r'^\d{1,2}/\d{1,2}$'
                # Keep rows where column 10 matches the date pattern AND column 14 is numeric
                # Convert amount column to numeric, coercing errors to NaN
                numeric_amount = pd.to_numeric(combined_df.iloc[:, amount_col_idx], errors='coerce')
                # Check date pattern
                is_valid_date_format = combined_df.iloc[:, date_col_idx].astype(str).str.match(date_pattern, na=False)

                # Keep rows that satisfy both conditions
                combined_df = combined_df[is_valid_date_format & numeric_amount.notna()]

                rows_after_filter = len(combined_df)
                log.info(f"Filtered rows based on date (col {date_col_idx}) and amount (col {amount_col_idx}). Kept {rows_after_filter}/{initial_rows} rows.")

            except IndexError:
                 log.warning(f"DataFrame for {pdf_path.name} has less than 15 columns. Skipping row filtering.")
            except Exception as e_filter:
                 log.warning(f"Error during row filtering for {pdf_path.name}: {e_filter}. Proceeding with unfiltered data.")
        else:
             log.warning(f"DataFrame for {pdf_path.name} has only {combined_df.shape[1]} columns. Skipping row filtering.")

        if combined_df.empty:
            log.warning(f"DataFrame became empty after filtering for {pdf_path.name}. Skipping file.")
            return False

        # --- Rename Columns by Index (Post-Filtering) ---
        # Define the output CSV path using the new naming convention
        output_csv_name = f"BALANCE - {owner_name} PDF - {pdf_path.stem}.csv"
        output_csv_path = owner_output_dir / output_csv_name

        # Define expected column names based on schema registry assumptions
        expected_columns = {
            9: "AccountLast4",    # Index 9 (10th col)
            10: "TransDate",      # Index 10 (11th col)
            11: "PostDate",       # Index 11 (12th col)
            12: "ReferenceNumber",# Index 12 (13th col)
            13: "RawMerchant",    # Index 13 (14th col)
            14: "Amount"          # Index 14 (15th col) - Assuming this is the correct index
        }
        # Check if the DataFrame still has enough columns after filtering
        if combined_df.shape[1] >= 15:
            log.debug(f"Renaming columns based on index for {pdf_path.name} after filtering.")
            try:
                # Create rename map using original column names at specific indices
                rename_map = {combined_df.columns[idx]: new_name
                              for idx, new_name in expected_columns.items()
                              if idx < combined_df.shape[1]} # Ensure index is within bounds
                combined_df.rename(columns=rename_map, inplace=True)
                log.debug(f"Columns after rename by index: {combined_df.columns.tolist()}")

                # Select only the renamed columns in the desired order
                final_cols_order = ["TransDate", "PostDate", "ReferenceNumber", "RawMerchant", "Amount", "AccountLast4"]
                # Keep only columns that actually exist after renaming
                final_cols_present = [col for col in final_cols_order if col in combined_df.columns]
                combined_df = combined_df[final_cols_present]
                log.debug(f"Selected and reordered final columns: {final_cols_present}")

            except IndexError:
                 log.warning(f"IndexError during column renaming for {pdf_path.name}. Columns might be incorrect.")
                 # Fallback: Keep original columns if renaming fails
            except Exception as e_rename:
                 log.warning(f"Error during column renaming for {pdf_path.name}: {e_rename}. Columns might be incorrect.")
                 # Fallback: Keep original columns

        else:
            log.warning(f"DataFrame for {pdf_path.name} has only {combined_df.shape[1]} columns after filtering. Cannot rename by index. Columns might be incorrect.")
            # Keep the columns we have, hoping they are somewhat correct


        # Save the potentially cleaned DataFrame
        try:
            combined_df.to_csv(output_csv_path, index=False)
            log.info(f"Successfully saved combined data to {output_csv_path.name}")
            return True # Indicate success
        except Exception as e_save:
            log.error(f"Error saving combined CSV for {pdf_path.name} to {output_csv_path.name}: {e_save}")
            return False # Indicate failure

    except FileNotFoundError:
        log.error(f"PDF file not found: {pdf_path}")
        return False # Indicate failure
    except Exception as e_tabula:
        # Catch broad exceptions during Tabula processing (e.g., corrupted PDF, Java issues)
        log.error(f"Failed to process PDF {pdf_path.name} with Tabula: {e_tabula}", exc_info=False) # Set exc_info=True for full traceback if needed
        return False # Indicate failure

def main():
    """Main script execution"""
    parser = argparse.ArgumentParser(
        description="Extract tables from PDF bank statements to CSV using Tabula.", # Updated description
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog="Example: poetry run python scripts/process_pdfs.py C:\\PDF_Statements C:\\MyCSVs Jordyn -v"
    )
    parser.add_argument("input_dir", help="Directory containing PDF files to process.")
    parser.add_argument("main_inbox_dir", help="Path to the main CSV inbox directory (e.g., C:\\MyCSVs).")
    parser.add_argument("owner_name", help="Name of the owner (e.g., Jordyn) - determines the subfolder in the inbox.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging (DEBUG level).")

    args = parser.parse_args()

    # --- Setup Logging Level ---
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.getLogger().setLevel(log_level) # Adjust root logger level

    log.info("="*50)
    log.info("Starting PDF Processing Script...")
    log.debug(f"Arguments: {args}")

    # --- Path Validation ---
    input_path = Path(args.input_dir).resolve()
    main_inbox_path = Path(args.main_inbox_dir).resolve()
    owner_name = args.owner_name
    owner_output_path = main_inbox_path / owner_name

    if not input_path.is_dir():
        log.error(f"Input directory not found or is not a directory: {input_path}")
        sys.exit(1)

    if not main_inbox_path.is_dir():
        # Check if the parent exists, maybe the user provided the owner path directly
        if main_inbox_path.parent.is_dir() and main_inbox_path.name == owner_name:
            log.warning(f"Provided main inbox path '{args.main_inbox_dir}' seems to include the owner name. Using parent '{main_inbox_path.parent}' as main inbox.")
            main_inbox_path = main_inbox_path.parent
            owner_output_path = main_inbox_path / owner_name # Recalculate
        else:
            log.error(f"Main CSV inbox directory not found or is not a directory: {main_inbox_path}")
            sys.exit(1)

    # Create the specific owner's output directory within the main inbox if it doesn't exist
    try:
        owner_output_path.mkdir(parents=True, exist_ok=True)
        log.info(f"Ensured owner output directory exists: {owner_output_path}")
    except Exception as e:
        log.error(f"Could not create owner output directory {owner_output_path}: {e}")
        sys.exit(1)

    # --- Process PDFs ---
    pdf_files = list(input_path.glob("*.pdf"))        # restore normal listing
    log.info("Found %d PDF file(s)…", len(pdf_files)) # Use the original logging style
    if not pdf_files:
        log.warning(f"No PDF files found in {input_path}")
        sys.exit(0)

    # log.info(f"Found {len(pdf_files)} PDF file(s) to process for owner '{owner_name}'.") # Replaced by the line above
    processed_count = 0
    skipped_count = 0
    for pdf_file in pdf_files:
        # Pass owner_output_path and owner_name to the processing function
        success = process_pdf(pdf_file, owner_output_path, owner_name)
        if success:
            processed_count += 1
        else:
            skipped_count += 1

    log.info(f"Finished processing. Successfully processed: {processed_count}, Skipped/Failed: {skipped_count}.")
    log.info("="*50)

if __name__ == "__main__":
    main()
    # --- Clean up hanging Java process ---
    try:
        # Force jpype initialization if it was used (tabula might use subprocess fallback)
        tabula.environment_info()
        import jpype
        if jpype.isJVMStarted():
            log.info("Shutting down JVM...")
            jpype.shutdownJVM()
            log.info("JVM shutdown complete.")
    except ImportError:
        log.debug("jpype not imported, likely using subprocess fallback. No JVM shutdown needed.")
    except Exception as e_jvm:
        log.warning(f"Error during JVM shutdown attempt: {e_jvm}")
