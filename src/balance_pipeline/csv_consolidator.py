###############################################################################
# BALANCE-pyexcel – CSV Consolidator Module
#
# Description : Ingests, processes, normalizes, and consolidates financial
#                transaction data from multiple CSV file formats into a single
#                pandas DataFrame, guided by rules in schema_registry.yml.
# Key Concepts: - CSV schema mapping via YAML (schema_registry.yml)
#                - Source identification (filename/header patterns)
#                - Header normalization and column mapping
#                - Date parsing and amount sign standardization
#                - Derived column generation (e.g., Account, AccountLast4)
#                - Merchant cleaning (lookup CSV + fallback function)
#                - Deterministic transaction ID (TxnID) generation
# Public API  : - process_csv_files(csv_paths: list[str | Path], schema_registry_path: str | Path, merchant_lookup_path: str | Path) -> pd.DataFrame
#                - (Helper functions will be internal initially)
# -----------------------------------------------------------------------------
# Change Log
# Date        Author            Type        Note
# 2025-05-16  Cline (AI)        feat        Initial creation of the module.
###############################################################################

# --- Standard Python Imports ---
from __future__ import annotations  # For using type hints before full definition
import logging
import json
import re
import hashlib # Added hashlib import
from collections import Counter # Added for schema matching smoke test
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union # Corrected Union import

# --- Third-party Libraries ---
import pandas as pd
import yaml # For loading schema_registry.yml

# --- Local Application Imports ---
from .config import SCHEMA_REGISTRY_PATH, MERCHANT_LOOKUP_PATH # Default paths
# We will need _hash_txn and clean_merchant from normalize.py
# For now, let's assume they might be refactored or directly used.
# If direct use: from .normalize import _txn_id_like_function, clean_merchant
# For now, I will re-implement _hash_txn logic as per spec and use clean_merchant from normalize
from .normalize import clean_merchant as project_clean_merchant # Alias to avoid conflict
from .normalize import _ID_COLS_FOR_HASH as NORMALIZE_ID_COLS_FOR_HASH # For TxnID generation reference
from .utils import _clean_desc_single # For fallback merchant cleaning if needed directly

# --- Setup Logger ---
log = logging.getLogger(__name__)

# --- Master Schema Columns (as per task description) ---
# Columns marked with `★` are mandatory.
MASTER_SCHEMA_COLUMNS = [
    "TxnID",                # ★
    "Owner",                # ★
    "Date",                 # ★
    "PostDate",
    "Merchant",             # ★
    "OriginalDescription",
    "Category",             # ★
    "Amount",               # ★
    "Tags",
    "Institution",
    "Account",              # ★ (Marked as mandatory based on TxnID dependency and general use)
    "AccountLast4",
    "AccountType",
    "SharedFlag",
    "SplitPercent",
    "StatementStart",
    "StatementEnd",
    "StatementPeriodDesc",
    "DataSourceName",
    "DataSourceDate",
    "ReferenceNumber",
    "Note",
    "IgnoredFrom",
    "TaxDeductible",
    "CustomName",
    "Currency",
    "Extras",
]

MANDATORY_MASTER_COLS = [
    "TxnID", "Owner", "Date", "Merchant", "Category", "Amount", "Account"
]


# Placeholder for main processing function and helpers
# These will be implemented in subsequent steps.

# --- Boolean Parsing Helper ---
BOOL_TRUE = {'1', 'true', 't', 'yes', 'y'}
BOOL_FALSE = {'0', 'false', 'f', 'no', 'n', ''} # Empty string often means false

def coerce_bool(series: pd.Series) -> pd.Series:
    """
    Coerces a pandas Series to nullable boolean dtype ('boolean').
    Maps common string representations of true/false.
    Values not in BOOL_TRUE or BOOL_FALSE become pd.NA.
    """
    if series.empty:
        return pd.Series(dtype='boolean')

    # Ensure series is string type and lowercase for mapping
    # Handle cases where series might already contain non-string (e.g. actual bools, numbers)
    # If a value is already a Python bool, str(value).lower() will work ('true'/'false')
    # If a value is numeric (1/0), str(value) will work ('1'/'0')
    
    # Replace non-string NaN-like values (e.g. numpy.nan) with a placeholder that won't match TRUE/FALSE sets
    # but can be identified to be turned into pd.NA later. Using a unique string.
    # Or, better, handle them before .str.lower()
    
    def map_value_to_bool(x):
        if pd.isna(x):
            return pd.NA
        s = str(x).lower().strip()
        if s in BOOL_TRUE:
            return True
        if s in BOOL_FALSE:
            return False
        return pd.NA

    return series.apply(map_value_to_bool).astype('boolean')


def _normalize_csv_header(header: str) -> str:
    """Normalizes a CSV column header: lowercase, strip, remove special chars except space."""
    if not isinstance(header, str):
        return ""
    # Convert to lowercase
    normalized = header.lower()
    # Remove special characters except spaces, then strip leading/trailing whitespace
    normalized = re.sub(r'[^a-z0-9\s]', '', normalized).strip()
    # Replace multiple spaces with a single space
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized

