# -*- coding: utf-8 -*-
"""
==============================================================================
Module: ingest.py
Project: BALANCE-pyexcel
Description: Handles the ingestion and initial processing of various CSV
             transaction files. It uses a schema registry defined in YAML
             to dynamically apply column mappings, sign corrections, and
             other rules based on the detected file format. It also handles
             recursive searching through owner-specific subdirectories.
==============================================================================

Version: 0.1.0
Last Modified: 2025-04-21 # Placeholder date
Author: Your Name / AI Assistant
"""

# ==============================================================================
# 0. IMPORTS
# ==============================================================================
from __future__ import annotations  # Ensures compatibility with type hints like str | Path
from pathlib import Path
from typing import Dict  # Used Dict explicitly
import pandas as pd
import yaml
import re
import logging

# ==============================================================================
# 1. CONFIGURATION & GLOBAL SETUP
# ==============================================================================

# --- Configure Logging ---
# Sets up basic logging to provide feedback during execution.
# Level INFO means informational messages and errors will be shown.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Define Standard Output Columns ---
# This list defines the exact columns (and their order) we want in the
# final DataFrame produced by the load_folder function. All input CSVs
# will be transformed to match this structure.
STANDARD_COLS = ["Owner", "Date", "Description", "Amount", "Account", "Category", "Bank", "Source"]

# --- Load Schema Registry from YAML ---
# The schema registry defines the rules for processing each different CSV format.
# It's loaded once when this module is imported.
_SCHEMA_REGISTRY_PATH = Path("rules/schema_registry.yml")
_SCHEMAS: list[dict] = [] # Initialize as empty list

try:
    # Attempt to read the YAML file using UTF-8 encoding.
    _SCHEMAS = yaml.safe_load(_SCHEMA_REGISTRY_PATH.read_text(encoding='utf-8'))
    if not isinstance(_SCHEMAS, list):
         # Ensure the loaded YAML is a list of dictionaries as expected.
         logging.error(f"CRITICAL: Schema registry file '{_SCHEMA_REGISTRY_PATH}' did not load as a list.")
         _SCHEMAS = []
    else:
         logging.info(f"Successfully loaded {_SCHEMA_REGISTRY_PATH} containing {len(_SCHEMAS)} schema(s).")
except FileNotFoundError:
    # Handle the critical error if the rules file doesn't exist.
    logging.error(f"CRITICAL: Schema registry file not found at '{_SCHEMA_REGISTRY_PATH}'. Ingestion will likely fail.")
    # _SCHEMAS remains empty
except yaml.YAMLError as e:
    # Handle errors during YAML parsing (e.g., incorrect formatting).
    logging.error(f"CRITICAL: Failed to parse schema registry YAML file '{_SCHEMA_REGISTRY_PATH}': {e}")
    # _SCHEMAS remains empty
except Exception as e:
    # Catch any other unexpected errors during file loading.
    logging.error(f"CRITICAL: An unexpected error occurred loading schema registry '{_SCHEMA_REGISTRY_PATH}': {e}")
    # _SCHEMAS remains empty


# ==============================================================================
# 2. HELPER FUNCTIONS (Internal Use Only)
# ==============================================================================

