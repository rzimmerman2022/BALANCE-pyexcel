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

import camelot  # Changed from tabula
import pdfplumber
import re
import pandas as pd
from pathlib import Path

# import duckdb # No longer directly writing Parquet from this script
import argparse
import logging
import sys

# --- Configure Logging ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
log = logging.getLogger(__name__)


# --- Helper Functions ---
def find_col_index(columns: list[str], keywords: list[str]) -> int | None:
    """Finds the index of the first column matching any keyword."""
    for i, col in enumerate(columns):
        for keyword in keywords:
            if keyword in col:
                return i
    return None


def find_transaction_table(tables, pdf_name: str) -> pd.DataFrame | None:
    """
    Identifies the most likely transaction table from a list of Camelot tables.

    Args:
        tables: Camelot TableList object.
        pdf_name (str): Name of the PDF file for logging.

    Returns:
        pd.DataFrame | None: The identified transaction DataFrame, or None if not found.
    """
    transaction_df = None
    expected_headers = [
        "trans",
        "post",
        "description",
        "charges",
        "credits",
        "amount",
        "date",
        "details",
        "merchant",
    ]  # Expanded keywords

    log.debug(
        f"Searching for transaction table among {tables.n} extracted tables for {pdf_name}..."
    )
    best_overall_score = -1
    best_table_index = -1
    best_header_row_index = (
        -1
    )  # Index of the row identified as header within the best table

    for i, table in enumerate(tables):
        if (
            not hasattr(table, "df") or table.df.empty or table.df.shape[1] < 4
        ):  # Need at least a few columns
            log.debug(f"Table {i} has no valid/sufficient DataFrame, skipping.")
            continue

        df = table.df
        max_rows_to_check = min(
            5, df.shape[0]
        )  # Check first 5 rows or fewer if table is small
        table_best_score = -1
        table_best_header_row = -1

        # Check original headers first
        cleaned_columns = [
            str(col).lower().strip().replace("\n", " ") for col in df.columns
        ]
        header_score = sum(
            1
            for keyword in expected_headers
            if any(keyword in col for col in cleaned_columns)
        )
        log.debug(
            f"Table {i} Original Header Score: {header_score}, Columns: {cleaned_columns}"
        )
        if header_score >= 3:  # Threshold for considering original headers
            table_best_score = header_score
            table_best_header_row = -1  # Indicate using original headers

        # Check first few rows
        for row_idx in range(max_rows_to_check):
            row_data = df.iloc[row_idx]
            # Ensure row has same number of elements as columns before checking
            if len(row_data) != df.shape[1]:
                log.debug(
                    f"Table {i}, Row {row_idx}: Skipping due to length mismatch ({len(row_data)} vs {df.shape[1]})"
                )
                continue

            cleaned_row = [
                str(cell).lower().strip().replace("\n", " ") for cell in row_data
            ]
            row_score = sum(
                1
                for keyword in expected_headers
                if any(keyword in cell for cell in cleaned_row)
            )
            log.debug(
                f"Table {i}, Row {row_idx} Score: {row_score}, Data: {cleaned_row}"
            )

            # If this row has a better score, update the best for this table
            if row_score >= 3 and row_score > table_best_score:
                table_best_score = row_score
                table_best_header_row = row_idx

        log.debug(
            f"Table {i} Best Score: {table_best_score}, Best Header Row Index: {table_best_header_row}"
        )

        # If this table's best score is better than the overall best score found so far
        if table_best_score > best_overall_score:
            best_overall_score = table_best_score
            best_table_index = i
            best_header_row_index = table_best_header_row

    # Process the best table found
    if best_table_index != -1:
        log.info(
            f"Table {best_table_index} identified as the most likely transaction table (score: {best_overall_score}, header row: {best_header_row_index})."
        )
        transaction_df = tables[best_table_index].df.copy()  # Use a copy

        # If a row was identified as header (not the original -1)
        if best_header_row_index != -1:
            log.warning(
                f"Promoting row {best_header_row_index} of Table {best_table_index} to header."
            )
            # Set the identified row as header
            transaction_df.columns = transaction_df.iloc[best_header_row_index]
            # Drop all rows above and including the header row, then reset index
            transaction_df = transaction_df.iloc[
                best_header_row_index + 1 :
            ].reset_index(drop=True)
        # else: log.debug("Using original headers for the selected table.") # Optional: log if original headers were best

        return transaction_df
    else:
        log.error(
            f"Could not identify a suitable transaction table in {pdf_name} (max score < 3)."
        )
        return None


