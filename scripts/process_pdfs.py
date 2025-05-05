# -*- coding: utf-8 -*-
"""
==============================================================================
Script: process_pdfs.py
Project: BALANCE-pyexcel
Description: Processes PDF bank statements found in an input directory using
             Camelot, extracts tables, and saves them as CSV files in an
             output directory. Includes error handling for problematic PDFs.
==============================================================================

Version: 0.1.0
Last Modified: 2025-05-04
Author: AI Assistant (Cline)
"""

import camelot
import pandas as pd
from pathlib import Path
import argparse
import logging
import sys
import os

# --- Configure Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# --- Define Schema ID ---
# Note: SCHEMA_ID is no longer used for filename generation directly
# SCHEMA_ID = "jordyn_pdf" # As suggested in the review

def process_pdf(pdf_path: Path, owner_output_dir: Path, owner_name: str) -> bool:
    """
    Extracts tables from a single PDF using Camelot, concatenates them,
    and saves the result as a single CSV in the specified owner's directory.

    Args:
        pdf_path (Path): Path to the input PDF file.
        owner_output_dir (Path): Directory for the specific owner within the main inbox.
        owner_name (str): Name of the owner.

    Returns:
        bool: True if processing and saving were successful, False otherwise.
    """
    log.info(f"Processing PDF: {pdf_path.name} for owner: {owner_name}")
    all_tables_df = []
    try:
        # Use Camelot to read tables. 'lattice' is often good for statements with clear lines.
        # 'stream' can be tried if lattice fails. Adjust 'pages' as needed (e.g., '1-end').
        tables = camelot.read_pdf(str(pdf_path), pages='all', flavor='lattice', suppress_stdout=True)

        if not tables:
            log.warning(f"No tables found by Camelot in {pdf_path.name}. Skipping.")
            return False # Indicate failure/skip

        log.info(f"Found {tables.n} table(s) in {pdf_path.name}. Attempting to concatenate.")

        # Concatenate all found tables into a single DataFrame
        for i, table in enumerate(tables):
            try:
                df = table.df
                # Basic check: skip empty tables or tables with only headers
                if not df.empty and len(df) > 1:
                    all_tables_df.append(df)
                    log.debug(f"Added table {i+1} (shape: {df.shape}) to concatenation list.")
                else:
                    log.debug(f"Skipping empty or header-only table {i+1}.")
            except Exception as e_df:
                log.warning(f"Error accessing or checking DataFrame for table {i+1} in {pdf_path.name}: {e_df}")

        if not all_tables_df:
            log.warning(f"No valid tables found to concatenate in {pdf_path.name}. Skipping.")
            return False # Indicate failure/skip

        # Concatenate the list of DataFrames
        combined_df = pd.concat(all_tables_df, ignore_index=True)
        log.info(f"Concatenated {len(all_tables_df)} table(s) into a single DataFrame with shape {combined_df.shape}.")

        # Define the output CSV path using the new naming convention
        output_csv_name = f"BALANCE - {owner_name} PDF - {pdf_path.stem}.csv"
        output_csv_path = owner_output_dir / output_csv_name

        # Save the combined DataFrame
        try:
            # Optional: Add more cleaning here if needed before saving
            combined_df.to_csv(output_csv_path, index=False)
            log.info(f"Successfully saved combined data to {output_csv_path.name}")
            return True # Indicate success
        except Exception as e_save:
            log.error(f"Error saving combined CSV for {pdf_path.name} to {output_csv_path.name}: {e_save}")
            return False # Indicate failure

    except FileNotFoundError:
        log.error(f"PDF file not found: {pdf_path}")
        return False # Indicate failure
    except Exception as e_camelot:
        # Catch broad exceptions during Camelot processing (e.g., corrupted PDF, dependency issues)
        log.error(f"Failed to process PDF {pdf_path.name} with Camelot: {e_camelot}", exc_info=False) # Set exc_info=True for full traceback if needed
        return False # Indicate failure

def main():
    """Main script execution"""
    parser = argparse.ArgumentParser(
        description="Extract tables from PDF bank statements to CSV using Camelot.",
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
    pdf_files = list(input_path.glob("*.pdf"))
    if not pdf_files:
        log.warning(f"No PDF files found in {input_path}")
        sys.exit(0)

    log.info(f"Found {len(pdf_files)} PDF file(s) to process for owner '{owner_name}'.")
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
    # --- Check for Ghostscript (Camelot dependency) ---
    # Basic check, might need refinement based on OS
    try:
        import shutil
        if shutil.which("gs") or shutil.which("gswin64c") or shutil.which("gswin32c"):
             log.debug("Ghostscript executable found in PATH.")
        else:
             log.warning("Ghostscript executable (gs, gswin64c, gswin32c) not found in PATH. Camelot may fail.")
             log.warning("Please install Ghostscript: https://www.ghostscript.com/releases/gsdnld.html")
    except Exception as e_gs_check:
         log.warning(f"Could not check for Ghostscript: {e_gs_check}")

    main()