def find_matching_schema(
    df_headers: List[str],
    filename: str,
    schema_registry: Dict[str, List[Dict[str, Any]]]
) -> Optional[Dict[str, Any]]:
    """
    Identifies the correct schema from the registry for a given CSV.
    Matches first by filename pattern, then by header signature.

    Args:
        df_headers (List[str]): List of actual (raw) column headers from the CSV.
        filename (str): The name of the CSV file.
        schema_registry (Dict[str, List[Dict[str, Any]]]): The loaded schema registry.

    Returns:
        Optional[Dict[str, Any]]: The matched schema definition, or None if no match.
    """
    normalized_df_headers = {_normalize_csv_header(h) for h in df_headers}
    file_path = Path(filename) # Use Path for robust name matching

    schemas = schema_registry.get('schemas', [])
    if not schemas:
        log.warning("Schema registry is empty or not in the expected format.")
        return None

    # Attempt 1: Match by filename pattern
    for schema in schemas:
        match_filename_pattern = schema.get('match_filename')
        if match_filename_pattern:
            if file_path.match(match_filename_pattern):
                log.info(f"Matched schema '{schema.get('id')}' by filename pattern '{match_filename_pattern}' for file '{filename}'.")
                # Further verify with header signature if present
                header_signature = schema.get('header_signature')
                if header_signature:
                    # Normalize schema's expected headers for comparison
                    normalized_schema_headers = {_normalize_csv_header(h) for h in header_signature}
                    if normalized_schema_headers.issubset(normalized_df_headers):
                        log.info(f"Header signature also matches for schema '{schema.get('id')}'.")
                        return schema
                    else:
                        log.warning(
                            f"Filename pattern matched schema '{schema.get('id')}' for '{filename}', "
                            f"but header signature did not. Expected subset: {normalized_schema_headers}, "
                            f"Got: {normalized_df_headers}. Will continue searching."
                        )
                else: # No header signature to check, filename match is enough
                    return schema
    
    log.info(f"No schema matched by filename pattern for '{filename}'. Trying header signature only.")

    # Attempt 2: Match by header signature only (if no filename match)
    # This is a fallback if filename patterns are not exhaustive or change.
    for schema in schemas:
        header_signature = schema.get('header_signature')
        if header_signature:
            # Normalize schema's expected headers for comparison
            normalized_schema_headers = {_normalize_csv_header(h) for h in header_signature}
            if normalized_schema_headers.issubset(normalized_df_headers):
                log.info(f"Matched schema '{schema.get('id')}' by header signature for file '{filename}'.")
                return schema
                
    log.warning(f"No schema found for file '{filename}' using filename or header signature.")
    return None

# --- Helper for TxnID Generation ---
# Based on normalize.py:_txn_id and task requirements
# NORMALIZE_ID_COLS_FOR_HASH = ["Date", "PostDate", "Amount", "Description", "Bank", "Account"]
# Master schema fields required for TxnID: Date, PostDate, Amount, OriginalDescription (or Merchant if OriginalDescription is not directly mapped), Account, Institution (or Bank if mapped)
# For simplicity and alignment with existing normalize.py, let's define the cols needed for hashing here.
# These are the *target* master schema column names after mapping.
# Removed PostDate and Institution as they are not reliably available across all sources.
TXN_ID_HASH_COLS = ["Date", "Amount", "OriginalDescription", "Account"]


def _generate_txn_id(row: pd.Series) -> str:
    """
    Generates a unique, deterministic transaction ID (TxnID) for a transaction row.
    Uses MD5 hash of concatenated key fields.
    """
    # Ensure all required columns for hashing are present in the row
    # Use .get(col, '') to handle potentially missing columns gracefully, defaulting to empty string
    # Convert to string and strip whitespace
    parts = []
    for col in TXN_ID_HASH_COLS:
        val = row.get(col)
        if pd.isna(val): # Handles None, pd.NaT, np.nan
            parts.append("")
        else:
            # For datetime objects (like Date, PostDate), convert to ISO format string
            if isinstance(val, (datetime, pd.Timestamp)):
                parts.append(val.isoformat()[:10]) # YYYY-MM-DD
            else:
                parts.append(str(val).strip())
    
    hash_input = "|".join(parts)
    
    # Import hashlib here if not already at module level, or ensure it is.
    # hashlib is now imported at the module level
    return hashlib.md5(hash_input.encode('utf-8')).hexdigest()[:16]