# ------------------------------------------------------------------------------
# Function: _find_schema
# ------------------------------------------------------------------------------
def _find_schema(csv_path: Path, df_head: pd.DataFrame) -> dict | None:
    """
    Finds the appropriate schema from the loaded registry (_SCHEMAS) that matches
    the given CSV file based on filename patterns and required header columns.

    Args:
        csv_path (Path): The path object of the CSV file being processed.
        df_head (pd.DataFrame): A DataFrame containing the first few rows (including
                                headers) of the CSV file, used for validation.

    Returns:
        dict | None: The dictionary representing the matched schema from the YAML file,
                    or None if no matching schema is found.
    """
    # Pre-check: Ensure the schema registry loaded correctly.
    if not _SCHEMAS:
        logging.error("Schema registry is empty or failed to load. Cannot match schema.")
        return None

    # Pre-process headers from the CSV preview for reliable matching.
    df_head.columns = [str(col).strip() for col in df_head.columns]
    actual_headers = set(df_head.columns) # Use a set for efficient checking

    # Iterate through each defined schema in the registry.
    for schema in _SCHEMAS:
        schema_id = schema.get('id', 'Unknown') # Get schema ID for logging
        try:
            # --- Rule 1: Match Filename ---
            filename_pattern = schema.get("match_filename")
            if not filename_pattern:
                 logging.warning(f"Schema '{schema_id}' missing 'match_filename'. Skipping.")
                 continue # Skip schema if pattern is missing
            # Use Path.match for glob pattern matching against the filename only.
            if not csv_path.match(filename_pattern):
                continue # Skip if filename doesn't match the pattern.

            # --- Rule 2: Match Header Signature ---
            required_headers = schema.get("header_signature", [])
            if not required_headers:
                # If no specific headers are required, a filename match is sufficient.
                logging.info(f"Schema '{schema_id}' matched based on filename only for: {csv_path.name}")
                return schema
            else:
                # Check if ALL required headers are present in the actual CSV headers.
                if not all(req_col in actual_headers for req_col in required_headers):
                    continue # Skip if any required header is missing.

            # --- Match Found ---
            # If both filename and header rules pass, this is the correct schema.
            logging.info(f"Schema '{schema_id}' matched headers and filename for: {csv_path.name}")
            return schema

        except Exception as e:
            # Log errors encountered while evaluating a specific schema.
            logging.error(f"Error while evaluating schema '{schema_id}' for {csv_path.name}: {e}")
            continue # Try the next schema definition.

    # --- No Match Found ---
    # If loop completes without returning, no schema matched the file.
    logging.warning(f"No schema definition found in registry for file: {csv_path.name}")
    return None

# ------------------------------------------------------------------------------
# Function: _apply_sign_rule
# ------------------------------------------------------------------------------
def _apply_sign_rule(df: pd.DataFrame, rule: str | None) -> pd.DataFrame:
    """
    Adjusts the sign of the 'Amount' column based on the rule defined in the schema.
    Ensures amounts representing outflows (expenses, withdrawals) are negative.

    Args:
        df (pd.DataFrame): The DataFrame for the current CSV file (after mapping).
                           It MUST have an 'Amount' column.
        rule (str | None): The sign rule string (e.g., 'as_is', 'flip_if_withdrawal',
                           'flip_if_positive') from the matched schema, or None.

    Returns:
        pd.DataFrame: The DataFrame with the 'Amount' sign potentially adjusted.
    """
    # If no rule specified or rule is 'as_is', no action needed.
    if rule is None or rule == "as_is":
        return df

    # --- Pre-checks ---
    # Ensure 'Amount' column exists before proceeding.
    if 'Amount' not in df.columns:
        logging.error("Sign rule application skipped: 'Amount' column not found.")
        return df
    # Ensure 'Amount' is numeric, coercing errors to NaN (Not a Number).
    # This prevents errors if Amount contained non-numeric values.
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')

    # --- Apply Rules ---
    try:
        if rule == "flip_if_withdrawal":
            # This rule assumes a 'Category' column exists and identifies outflows
            # by checking if the Category contains "Withdrawal" or "Payment".
            # REVIEW: Does YOUR data always have a useful 'Category' for this?
            if 'Category' in df.columns:
                # Create a boolean mask for rows matching the criteria.
                # Use .notna() to avoid errors on empty Category cells.
                # Use regex=True to allow matching "Payment" or "Withdrawal".
                withdrawal_mask = df["Category"].notna() & df["Category"].str.contains("Withdrawal|Payment", case=False, na=False, regex=True)
                # For matched rows, ensure the Amount is negative (take absolute value, then negate).
                df.loc[withdrawal_mask, "Amount"] = -df.loc[withdrawal_mask, "Amount"].abs()
                logging.info(f"Applied 'flip_if_withdrawal' sign rule using 'Category' column.")
            else:
                # Log a warning if the required Category column is missing for this rule.
                logging.warning("Sign rule 'flip_if_withdrawal' requires a 'Category' column, which was not found.")

        elif rule == "flip_if_positive":
            # This rule assumes any positive value in 'Amount' represents an outflow
            # that needs its sign flipped (e.g., Rocket Money, some aggregators).
            positive_mask = df["Amount"].notna() & (df["Amount"] > 0)
            # Multiply positive amounts by -1 to make them negative.
            df.loc[positive_mask, "Amount"] *= -1
            logging.info("Applied 'flip_if_positive' sign rule.")

        # Add other potential rules here if needed later (e.g., flip_if_negative)

        else:
            # Log if an unknown rule string is encountered in the YAML.
            logging.warning(f"Unknown sign_rule '{rule}' specified in schema. Amount signs left 'as_is'.")

    except Exception as e:
        # Log any unexpected errors during sign rule application.
        logging.error(f"Error applying sign rule '{rule}': {e}")

    return df

