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
from typing import Any # Added for F821
import pandas as pd
import yaml
import re
import logging
from balance_pipeline.errors import RecoverableFileError, FatalSchemaError
from balance_pipeline.schema_registry import load_registry, find_matching_schema
from .sign_rules import flip_if_positive, flip_if_withdrawal

# Local application imports
from . import config # Import config module to access constants

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
# Added PostDate for TxnID hashing
STANDARD_COLS = ["Owner", "Date", "PostDate", "Description", "Amount", "Account", "AccountLast4", "AccountType", "Category", "Bank", "Source"]

# --- Load Schema Registry from YAML ---
# The schema registry defines the rules for processing each different CSV format.
# It's loaded once when this module is imported using the path from config.
_SCHEMA_REGISTRY_PATH = config.SCHEMA_REGISTRY_PATH # Use path from config
_SCHEMAS: list[dict] = [] # Initialize as empty list

try:
    _SCHEMAS = load_registry(_SCHEMA_REGISTRY_PATH)
    logging.info(f"Successfully loaded {_SCHEMA_REGISTRY_PATH} containing {len(_SCHEMAS)} schema(s).")
except FileNotFoundError as e:
    raise FatalSchemaError(f"Schema registry file not found at '{_SCHEMA_REGISTRY_PATH}'") from e
except yaml.YAMLError as e:
    raise FatalSchemaError(f"Failed to parse schema registry YAML file '{_SCHEMA_REGISTRY_PATH}': {e}") from e