# --- Define Schema ID --- # Original line, keep for context
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
                log.warning(
                    f"Could not extract text from first page of {pdf_path.name}"
                )
                return None

            # Regex to find "MM/DD/YYYY - MM/DD/YYYY" pattern (more robust)
            # Allows for different separators and spacing
            match = re.search(
                r"(\d{1,2}/\d{1,2}/(\d{4}))\s*[-–—to]+\s*(\d{1,2}/\d{1,2}/\d{4})",
                text,
                re.IGNORECASE,
            )
            if match:
                # Year is typically consistent, take the first one found
                year = match.group(2)
                log.debug(
                    f"Extracted year '{year}' from header pattern in {pdf_path.name}"
                )
                return year
            else:
                # Fallback: Look for "Statement Period MM/DD/YY - MM/DD/YY" and infer century
                match_short_year = re.search(
                    r"(\d{1,2}/\d{1,2}/(\d{2}))\s*[-–—to]+\s*(\d{1,2}/\d{1,2}/\d{2})",
                    text,
                    re.IGNORECASE,
                )
                if match_short_year:
                    short_year = match_short_year.group(2)
                    # Basic assumption: 'YY' >= 70 means 19YY, else 20YY (adjust if needed)
                    year = (
                        f"20{short_year}" if int(short_year) < 70 else f"19{short_year}"
                    )
                    log.warning(
                        f"Extracted year '{year}' using short year fallback in {pdf_path.name}"
                    )
                    return year
                else:
                    # Fallback: Look for just a 4-digit year near the top
                    match_year_only = re.search(
                        r"\b(20\d{2})\b", text[:500]
                    )  # Search near top
                    if match_year_only:
                        year = match_year_only.group(1)
                        log.warning(
                            f"Found year '{year}' using generic year fallback in {pdf_path.name}"
                        )
                        return year
                    else:
                        log.warning(
                            f"Could not find statement period year in header of {pdf_path.name}"
                        )
                        return None
    except Exception as e:
        log.error(
            f"Error reading PDF header with pdfplumber for {pdf_path.name}: {e}",
            exc_info=True,
        )
        return None