def apply_schema_transformations(
    df: pd.DataFrame,
    schema_rules: Dict[str, Any],
    merchant_lookup_rules: List[Tuple[re.Pattern, str]]
) -> pd.DataFrame:
    """
    Applies all transformations defined by a schema to a DataFrame.
    This includes column mapping, date parsing, amount signing, derived columns, etc.

    Args:
        df (pd.DataFrame): The raw DataFrame from a CSV.
        schema_rules (Dict[str, Any]): The specific schema definition to apply.
        merchant_lookup_rules (List[Tuple[re.Pattern, str]]): Loaded merchant lookup rules.

    Returns:
        pd.DataFrame: The transformed DataFrame, partially conforming to the master schema.
                      Further processing like TxnID, Owner, final merchant cleaning happens later.
    """
    log.info(f"Applying schema transformations for schema ID: '{schema_rules.get('id')}'")
    transformed_df = df.copy()

    # 1. Header Normalization (of DataFrame columns for mapping)
    # The schema's column_map keys are expected to be raw headers from the source CSV.
    # We need to map these raw headers to our internal canonical names.
    # The _normalize_csv_header function is for matching, not for renaming df columns yet.
    
    # Store original column names for 'Extras'
    original_columns = list(transformed_df.columns)
    
    # 2. Apply Column Mapping
    column_map = schema_rules.get('column_map', {})
    if not column_map:
        log.warning(f"Schema '{schema_rules.get('id')}' has no column_map. Columns will be as-is.")
        # Proceed, but 'Extras' will include all original columns if they don't match master schema.
    
    # Normalize keys in column_map for matching against normalized df headers
    # However, the task implies column_map keys are the *raw* headers.
    # "Normalize original CSV headers ... before attempting to match them with keys in column_map."
    # This means we should normalize the DataFrame's current headers first.
    
    df_normalized_header_map = {col: _normalize_csv_header(col) for col in transformed_df.columns}
    # And normalize the keys in the schema's column_map as well for robust matching
    normalized_schema_column_map = {_normalize_csv_header(k): v for k, v in column_map.items()}

    rename_dict = {}
    mapped_source_cols_normalized = set()

    for original_col_name, normalized_col_name_df in df_normalized_header_map.items():
        if normalized_col_name_df in normalized_schema_column_map:
            target_col_name = normalized_schema_column_map[normalized_col_name_df]
            rename_dict[original_col_name] = target_col_name
            mapped_source_cols_normalized.add(normalized_col_name_df)
        # If a column from schema_column_map is NOT in df_normalized_header_map, it's a config error or missing col in CSV.
        # This will be implicitly handled as the column won't be renamed.

    # Check for schema_column_map keys that weren't found in the CSV's headers
    for normalized_schema_key in normalized_schema_column_map.keys():
        if normalized_schema_key not in df_normalized_header_map.values():
            # Find the original raw key from column_map for logging
            original_raw_key_for_log = "Unknown (normalized key not found back in original map)"
            for raw_k, raw_v in column_map.items(): # schema_rules.get('column_map', {})
                if _normalize_csv_header(raw_k) == normalized_schema_key:
                    original_raw_key_for_log = raw_k
                    break
            log.warning(
                f"Column '{original_raw_key_for_log}' (normalized: '{normalized_schema_key}') defined in schema "
                f"'{schema_rules.get('id')}' column_map not found in the CSV file. It will be missing."
            )
            
    transformed_df = transformed_df.rename(columns=rename_dict)
    log.info(f"Applied column mapping. Renamed columns: {rename_dict}")

    # 3. Handle 'Extras' (unmapped columns)
    # Unmapped columns are those original columns not in rename_dict.keys()
    # Their new names (if they were part of a rename) are not relevant for 'Extras'.
    # We need columns from 'original_columns' that were NOT mapped.
    
    mapped_original_cols = set(rename_dict.keys())
    unmapped_original_cols = [col for col in original_columns if col not in mapped_original_cols]
    
    if unmapped_original_cols:
        # Create a DataFrame of just the unmapped columns
        extras_df = df[unmapped_original_cols].copy()
        # Convert each row of extras_df to a JSON string
        # Ensure NaN/NaT are handled correctly by converting to None for JSON serialization
        transformed_df['Extras'] = extras_df.apply(
            lambda row: json.dumps(row.dropna().to_dict()), axis=1
        )
        log.info(f"Collected unmapped columns into 'Extras': {unmapped_original_cols}")
    else:
        transformed_df['Extras'] = None # Or pd.NA or empty JSON string '{}'
        log.info("No unmapped columns found for 'Extras'.")

    # 4. Date Parsing
    # The schema can specify multiple date columns to parse, each with its own format string
    # For now, let's assume 'Date' and 'PostDate' are the primary ones.
    # The task mentions: "Use the date_format specified in the matched schema to parse date strings
    # from the source CSV into datetime objects for Date and PostDate."
    # This implies date_format could be a single string or a dict if multiple date cols have different formats.
    # The current schema_registry.yml shows date_format as a single string.
    
    date_columns_to_parse = {} # Stores {col_name: format_str or None}
    schema_date_format = schema_rules.get('date_format')

    # Identify which of the mapped columns are potential date columns
    # Common date columns are 'Date', 'PostDate'.
    # The column_map would have mapped source columns to these canonical names.
    potential_date_cols_in_df = [col for col in ['Date', 'PostDate'] if col in transformed_df.columns]

    for date_col_name in potential_date_cols_in_df:
        # If a global date_format is provided in the schema, use it.
        # Otherwise, pandas will attempt to infer.
        date_columns_to_parse[date_col_name] = schema_date_format

    for col_name, fmt_str in date_columns_to_parse.items():
        if col_name in transformed_df.columns:
            try:
                # Ensure the column is string type before parsing, if it's not already datetime
                if not pd.api.types.is_datetime64_any_dtype(transformed_df[col_name]):
                    transformed_df[col_name] = pd.to_datetime(
                        transformed_df[col_name], format=fmt_str, errors='coerce'
                    )
                    log.info(f"Parsed date column '{col_name}' using format '{fmt_str if fmt_str else 'inferred'}'.")
                else:
                    log.info(f"Column '{col_name}' is already datetime type. Skipping parsing.")
            except Exception as e:
                log.warning(f"Could not parse date column '{col_name}' with format '{fmt_str}': {e}. Column left as is or NaT.")
                # If errors='coerce', unparseable dates become NaT (Not a Time)
        else:
            log.warning(f"Date column '{col_name}' specified for parsing not found in DataFrame after mapping.")

    # 5. Amount Sign Standardization & Numeric Conversion
    amount_col_name = 'Amount' # Assuming 'Amount' is the canonical name after mapping
    if amount_col_name in transformed_df.columns:
        # Apply amount_regex if present
        amount_regex_str = schema_rules.get('amount_regex')
        if amount_regex_str:
            try:
                # Extract the numeric part using regex. Expects one capturing group.
                # Ensure it handles cases where the column might already be numeric or partly clean.
                transformed_df[amount_col_name] = transformed_df[amount_col_name].astype(str).str.extract(f'({amount_regex_str})', expand=False)
                log.info(f"Applied amount_regex '{amount_regex_str}' to column '{amount_col_name}'.")
            except Exception as e:
                log.error(f"Error applying amount_regex to '{amount_col_name}': {e}. Amount column may be incorrect.")
        
        # Convert to numeric, coercing errors to NaN
        transformed_df[amount_col_name] = pd.to_numeric(transformed_df[amount_col_name], errors='coerce')

        sign_rule = schema_rules.get('sign_rule')
        if sign_rule == 'flip_if_positive':
            transformed_df[amount_col_name] = transformed_df[amount_col_name].apply(
                lambda x: -abs(x) if pd.notna(x) and x > 0 else x
            )
            log.info(f"Applied sign_rule 'flip_if_positive' to '{amount_col_name}'.")
        elif sign_rule == 'flip_if_negative': # Not explicitly in task, but good to have
             transformed_df[amount_col_name] = transformed_df[amount_col_name].apply(
                lambda x: abs(x) if pd.notna(x) and x < 0 else x
            )
             log.info(f"Applied sign_rule 'flip_if_negative' to '{amount_col_name}'.")
        elif sign_rule == 'flip_always':
            transformed_df[amount_col_name] = -transformed_df[amount_col_name]
            log.info(f"Applied sign_rule 'flip_always' to '{amount_col_name}'.")
        elif sign_rule == 'flip_if_withdrawal':
            # Specific rule for chase_total_checking
            if 'Category' in transformed_df.columns:
                withdrawal_categories = ['withdrawal', 'payment']
                # Apply to rows where Category matches and Amount is positive
                mask = (
                    transformed_df['Category'].astype(str).str.lower().isin(withdrawal_categories) &
                    (transformed_df[amount_col_name] > 0) &
                    pd.notna(transformed_df[amount_col_name])
                )
                transformed_df.loc[mask, amount_col_name] = -transformed_df.loc[mask, amount_col_name]
                log.info(f"Applied sign_rule 'flip_if_withdrawal' to '{amount_col_name}' based on 'Category'.")
            else:
                log.warning("Sign_rule 'flip_if_withdrawal' specified, but 'Category' column not found. Rule not applied.")
        elif sign_rule == 'as_is':
            log.info(f"Sign_rule for '{amount_col_name}' is 'as_is'. No changes to sign.")
        elif isinstance(sign_rule, dict) and sign_rule.get('type') == 'flip_if_column_value_matches':
            rule_col_name = sign_rule.get('column')
            debit_values = [str(v).lower() for v in sign_rule.get('debit_values', [])] # Normalize to lower string

            actual_col_to_check = None
            if rule_col_name in transformed_df.columns:
                actual_col_to_check = rule_col_name
            else:
                # Try normalized version if original rule_col_name not found (e.g. schema used raw name, df has normalized)
                normalized_rule_col_name = _normalize_csv_header(rule_col_name)
                # Check against normalized df headers that might exist if not mapped
                # This is tricky because df columns are already mapped ones or original unmapped.
                # The rule should ideally refer to a column name present in transformed_df at this stage.
                # Let's assume rule_col_name refers to a column name that *should* exist in transformed_df.
                # If it was mapped, it's the target name. If it's an original unmapped name, it's that.
                # The most robust is to check existence directly.
                log.warning(f"Column '{rule_col_name}' for complex sign rule not directly found. This rule might not apply correctly.")


            if actual_col_to_check and debit_values:
                log.info(f"Applying complex sign_rule 'flip_if_column_value_matches' on column '{actual_col_to_check}' with debit_values: {debit_values}.")
                # Log unique values from the column that drives the sign_rule
                if actual_col_to_check in transformed_df.columns:
                    unique_sign_rule_values = transformed_df[actual_col_to_check].astype(str).unique().tolist()
                    log.info(f"Unique values in '{actual_col_to_check}' (for sign_rule): {unique_sign_rule_values}")
                
                def adjust_sign(row):
                    amount = row[amount_col_name]
                    type_val_series = row[actual_col_to_check]
                    
                    if pd.isna(amount) or pd.isna(type_val_series):
                        return amount # Don't change NaN amounts or if type is NaN

                    type_val = str(type_val_series).lower().strip()
                    
                    is_debit_type = type_val in debit_values
                    
                    if is_debit_type: # Should be negative
                        return -abs(amount) if amount > 0 else amount
                    else: # Should be positive (credit/inflow)
                        return abs(amount) if amount < 0 else amount
                
                transformed_df[amount_col_name] = transformed_df.apply(adjust_sign, axis=1)
            elif not actual_col_to_check:
                 log.warning(f"Column '{rule_col_name}' specified in complex sign_rule not found in DataFrame. Rule not applied.")
            else: # no debit_values
                 log.warning(f"No 'debit_values' provided for complex sign_rule. Rule not applied effectively.")

        elif sign_rule: # Any other non-empty sign rule not recognized (includes simple strings not caught above)
            log.warning(f"Unrecognized or improperly structured sign_rule: '{sign_rule}'. Amount signs may be incorrect.")
        
        # Ensure 'Amount' is float
        transformed_df[amount_col_name] = transformed_df[amount_col_name].astype(float, errors='ignore')

    else:
        log.warning(f"Amount column '{amount_col_name}' not found after mapping. Cannot apply sign rules or ensure numeric type.")

    # 6. Derived Columns (interpreting schema['derived_columns']) - Placeholder for now
    # This will be a complex part.
    derived_columns_rules = schema_rules.get('derived_columns', {})
    if derived_columns_rules:
        log.info(f"Applying derived_columns rules: {derived_columns_rules}")
        for target_col, rule_spec in derived_columns_rules.items():
            if not isinstance(rule_spec, dict):
                log.warning(f"Rule specification for derived column '{target_col}' is not a dictionary. Skipping.")
                continue

            rule_type = rule_spec.get('type')
            
            try:
                if rule_type == 'static_value':
                    transformed_df[target_col] = rule_spec.get('value')
                    log.info(f"Derived column '{target_col}' set with static value: {rule_spec.get('value')}")
                
                elif rule_type == 'from_column':
                    source_col = rule_spec.get('source_column')
                    if source_col and source_col in transformed_df.columns:
                        transformed_df[target_col] = transformed_df[source_col]
                        log.info(f"Derived column '{target_col}' copied from '{source_col}'.")
                    else:
                        log.warning(f"Source column '{source_col}' for derived column '{target_col}' not found. Skipping.")
                        transformed_df[target_col] = pd.NA

                elif rule_type == 'regex_extract':
                    source_col = rule_spec.get('source_column')
                    pattern = rule_spec.get('pattern')
                    group_index = rule_spec.get('group_index', 1) # Default to first capturing group
                    if source_col and source_col in transformed_df.columns and pattern:
                        # Ensure source_col is string type for regex
                        transformed_df[target_col] = transformed_df[source_col].astype(str).str.extract(
                            pat=str(pattern), expand=False, flags=re.IGNORECASE
                        ).str.get(group_index -1 if isinstance(group_index, int) and group_index > 0 else 0) # .str.get() for Series of lists/tuples if expand=True
                        # If expand=False, str.extract returns a Series. If pattern has groups, it's a Series of matches.
                        # If the pattern is just (value), then it's fine.
                        # A common use case is `(\d{4})` to get last 4. str.extract would return a Series of these.
                        # If pattern has multiple groups and expand=False, it returns a DataFrame.
                        # For simplicity, assuming pattern extracts a single value or the first group.
                        # A more robust way for single group extraction:
                        extracted_series = transformed_df[source_col].astype(str).str.extract(pat=str(pattern), expand=False)
                        if isinstance(extracted_series, pd.DataFrame) and group_index <= len(extracted_series.columns):
                             transformed_df[target_col] = extracted_series.iloc[:, group_index -1]
                        elif isinstance(extracted_series, pd.Series):
                             transformed_df[target_col] = extracted_series
                        else:
                             transformed_df[target_col] = pd.NA
                             log.warning(f"Regex extract for '{target_col}' from '{source_col}' did not yield expected Series/DataFrame or group_index is out of bounds.")

                        log.info(f"Derived column '{target_col}' from '{source_col}' using regex: '{pattern}', group: {group_index}.")
                    else:
                        log.warning(f"Missing source_column, pattern, or column not found for regex_extract for '{target_col}'. Skipping.")
                        transformed_df[target_col] = pd.NA
                
                elif rule_type == 'concatenate':
                    source_cols = rule_spec.get('source_columns', [])
                    separator = rule_spec.get('separator', ' ')
                    if source_cols and all(sc in transformed_df.columns for sc in source_cols):
                        # Ensure all source columns are string type
                        concat_series = None
                        for i, sc in enumerate(source_cols):
                            current_col_series = transformed_df[sc].astype(str)
                            if i == 0:
                                concat_series = current_col_series
                            else:
                                concat_series = concat_series + separator + current_col_series
                        transformed_df[target_col] = concat_series
                        log.info(f"Derived column '{target_col}' by concatenating {source_cols} with '{separator}'.")
                    else:
                        log.warning(f"One or more source columns for concatenate for '{target_col}' not found. Skipping. Needed: {source_cols}")
                        transformed_df[target_col] = pd.NA
                
                else:
                    log.warning(f"Unknown rule type '{rule_type}' for derived column '{target_col}'. Skipping.")
                    transformed_df[target_col] = pd.NA
            
            except Exception as e:
                log.error(f"Error applying derived column rule for '{target_col}' (type: {rule_type}): {e}", exc_info=True)
                transformed_df[target_col] = pd.NA # Ensure column exists even if derivation fails

    # 7. Specific source pre-processing (e.g., Rocket Money) - Placeholder
    # This should be minimized by making YAML expressive.
    # schema_id = schema_rules.get('id', '').lower()
    # if 'rocket_money' in schema_id:
    #    # ... Rocket Money specific logic ...

    # 8. Populate DataSourceName (from schema['id'])
    transformed_df['DataSourceName'] = schema_rules.get('id', 'UnknownSchema')
    log.info(f"Populated 'DataSourceName' with '{transformed_df['DataSourceName'].iloc[0]}'.")

    # 9. Add static columns from schema['extra_static_cols']
    extra_static_cols = schema_rules.get('extra_static_cols', {})
    if extra_static_cols:
        for col_name, static_value in extra_static_cols.items():
            transformed_df[col_name] = static_value
            log.info(f"Added static column '{col_name}' with value '{static_value}'.")
    
    # TODO: Implement remaining transformations:
    # - Complex sign_rule (e.g. based on another column's value)
    # - Specific source pre-processing (if unavoidable by YAML)

    # Verify apply_schema_transformations returns only canonical + extras
    expected_cols = set(MASTER_SCHEMA_COLUMNS) | {"Extras"}
    for col in transformed_df.columns:
        if col not in expected_cols:
            log.warning("Unexpected column survived mapping: %s", col)

    return transformed_df


