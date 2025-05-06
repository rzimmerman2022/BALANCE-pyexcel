# -*- coding: utf-8 -*-
"""
==============================================================================
Script: process_pdfs.py
Project: BALANCE-pyexcel
Description: Processes PDF bank statements found in an input directory using
             Camelot (dual-pass: lattice then stream) and pdfplumber to
             extract tables and statement year, cleans the data, and saves
             results as CSV files.
==============================================================================

Version: 0.2.0
Last Modified: 2025-05-05
Author: AI Assistant (Cline)
"""

import camelot # Changed from tabula
import pdfplumber
import re
import pandas as pd
from pathlib import Path
import argparse
import logging
import sys

# --- Configure Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# --- Define Schema ID ---
def extract_year_from_header(pdf_path: Path) -> str | None:
    """Extracts the statement year from the PDF header using pdfplumber."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Check if there are any pages
            if not pdf.pages:
                log.warning(f"PDF {pdf_path.name} has no pages.")
                return None
            first_page = pdf.pages[0]
            # Extract text with layout preservation if possible, adjust tolerances
            text = first_page.extract_text(x_tolerance=2, y_tolerance=2, layout=True)
            if not text:
                # Fallback to simpler text extraction if layout fails
                text = first_page.extract_text(x_tolerance=2, y_tolerance=2)
            if not text:
                log.warning(f"Could not extract text from first page of {pdf_path.name}")
                return None

            # Regex to find "MM/DD/YYYY - MM/DD/YYYY" pattern (more robust)
            # Allows for different separators and spacing
            match = re.search(r'(\d{1,2}/\d{1,2}/(\d{4}))\s*[-–—to]+\s*(\d{1,2}/\d{1,2}/\d{4})', text, re.IGNORECASE)
            if match:
                # Year is typically consistent, take the first one found
                year = match.group(2)
                log.debug(f"Extracted year '{year}' from header pattern in {pdf_path.name}")
                return year
            else:
                # Fallback: Look for "Statement Period MM/DD/YY - MM/DD/YY" and infer century
                match_short_year = re.search(r'(\d{1,2}/\d{1,2}/(\d{2}))\s*[-–—to]+\s*(\d{1,2}/\d{1,2}/\d{2})', text, re.IGNORECASE)
                if match_short_year:
                    short_year = match_short_year.group(2)
                    # Basic assumption: 'YY' >= 70 means 19YY, else 20YY (adjust if needed)
                    year = f"20{short_year}" if int(short_year) < 70 else f"19{short_year}"
                    log.warning(f"Extracted year '{year}' using short year fallback in {pdf_path.name}")
                    return year
                else:
                    # Fallback: Look for just a 4-digit year near the top
                    match_year_only = re.search(r'\b(20\d{2})\b', text[:500]) # Search near top
                    if match_year_only:
                        year = match_year_only.group(1)
                        log.warning(f"Found year '{year}' using generic year fallback in {pdf_path.name}")
                        return year
                    else:
                        log.warning(f"Could not find statement period year in header of {pdf_path.name}")
                        return None
    except Exception as e:
        log.error(f"Error reading PDF header with pdfplumber for {pdf_path.name}: {e}", exc_info=True)
        return None

def process_pdf(pdf_path: Path, owner_output_dir: Path, owner_name: str) -> bool:
    """
    Extracts tables from a single PDF using Camelot (dual-pass), injects the
    statement year using pdfplumber, cleans data, renames columns, validates,
    and saves the result as a CSV.

    Args:
        pdf_path (Path): Path to the input PDF file.
        owner_output_dir (Path): Directory for the specific owner within the main inbox.
        owner_name (str): Name of the owner.

    Returns:
        bool: True if processing and saving were successful, False otherwise.
    """
    log.info(f"Processing PDF: {pdf_path.name} for owner: {owner_name}")

    # --- 1. Extract Statement Year ---
    statement_year = extract_year_from_header(pdf_path)
    if not statement_year:
        log.error(f"Could not determine statement year for {pdf_path.name}. Skipping.")
        return False

    # --- 2. Extract Tables with Camelot (Dual-Pass) ---
    tables = []
    try:
        log.debug(f"Attempting Camelot lattice extraction for {pdf_path.name}")
        tables = camelot.read_pdf(str(pdf_path), pages="1-end", flavor="lattice", suppress_stdout=True, line_scale=40)
        log.info(f"Lattice found {tables.n} table(s). Checking validity...")

        # Basic validity check: are there tables and do they have rows?
        # Wells Fargo statements often have multiple small tables before the main one.
        # A simple row count check might be too strict. Let's check total rows across tables.
        total_rows = sum(t.df.shape[0] for t in tables if hasattr(t, 'df'))
        if tables.n == 0 or total_rows < 5: # Heuristic: need at least a few rows total
            log.warning(f"Lattice extraction yielded too few rows ({total_rows}) or tables ({tables.n}). Falling back to stream mode.")
            tables = [] # Reset tables before trying stream

    except Exception as e_lattice:
        log.warning(f"Camelot lattice extraction failed for {pdf_path.name}: {e_lattice}. Falling back to stream mode.")
        tables = [] # Ensure tables is empty

    # Fallback to stream if lattice failed or produced insufficient results
    if not tables:
        try:
            log.debug(f"Attempting Camelot stream extraction for {pdf_path.name}")
            # Stream often needs more tuning (edge_tol, row_tol)
            tables = camelot.read_pdf(str(pdf_path), pages="1-end", flavor="stream", suppress_stdout=True, edge_tol=500, row_tol=10)
            log.info(f"Stream found {tables.n} table(s).")
            total_rows = sum(t.df.shape[0] for t in tables if hasattr(t, 'df'))
            if tables.n == 0 or total_rows < 5:
                 log.error(f"Stream extraction also yielded insufficient results ({total_rows} rows, {tables.n} tables) for {pdf_path.name}. Skipping.")
                 return False
        except Exception as e_stream:
            log.error(f"Camelot stream extraction failed for {pdf_path.name}: {e_stream}. Skipping.")
            return False

    # --- 3. Concatenate and Basic Cleanup ---
    all_dfs = [table.df for table in tables if hasattr(table, 'df') and not table.df.empty]
    if not all_dfs:
        log.warning(f"No valid DataFrames found after Camelot extraction in {pdf_path.name}. Skipping.")
        return False

    combined_df = pd.concat(all_dfs, ignore_index=True)
    log.info(f"Concatenated {len(all_dfs)} table(s) into DataFrame shape {combined_df.shape}.")

    # Drop fully empty rows
    combined_df.dropna(how='all', inplace=True)
    # Reset index after dropping rows
    combined_df.reset_index(drop=True, inplace=True)

    if combined_df.empty:
        log.warning(f"DataFrame empty after initial cleanup for {pdf_path.name}. Skipping.")
        return False

    # --- 4. Identify and Rename Columns ---
    # This is heuristic-based for typical Wells Fargo statements. May need adjustment.
    # Assumes: Col 0/1: Trans Date (MM/DD), Col 1/2: Post Date (MM/DD or junk), Col ~Mid: Description, Last Col: Amount
    num_cols = combined_df.shape[1]
    rename_map = {}

    # Try to find columns based on content patterns
    potential_trans_date_col = -1
    potential_post_date_col = -1
    potential_amount_col = -1

    for i in range(num_cols):
        col_series = combined_df.iloc[:, i].astype(str)
        # Date pattern (MM/DD) - check a sample
        if col_series.str.match(r'^\d{1,2}/\d{1,2}$').sum() > len(combined_df) * 0.5: # If >50% match MM/DD
             if potential_trans_date_col == -1:
                 potential_trans_date_col = i
             elif potential_post_date_col == -1:
                 potential_post_date_col = i # Assume second date-like col is PostDate
        # Amount pattern (contains digits, possibly $, ., -) - check last few columns
        if i >= num_cols - 2: # Check last 2 columns
            # More robust check: contains digits and possibly currency symbols/decimal
             if col_series.str.contains(r'[\d.,$]+', na=False).sum() > len(combined_df) * 0.3: # If >30% look like numbers/currency
                 potential_amount_col = i
                 break # Assume rightmost numeric-like column is Amount

    # Assign based on findings or fall back to positional defaults
    if potential_trans_date_col != -1:
        rename_map[combined_df.columns[potential_trans_date_col]] = "TransDate"
    else:
        log.warning(f"Could not reliably detect TransDate column for {pdf_path.name}. Assuming column 0 or 1.")
        # Default assumption if detection fails (might be col 0 or 1)
        rename_map[combined_df.columns[min(1, num_cols-1)]] = "TransDate" # Use col 1 if possible, else 0

    if potential_post_date_col != -1:
        rename_map[combined_df.columns[potential_post_date_col]] = "PostDate"
    else:
        # Often PostDate is less critical or noisy, don't assume default if not found
        log.debug(f"PostDate column not detected for {pdf_path.name}.")
        pass # Don't rename if not found

    if potential_amount_col != -1:
        rename_map[combined_df.columns[potential_amount_col]] = "Amount"
    else:
        log.warning(f"Could not reliably detect Amount column for {pdf_path.name}. Assuming last column.")
        rename_map[combined_df.columns[num_cols - 1]] = "Amount" # Default to last column

    # Description: Assume it's the column before Amount, or a prominent middle column if Amount is last
    potential_desc_col = -1
    amount_col_idx = potential_amount_col if potential_amount_col != -1 else num_cols - 1
    if amount_col_idx > 0:
         # Check column right before amount
         potential_desc_col = amount_col_idx - 1
         # Simple check: is it mostly non-numeric?
         desc_col_series = combined_df.iloc[:, potential_desc_col].astype(str)
         if desc_col_series.str.contains(r'\d', na=False).sum() < len(combined_df) * 0.3: # If <30% contain digits
             rename_map[combined_df.columns[potential_desc_col]] = "Description"
         else:
             potential_desc_col = -1 # Reset if it looks too numeric

    if potential_desc_col == -1:
         # Fallback: find the column with the longest average string length (heuristic)
         avg_lengths = {i: combined_df.iloc[:, i].astype(str).str.len().mean() for i in range(num_cols) if i not in [potential_trans_date_col, potential_post_date_col, amount_col_idx]}
         if avg_lengths:
             desc_col_idx = max(avg_lengths, key=avg_lengths.get)
             rename_map[combined_df.columns[desc_col_idx]] = "Description"
             log.debug(f"Using column {desc_col_idx} (longest avg length) as Description fallback.")
         else:
             log.warning(f"Could not determine Description column for {pdf_path.name}.")


    log.debug(f"Attempting to rename columns using map: {rename_map}")
    combined_df.rename(columns=rename_map, inplace=True)

    # Check if essential columns were renamed
    required_cols = ["TransDate", "Description", "Amount"]
    if not all(col in combined_df.columns for col in required_cols):
        log.error(f"Essential columns ({required_cols}) not found after renaming for {pdf_path.name}. Columns found: {combined_df.columns.tolist()}. Skipping.")
        return False

    # --- 5. Clean Amount Column ---
    log.debug("Cleaning Amount column...")
    combined_df["Amount"] = combined_df["Amount"].astype(str).str.replace(r'[$,]', '', regex=True).str.strip()
    # Handle credits represented like '100.00-' or '(100.00)'
    combined_df["Amount"] = combined_df["Amount"].str.replace(r'\((\d+\.?\d*)\)', r'-\1', regex=True) # (100.00) -> -100.00
    combined_df["Amount"] = combined_df["Amount"].str.replace(r'(\d+\.?\d*)-$', r'-\1', regex=True) # 100.00- -> -100.00
    combined_df["Amount"] = pd.to_numeric(combined_df["Amount"], errors='coerce')

    # --- 6. Validate Amount Column ---
    if combined_df["Amount"].notna().sum() == 0:
        log.error(f"No valid numeric values found in Amount column after cleaning for {pdf_path.name}. Skipping write.")
        return False
    else:
        # Drop rows where Amount *is* NA after cleaning
        initial_rows = len(combined_df)
        combined_df.dropna(subset=["Amount"], inplace=True)
        if len(combined_df) < initial_rows:
            log.debug(f"Dropped {initial_rows - len(combined_df)} rows with invalid Amount.")

    if combined_df.empty:
        log.warning(f"DataFrame became empty after dropping rows with invalid Amount for {pdf_path.name}. Skipping.")
        return False

    # --- 7. Inject Year into TransDate ---
    log.debug(f"Injecting year '{statement_year}' into TransDate...")
    # Ensure TransDate is string, handle potential NaNs introduced earlier if any step failed partially
    combined_df["TransDate"] = combined_df["TransDate"].astype(str).str.strip()
    # Append year only if it looks like MM/DD
    date_pattern = r'^\d{1,2}/\d{1,2}$'
    needs_year = combined_df["TransDate"].str.match(date_pattern, na=False)
    combined_df.loc[needs_year, "TransDate"] = combined_df.loc[needs_year, "TransDate"] + f"/{statement_year}"

    # Convert to datetime
    combined_df["TransDate"] = pd.to_datetime(combined_df["TransDate"], format='%m/%d/%Y', errors='coerce')

    # Validate TransDate conversion
    if combined_df["TransDate"].isna().any():
        num_failed = combined_df["TransDate"].isna().sum()
        log.warning(f"{num_failed} rows failed TransDate conversion for {pdf_path.name}. Dropping these rows.")
        combined_df.dropna(subset=["TransDate"], inplace=True)

    if combined_df.empty:
        log.warning(f"DataFrame became empty after dropping rows with invalid TransDate for {pdf_path.name}. Skipping.")
        return False

    # --- 8. Final Column Selection and Save ---
    final_columns = ["TransDate", "PostDate", "Description", "Amount"]
    # Keep only columns that exist in the DataFrame
    final_columns_present = [col for col in final_columns if col in combined_df.columns]
    # Ensure required columns are still present
    if not all(col in final_columns_present for col in required_cols):
         log.error(f"Required columns missing before save for {pdf_path.name}. Columns: {final_columns_present}. Skipping.")
         return False

    final_df = combined_df[final_columns_present]
    log.debug(f"Final DataFrame shape {final_df.shape} with columns {final_columns_present}")

    # Define output path (using year and month from TransDate for better sorting, if possible)
    try:
        # Get month from the first valid TransDate for filename
        first_valid_date = final_df["TransDate"].iloc[0]
        output_month = f"{first_valid_date.month:02d}"
        output_csv_name = f"BALANCE - {owner_name} PDF - {statement_year}-{output_month}.csv"
    except (IndexError, AttributeError):
        log.warning(f"Could not determine month from TransDate for {pdf_path.name}. Using original PDF stem name.")
        output_csv_name = f"BALANCE - {owner_name} PDF - {pdf_path.stem}.csv" # Fallback name

    output_csv_path = owner_output_dir / output_csv_name

    try:
        final_df.to_csv(output_csv_path, index=False, date_format='%Y-%m-%d') # Use ISO date format
        log.info(f"Successfully saved cleaned data to {output_csv_path.name}")
        return True # Indicate success
    except Exception as e_save:
        log.error(f"Error saving final CSV for {pdf_path.name} to {output_csv_path.name}: {e_save}")
        return False # Indicate failure

    # Removed FileNotFoundError catch as Path object checks should handle it earlier
    # Catch broad exceptions during Camelot/pdfplumber processing
    except Exception as e_process:
        log.error(f"Failed to process PDF {pdf_path.name}: {e_process}", exc_info=True)
        return False # Indicate failure


def main():
    """Main script execution"""
    parser = argparse.ArgumentParser(
        description="Extract tables from PDF bank statements to CSV using Camelot and pdfplumber.", # Updated description
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog="Example: poetry run python scripts/process_pdfs.py C:\\PDF_Statements C:\\MyCSVs Jordyn -v"
    )
    parser.add_argument("input_dir", help="Directory containing PDF files to process (e.g., 'csv_inbox_real/Jordyn').")
    parser.add_argument("main_inbox_dir", help="Path to the main CSV inbox directory (e.g., 'CSVs'). Owner subfolder will be created here.")
    parser.add_argument("owner_name", help="Name of the owner (e.g., Jordyn) - used for subfolder name and output filename.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging (DEBUG level).")

    args = parser.parse_args()

    # --- Setup Logging Level ---
    log_level = logging.DEBUG if args.verbose else logging.INFO
    # Configure root logger AND specific logger for this script
    logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # Ensure our script's logger also adheres to the level
    logging.getLogger(__name__).setLevel(log_level)

    log.info("="*60)
    log.info("Starting PDF Processing Script (Camelot + pdfplumber)")
    log.info(f"Input Dir: {args.input_dir}")
    log.info(f"Output Base Dir: {args.main_inbox_dir}")
    log.info(f"Owner: {args.owner_name}")
    log.info(f"Verbose: {args.verbose}")
    log.info("="*60)


    # --- Path Validation ---
    # Input dir is specific to owner's PDFs, e.g., csv_inbox_real/Jordyn
    input_path = Path(args.input_dir).resolve()
    # Output dir is the base CSVs dir, e.g., CSVs
    main_inbox_path = Path(args.main_inbox_dir).resolve()
    owner_name = args.owner_name
    # Owner's final output dir, e.g., CSVs/Jordyn
    owner_output_path = main_inbox_path / owner_name

    if not input_path.is_dir():
        log.error(f"Input PDF directory not found: {input_path}")
        sys.exit(1)

    # Ensure the main output directory exists
    if not main_inbox_path.is_dir():
         log.error(f"Main CSV output directory not found: {main_inbox_path}")
         sys.exit(1) # Changed from trying to correct path

    # Create the specific owner's output directory within the main inbox
    try:
        owner_output_path.mkdir(parents=True, exist_ok=True)
        log.info(f"Ensured owner output directory exists: {owner_output_path}")
    except Exception as e:
        log.error(f"Could not create owner output directory {owner_output_path}: {e}")
        sys.exit(1)

    # --- Process PDFs ---
    pdf_files = sorted(list(input_path.glob("*.pdf"))) # Sort for deterministic processing
    log.info(f"Found {len(pdf_files)} PDF file(s) in {input_path}")
    if not pdf_files:
        log.warning("No PDF files found to process.")
        sys.exit(0)

    processed_count = 0
    skipped_count = 0
    for pdf_file in pdf_files:
        success = process_pdf(pdf_file, owner_output_path, owner_name)
        if success:
            processed_count += 1
        else:
            skipped_count += 1
            log.warning(f"Skipped or failed processing for: {pdf_file.name}") # Add specific skip message

    log.info("-" * 60)
    log.info(f"Processing Summary:")
    log.info(f"  Total PDFs Found: {len(pdf_files)}")
    log.info(f"  Successfully Processed & Saved: {processed_count}")
    log.info(f"  Skipped / Failed: {skipped_count}")
    log.info("="*60)

if __name__ == "__main__":
    main()
    # No JVM shutdown needed for Camelot/pdfplumber