def append_to_master(df_input: pd.DataFrame, owner_name: str):
    """
    Appends a DataFrame to the master Parquet file (data/processed/combined_transactions.parquet).
    Ensures schema consistency and handles file/table creation.
    """
    # Stage 1: This function no longer writes to a Parquet file.
    # The df_input and owner_name are passed but not used for file output here.
    # Future stages might reintroduce staging logic if needed.
    log.info(
        f"append_to_master called for owner {owner_name} with {len(df_input)} rows. Parquet writing is disabled in Stage 1."
    )
    # To prevent breaking the call site, the function still exists but does nothing.
    # If df_input manipulation (like adding Owner column or schema alignment)
    # was critical for other non-Parquet purposes, it could be kept.
    # For Stage 1, the primary goal is to stop Parquet output from this script.
    pass  # Explicitly do nothing


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
    try:  # Wrap main logic in a try block
        # --- 1. Extract Statement Year ---
        statement_year = extract_year_from_header(pdf_path)
        if not statement_year:
            log.error(
                f"Could not determine statement year for {pdf_path.name}. Skipping."
            )
            return False

        # --- 2. Extract Tables with Camelot (Stream First) ---
        # tables = [] # F841: Local variable `tables` is assigned to but never used
        combined_df = None  # Initialize combined_df
        extraction_mode = None

        # Try Stream first
        try:
            log.info(f"Attempting Camelot stream extraction for {pdf_path.name}")
            stream_tables = camelot.read_pdf(
                str(pdf_path),
                pages="1-end",
                flavor="stream",
                suppress_stdout=True,
                edge_tol=500,
                row_tol=10,
            )
            log.info(f"Stream found {stream_tables.n} table(s).")
            # --- Select the Transaction Table (Stream) ---
            transaction_df_stream = find_transaction_table(stream_tables, pdf_path.name)
            if transaction_df_stream is not None:
                # tables = stream_tables # Keep original table list if needed later (F841)
                combined_df = transaction_df_stream  # Use the selected table
                extraction_mode = "stream"
                log.info(
                    f"Using transaction table found via stream mode. Shape: {combined_df.shape}"
                )
            else:
                log.warning(
                    f"Stream mode did not identify a transaction table for {pdf_path.name}."
                )

        except Exception as e_stream:
            log.warning(
                f"Camelot stream extraction failed for {pdf_path.name}: {e_stream}. Trying lattice."
            )

        # Try Lattice if Stream failed or didn't find a table
        if extraction_mode is None:
            try:
                log.info(f"Attempting Camelot lattice extraction for {pdf_path.name}")
                lattice_tables = camelot.read_pdf(
                    str(pdf_path),
                    pages="1-end",
                    flavor="lattice",
                    suppress_stdout=True,
                    line_scale=40,
                )
                log.info(f"Lattice found {lattice_tables.n} table(s).")
                # --- Select the Transaction Table (Lattice) ---
                transaction_df_lattice = find_transaction_table(
                    lattice_tables, pdf_path.name
                )
                if transaction_df_lattice is not None:
                    # tables = lattice_tables # Keep original table list - F841 tables was unused
                    combined_df = transaction_df_lattice  # Use the selected table
                    extraction_mode = "lattice"
                    log.info(
                        f"Using transaction table found via lattice mode. Shape: {combined_df.shape}"
                    )
                else:
                    log.error(
                        f"Lattice mode also did not identify a transaction table for {pdf_path.name}. Skipping."
                    )
                    return False

            except Exception as e_lattice:
                log.error(
                    f"Camelot lattice extraction also failed for {pdf_path.name}: {e_lattice}. Skipping."
                )
                return False

        # --- 3. Basic Cleanup (on selected table) ---

        # Drop fully empty rows
        combined_df.dropna(how="all", inplace=True)
        # Reset index after dropping rows
        combined_df.reset_index(drop=True, inplace=True)

        if combined_df.empty:
            log.warning(
                f"DataFrame empty after initial cleanup for {pdf_path.name}. Skipping."
            )
            return False

        # --- 4. Identify and Rename Columns ---
        # This needs to be more robust and handle different potential column names/orders
        # based on stream vs lattice and potential header misinterpretations.

        # Clean current column names first
        original_columns = combined_df.columns.tolist()
        combined_df.columns = [
            str(col).lower().strip().replace("\n", " ") for col in original_columns
        ]
        cleaned_columns = combined_df.columns.tolist()
        log.debug(f"Cleaned columns for renaming: {cleaned_columns}")

        # num_cols = len(cleaned_columns) # F841 unused - This was already handled, ensuring it stays commented
        # Find essential columns based on keywords using helper function
        trans_date_col_idx = find_col_index(cleaned_columns, ["trans date", "date"])
        post_date_col_idx = find_col_index(cleaned_columns, ["post date"])
        desc_col_idx = find_col_index(
            cleaned_columns, ["description", "merchant", "details"]
        )
        ref_col_idx = find_col_index(cleaned_columns, ["reference number", "ref"])
        acct_col_idx = find_col_index(cleaned_columns, ["card ending", "account"])
        charges_col_idx = find_col_index(
            cleaned_columns, ["charges", "debit", "withdrawals"]
        )
        credits_col_idx = find_col_index(cleaned_columns, ["credits", "deposit"])
        amount_col_idx = find_col_index(
            cleaned_columns, ["amount"]
        )  # For cases where it's a single column

        # --- Map to Standard Names ---
        final_col_map = {}  # Map standard name -> original cleaned name
        if trans_date_col_idx is not None:
            final_col_map["TransDate"] = cleaned_columns[trans_date_col_idx]
        if post_date_col_idx is not None:
            final_col_map["PostDate"] = cleaned_columns[post_date_col_idx]
        if desc_col_idx is not None:
            final_col_map["RawMerchant"] = cleaned_columns[desc_col_idx]
        if ref_col_idx is not None:
            final_col_map["ReferenceNumber"] = cleaned_columns[ref_col_idx]
        if acct_col_idx is not None:
            final_col_map["AccountLast4"] = cleaned_columns[acct_col_idx]

        # --- Handle Amount (Charges/Credits or Single Column) ---
        has_charges_credits = (
            charges_col_idx is not None and credits_col_idx is not None
        )
        has_single_amount = amount_col_idx is not None
        charges_col_name = (
            cleaned_columns[charges_col_idx] if charges_col_idx is not None else None
        )
        credits_col_name = (
            cleaned_columns[credits_col_idx] if credits_col_idx is not None else None
        )
        single_amount_col_name = (
            cleaned_columns[amount_col_idx] if amount_col_idx is not None else None
        )

        if not has_charges_credits and not has_single_amount:
            log.error(
                f"Could not identify Amount columns (neither Charges/Credits nor Amount) in {pdf_path.name}. Columns: {cleaned_columns}. Skipping."
            )
            return False

        # Select only the columns we intend to use
        cols_to_keep_original = list(
            final_col_map.values()
        )  # Get original names mapped so far
        if has_charges_credits:
            cols_to_keep_original.extend([charges_col_name, credits_col_name])
        elif has_single_amount:
            cols_to_keep_original.append(single_amount_col_name)
            final_col_map["Amount"] = (
                single_amount_col_name  # Map directly if single column
            )

        # Ensure no duplicates and preserve order
        seen = set()
        cols_to_keep = []
        for col in (
            combined_df.columns
        ):  # Iterate through original cleaned columns to keep order
            if col in cols_to_keep_original and col not in seen:
                cols_to_keep.append(col)
                seen.add(col)

        combined_df = combined_df[cols_to_keep]
        log.debug(f"Kept columns: {cols_to_keep}")

        # Rename based on final_col_map (invert map for pandas rename)
        rename_dict = {
            v: k for k, v in final_col_map.items() if v in combined_df.columns
        }  # Ensure col exists
        combined_df.rename(columns=rename_dict, inplace=True)
        log.info(f"Renamed columns: {combined_df.columns.tolist()}")

        # --- 5. Identify and Clean Numeric Columns ---
        log.debug("Identifying and cleaning potential numeric columns...")
        # Updated regex to handle optional $ inside parentheses
        money_re = re.compile(
            r"""^          # start
                -?         # optional leading minus
                \$?        # optional leading dollar
                \(?        # optional opening paren
                -?         # optional minus again (rare but harmless)
                \$?        # optional $ inside the paren
                \d[\d,]*   # digits & thousands commas
                (\.\d+)?   # optional decimal part
                \)?        # optional closing paren
                $          # end
            """,
            re.VERBOSE,
        )
        numeric_cols_original_names = []
        for col in cols_to_keep:  # Use the list of columns kept before renaming
            # Check if the column likely contains monetary values
            # Use head(20) to avoid checking entire large columns
            try:
                is_money = (
                    combined_df[col]
                    .astype(str)
                    .str.strip()
                    .head(20)
                    .str.match(money_re)
                    .any()
                )
                if pd.notna(is_money) and is_money:
                    numeric_cols_original_names.append(col)
                    log.debug(f"Identified potential numeric column: {col}")
                    # Clean the column: remove $, handle parentheses for negatives (allowing commas inside)
                    combined_df[col] = (
                        combined_df[col]
                        .astype(str)
                        .str.replace(r"[$,]", "", regex=True)
                        .str.strip()
                    )
                    combined_df[col] = combined_df[col].str.replace(
                        r"\(([\d,]+\.?\d*)\)", r"-\1", regex=True
                    )  # (1,234.56) -> -1234.56
                    # Convert to numeric, coercing errors
                    combined_df[col] = pd.to_numeric(combined_df[col], errors="coerce")
            except Exception as e:
                log.warning(
                    f"Error processing column '{col}' during numeric check/clean: {e}"
                )
                continue  # Skip this column if error occurs

        log.debug(f"Cleaned numeric columns: {numeric_cols_original_names}")

        # --- 6. Derive Final 'Amount' Column (Revised Cleaning) ---
        log.debug("Deriving final 'Amount' column (with revised cleaning)...")
        # Get potentially renamed column names
        creds_final_name = rename_dict.get(credits_col_name, credits_col_name)
        chgs_final_name = rename_dict.get(charges_col_name, charges_col_name)
        tot_final_name = rename_dict.get(single_amount_col_name, single_amount_col_name)

        # Get the series
        creds_series = (
            combined_df.get(creds_final_name)
            if creds_final_name in combined_df
            else None
        )
        chgs_series = (
            combined_df.get(chgs_final_name) if chgs_final_name in combined_df else None
        )
        tot_series = (
            combined_df.get(tot_final_name) if tot_final_name in combined_df else None
        )

        # --- Clean and Convert within Step 6 ---
        def clean_and_convert(series):
            if series is None:
                return None
            # Ensure string type, clean $, handle (), convert to numeric
            cleaned = (
                series.astype(str).str.replace(r"[$,]", "", regex=True).str.strip()
            )
            cleaned = cleaned.str.replace(r"\((\d+\.?\d*)\)", r"-\1", regex=True)
            return pd.to_numeric(cleaned, errors="coerce")

        creds_numeric = clean_and_convert(creds_series)
        chgs_numeric = clean_and_convert(chgs_series)
        tot_numeric = clean_and_convert(tot_series)  # Clean tot as well if it exists

        cols_to_drop_after_calc = []

        if creds_numeric is not None or chgs_numeric is not None:
            log.debug(
                f"Calculating Amount from Credits ('{creds_final_name}') and/or Charges ('{chgs_final_name}')"
            )
            creds_float = creds_numeric.fillna(0) if creds_numeric is not None else 0.0
            chgs_float = chgs_numeric.fillna(0) if chgs_numeric is not None else 0.0
            combined_df["Amount"] = (
                creds_float - chgs_float
            )  # Credits are +, Charges are -

            if creds_series is not None and creds_final_name != "Amount":
                cols_to_drop_after_calc.append(creds_final_name)
            if chgs_series is not None and chgs_final_name != "Amount":
                cols_to_drop_after_calc.append(chgs_final_name)

            if tot_numeric is not None:
                log.debug(
                    f"Found existing total column ('{tot_final_name}'), using its values where available."
                )
                # Use the cleaned tot_numeric, fillna for the where condition
                tot_float = tot_numeric  # Already numeric
                combined_df["Amount"] = combined_df["Amount"].where(
                    tot_numeric.isna(), tot_float
                )
                if tot_series is not None and tot_final_name != "Amount":
                    cols_to_drop_after_calc.append(tot_final_name)

        elif tot_numeric is not None:
            log.debug(f"Using existing total column ('{tot_final_name}') as Amount.")
            # Assign the cleaned numeric series directly
            if tot_final_name != "Amount":
                combined_df["Amount"] = tot_numeric
                if tot_series is not None:
                    cols_to_drop_after_calc.append(tot_final_name)
            else:
                # Already named 'Amount', ensure it's the cleaned numeric version
                combined_df["Amount"] = tot_numeric

        else:
            # Best effort: use the first identified numeric column (using original names list)
            log.warning(
                "Could not find standard 'credits'/'charges'/'amount'. Using first identified numeric column as Amount."
            )
            numeric_cols_final_names = [
                rename_dict.get(orig_name, orig_name)
                for orig_name in numeric_cols_original_names
                if rename_dict.get(orig_name, orig_name) in combined_df
            ]

            if numeric_cols_final_names:
                first_numeric_col = numeric_cols_final_names[0]
                log.warning(f"Using '{first_numeric_col}' as fallback Amount column.")
                if first_numeric_col != "Amount":
                    combined_df["Amount"] = combined_df[first_numeric_col].astype(float)
                    # Drop all *other* numeric columns identified
                    cols_to_drop_after_calc.extend(
                        [col for col in numeric_cols_final_names]
                    )  # Drop all including the one used
                else:
                    # Already named 'Amount', just ensure type
                    combined_df["Amount"] = combined_df["Amount"].astype(float)
                    # Drop other numeric columns
                    cols_to_drop_after_calc.extend(
                        [col for col in numeric_cols_final_names if col != "Amount"]
                    )
            else:  # Ensure this else aligns with the 'if numeric_cols_final_names:'
                log.error(
                    f"No numeric columns found to use as fallback Amount for {pdf_path.name}. Skipping."
                )
                return False  # Cannot proceed without an Amount

        # --- 7. Drop Intermediate Numeric Columns ---
        # Remove duplicates before dropping
        cols_to_drop_after_calc = sorted(list(set(cols_to_drop_after_calc)))
        # Ensure columns actually exist before attempting to drop
        cols_to_drop_final = [
            col
            for col in cols_to_drop_after_calc
            if col in combined_df.columns and col != "Amount"
        ]  # Don't drop the final Amount!
        if cols_to_drop_final:
            log.debug(f"Dropping intermediate numeric columns: {cols_to_drop_final}")
            combined_df.drop(columns=cols_to_drop_final, inplace=True)
        else:
            log.debug("No intermediate numeric columns to drop.")

        # --- 8. Validate Final Amount Column ---
        # Check if 'Amount' column exists and has valid data
        if "Amount" not in combined_df.columns:
            log.error(
                f"'Amount' column not found after processing for {pdf_path.name}. Columns: {combined_df.columns.tolist()}. Skipping."
            )
            return False
        if combined_df["Amount"].notna().sum() == 0:
            log.error(
                f"No valid numeric values found in Amount column after cleaning for {pdf_path.name}. Skipping write."
            )
            return False
        else:
            # Drop rows where Amount *is* NA after cleaning
            initial_rows = len(combined_df)
            combined_df.dropna(subset=["Amount"], inplace=True)
            if len(combined_df) < initial_rows:
                log.debug(
                    f"Dropped {initial_rows - len(combined_df)} rows with invalid Amount."
                )

        if combined_df.empty:
            log.warning(
                f"DataFrame became empty after dropping rows with invalid Amount for {pdf_path.name}. Skipping."
            )
            return False

        # --- 7. Inject Year into TransDate ---
        log.debug(f"Injecting year '{statement_year}' into TransDate...")
        # Ensure TransDate is string, handle potential NaNs introduced earlier if any step failed partially
        # Clean multi-line entries, keeping only the first line (potential date)
        combined_df["TransDate"] = (
            combined_df["TransDate"].astype(str).str.split("\n").str[0].str.strip()
        )
        log.debug(
            f"Cleaned TransDate column head:\n{combined_df['TransDate'].head().to_string()}"
        )
        # Append year only if it looks like MM/DD
        date_pattern = r"^\d{1,2}/\d{1,2}$"
        needs_year = combined_df["TransDate"].str.match(date_pattern, na=False)
        combined_df.loc[needs_year, "TransDate"] = (
            combined_df.loc[needs_year, "TransDate"] + f"/{statement_year}"
        )

        # Convert to datetime, letting pandas infer the format
        log.debug("Attempting TransDate conversion with inferred format...")
        combined_df["TransDate"] = pd.to_datetime(
            combined_df["TransDate"], errors="coerce"
        )

        # --- Validate TransDate and Drop Invalid Rows ---
        initial_rows_date = len(combined_df)
        combined_df.dropna(subset=["TransDate"], inplace=True)
        if len(combined_df) < initial_rows_date:
            log.warning(
                f"Dropped {initial_rows_date - len(combined_df)} rows with invalid TransDate."
            )
        if combined_df.empty:
            log.warning(
                f"DataFrame became empty after dropping rows with invalid TransDate for {pdf_path.name}. Skipping."
            )
            return False  # Skip saving if no valid rows remain

        # --- Temporarily Comment Out Date Validation/Dropping --- # Keep this comment block if needed for future reference
        # log.debug("Skipping TransDate validation/dropping for now.") # Original comment
        # # Validate TransDate conversion # Original comment
        # if combined_df["TransDate"].isna().any(): # Original comment
        #     num_failed = combined_df["TransDate"].isna().sum() # Original comment
        #     log.warning(f"{num_failed} rows failed TransDate conversion for {pdf_path.name}. Retaining these rows with NaT.") # Original comment
        #     # combined_df.dropna(subset=["TransDate"], inplace=True) # Don't drop # Original comment

        # if combined_df.empty: # Original comment
        #     log.warning(f"DataFrame became empty after dropping rows with invalid TransDate for {pdf_path.name}. Skipping.") # Original comment
        # --- End Temporary Comment Out ---

        # Check if empty *after* dropping invalid dates (already handled above, but double-check doesn't hurt)
        if combined_df.empty:
            log.warning(
                "DataFrame is empty before final column selection (double-check). Skipping."
            )
            return False  # Should have already returned if empty after date drop

        # --- 8. Final Column Selection and Save ---
        # Select columns based on the schema's expected input (and what we successfully renamed)
        # Schema expects: TransDate, RawMerchant, Amount, AccountLast4, PostDate, ReferenceNumber
        # We renamed to: TransDate, PostDate, RawMerchant, Amount, AccountLast4 (potentially)
        # Select all columns that were successfully renamed and exist in the DataFrame
        final_columns_present = combined_df.columns.tolist()

        # Ensure the core required columns for the schema are still there before saving
        schema_required_cols = [
            "TransDate",
            "RawMerchant",
            "Amount",
        ]  # From jordyn_pdf schema map
        if not all(col in final_columns_present for col in schema_required_cols):
            log.error(
                f"Schema-required columns ({schema_required_cols}) missing before save for {pdf_path.name}. Columns present: {final_columns_present}. Skipping."
            )
            return False

        # --- ADD NEWLINE CLEANING STEP ---
        log.debug("Cleaning newline characters from string columns before saving...")
        string_cols_to_clean = [
            "RawMerchant",
            "ReferenceNumber",
            "AccountLast4",
            "PostDate",
        ]  # Add others if needed
        for col in string_cols_to_clean:
            if col in combined_df.columns:
                # Ensure column is string type, replace NaN/NaT with empty string, then replace newline
                # Using .astype(str) handles potential NaNs/NaTs safely
                combined_df[col] = (
                    combined_df[col]
                    .astype(str)
                    .str.replace("nan", "", regex=False)
                    .str.replace("NaT", "", regex=False)
                    .str.replace("\r", " ", regex=False)
                    .str.replace("\n", " ", regex=False)
                    .str.strip()
                )
                log.debug(f"Cleaned newlines/CRs in column: {col}")
        # --- END NEWLINE CLEANING STEP ---

        final_df = combined_df[
            final_columns_present
        ]  # Keep all successfully processed columns
        log.info(
            f"Final DataFrame shape {final_df.shape} with columns {final_columns_present}"
        )

        # --- filename & output path ----------------------------------
        try:  # ← 8 spaces now
            # Get month from the first valid TransDate for filename
            first_valid_date = final_df["TransDate"].iloc[0]
            # Check if the date is valid before accessing .month
            if pd.notna(first_valid_date):
                output_month = f"{first_valid_date.month:02d}"
                output_csv_name = (
                    f"BALANCE - {owner_name} PDF - {statement_year}-{output_month}.csv"
                )
            else:
                # Fallback if the first date is NaT
                log.warning(
                    f"First TransDate is invalid for {pdf_path.name}. "
                    "Using original PDF stem name."
                )
                output_csv_name = f"BALANCE - {owner_name} PDF - {pdf_path.stem}.csv"
        except (IndexError, AttributeError, ValueError):  # Added ValueError
            log.warning(
                f"Could not determine month from TransDate for {pdf_path.name}. "
                "Using original PDF stem name."
            )
            output_csv_name = (
                f"BALANCE - {owner_name} PDF - {pdf_path.stem}.csv"  # Fallback name
            )

        output_csv_path = owner_output_dir / output_csv_name  # ← aligned with try

        try:
            final_df.to_csv(
                output_csv_path, index=False, date_format="%Y-%m-%d"
            )  # Use ISO date format
            log.info(f"Successfully saved cleaned data to {output_csv_path.name}")

            # --- Append to Master Parquet ---
            # This operation is considered an add-on. Errors here should be logged
            # but not cause the primary PDF-to-CSV processing to be marked as failed.
            try:
                log.info(
                    f"Attempting to append data from {pdf_path.name} to master Parquet file."
                )
                append_to_master(
                    final_df, owner_name
                )  # Pass original final_df and owner_name
            except Exception as e_parquet_append:
                # Log the error from appending to Parquet.
                # This does not change the return status of process_pdf,
                # as CSV creation was successful.
                log.error(
                    f"Error during master Parquet append for {pdf_path.name}: {e_parquet_append}",
                    exc_info=True,
                )
            # --- End Append to Master Parquet ---

            return True  # Indicate success of CSV processing primarily
        except Exception as e_save:
            log.error(
                f"Error saving final CSV for {pdf_path.name} to {output_csv_path.name}: {e_save}"
            )
            # Let the outer except block handle this by returning False directly
            return False  # Indicate failure on save

    # Catch broad exceptions during Camelot/pdfplumber processing or saving
    except Exception as e_process:  # This except now correctly pairs with the outer try
        log.error(f"Failed to process PDF {pdf_path.name}: {e_process}", exc_info=True)
        return False  # Indicate failure for any reason during processing/saving