def _clean_merchant_column(
    df: pd.DataFrame,
    merchant_lookup_rules: List[Tuple[re.Pattern, str]]
) -> pd.Series:
    """
    Cleans the merchant names in a DataFrame.
    Uses 'OriginalDescription' as the primary source for cleaning,
    falls back to 'Merchant' if 'OriginalDescription' is not available or empty.
    Applies regex lookup rules and then a fallback general cleaner.
    """
    # Determine the source column for merchant cleaning
    if 'OriginalDescription' in df.columns and not df['OriginalDescription'].isna().all():
        source_merchant_col = 'OriginalDescription'
    elif 'Merchant' in df.columns: # Fallback to Merchant if OriginalDescription is not good
        source_merchant_col = 'Merchant'
        log.info("Using 'Merchant' column as source for merchant cleaning as 'OriginalDescription' is unavailable/empty.")
    else:
        log.warning("Neither 'OriginalDescription' nor 'Merchant' column found for merchant cleaning. Returning empty Series.")
        return pd.Series([None] * len(df), index=df.index, dtype=str)

    def clean_single_merchant(merchant_string: Any) -> str:
        if not isinstance(merchant_string, str) or pd.isna(merchant_string):
            return "Unknown Merchant" # Default for missing/invalid input

        for pattern, canonical_name in merchant_lookup_rules:
            if pattern.search(merchant_string):
                return canonical_name
        
        # Fallback to project's general merchant cleaner
        return project_clean_merchant(merchant_string)

    return df[source_merchant_col].apply(clean_single_merchant)