except Exception as e:
    raise FatalSchemaError(f"An unexpected error occurred loading schema registry '{_SCHEMA_REGISTRY_PATH}': {e}") from e


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
        raise FatalSchemaError("Schema registry is empty or failed to load. Cannot match schema.")

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
                logging.info("Applied 'flip_if_withdrawal' sign rule using 'Category' column.")
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
def _derive_columns(df: pd.DataFrame, derived_cfg: dict | None) -> pd.DataFrame:
    """
    Derives new columns based on rules defined in the schema's 'derived_columns' section.
    Supports 'static_value' and 'regex_extract' rule types.

    Args:
        df (pd.DataFrame): The DataFrame for the current CSV (after mapping).
        derived_cfg (dict | None): The 'derived_columns' dictionary from the schema.
                                   Example:
                                   {
                                       'NewColName1': {'static_value': 'SomeValue'},
                                       'NewColName2': {
                                           'regex_extract': {
                                               'column': 'SourceColumn',
                                               'pattern': '(?P<capture_group_name>...)'
                                           }
                                       }
                                   }

    Returns:
        pd.DataFrame: The DataFrame with new derived columns added.
    """
    if derived_cfg is None:
        return df

    logging.info(f"Applying derived_columns rules: {derived_cfg}")

    for new_col_name, rule_cfg in derived_cfg.items(): # Renamed rule_config to rule_cfg for clarity
        if not isinstance(rule_cfg, dict):
            logging.warning(f"Skipping invalid derived_column config for '{new_col_name}': Expected a dictionary, got {type(rule_cfg)}. Config: {rule_cfg}")
            df[new_col_name] = pd.NA
            continue

        # 1️⃣ New Shape-A path (e.g., rule: regex_extract, column: ..., pattern: ...)
        rule_type = rule_cfg.get("rule")
        rule_details = rule_cfg # For Shape A, rule_cfg itself contains all details

        # 2️⃣ Back-compat path (old nested keys like regex_extract: {...} or static_value: "value")
        if rule_type is None:
            if "regex_extract" in rule_cfg:
                rule_type = "regex_extract"
                rule_details = rule_cfg["regex_extract"]
            elif "static_value" in rule_cfg: # This was the old way for static_value
                rule_type = "static_value"
                # For old static_value, rule_details was the value itself, not a dict.
                # The new logic below expects rule_details to be a dict for static_value if it's from Shape A.
                # So, we need to handle this carefully.
                # If old style, rule_details becomes the value. If new style, rule_details is the dict.
                rule_details = rule_cfg["static_value"]
            
        if rule_type is None:
            logging.warning(f"Unknown rule type for derived column '{new_col_name}'. Rule config: {rule_cfg}. Skipping.")
            df[new_col_name] = pd.NA
            continue
        
        try:
            if rule_type == "static_value":
                # For Shape A: rule_details is a dict like {'rule': 'static_value', 'value': 'ActualValue'}
                # For old Shape B: rule_details is the 'ActualValue' itself.
                if isinstance(rule_details, dict): # Shape A
                    static_val = rule_details.get("value")
                else:  # Old Shape B
                    static_val = rule_details
                
                if static_val is None:
                    logging.warning(f"Skipping static_value for '{new_col_name}': 'value' not found or is None. Details: {rule_details}")
                    df[new_col_name] = pd.NA
                    continue
                df[new_col_name] = static_val
                logging.info(f"Derived column '{new_col_name}' with static value: '{static_val}'")

            elif rule_type == "regex_extract":
                # For Shape A: rule_details is a dict like {'rule': 'regex_extract', 'column': 'X', 'pattern': 'Y'}
                # For old Shape B: rule_details is a dict like {'column': 'X', 'pattern': 'Y'}
                # The structure of rule_details is the same (a dict with 'column' and 'pattern') for both.
                if not isinstance(rule_details, dict):
                    logging.warning(f"Skipping regex_extract for '{new_col_name}': rule details not a dict. Details: {rule_details}")
                    df[new_col_name] = pd.NA
                    continue

                source_col = rule_details.get("column")
                pattern_str = rule_details.get("pattern")
                
                if not source_col or not pattern_str:
                    logging.warning(f"Skipping regex_extract for '{new_col_name}': missing 'column' or 'pattern' in details. Details: {rule_details}")
                    df[new_col_name] = pd.NA
                    continue
                
                if source_col not in df.columns:
                    logging.warning(f"Skipping regex_extract for '{new_col_name}': source column '{source_col}' not found in DataFrame.")
                    df[new_col_name] = pd.NA
                    continue

                regex = re.compile(pattern_str)
                capture_group_name = list(regex.groupindex.keys())[0] if regex.groupindex else None

                def extract_with_regex(text_to_search: str) -> Any:
                    if pd.isna(text_to_search):
                        return pd.NA
                    match = regex.search(str(text_to_search))
                    if match:
                        if capture_group_name and capture_group_name in match.groupdict():
                            return match.group(capture_group_name)
                        elif match.groups():
                            return match.group(1)
                    return pd.NA

                df[new_col_name] = df[source_col].apply(extract_with_regex)
                logging.info(f"Derived column '{new_col_name}' from '{source_col}' using regex: '{pattern_str}' (capture group: '{capture_group_name or '1st unnamed'}')")
            
            else:  # Handles any other string in rule_type that isn't 'static_value' or 'regex_extract'
                logging.warning(f"Unknown rule type '{rule_type}' specified for derived column '{new_col_name}'. Config: {rule_cfg}. Skipping.")
                df[new_col_name] = pd.NA

        except Exception as e:
            logging.error(f"Error deriving column '{new_col_name}' with rule_type '{rule_type}': {e}", exc_info=True)
            df[new_col_name] = pd.NA

    return df

# ==============================================================================
# 3. PUBLIC API FUNCTION
# ==============================================================================