# ------------------------------------------------------------------------------
# Function: _derive_columns
# ------------------------------------------------------------------------------
def _derive_columns(df: pd.DataFrame, derived_cfg: dict[str, str] | None) -> pd.DataFrame:
    """
    Derives new columns using regular expressions on the 'Description' column,
    based on patterns defined in the schema's 'derived_columns' section.

    Currently tailored for extracting an 'Amount' if it's embedded in the description.

    Args:
        df (pd.DataFrame): The DataFrame for the current CSV (after mapping).
        derived_cfg (dict[str, str] | None): The 'derived_columns' dictionary
                                              from the schema, or None.

    Returns:
        pd.DataFrame: The DataFrame potentially with new derived columns added,
                      and 'Amount' possibly filled or created.
    """
    # If no derivation rules are defined, return the DataFrame as is.
    if derived_cfg is None:
        return df

    # --- Pre-checks ---
    # Derivation relies on the 'Description' column.
    if 'Description' not in df.columns:
        logging.error("Cannot derive columns: 'Description' column not found.")
        return df
    # Ensure 'Description' is treated as string data.
    df["Description"] = df["Description"].astype(str)

    logging.info(f"Attempting to derive columns using patterns: {derived_cfg}")

    # Loop through each derivation rule defined in the YAML.
    for new_col, pattern in derived_cfg.items():
        try:
            # Compile the regex pattern for efficiency.
            regex = re.compile(pattern)

            # Define a helper function to apply the regex and extract the amount.
            def extract_amount_from_regex(text: str) -> float | None:
                match = regex.search(text)
                if match:
                    try:
                        # Try extracting named group 'amt' first (preferred).
                        # (?P<amt>...) in regex defines a named group.
                        return float(match.group('amt'))
                    except IndexError:
                        # If 'amt' group doesn't exist, try the first captured group.
                        try:
                            return float(match.group(1))
                        except IndexError:
                            logging.warning(f"Regex pattern '{pattern}' matched '{text}' but required capture group ('amt' or group 1) not found.")
                            return pd.NA # Use pandas NA for missing numeric
                        except ValueError:
                             logging.warning(f"Could not convert captured group 1 to float from regex '{pattern}' on text '{text}'")
                             return pd.NA
                    except ValueError:
                        # Handle cases where the extracted value isn't a valid float.
                        logging.warning(f"Could not convert captured group 'amt' to float from regex '{pattern}' on text '{text}'")
                        return pd.NA
                # Return NA if the regex pattern doesn't match the description.
                return pd.NA

            # Apply the extraction function to the 'Description' column to create the new column.
            df[new_col] = df["Description"].apply(extract_amount_from_regex)
            logging.info(f"Derived column '{new_col}' using regex pattern: '{pattern}'")

            # --- Special Handling for Amount Derivation ---
            # If we specifically derived an amount (using key 'AmountFromDesc' in YAML)
            # use it to populate or create the main 'Amount' column.
            # REVIEW: Ensure the key 'AmountFromDesc' matches your YAML for Wells Fargo.
            if new_col == "AmountFromDesc":
                if "Amount" not in df.columns:
                    # If 'Amount' doesn't exist at all, create it from the derived values.
                    df["Amount"] = df[new_col]
                    logging.info("Created 'Amount' column from derived column 'AmountFromDesc'")
                else:
                    # If 'Amount' exists but has missing values, fill them using derived values.
                    original_na_count = df["Amount"].isna().sum()
                    # Use fillna() which is efficient for this purpose.
                    df["Amount"] = df["Amount"].fillna(df[new_col])
                    filled_na_count = original_na_count - df["Amount"].isna().sum()
                    if filled_na_count > 0:
                        logging.info(f"Filled {filled_na_count} missing 'Amount' values using derived column '{new_col}'")

                # Optionally drop the intermediate derived column after use.
                # Keep it for now for debugging, can be removed later.
                # df = df.drop(columns=[new_col])

        except Exception as e:
            # Log errors encountered during the derivation process for a specific rule.
            logging.error(f"Error deriving column '{new_col}' with pattern '{pattern}': {e}")

    return df