def process_csv_files(
    csv_files: List[Union[str, Path]],
    schema_registry_override_path: Optional[Path] = None,
    merchant_lookup_override_path: Optional[Path] = None
) -> pd.DataFrame:
    """
    Main public function to ingest, process, and consolidate multiple CSV files.

    Args:
        csv_files (List[Union[str, Path]]): List of paths to CSV files to process.
        schema_registry_override_path (Optional[Path]): Path to schema registry YAML.
                                                        Defaults to path from config.py.
        merchant_lookup_override_path (Optional[Path]): Path to merchant lookup CSV.
                                                         Defaults to path from config.py.
    Returns:
        pd.DataFrame: A single DataFrame containing all consolidated and normalized transactions.
    """
    schema_reg_path = schema_registry_override_path or SCHEMA_REGISTRY_PATH
    merchant_lkp_path = merchant_lookup_override_path or MERCHANT_LOOKUP_PATH

    schema_registry = load_and_parse_schema_registry(schema_reg_path)
    merchant_rules = load_merchant_lookup_rules(merchant_lkp_path)

    all_processed_dfs: List[pd.DataFrame] = []
    schema_ids_found: List[str] = [] # For schema matching smoke test

    for csv_file_path_obj in [Path(p) for p in csv_files]:
        log.info(f"Processing CSV file: {csv_file_path_obj.name}")
        try:
            raw_df = pd.read_csv(csv_file_path_obj, dtype=str) # Read all as string initially
            if raw_df.empty:
                log.warning(f"CSV file {csv_file_path_obj.name} is empty. Skipping.")
                continue
        except Exception as e:
            log.error(f"Failed to read CSV {csv_file_path_obj.name}: {e}", exc_info=True)
            continue

        # Infer Owner (e.g., from subfolder name "Jordyn"/"Ryan")
        # Assumes CSVs are in a structure like .../OwnerName/file.csv
        owner = csv_file_path_obj.parent.name
        log.info(f"Inferred Owner: '{owner}' from path.")

        # DataSourceDate (file modification date)
        try:
            ds_date = datetime.fromtimestamp(csv_file_path_obj.stat().st_mtime)
        except Exception as e:
            log.warning(f"Could not get file modification date for {csv_file_path_obj.name}: {e}. Using current time.")
            ds_date = datetime.now()
        
        # Identify Schema
        # Use raw_df.columns.tolist() for header matching
        matched_schema = find_matching_schema(raw_df.columns.tolist(), csv_file_path_obj.name, schema_registry)

        if not matched_schema:
            log.error(f"No matching schema found for {csv_file_path_obj.name}. Skipping file.")
            schema_ids_found.append('None (no match)') # For smoke test
            continue
        
        schema_id_for_file = matched_schema.get('id', 'None (id missing in schema)')
        schema_ids_found.append(schema_id_for_file) # For smoke test
        log.info(f"Using schema '{schema_id_for_file}' for {csv_file_path_obj.name}.")

        # Apply schema transformations (column mapping, basic types, derived, static, etc.)
        processed_df = apply_schema_transformations(raw_df, matched_schema, merchant_rules)

        # Populate initial metadata fields
        processed_df['Owner'] = owner
        processed_df['DataSourceDate'] = ds_date

        # Merchant Cleaning (final step for Merchant column)
        # This uses the merchant_rules and the project's fallback cleaner.
        # The result should go into the 'Merchant' column of the master schema.
        # apply_schema_transformations might have mapped a column to 'Merchant' or 'OriginalDescription'.
        # _clean_merchant_column will use 'OriginalDescription' preferably.
        processed_df['Merchant'] = _clean_merchant_column(processed_df, merchant_rules)
        log.info("Applied final merchant cleaning.")

        # Log merchant blanks for the current file
        if 'Merchant' in processed_df.columns and not processed_df.empty:
            blanks = processed_df['Merchant'].isna().sum()
            percentage_blanks = (blanks / len(processed_df)) * 100 if len(processed_df) > 0 else 0
            log.info(f"🛒 Merchant blanks after clean for file {csv_file_path_obj.name}: {blanks} ({percentage_blanks:.2f}%)")
        elif processed_df.empty:
            log.info(f"🛒 Merchant blanks after clean for file {csv_file_path_obj.name}: N/A (empty DataFrame)")
        else:
            log.info(f"🛒 Merchant column not found after clean for file {csv_file_path_obj.name}, cannot count blanks.")


        # Generate TxnID
        # The _generate_txn_id function now handles potentially missing columns from TXN_ID_HASH_COLS
        # by using an empty string for hashing if a column is missing or its value is NA.
        # Thus, the explicit check for missing_hash_cols here is no longer strictly necessary
        # as long as apply_schema_transformations ensures the columns in TXN_ID_HASH_COLS exist
        # (even if all NA) or _generate_txn_id correctly uses .get().
        # The current _generate_txn_id uses .get(), so it's robust.
        processed_df['TxnID'] = processed_df.apply(_generate_txn_id, axis=1)
        log.info("Generated 'TxnID' column.")
        if processed_df['TxnID'].isnull().any(): # This check is fine, as apply might return None if input is weird
             log.warning(f"Some TxnIDs are null for {csv_file_path_obj.name} (this might be due to all hashable fields being empty/NA for a row).")


        # Populate Remaining Master Schema Fields (Defaults)
        processed_df['Currency'] = "USD"
        if 'SharedFlag' not in processed_df.columns: # Default if not set by derived or mapping
            processed_df['SharedFlag'] = None # Per spec: default to None/False
        if 'SplitPercent' not in processed_df.columns:
            processed_df['SplitPercent'] = None # Per spec: default to None

        # Ensure all master schema columns exist, fill with NA if not already present
        for col in MASTER_SCHEMA_COLUMNS:
            if col not in processed_df.columns:
                processed_df[col] = pd.NA # Use pd.NA for pandas-idiomatic null

        # Data Type Coercion for final master schema columns
        # This is a crucial step to ensure consistency.
        dtype_map = {
            "TxnID": str, "Owner": str, "Date": "datetime64[ns]", "PostDate": "datetime64[ns]",
            "Merchant": str, "OriginalDescription": str, "Category": str, "Amount": float,
            "Tags": str, "Institution": str, "Account": str, "AccountLast4": str,
            "AccountType": str, "SharedFlag": bool, "SplitPercent": float,
            "StatementStart": "datetime64[ns]", "StatementEnd": "datetime64[ns]",
            "StatementPeriodDesc": str, "DataSourceName": str, "DataSourceDate": "datetime64[ns]",
            "ReferenceNumber": str, "Note": str, "IgnoredFrom": str,
            "TaxDeductible": bool, "CustomName": str, "Currency": str, "Extras": str,
        }
        for col, dtype_str in dtype_map.items():
            if col in processed_df.columns:
                try:
                    if dtype_str == "datetime64[ns]":
                        processed_df[col] = pd.to_datetime(processed_df[col], errors='coerce')
                    elif dtype_str == bool:
                        # Handle boolean conversion carefully: map common strings to bool, others to NA
                        # Example: 'true', 'yes', '1' -> True; 'false', 'no', '0' -> False
                        # For simplicity now, direct astype might work if values are already 0/1 or True/False
                        # A more robust approach would be a custom mapping.
                        # Use the new coerce_bool helper
                        processed_df[col] = coerce_bool(processed_df[col])

                    elif dtype_str == float:
                         # Ensure any non-convertible values become NaN, then cast to float
                         processed_df[col] = pd.to_numeric(processed_df[col], errors='coerce')
                         # Explicitly cast to float64 if not already, to avoid object dtype with mixed NaNs/floats
                         if not pd.api.types.is_float_dtype(processed_df[col]):
                            processed_df[col] = processed_df[col].astype(float)

                    else: # typically str or int (though int needs similar care to float for errors)
                        if dtype_str == int: # Example for int, though not in current master schema as primary
                            processed_df[col] = pd.to_numeric(processed_df[col], errors='coerce').astype('Int64') # Nullable Int
                        else: # primarily str
                            processed_df[col] = processed_df[col].astype(str, errors='ignore').fillna(pd.NA)
                            # Replace "nan" strings that might result from .astype(str) on NaN numerics
                            processed_df.loc[processed_df[col].str.lower() == 'nan', col] = pd.NA
                except Exception as e:
                    log.warning(f"Could not coerce column '{col}' to type '{dtype_str}': {e}. Column may have mixed types or errors.")
            # If column is missing, it was already added with pd.NA

        # Final Column Selection & Ordering (with fill_value as per manual fix step)
        log.info(f"Applying reindex to MASTER_SCHEMA_COLUMNS with fill_value=pd.NA for {csv_file_path_obj.name}")
        processed_df = processed_df.reindex(columns=MASTER_SCHEMA_COLUMNS, fill_value=pd.NA)
        
        all_processed_dfs.append(processed_df)
        log.info(f"Finished processing {csv_file_path_obj.name}. {len(processed_df)} rows added.")

    if not all_processed_dfs:
        log.warning("No CSV files were processed successfully. Returning an empty DataFrame.")
        # Log schema matching smoke test results even if no DFs were processed
        log.info(f"Schema matching smoke test - Counts of schema_ids found: {Counter(schema_ids_found)}")
        return pd.DataFrame(columns=MASTER_SCHEMA_COLUMNS)

    # Log schema matching smoke test results
    log.info(f"Schema matching smoke test - Counts of schema_ids found: {Counter(schema_ids_found)}")

    final_df = pd.concat(all_processed_dfs, ignore_index=True)
    log.info(f"Successfully consolidated {len(all_processed_dfs)} CSV files into a single DataFrame with {len(final_df)} total rows.")
    
    # Log total merchant blanks in final_df
    if not final_df.empty and 'Merchant' in final_df.columns:
        total_merchant_blanks = final_df['Merchant'].isna().sum()
        total_percentage_blanks = (total_merchant_blanks / len(final_df)) * 100 if len(final_df) > 0 else 0
        log.info(f"🛒 Total merchant blanks in final_df after concatenation: {total_merchant_blanks} ({total_percentage_blanks:.2f}%)")
    elif final_df.empty:
        log.info("🛒 Total merchant blanks in final_df: N/A (final DataFrame is empty)")
    else:
        log.info("🛒 Merchant column not found in final_df, cannot count total blanks.")

    # Final sort by Date (and perhaps Owner/Account for stability)
    final_df = final_df.sort_values(by=['Date', 'Owner', 'Amount'], ascending=[True, True, True], na_position='first')
    
    return final_df