# ------------------------------------------------------------------------------
# Function: load_folder
# ------------------------------------------------------------------------------
def load_folder(
    folder: Path, 
    *_, 
    exclude_patterns: list[str] | None = None, 
    only_patterns: list[str] | None = None, 
    **kwargs
) -> pd.DataFrame:
    """
    Loads, processes, and combines all valid CSV transaction files found
    recursively within the specified base folder. It expects subdirectories
    named after the owner (e.g., /Jordyn/, /Ryan/).

    Processing Logic:
    1. Walks subdirectories using rglob('*.csv'), applying exclude/only patterns.
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
        exclude_patterns (list[str] | None): Optional list of glob patterns to exclude.
                                             Paths are relative to the `folder`.
        only_patterns (list[str] | None): Optional list of glob patterns to exclusively include.
                                          Paths are relative to the `folder`.

    Returns:
        pd.DataFrame: A single, combined DataFrame containing standardized data
                      from all processed files, matching STANDARD_COLS. Returns an
                      empty DataFrame with STANDARD_COLS if no files are processed.

    Raises:
        FileNotFoundError: If the specified `folder` does not exist or is not a directory.
        ValueError: If the schema registry (_SCHEMAS) failed to load.
    """
    # --- Initial Checks ---
    kwargs.pop("owner_hint", None)   # Gracefully ignore legacy owner_hint
    exclude_patterns = exclude_patterns or []
    only_patterns = only_patterns or []

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
    all_csv_files = list(folder.rglob("*.csv"))
    logging.info(f"Found {len(all_csv_files)} CSV files initially in {folder} and its subdirectories.")

    # Apply filtering based on exclude and only patterns
    files_to_process = []
    for csv_path in all_csv_files:
        # Path relative to the input folder for matching patterns
        relative_path_str = str(csv_path.relative_to(folder)).replace("\\", "/") # Normalize to forward slashes

        # Check exclusion patterns
        excluded = False
        for pattern in exclude_patterns:
            if csv_path.match(pattern) or Path(relative_path_str).match(pattern):
                logging.debug(f"Excluding '{csv_path.name}' due to exclude pattern: '{pattern}'")
                excluded = True
                break
        if excluded:
            continue

        # Check inclusion patterns (if any are specified)
        if only_patterns:
            included = False
            for pattern in only_patterns:
                if csv_path.match(pattern) or Path(relative_path_str).match(pattern):
                    included = True
                    break
            if not included:
                logging.debug(f"Skipping '{csv_path.name}' as it does not match any 'only' patterns: {only_patterns}")
                continue
        
        files_to_process.append(csv_path)

    logging.info(f"Processing {len(files_to_process)} CSV files after applying exclude/only filters.")

    for csv_path in files_to_process:
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
            df = _derive_columns(df, derived_cfg) # Pass derived_cfg directly, new function handles None

            # Handle extras_ignore: remove specified columns if they exist
            extras_to_ignore = schema.get("extras_ignore", [])
            # logging.critical(f"<<<<< EXTRAS_IGNORE in INGEST.PY: Schema ID {schema_id}, extras_to_ignore: {extras_to_ignore} >>>>>") # Removed critical log
            if extras_to_ignore:
                cols_to_drop_from_df = [col for col in extras_to_ignore if col in df.columns]
                if cols_to_drop_from_df:
                    df = df.drop(columns=cols_to_drop_from_df)
                    logging.info(f"Dropped columns from DataFrame based on 'extras_ignore': {cols_to_drop_from_df} for schema '{schema_id}'")
            
            # Check if essential columns exist AFTER mapping/derivation.
            essential_cols = ["Date", "Description", "Amount"]
            missing_essentials = [col for col in essential_cols if col not in df.columns]
            if missing_essentials:
                logging.error(f"Essential columns {missing_essentials} missing after mapping/derivation for {csv_path.name} (Schema: {schema_id}). Skipping file.")
                continue

            # Normalize core data types (errors='coerce' turns failures into NaT/NaN).
            date_format = schema.get("date_format") # Get format from schema if specified

            # REMOVED: Redundant jordyn_pdf specific date handling block.

            # --- Date Parsing ---
            # Use the date_format specified in the schema, handle MM/DD case, or fall back to pandas default inference.
            if date_format:
                # Use specified format from schema
                logging.debug(f"Using specified date format '{date_format}' for schema '{schema_id}'.")
                df["Date"] = pd.to_datetime(df["Date"], format=date_format, errors='coerce')
            elif schema_id == 'jordyn_pdf_document':
                 # Handle MM/DD format specifically for these files if no format is in YAML
                 logging.debug(f"Applying explicit '%m/%d' date parsing for schema '{schema_id}'. Year will be inferred by pandas (likely current year).")
                 # Pandas often infers the current year when format doesn't include year.
                 # This might need refinement if statements span year boundaries or are from past years.
                 df["Date"] = pd.to_datetime(df["Date"], format='%m/%d', errors='coerce')
            else:
                # Fallback to default inference (month-first) for other schemas if no format specified
                logging.debug(f"No date format specified for schema '{schema_id}'. Using pandas default inference (month-first).")
                df["Date"] = pd.to_datetime(df["Date"], errors='coerce', dayfirst=False) # Explicitly month-first default

            # --- Amount Parsing ---
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
        except FileNotFoundError as e:
            raise RecoverableFileError(f"File disappeared during processing: {csv_path}") from e
        except Exception as e:
            raise RecoverableFileError(f"Failed to process file {csv_path.name}: {e}") from e

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