# ==============================================================================
# 3. PUBLIC API FUNCTION
# ==============================================================================

# ------------------------------------------------------------------------------
# Function: load_folder
# ------------------------------------------------------------------------------
def load_folder(folder: Path) -> pd.DataFrame:
    """
    Loads, processes, and combines all valid CSV transaction files found
    recursively within the specified base folder. It expects subdirectories
    named after the owner (e.g., /Jordyn/, /Ryan/).

    Processing Logic:
    1. Walks subdirectories using rglob('*.csv').
    2. Determines Owner from the immediate parent directory name.
    3. Reads CSV headers to identify the file's schema using _find_schema (and YAML).
    4. Reads the full CSV.
    5. Applies column mapping based on the matched schema.
    6. Derives columns if specified in the schema (e.g., Amount from Description).
    7. Normalizes essential data types (Date, Amount).
    8. Applies amount sign correction based on the matched schema's sign_rule.
    9. Adds the Owner column.
    10. Ensures all STANDARD_COLS are present, filling missing ones with NA.
    11. Selects and orders columns according to STANDARD_COLS.
    12. Concatenates results from all successfully processed files.

    Args:
        folder (Path): The root folder containing owner subfolders (e.g., /Jordyn, /Ryan)
                       which in turn contain the CSV files.

    Returns:
        pd.DataFrame: A single, combined DataFrame containing standardized data
                      from all processed files, matching STANDARD_COLS. Returns an
                      empty DataFrame with STANDARD_COLS if no files are processed.

    Raises:
        FileNotFoundError: If the specified `folder` does not exist or is not a directory.
        ValueError: If the schema registry (_SCHEMAS) failed to load.
    """
    # --- Initial Checks ---
    if not folder.is_dir():
        logging.error(f"Specified inbox path is not a valid directory: {folder}")
        raise FileNotFoundError(f"CSV inbox path not found or not a directory: {folder}")
    if not _SCHEMAS:
        # Cannot proceed without rules defined in the schema registry.
        raise ValueError("Schema registry is empty or failed to load. Cannot process files.")

    parts: list[pd.DataFrame] = [] # List to hold DataFrames from each processed file.
    logging.info(f"Starting recursive CSV scan under root folder: {folder}")

    # --- Loop through all CSVs in subfolders ---
    # Use rglob to find *.csv files in the root folder and all subdirectories.
    for csv_path in folder.rglob("*.csv"):
        # Assume the immediate parent directory name is the owner.
        owner = csv_path.parent.name.capitalize()
        logging.info(f"Processing file: {csv_path} for owner: {owner}")

        # Use a try-except block to handle errors for individual files gracefully.
        # This allows the process to continue even if one file fails.
        try:
            # --- 1. Read Preview & Find Schema ---
            # Read only first 5 rows to get headers for schema detection.
            # Use low_memory=False to help pandas guess types better with mixed data initially.
            preview_df = pd.read_csv(csv_path, nrows=5, low_memory=False)
            # Find the matching schema from the registry based on filename and headers.
            schema = _find_schema(csv_path, preview_df)

            # If no schema matches, skip this file.
            if schema is None:
                logging.warning(f"Skipping file: No matching schema found for {csv_path.name}")
                continue

            schema_id = schema.get('id', 'Unknown') # Get schema ID for logging

            # --- 2. Read Full File ---
            # Now read the entire CSV file.
            # Consider adding parameters like encoding, delimiter if pandas struggles.
            df = pd.read_csv(csv_path, low_memory=False)
            # Clean header whitespace immediately after reading.
            df.columns = [str(col).strip() for col in df.columns]
            logging.info(f"Read {len(df)} rows using schema '{schema_id}'.")

            # --- 3. Apply Schema Rules: Mapping, Derivation, Types, Sign ---
            # Apply column renaming based on the schema's 'column_map'.
            column_map = schema.get("column_map", {})
            df = df.rename(columns=column_map)
            
            # Add any static columns specified in the schema (e.g., Source for aggregator sources)
            extra_static_cols = schema.get("extra_static_cols", {})
            for col_name, col_value in extra_static_cols.items():
                df[col_name] = col_value
                logging.info(f"Added static column '{col_name}' with value '{col_value}' to all rows.")

            # Derive any additional columns specified in the schema.
            derived_cfg = schema.get("derived_columns")
            if derived_cfg:
                df = _derive_columns(df, derived_cfg)

            # Check if essential columns exist AFTER mapping/derivation.
            essential_cols = ["Date", "Description", "Amount"]
            missing_essentials = [col for col in essential_cols if col not in df.columns]
            if missing_essentials:
                logging.error(f"Essential columns {missing_essentials} missing after mapping/derivation for {csv_path.name} (Schema: {schema_id}). Skipping file.")
                continue

            # Normalize core data types (errors='coerce' turns failures into NaT/NaN).
            df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
            df["Amount"] = pd.to_numeric(df["Amount"], errors='coerce')

            # Drop rows where Date or Amount conversion failed, as they are critical.
            initial_rows = len(df)
            df.dropna(subset=["Date", "Amount"], inplace=True)
            if len(df) < initial_rows:
                logging.warning(f"Dropped {initial_rows - len(df)} rows from {csv_path.name} due to invalid Date or Amount.")
            if df.empty:
                logging.warning(f"File became empty after dropping invalid rows: {csv_path.name}. Skipping file.")
                continue

            # Apply the amount sign correction rule defined in the schema.
            df = _apply_sign_rule(df, schema.get("sign_rule"))

            # --- 4. Add Owner and Ensure Standard Columns ---
            # Add the owner column determined from the parent folder name.
            df["Owner"] = owner

            # Ensure all columns defined in STANDARD_COLS exist.
            # If a standard column wasn't created through mapping (e.g., Category), add it with NA.
            output_df = pd.DataFrame() # Start fresh to ensure correct order and columns
            for col in STANDARD_COLS:
                if col in df.columns:
                    output_df[col] = df[col]
                else:
                    # Assign NA (Pandas' missing value marker) if column is missing.
                    output_df[col] = pd.NA
                    logging.debug(f"Standard column '{col}' not found for {csv_path.name}; added with NA.")

            # Append the processed DataFrame to our list.
            parts.append(output_df)
            logging.info(f"Successfully processed and standardized {csv_path.name} ({len(output_df)} rows).")

        # --- Handle File-Specific Errors ---
        except pd.errors.EmptyDataError:
            # Skip files that are completely empty.
            logging.warning(f"Skipping empty CSV file: {csv_path.name}")
        except FileNotFoundError:
             # Should not happen within rglob, but handle just in case.
             logging.error(f"File disappeared during processing?: {csv_path}")
        except Exception as e:
            # Log any other unexpected error during the processing of a single file.
            # Use exc_info=True to include the traceback for debugging.
            logging.error(f"Failed to process file {csv_path.name}: {e}", exc_info=True)
            # Continue to the next file.

    # --- Final Combination ---
    # Check if any files were successfully processed.
    if not parts:
        logging.warning(f"No CSV files could be successfully processed under {folder}. Returning empty DataFrame.")
        # Return an empty DataFrame but with the standard columns defined.
        return pd.DataFrame(columns=STANDARD_COLS)

    # Concatenate all the processed DataFrames into a single one.
    # ignore_index=True creates a new clean index for the combined DataFrame.
    combined_df = pd.concat(parts, ignore_index=True)
    logging.info(f"Finished processing folder. Total rows ingested across {len(parts)} file(s): {len(combined_df)}")
    return combined_df

# ==============================================================================
# END OF FILE: ingest.py
# ==============================================================================