def load_and_parse_schema_registry(yaml_path: Path) -> dict:
    """Loads and parses the schema_registry.yml file."""
    log.info(f"Loading schema registry from: {yaml_path}")
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            registry = yaml.safe_load(f)
        if not isinstance(registry, list): # Expecting a list of schema dicts
            log.error(f"Schema registry at {yaml_path} is not a list. Found type: {type(registry)}")
            raise ValueError("Schema registry must be a list of schema definitions.")
        log.info(f"Successfully loaded {len(registry)} schema definitions.")
        return {'schemas': registry} # Wrap in a dict for easier access if needed
    except FileNotFoundError:
        log.error(f"Schema registry file not found: {yaml_path}")
        raise
    except yaml.YAMLError as e:
        log.error(f"Error parsing YAML from {yaml_path}: {e}")
        raise
    except Exception as e:
        log.error(f"An unexpected error occurred while loading schema registry {yaml_path}: {e}")
        raise

def load_merchant_lookup_rules(csv_path: Path) -> List[Tuple[re.Pattern, str]]:
    """
    Loads merchant cleaning rules from the merchant_lookup.csv file.
    Similar to _load_merchant_lookup in normalize.py but adapted for this module.
    """
    log.info(f"Loading merchant lookup rules from: {csv_path}")
    rules: List[Tuple[re.Pattern, str]] = []
    try:
        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = pd.read_csv(f) # Using pandas to read CSV for simplicity here
            if list(reader.columns) != ['pattern', 'canonical']:
                err_msg = (
                    f"Invalid header in {csv_path}. "
                    f"Expected ['pattern', 'canonical'], got {list(reader.columns)}"
                )
                log.error(err_msg)
                raise ValueError(err_msg)

            for index, row in reader.iterrows():
                pattern_str, canonical_name = row['pattern'], row['canonical']
                if not isinstance(pattern_str, str) or not isinstance(canonical_name, str):
                    log.warning(f"Skipping row {index + 2} in {csv_path} due to invalid data types: {row.to_dict()}")
                    continue
                try:
                    compiled_regex = re.compile(pattern_str, re.IGNORECASE)
                    rules.append((compiled_regex, canonical_name))
                except re.error as e:
                    err_msg = (
                        f"Invalid regex pattern in {csv_path} at row {index + 2}: "
                        f"'{pattern_str}'. Error: {e}"
                    )
                    log.error(err_msg)
                    raise ValueError(err_msg) from e
        log.info(f"Successfully loaded and compiled {len(rules)} merchant lookup rules from {csv_path}.")
    except FileNotFoundError:
        log.error(f"Merchant lookup file not found: {csv_path}. Proceeding without custom merchant rules.")
        # Return empty list, merchant cleaning will rely on fallback.
    except ValueError as e: # Catch ValueErrors from header/regex checks
        log.error(f"ValueError during merchant lookup loading: {e}")
        raise
    except Exception as e:
        log.error(f"Unexpected error loading merchant lookup {csv_path}: {e}", exc_info=True)
        # Fallback to empty list on other errors
    return rules


if __name__ == '__main__':
    # This section can be used for basic testing of the module if run directly.
    # For example, to test loading configurations.
    logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s')
    log.info("CSV Consolidator module direct execution (for testing).")

    try:
        registry_data = load_and_parse_schema_registry(SCHEMA_REGISTRY_PATH)
        # log.info(f"Loaded schema registry: {json.dumps(registry_data, indent=2)}")
    except Exception as e:
        log.error(f"Failed to load schema registry during test: {e}")

    try:
        merchant_rules = load_merchant_lookup_rules(MERCHANT_LOOKUP_PATH)
        # log.info(f"Loaded {len(merchant_rules)} merchant rules.")
    except Exception as e:
        log.error(f"Failed to load merchant rules during test: {e}")

    log.info("CSV Consolidator module test execution finished.")