def main():
    """Main script execution"""
    parser = argparse.ArgumentParser(
        description="Extract tables from PDF bank statements to CSV using Camelot and pdfplumber.",  # Updated description
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog="Example: poetry run python scripts/process_pdfs.py C:\\PDF_Statements C:\\MyCSVs Jordyn -v",
    )
    parser.add_argument(
        "input_dir",
        help="Directory containing PDF files to process (e.g., 'csv_inbox_real/Jordyn').",
    )
    parser.add_argument(
        "main_inbox_dir",
        help="Path to the main CSV inbox directory (e.g., 'CSVs'). Owner subfolder will be created here.",
    )
    parser.add_argument(
        "owner_name",
        help="Name of the owner (e.g., Jordyn) - used for subfolder name and output filename.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging (DEBUG level).",
    )

    args = parser.parse_args()

    # --- Setup Logging Level ---
    log_level = logging.DEBUG if args.verbose else logging.INFO
    # Configure root logger AND specific logger for this script
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    # Ensure our script's logger also adheres to the level
    logging.getLogger(__name__).setLevel(log_level)

    log.info("=" * 60)
    log.info("Starting PDF Processing Script (Camelot + pdfplumber)")
    log.info(f"Input Dir: {args.input_dir}")
    log.info(f"Output Base Dir: {args.main_inbox_dir}")
    log.info(f"Owner: {args.owner_name}")
    log.info(f"Verbose: {args.verbose}")
    log.info("=" * 60)

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
        sys.exit(1)  # Changed from trying to correct path

    # Create the specific owner's output directory within the main inbox
    try:
        owner_output_path.mkdir(parents=True, exist_ok=True)
        log.info(f"Ensured owner output directory exists: {owner_output_path}")
    except Exception as e:
        log.error(f"Could not create owner output directory {owner_output_path}: {e}")
        sys.exit(1)

    # --- Process PDFs ---
    pdf_files = sorted(
        list(input_path.glob("*.pdf"))
    )  # Sort for deterministic processing
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
            log.warning(
                f"Skipped or failed processing for: {pdf_file.name}"
            )  # Add specific skip message

    # ────────────────── summary / exit code ──────────────────
    log.info("------------------------------------------------------------")
    log.info("Processing Summary:")
    log.info("  Total PDFs Found: %s", len(pdf_files))
    log.info("  Successfully Processed & Saved: %s", processed_count)
    log.info("  Skipped / Failed: %s", skipped_count)
    log.info("============================================================")

    # exit code: 0 = at least one file processed; 1 = total failure
    sys.exit(0 if processed_count else 1)


if __name__ == "__main__":
    main()
    # No JVM shutdown needed for Camelot/pdfplumber
