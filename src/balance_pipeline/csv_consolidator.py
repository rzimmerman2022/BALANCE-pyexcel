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
# 2025-05-28  Cline (AI)        feat        Map common header aliases in _normalize_csv_header.
# 2025-05-16  Cline (AI)        feat        Initial creation of the module.
###############################################################################

# --- Standard Python Imports ---
from __future__ import annotations  # For using type hints before full definition
import logging
import json
import re
import hashlib  # Added hashlib import
import numpy as np # Added for sharing_status derivation
from collections import Counter  # Added for schema matching smoke test
from datetime import datetime
from pathlib import Path
import traceback # For more detailed error logging if needed
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Set, # Added Set import
    Tuple,
    Union,
    cast,
)

# --- Third-party Libraries ---
import pandas as pd
from pandas import BooleanDtype  # For explicit nullable boolean type
from pandas.api.types import is_numeric_dtype
import yaml  # For loading schema_registry.yml

# --- Local Application Imports ---
from .config import SCHEMA_REGISTRY_PATH, MERCHANT_LOOKUP_PATH  # Default paths
from .constants import MASTER_SCHEMA_COLUMNS  # Added import

# We will need _hash_txn and clean_merchant from normalize.py
# For now, let's assume they might be refactored or directly used.
# If direct use: from .normalize import _txn_id_like_function, clean_merchant
# For now, I will re-implement _hash_txn logic as per spec and use clean_merchant from normalize
from balance_pipeline.transaction_cleaner import apply_comprehensive_cleaning
from balance_pipeline.schema_registry import find_matching_schema as _find_schema
from .errors import RecoverableFileError
from balance_pipeline.foundation import CORE_FOUNDATION_COLUMNS # Added import

# Add these helper functions near the top of csv_consolidator.py, after imports

# Import the new configuration values
from . import config # Changed to import config module

# Verify consistency between foundation and config for core columns
assert CORE_FOUNDATION_COLUMNS == config.CORE_REQUIRED_COLUMNS, \
    "CORE_FOUNDATION_COLUMNS from foundation.py does not match config.CORE_REQUIRED_COLUMNS. Please reconcile."

def get_required_columns_for_mode() -> List[str]:
    """
    Returns the list of columns that must be present based on the current schema mode.
    
    In 'strict' mode: Returns all 25 columns from MASTER_SCHEMA_COLUMNS
    In 'flexible' mode: Returns only the core required columns
    """
    if config.SCHEMA_MODE == "strict":
        return MASTER_SCHEMA_COLUMNS
    else:
        return config.CORE_REQUIRED_COLUMNS


def identify_relevant_column_groups(df: pd.DataFrame) -> Set[str]:
    """
    Analyzes a DataFrame to determine which optional column groups are relevant
    based on the presence of data in those columns.
    
    This function helps us understand what type of data source we're dealing with
    by looking at which optional columns actually contain data.
    
    Returns:
        Set of column group names that should be retained
    """
    relevant_groups = set()
    
    for group_name, columns in config.OPTIONAL_COLUMN_GROUPS.items():
        # Check if any column in this group exists and has non-null data
        for col in columns:
            if col in df.columns and not df[col].isna().all():
                relevant_groups.add(group_name)
                break  # One non-empty column is enough to include the group
                
    return relevant_groups


def get_columns_to_retain(df: pd.DataFrame) -> List[str]:
    """
    Determines which columns should be retained in the final output based on:
    1. The current schema mode
    2. Which columns actually contain data
    
    In 'strict' mode: Returns all MASTER_SCHEMA_COLUMNS
    In 'flexible' mode: Returns core columns + relevant optional columns
    """
    if config.SCHEMA_MODE == "strict":
        return MASTER_SCHEMA_COLUMNS
    
    # Start with core required columns
    columns_to_retain = config.CORE_REQUIRED_COLUMNS.copy()
    
    # Add columns from relevant groups
    relevant_groups = identify_relevant_column_groups(df)
    for group_name in relevant_groups:
        columns_to_retain.extend(config.OPTIONAL_COLUMN_GROUPS[group_name])
    
    # Remove duplicates while preserving order - Fixed the set.add issue
    seen: Set[str] = set()
    unique_columns: List[str] = []
    for col in columns_to_retain:
        if col not in seen:
            seen.add(col)
            unique_columns.append(col)
    return unique_columns


def remove_empty_columns(df: pd.DataFrame, preserve_columns: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Removes columns that are entirely empty (all NA/null/empty string) from a DataFrame.
    
    Args:
        df: The DataFrame to clean
        preserve_columns: List of column names that should never be removed,
                         even if empty (defaults to CORE_REQUIRED_COLUMNS)
    
    Returns:
        DataFrame with empty columns removed (except preserved ones)
    """
    if preserve_columns is None:
        preserve_columns = config.CORE_REQUIRED_COLUMNS
    
    columns_to_drop = []
    
    for col in df.columns:
        # Skip if this is a preserved column
        if col in preserve_columns:
            continue
            
        # Check if column is entirely empty
        # Consider a column empty if all values are NA, None, or empty string
        if col in df.columns:
            is_all_na = df[col].isna().all()
            is_all_empty_string = (df[col] == '').all()
            is_all_none = df[col].isnull().all()
            
            if is_all_na or is_all_empty_string or is_all_none:
                columns_to_drop.append(col)
    
    if columns_to_drop:
        log.info(f"Removing {len(columns_to_drop)} empty columns in flexible mode: {columns_to_drop}")
        return df.drop(columns=columns_to_drop)
    
    return df

# --- Setup Logger ---
log = logging.getLogger(__name__)

# MANDATORY_MASTER_COLS was defined here, but MASTER_SCHEMA_COLUMNS is now imported.
# If MANDATORY_MASTER_COLS is still needed, it should be defined based on the imported MASTER_SCHEMA_COLUMNS or also moved to constants.py
# For now, assuming it might be implicitly handled or defined elsewhere if still used.
# Based on the prompt, only MASTER_SCHEMA_COLUMNS is the focus.
MANDATORY_MASTER_COLS = [
    "TxnID",
    "Owner",
    "Date",
    "Merchant",
    "Category",
    "Amount",
    "Account",
]

# --- PipelineDebugTracer Class ---
class PipelineDebugTracer:
    def __init__(self, filename: str):
        self.filename = filename
        self.stages: List[Dict[str, Any]] = []
        log.debug(f"[DebugTracer] Initialized for file: {self.filename}")

    def capture_stage(self, 
                      stage_name: str, 
                      df: pd.DataFrame, 
                      sample_rows: int = 3, 
                      focus_columns: Optional[List[str]] = None) -> None:
        """Capture the state of data at a specific stage"""
        if df is None:
            log.warning(f"[DebugTracer] DataFrame is None for stage: {stage_name}. Skipping capture.")
            stage_data: Dict[str, Any] = {
                'stage_name': stage_name,
                'status': 'DataFrame was None',
                'row_count': 0,
                'columns': [],
                'dtypes': {},
                'null_counts': {},
                'sample_data': {}
            }
            self.stages.append(stage_data)
            return

        log.debug(f"[DebugTracer] Capturing stage: {stage_name} for {self.filename}")
        try:
            stage_data = {
                'stage_name': stage_name,
                'row_count': len(df),
                'columns': list(df.columns),
                'dtypes': {col: str(df[col].dtype) for col in df.columns if col in df}, # Check col in df for safety
                'null_counts': df.isnull().sum().to_dict() if not df.empty else {},
                'sample_data': {}
            }
            
            # Capture sample data for key columns or all if not specified
            # If focus_columns is empty list, sample nothing. If None, sample first 10.
            cols_to_sample = []
            if focus_columns is None: # Sample first 10 if no focus specified
                 cols_to_sample = [col for col in df.columns[:10] if col in df]
            elif focus_columns: # If focus_columns is not empty list
                 cols_to_sample = [col for col in focus_columns if col in df]
            # If focus_columns is an empty list, cols_to_sample remains empty, no samples taken.


            for col in cols_to_sample:
                # Ensure column exists before trying to access it
                if col in df.columns:
                    # Convert to list, handling potential errors if values are unusual
                    try:
                        sample_list = df[col].head(sample_rows).tolist()
                        # Sanitize for JSON serializability if needed, e.g. NaT
                        sanitized_sample_list: List[Union[str, None]] = []
                        for item in sample_list:
                            if pd.isna(item):
                                sanitized_sample_list.append(None)  # Represent NaN/NaT as None
                            elif isinstance(item, (datetime, pd.Timestamp)):
                                sanitized_sample_list.append(item.isoformat())
                            else:
                                sanitized_sample_list.append(str(item))  # Convert to string
                        stage_data['sample_data'][col] = sanitized_sample_list
                    except Exception as e:
                        stage_data['sample_data'][col] = f"Error sampling column {col}: {e}"
                else:
                    stage_data['sample_data'][col] = "Column not found in DataFrame"
            
            self.stages.append(stage_data)
        except Exception as e:
            log.error(f"[DebugTracer] Error during capture_stage '{stage_name}': {e}\n{traceback.format_exc()}")
            # Add a placeholder stage indicating error
            self.stages.append({
                'stage_name': stage_name,
                'status': f'Error during capture: {e}',
                'error_trace': traceback.format_exc()
            })


    def generate_report(self) -> str:
        """Generate a comprehensive debug report as a string"""
        report_parts = [f"=== PIPELINE DEBUG REPORT for {self.filename} ==="]
        for stage in self.stages:
            report_parts.append(f"\n--- STAGE: {stage.get('stage_name', 'Unknown Stage')} ---")
            if 'status' in stage and 'Error' in stage['status']: # Handle error stages
                report_parts.append(f"  Status: {stage['status']}")
                if 'error_trace' in stage:
                    report_parts.append(f"  Trace: {stage['error_trace']}")
                continue

            report_parts.append(f"  Row Count: {stage.get('row_count', 'N/A')}")
            report_parts.append(f"  Columns: {stage.get('columns', 'N/A')}")
            # report_parts.append(f"  dtypes: {stage.get('dtypes', 'N/A')}") # Can be very verbose
            report_parts.append(f"  Null Counts: {json.dumps(stage.get('null_counts', {}), indent=2)}")
            
            sample_data = stage.get('sample_data', {})
            if sample_data:
                report_parts.append("  Sample Data (first few rows):")
                for col, values in sample_data.items():
                    report_parts.append(f"    {col}: {values}")
            else:
                report_parts.append("  Sample Data: None captured or specified.")
        
        return "\n".join(report_parts)

    def save_report(self, output_dir: Path = Path("debug_reports")) -> None:
        """Save the debug report to a file"""
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            # Sanitize filename from self.filename to avoid issues with special characters
            safe_report_filename_base = re.sub(r'[^\w\.-]', '_', Path(self.filename).stem)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_filename = f"debug_{safe_report_filename_base}_{timestamp}.txt"
            filepath = output_dir / report_filename
            
            report_content = self.generate_report()
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            log.info(f"[DebugTracer] Debug report saved to: {filepath}")
        except Exception as e:
            log.error(f"[DebugTracer] Failed to save debug report for {self.filename}: {e}\n{traceback.format_exc()}")

# Placeholder for main processing function and helpers
# These will be implemented in subsequent steps.

# --- Boolean Parsing Helper ---
BOOL_TRUE = {"1", "true", "t", "yes", "y"}
BOOL_FALSE = {"0", "false", "f", "no", "n", ""}  # Empty string often means false


def coerce_bool(
    series: pd.Series[Any],
) -> pd.Series[BooleanDtype]:  # Updated type hints
    """
    Coerces a pandas Series to nullable boolean dtype ('boolean').
    Maps common string representations of true/false.
    Values not in BOOL_TRUE or BOOL_FALSE become pd.NA.
    """
    if series.empty:
        return pd.Series(
            dtype="boolean"
        )  # This creates a Series of object dtype with pd.BooleanDtype() objects if not careful

    # Ensure series is string type and lowercase for mapping
    # Handle cases where series might already contain non-string (e.g. actual bools, numbers)
    # If a value is already a Python bool, str(value).lower() will work ('true'/'false')
    # If a value is numeric (1/0), str(value) will work ('1'/'0')

    # Replace non-string NaN-like values (e.g. numpy.nan) with a placeholder that won't match TRUE/FALSE sets
    # but can be identified to be turned into pd.NA later. Using a unique string.
    # Or, better, handle them before .str.lower()

    def map_value_to_bool(
        x: Any,
    ) -> Optional[bool]:  # x is str after .astype(str) in caller
        if pd.isna(x):
            return None  # Mypy prefers None for pd.NA in some contexts with bool
        s = str(x).lower().strip()
        if s in BOOL_TRUE:
            return True
        if s in BOOL_FALSE:
            return False
        return None  # Changed pd.NA to None

    # Ensure the result of apply is correctly typed before astype
    # The .astype("boolean") should correctly produce a Series[BooleanDtype]
    return series.apply(map_value_to_bool).astype("boolean")  # type: ignore[return-value] # Mypy struggles with pandas extension dtypes


def _normalize_csv_header(
    header: Any,
) -> str:  # Allow Any for robustness, will cast to str
    """Normalizes a CSV column header: lowercase, strip, remove special chars except space, and applies common aliases."""
    if not isinstance(header, str):
        header = str(header)  # Attempt to convert to string if not already

    # Ensure header is treated as str for subsequent operations
    processed_header = cast(str, header) # cast is already imported
    # Convert to lowercase
    normalized = processed_header.lower()
    # Remove special characters except spaces, then strip leading/trailing whitespace
    normalized = re.sub(r"[^a-z0-9\s]", "", normalized).strip()
    # Replace multiple spaces with a single space
    normalized = re.sub(r"\s+", " ", normalized)

    # Alias mapping from main branch
    alias_map = {
        'txn date': 'date',
        'transaction date': 'date',
        'account name': 'account',
        'running balance': 'balance',
        "description": "merchant",
        "merchant": "description",
    }

    return alias_map.get(normalized, normalized)


# --- Helper for TxnID Generation ---
# Based on normalize.py:_txn_id and task requirements
# NORMALIZE_ID_COLS_FOR_HASH = ["Date", "PostDate", "Amount", "Description", "Bank", "Account"]
# Master schema fields required for TxnID: Date, PostDate, Amount, OriginalDescription (or Merchant if OriginalDescription is not directly mapped), Account, Institution (or Bank if mapped)
# For simplicity and alignment with existing normalize.py, let's define the cols needed for hashing here.
# These are the *target* master schema column names after mapping.
# Removed PostDate and Institution as they are not reliably available across all sources.
TXN_ID_HASH_COLS = ["Date", "Amount", "Description", "Account"] # Changed OriginalDescription to Description


def _generate_txn_id(row: pd.Series[Any]) -> str:  # Updated type hint
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
        if col == "Description":
            desc = val # val is row.get("Description") from the current iteration
            desc_part = str(desc)[:20] if pd.notna(desc) else "NoDesc"
            parts.append(desc_part)
        elif pd.isna(val):  # Handles None, pd.NaT, np.nan
            parts.append("")
        else:
            # For datetime objects (like Date, PostDate), convert to ISO format string
            if isinstance(val, (datetime, pd.Timestamp)):
                parts.append(val.isoformat()[:10])  # YYYY-MM-DD
            else:
                parts.append(str(val).strip())

    hash_input = "|".join(parts)

    # Import hashlib here if not already at module level, or ensure it is.
    # hashlib is now imported at the module level
    return hashlib.md5(hash_input.encode("utf-8")).hexdigest()[:16]


def apply_schema_transformations(
    df: pd.DataFrame,
    schema_rules: Dict[str, Any],
    merchant_lookup_rules: List[Tuple[re.Pattern[str], str]],  # Updated type hint
    filename: str,  # Added filename parameter
    debug_tracer: Optional[PipelineDebugTracer] = None  # Added debug_tracer parameter
) -> pd.DataFrame:
    """
    Applies all transformations defined by a schema to a DataFrame.
    This includes column mapping, date parsing, amount signing, derived columns, etc.

    Args:
        df (pd.DataFrame): The raw DataFrame from a CSV.
        schema_rules (Dict[str, Any]): The specific schema definition to apply.
        merchant_lookup_rules (List[Tuple[re.Pattern, str]]): Loaded merchant lookup rules.
        filename (str): The name of the CSV file being processed, for logging.

    Returns:
        pd.DataFrame: The transformed DataFrame, partially conforming to the master schema.
                      Further processing like TxnID, Owner, final merchant cleaning happens later.
    """
    schema_id = schema_rules.get("id", "UnknownSchema")
    log.debug(
        f"[APPLY_SCHEMA_STATE] File: {filename} | Schema: {schema_id} | Stage: Before Transformations | Columns: {list(df.columns)}"
    )
    
    if debug_tracer:
        debug_tracer.capture_stage("1_RAW_CSV_LOADED", df, 
                                   focus_columns=['Date', 'Amount', 'Description', 'Merchant', 'Original Statement', 'Transaction Date', 'Details']) # Added more potential raw cols

    transformed_df = df.copy()

    # 1. Header Normalization (of DataFrame columns for mapping)
    # The schema's column_map keys are expected to be raw headers from the source CSV.
    # We need to map these raw headers to our internal canonical names.
    # The _normalize_csv_header function is for matching, not for renaming df columns yet.

    # Store original column names for 'Extras'
    original_columns = list(transformed_df.columns)

    # 2. Apply Column Mapping
    column_map = schema_rules.get("column_map", {})
    if not column_map:
        log.warning(
            f"[APPLY_SCHEMA_WARN] File: {filename} | Schema: {schema_id} | Step: Column Mapping | Detail: Schema has no column_map. Columns will be as-is."
        )
        # Proceed, but 'Extras' will include all original columns if they don't match master schema.

    # Normalize keys in column_map for matching against normalized df headers
    # However, the task implies column_map keys are the *raw* headers.
    # "Normalize original CSV headers ... before attempting to match them with keys in column_map."
    # This means we should normalize the DataFrame's current headers first.

    df_normalized_header_map = {
        col: _normalize_csv_header(col) for col in transformed_df.columns
    }
    # And normalize the keys in the schema's column_map as well for robust matching
    normalized_schema_column_map = {
        _normalize_csv_header(k): v for k, v in column_map.items()
    }

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
            original_raw_key_for_log = (
                "Unknown (normalized key not found back in original map)"
            )
            for (
                raw_k,
                raw_v,
            ) in column_map.items():  # schema_rules.get('column_map', {})
                if _normalize_csv_header(raw_k) == normalized_schema_key:
                    original_raw_key_for_log = raw_k
                    break
            log.warning(
                f"[APPLY_SCHEMA_WARN] File: {filename} | Schema: {schema_id} | Step: Column Mapping | Detail: Column '{original_raw_key_for_log}' (normalized: '{normalized_schema_key}') defined in schema column_map not found in CSV."
            )

    transformed_df = transformed_df.rename(columns=rename_dict)
    log.debug(f"[APPLY_SCHEMA_TRANSFORM] File: {filename} | Schema: {schema_id} | Step: Column Mapping | Details: Renamed columns {rename_dict}")

    if debug_tracer:
        debug_tracer.capture_stage("2_AFTER_COLUMN_MAPPING", transformed_df,
                                   focus_columns=['Date', 'Amount', 'OriginalDescription', 'Merchant', 'Description', 'Account'])
        # Capture merchant-related columns specifically
        relevant_merchant_cols = ['Merchant', 'OriginalMerchant', 'Description', 'OriginalDescription', 'Details', 'Original Statement']
        existing_merchant_cols = [col for col in relevant_merchant_cols if col in transformed_df.columns]
        if existing_merchant_cols: # Only capture if any relevant columns exist
             debug_tracer.capture_stage("2A_MERCHANT_RELATED_COLUMNS_POST_MAP", transformed_df, 
                                   focus_columns=existing_merchant_cols)


    # 3. Handle 'Extras' (unmapped columns)
    # Unmapped columns are those original columns not in rename_dict.keys()
    # Their new names (if they were part of a rename) are not relevant for 'Extras'.
    # We need columns from 'original_columns' that were NOT mapped.

    mapped_original_cols = set(rename_dict.keys())
    unmapped_original_cols = [
        col for col in original_columns if col not in mapped_original_cols
    ]

    if unmapped_original_cols:
        # Create a DataFrame of just the unmapped columns
        extras_df = df[unmapped_original_cols].copy()
        # Convert each row of extras_df to a JSON string
        # Ensure NaN/NaT are handled correctly by converting to None for JSON serialization
        transformed_df["Extras"] = extras_df.apply(
            lambda row: json.dumps(row.dropna().to_dict()), axis=1
        )
        # This log will be replaced by a more specific one after extras_ignore logic
        # log.info(f"Collected unmapped columns into 'Extras': {unmapped_original_cols}")
    else:
        transformed_df["Extras"] = None  # Or pd.NA or empty JSON string '{}'
        # This log will be replaced
        # log.info("No unmapped columns found for 'Extras'.")

    # 4. Date Parsing
    # The schema can specify multiple date columns to parse, each with its own format string
    # For now, let's assume 'Date' and 'PostDate' are the primary ones.
    # The task mentions: "Use the date_format specified in the matched schema to parse date strings
    # from the source CSV into datetime objects for Date and PostDate."
    # This implies date_format could be a single string or a dict if multiple date cols have different formats.
    # The current schema_registry.yml shows date_format as a single string.

    date_columns_to_parse = {}  # Stores {col_name: format_str or None}
    schema_date_format = schema_rules.get("date_format")

    # Identify which of the mapped columns are potential date columns
    # Common date columns are 'Date', 'PostDate'.
    # The column_map would have mapped source columns to these canonical names.
    potential_date_cols_in_df = [
        col for col in ["Date", "PostDate"] if col in transformed_df.columns
    ]

    for date_col_name in potential_date_cols_in_df:
        # If a global date_format is provided in the schema, use it.
        # Otherwise, pandas will attempt to infer.
        date_columns_to_parse[date_col_name] = schema_date_format

    for col_name, fmt_str in date_columns_to_parse.items():
        if col_name in transformed_df.columns:
            if debug_tracer:
                # Capture raw date values before parsing for this specific column
                # Make sure to use a unique stage name if looping, or capture all relevant date columns at once
                debug_tracer.capture_stage(f"3A_BEFORE_DATE_PARSE_{col_name.replace(' ', '_')}", 
                                          transformed_df, 
                                          focus_columns=[col_name])
                sample_dates = transformed_df[col_name].head(5).tolist() # Use a local var for sample_dates
                log.info(f"[DATE_DEBUG] File: {filename} | Column '{col_name}' raw values: {sample_dates}")
                log.info(f"[DATE_DEBUG] File: {filename} | Attempting to parse '{col_name}' with format: {fmt_str if fmt_str else 'inferred'}")

            try:
                # Ensure the column is string type before parsing, if it's not already datetime
                if not pd.api.types.is_datetime64_any_dtype(transformed_df[col_name]):
                    transformed_df[col_name] = pd.to_datetime(
                        transformed_df[col_name], format=fmt_str, errors="coerce"
                    )
                    log.debug(
                        f"[APPLY_SCHEMA_TRANSFORM] File: {filename} | Schema: {schema_id} | Step: Date Parsing | Column: {col_name} | Format: {fmt_str if fmt_str else 'inferred'}"
                    )
                else:
                    log.debug(
                        f"[APPLY_SCHEMA_TRANSFORM] File: {filename} | Schema: {schema_id} | Step: Date Parsing | Column: {col_name} | Detail: Already datetime type, skipping parsing."
                    )
            except Exception as e:
                log.warning(
                    f"[APPLY_SCHEMA_WARN] File: {filename} | Schema: {schema_id} | Step: Date Parsing | Column: {col_name} | Format: {fmt_str} | Error: {e}. Column left as is or NaT."
                )
                # If errors='coerce', unparseable dates become NaT (Not a Time)
        else:
            log.warning(
                f"[APPLY_SCHEMA_WARN] File: {filename} | Schema: {schema_id} | Step: Date Parsing | Column: {col_name} | Detail: Specified for parsing but not found in DataFrame after mapping."
            )

    if debug_tracer:
        debug_tracer.capture_stage("3B_AFTER_ALL_DATE_PARSING", transformed_df,
                                   focus_columns=potential_date_cols_in_df) # potential_date_cols_in_df was defined earlier

    # 5. Amount Sign Standardization & Numeric Conversion
    amount_col_name = "Amount"  # Assuming 'Amount' is the canonical name after mapping
    if amount_col_name in transformed_df.columns:
        # Apply amount_regex if present
        amount_regex_str = schema_rules.get("amount_regex")
        if amount_regex_str:
            try:
                # Extract the numeric part using regex. Expects one capturing group.
                # Ensure it handles cases where the column might already be numeric or partly clean.
                transformed_df[amount_col_name] = (
                    transformed_df[amount_col_name]
                    .astype(str)
                    .str.extract(f"({amount_regex_str})", expand=False)
                )
                log.debug(
                    f"[APPLY_SCHEMA_TRANSFORM] File: {filename} | Schema: {schema_id} | Step: Amount Regex | Column: {amount_col_name} | Regex: {amount_regex_str}"
                )
            except Exception as e:
                log.error(
                    f"[APPLY_SCHEMA_ERROR] File: {filename} | Schema: {schema_id} | Step: Amount Regex | Column: {amount_col_name} | Error: {e}. Amount column may be incorrect."
                )

        # Convert to numeric, coercing errors to NaN
        transformed_df[amount_col_name] = pd.to_numeric(
            transformed_df[amount_col_name], errors="coerce"
        )
        log.debug(f"[APPLY_SCHEMA_TRANSFORM] File: {filename} | Schema: {schema_id} | Step: Amount ToNumeric | Column: {amount_col_name}")

        sign_rule_from_schema = schema_rules.get("sign_rule")

        # --- BEGIN VALIDATION GUARD ---
        ALLOWED_SIGN_RULES = {"flip_if_positive", "as_is", "flip_if_withdrawal"}
        # Determine the effective sign rule. If not specified in schema, it defaults to "as_is".
        # This effective rule is used for validation. The original sign_rule_from_schema (which can be None)
        # is used for the actual sign application logic.
        effective_sign_rule_for_validation = sign_rule_from_schema if sign_rule_from_schema is not None else "as_is"

        if effective_sign_rule_for_validation not in ALLOWED_SIGN_RULES:
            sorted_allowed_rules_str = ", ".join(sorted(list(ALLOWED_SIGN_RULES)))
            # schema_id is available in this scope from apply_schema_transformations parameters
            raise ValueError(
                f"Unknown sign_rule '{effective_sign_rule_for_validation}' in schema '{schema_id}'. Allowed: {sorted_allowed_rules_str}"
            )
        # --- END VALIDATION GUARD ---

        if sign_rule_from_schema: # Log only if a rule is actually applied
            log.debug(f"[APPLY_SCHEMA_TRANSFORM] File: {filename} | Schema: {schema_id} | Step: Amount Sign Rule | Column: {amount_col_name} | Rule: {sign_rule_from_schema}")

        # Apply the rule using the original value from schema (sign_rule_from_schema)
        if sign_rule_from_schema == "flip_if_positive":
            transformed_df[amount_col_name] = transformed_df[amount_col_name].apply(
                lambda x: -abs(x) if pd.notna(x) and x > 0 else x
            )
        elif (
            sign_rule_from_schema == "flip_if_negative"
        ):  # Not explicitly in task, but good to have
            transformed_df[amount_col_name] = transformed_df[amount_col_name].apply(
                lambda x: abs(x) if pd.notna(x) and x < 0 else x
            )
        elif sign_rule_from_schema == "flip_always":
            transformed_df[amount_col_name] = -transformed_df[amount_col_name]
        elif sign_rule_from_schema == "flip_if_withdrawal":
            # Specific rule for chase_total_checking
            if "Category" in transformed_df.columns:
                withdrawal_categories = ["withdrawal", "payment"]
                # Apply to rows where Category matches and Amount is positive
                mask = (
                    transformed_df["Category"]
                    .astype(str)
                    .str.lower()
                    .isin(withdrawal_categories)
                    & (transformed_df[amount_col_name] > 0)
                    & pd.notna(transformed_df[amount_col_name])
                )
                transformed_df.loc[mask, amount_col_name] = -transformed_df.loc[
                    mask, amount_col_name
                ]
            else:
                log.warning(
                    f"[APPLY_SCHEMA_WARN] File: {filename} | Schema: {schema_id} | Step: Amount Sign Rule | Rule: flip_if_withdrawal | Detail: 'Category' column not found. Rule not applied."
                )
        elif sign_rule_from_schema == "as_is":
            pass # No change, already logged the rule
        elif (
            isinstance(sign_rule_from_schema, dict) # Check the original value from schema
            and sign_rule_from_schema.get("type") == "flip_if_column_value_matches"
        ):
            rule_col_name = sign_rule_from_schema.get("column") # Changed sign_rule to sign_rule_from_schema
            debit_values = [
                str(v).lower() for v in sign_rule_from_schema.get("debit_values", []) # Changed sign_rule to sign_rule_from_schema
            ]  # Normalize to lower string

            actual_col_to_check = None
            if rule_col_name in transformed_df.columns:
                actual_col_to_check = rule_col_name
            else:
                # Try normalized version if original rule_col_name not found (e.g. schema used raw name, df has normalized)
                # Check against normalized df headers that might exist if not mapped
                # This is tricky because df columns are already mapped ones or original unmapped.
                # The rule should ideally refer to a column name present in transformed_df at this stage.
                # Let's assume rule_col_name refers to a column name that *should* exist in transformed_df.
                # If it was mapped, it's the target name. If it's an original unmapped name, it's that.
                # The most robust is to check existence directly.
                log.warning(
                    f"Column '{rule_col_name}' for complex sign rule not directly found. This rule might not apply correctly."
                )

            if actual_col_to_check and debit_values:
                # Log unique values from the column that drives the sign_rule
                if actual_col_to_check in transformed_df.columns:
                    unique_sign_rule_values = (
                        transformed_df[actual_col_to_check]
                        .astype(str)
                        .unique()
                        .tolist()
                    )
                    log.debug(
                        f"[APPLY_SCHEMA_TRANSFORM_DETAIL] File: {filename} | Schema: {schema_id} | Step: Amount Sign Rule (Complex) | Detail: Unique values in '{actual_col_to_check}' for rule: {unique_sign_rule_values}"
                    )

                def adjust_sign(row: pd.Series[Any]) -> float:
                    amount = float(row[amount_col_name])
                    type_val_series = row[actual_col_to_check]

                    if pd.isna(amount) or pd.isna(type_val_series):
                        return amount  # Don't change NaN amounts or if type is NaN

                    type_val = str(type_val_series).lower().strip()

                    is_debit_type = type_val in debit_values

                    if is_debit_type:  # Should be negative
                        return -abs(amount) if amount > 0 else amount
                    else:  # Should be positive (credit/inflow)
                        return abs(amount) if amount < 0 else amount

                transformed_df[amount_col_name] = transformed_df.apply(
                    adjust_sign, axis=1
                )
            elif not actual_col_to_check:
                log.warning(
                    f"[APPLY_SCHEMA_WARN] File: {filename} | Schema: {schema_id} | Step: Amount Sign Rule (Complex) | Detail: Column '{rule_col_name}' not found. Rule not applied."
                )
            else:  # no debit_values
                log.warning(
                    f"[APPLY_SCHEMA_WARN] File: {filename} | Schema: {schema_id} | Step: Amount Sign Rule (Complex) | Detail: No 'debit_values' provided. Rule not applied effectively."
                )

        elif sign_rule_from_schema and sign_rule_from_schema not in ["as_is", "flip_if_positive", "flip_if_negative", "flip_always", "flip_if_withdrawal"]: # Unrecognized simple string rule, changed sign_rule to sign_rule_from_schema
            log.warning(
                f"[APPLY_SCHEMA_WARN] File: {filename} | Schema: {schema_id} | Step: Amount Sign Rule | Detail: Unrecognized sign_rule '{sign_rule_from_schema}'. Amount signs may be incorrect."
            )

        # Ensure 'Amount' is float
        transformed_df[amount_col_name] = transformed_df[amount_col_name].astype(
            float, errors="ignore"
        )
        log.debug(f"[APPLY_SCHEMA_TRANSFORM] File: {filename} | Schema: {schema_id} | Step: Amount Astype Float | Column: {amount_col_name}")

    else:
        log.warning(
            f"[APPLY_SCHEMA_WARN] File: {filename} | Schema: {schema_id} | Step: Amount Processing | Detail: Amount column '{amount_col_name}' not found after mapping. Cannot apply sign rules or ensure numeric type."
        )
    
    if debug_tracer:
        debug_tracer.capture_stage("4_AFTER_AMOUNT_PROCESSING", transformed_df,
                                   focus_columns=['Amount', 'Category']) # Category might influence sign

    # 6. Derived Columns
    derived_cfg = schema_rules.get(
        "derived_columns", {}
    )  # Use derived_cfg to match ingest.py
    if derived_cfg:
        # log.info(f"Applying derived_columns rules: {derived_cfg}") # Too verbose for info, individual steps will be debug
        for (
            new_col_name,
            rule_cfg,
        ) in derived_cfg.items():  # Use new_col_name and rule_cfg
            if not isinstance(rule_cfg, dict):
                log.warning(
                    f"[APPLY_SCHEMA_WARN] File: {filename} | Schema: {schema_id} | Step: Derived Column | New Column: {new_col_name} | Detail: Invalid config, expected dict, got {type(rule_cfg)}. Config: {rule_cfg}"
                )
                transformed_df[new_col_name] = pd.NA
                continue
            
            # Prioritize 'type' key for rule type, fallback to 'rule' for compatibility
            rule_type = rule_cfg.get("type") 
            if not rule_type:
                rule_type = rule_cfg.get("rule") # Fallback for older 'rule:' syntax

            rule_details = rule_cfg # rule_cfg itself contains parameters like 'value', 'column', 'pattern'

            # Further fallback for very old structures if rule_type is still None
            # This part handles cases where rule_cfg might be {'static_value': 'ActualValue'}
            if not rule_type:
                if "regex_extract" in rule_cfg and isinstance(rule_cfg["regex_extract"], dict):
                    rule_type = "regex_extract"
                    rule_details = rule_cfg["regex_extract"] # rule_details becomes the nested dict
                elif "static_value" in rule_cfg: # This could be rule_cfg: {'static_value': 'ActualValue'} or {'static_value': {'value': 'ActualValue'}}
                    rule_type = "static_value"
                    # If rule_cfg['static_value'] is not a dict, rule_details remains rule_cfg, and 'value' is extracted from rule_details['static_value']
                    # If rule_cfg['static_value'] IS a dict (e.g. {'value': 'ActualValue'}), then rule_details should become that dict.
                    if isinstance(rule_cfg["static_value"], dict):
                         rule_details = rule_cfg["static_value"]
                    # else rule_details remains rule_cfg, and 'value' will be sought from rule_details['static_value']

            if rule_type is None: # If still no rule_type, then it's an unknown configuration
                log.warning(
                    f"[APPLY_SCHEMA_WARN] File: {filename} | Schema: {schema_id} | Step: Derived Column | New Column: {new_col_name} | Detail: Unknown rule type or invalid rule structure. Config: {rule_cfg}. Skipping."
                )
                transformed_df[new_col_name] = pd.NA
                continue
            
            log_details_for_derived = f"Rule Type: {rule_type}"
            try:
                if rule_type == "static_value":
                    # For static_value, the value can be directly under rule_details['value']
                    # or, for very old format, it might be rule_details['static_value']
                    static_val = rule_details.get("value")
                    if static_val is None and rule_type == "static_value" and "static_value" in rule_details: # Check for old format like {'static_value': 'ActualValue'}
                        static_val = rule_details.get("static_value")
                    
                    log_details_for_derived += f" | Value: {static_val}"

                    if static_val is None: # After checking both .get('value') and .get('static_value') for static_value type
                        log.warning(
                            f"[APPLY_SCHEMA_WARN] File: {filename} | Schema: {schema_id} | Step: Derived Column (static_value) | New Column: {new_col_name} | Detail: 'value' not found or is None in rule_details. Config: {rule_cfg}"
                        )
                        transformed_df[new_col_name] = pd.NA
                        continue
                    transformed_df[new_col_name] = static_val

                elif rule_type == "regex_extract":
                    # rule_details should be a dict containing 'column' and 'pattern'
                    if not isinstance(rule_details, dict):
                        log.warning(
                            f"[APPLY_SCHEMA_WARN] File: {filename} | Schema: {schema_id} | Step: Derived Column (regex_extract) | New Column: {new_col_name} | Detail: Rule details for regex_extract not a dict. Config: {rule_cfg}"
                        )
                        transformed_df[new_col_name] = pd.NA
                        continue

                    source_col = rule_details.get("column") # This is the source column for regex
                    pattern_str = rule_details.get("pattern")
                    log_details_for_derived += f" | Source Column: {source_col} | Pattern: {pattern_str}"

                    if not source_col or not pattern_str:
                        log.warning(
                            f"[APPLY_SCHEMA_WARN] File: {filename} | Schema: {schema_id} | Step: Derived Column (regex_extract) | New Column: {new_col_name} | Detail: Missing 'column' or 'pattern' in rule_details. Config: {rule_cfg}"
                        )
                        transformed_df[new_col_name] = pd.NA
                        continue

                    if source_col not in transformed_df.columns:
                        log.warning(
                            f"[APPLY_SCHEMA_WARN] File: {filename} | Schema: {schema_id} | Step: Derived Column (regex_extract) | New Column: {new_col_name} | Detail: Source column '{source_col}' not found."
                        )
                        transformed_df[new_col_name] = pd.NA
                        continue

                    regex = re.compile(pattern_str)
                    capture_group_name = (
                        list(regex.groupindex.keys())[0] if regex.groupindex else None
                    )
                    log_details_for_derived += f" | Capture Group: {capture_group_name or '1st unnamed'}"


                    def extract_with_regex(text_to_search: Any) -> Any:
                        if pd.isna(text_to_search):
                            return pd.NA
                        match = regex.search(str(text_to_search))
                        if match:
                            if (
                                capture_group_name
                                and capture_group_name in match.groupdict()
                            ):
                                return match.group(capture_group_name)
                            elif match.groups():
                                return match.group(1)
                        return pd.NA

                    transformed_df[new_col_name] = transformed_df[source_col].apply(
                        extract_with_regex
                    )

                else: # Should have been caught by rule_type is None check earlier
                    log.warning(
                        f"[APPLY_SCHEMA_WARN] File: {filename} | Schema: {schema_id} | Step: Derived Column | New Column: {new_col_name} | Detail: Unknown rule type '{rule_type}'. Config: {rule_cfg}. Skipping."
                    )
                    transformed_df[new_col_name] = pd.NA
                    continue # Skip the common log for this iteration

                log.debug(f"[APPLY_SCHEMA_TRANSFORM] File: {filename} | Schema: {schema_id} | Step: Derived Column | New Column: {new_col_name} | Details: {log_details_for_derived}")

            except Exception as e:
                log.error(
                    f"[APPLY_SCHEMA_ERROR] File: {filename} | Schema: {schema_id} | Step: Derived Column | New Column: {new_col_name} | Rule Type: {rule_type} | Error: {e}",
                    exc_info=True,
                )
                transformed_df[new_col_name] = pd.NA
    
    if debug_tracer:
        # Capture after all derived columns are processed
        derived_col_names = list(derived_cfg.keys()) if derived_cfg else []
        # Also include some key base columns to see context
        focus_cols_for_derived = list(set(derived_col_names + ['Account', 'AccountLast4', 'Institution', 'Owner', 'DataSourceName']))
        existing_focus_cols = [col for col in focus_cols_for_derived if col in transformed_df.columns]
        if existing_focus_cols: # Only capture if any relevant columns exist
            debug_tracer.capture_stage("5_AFTER_DERIVED_COLUMNS", transformed_df,
                                   focus_columns=existing_focus_cols)


    # Alias OriginalDescription to Description if Description is missing
    if (
        "OriginalDescription" in transformed_df.columns
        and "Description" not in transformed_df.columns
    ):
        transformed_df["Description"] = transformed_df["OriginalDescription"]
        log.debug(
            f"[APPLY_SCHEMA_TRANSFORM] File: {filename} | Schema: {schema_id} | Step: Alias OriginalDescription | Detail: Aliased 'OriginalDescription' to 'Description' as 'Description' was missing."
        )

    # Handle extras_ignore: remove specified columns if they exist
    # This should happen after all columns (original, mapped, derived) are settled.
    extras_to_ignore = schema_rules.get("extras_ignore", [])
    if extras_to_ignore:
        # Columns to drop should be those present in the DataFrame at this stage.
        # These could be original column names if they weren't mapped, or new names if they were.
        # The extras_ignore list in schema_registry.yml refers to original column names.
        # However, the current transformed_df has already undergone renames.
        # The logic in ingest.py's load_folder was:
        #   cols_to_drop_from_df = [col for col in extras_to_ignore if col in df.columns]
        #   df = df.drop(columns=cols_to_drop_from_df)
        # This implies extras_ignore contains names as they appear *after* potential mapping
        # or are original names that were *not* mapped.
        # Given the `schema_registry.yml` has `extras_ignore: ["Name", ...]` and "Name" is an *original* column
        # that is *not* in `column_map` for the affected schemas, it means we should check `extras_to_ignore`
        # against the columns currently in `transformed_df`.

        # Let's re-evaluate: extras_ignore should refer to columns as they are *named in the source CSV*
        # or as they are *after mapping if they were mapped to something that should then be ignored*.
        # The user's schema_registry.yml has `extras_ignore: ["Name"]` etc. "Name" is an original column.
        # The current `transformed_df` might still have "Name" if it wasn't mapped, or it might have been mapped.
        # The simplest interpretation that matches `ingest.py`'s apparent behavior is to check against current df columns.

        # However, the log "Unexpected column survived mapping: Name" suggests "Name" *is* still in the df
        # after mapping (because it wasn't in column_map).
        # So, the list in extras_ignore should contain names as they are in the DataFrame *at the point of ignoring*.

        # The `extras_ignore` in `schema_registry.yml` lists original column names.
        # These original names might still exist in `transformed_df` if they were not part of `rename_dict`.
        # Or, if an original column listed in `extras_ignore` *was* mapped, we should ignore its *new* name.
        # This is getting complex. The `ingest.py` version was simpler:
        # `cols_to_drop_from_df = [col for col in extras_to_ignore if col in df.columns]`
        # This assumes `extras_ignore` contains names that are currently present in the DataFrame.
        # Let's stick to the user's `schema_registry.yml` where `extras_ignore` lists original names.
        # We need to find which of these original names are still present (i.e., were not mapped and renamed).

        # The `unmapped_original_cols` list contains original column names that were not mapped.
        # The `Extras` column now holds a JSON of these.
        # The `extras_ignore` from schema should refer to original column names.
        # We need to ensure these are not carried forward if they are not part of `MASTER_SCHEMA_COLUMNS`.
        # The current `Extras` column creation already handles unmapped columns.
        # The `extras_ignore` directive is about *preventing* certain unmapped columns from even going into the `Extras` JSON,
        # or dropping them if they somehow survived as actual columns.

        # Let's refine the logic for `Extras` creation and then apply `extras_ignore`.
        # Current `Extras` logic:
        # mapped_original_cols = set(rename_dict.keys())
        # unmapped_original_cols = [col for col in original_columns if col not in mapped_original_cols]
        # extras_df = df[unmapped_original_cols].copy() ...

        # New approach for extras_ignore:
        # 1. Identify columns to be put into 'Extras': these are `unmapped_original_cols`.
        # 2. From this list, remove any columns specified in `extras_ignore`.
        # 3. Then, create the 'Extras' JSON from the filtered list.
        # 4. Also, explicitly drop any columns listed in `extras_ignore` that might still exist as actual columns
        #    in `transformed_df` (e.g. if they were mapped to a name that is also in `extras_ignore`, though unlikely).

        # First, drop any columns listed in extras_ignore that are currently actual columns in transformed_df.
        # These would be original names that were NOT mapped by `rename_dict`.
        cols_to_drop_directly = [
            col for col in extras_to_ignore if col in transformed_df.columns
        ]
        if cols_to_drop_directly:
            transformed_df.drop(
                columns=cols_to_drop_directly, inplace=True, errors="ignore"
            )
            log.debug(
                f"[APPLY_SCHEMA_TRANSFORM] File: {filename} | Schema: {schema_id} | Step: Extras Ignore | Details: Dropped columns directly {cols_to_drop_directly}"
            )
            # Update unmapped_original_cols if any were dropped directly
            unmapped_original_cols = [
                col
                for col in unmapped_original_cols
                if col not in cols_to_drop_directly
            ]

        # Re-create 'Extras' column logic, considering extras_ignore for what goes into JSON.
        # `original_columns` are the raw headers from the input CSV `df`.
        # `rename_dict` maps raw headers to canonical names.

        # Columns that were mapped:
        mapped_raw_headers = set(rename_dict.keys())
        # Columns from original CSV that were NOT mapped:
        unmapped_raw_headers = [
            col for col in original_columns if col not in mapped_raw_headers
        ]

        # From these unmapped raw headers, filter out those listed in extras_ignore:
        final_cols_for_extras_json = [
            col for col in unmapped_raw_headers if col not in extras_to_ignore
        ]

        if final_cols_for_extras_json:
            # Create a DataFrame of just these columns from the *original* df
            extras_df_filtered = df[final_cols_for_extras_json].copy()
            transformed_df["Extras"] = extras_df_filtered.apply(
                lambda row: json.dumps(row.dropna().to_dict()), axis=1
            )
            log.debug(
                f"[APPLY_SCHEMA_TRANSFORM] File: {filename} | Schema: {schema_id} | Step: Extras Collection | Details: Unmapped original columns for Extras JSON (after extras_ignore): {final_cols_for_extras_json}"
            )
        else:
            transformed_df["Extras"] = None
            log.debug(
                f"[APPLY_SCHEMA_TRANSFORM] File: {filename} | Schema: {schema_id} | Step: Extras Collection | Details: No unmapped columns left for 'Extras' JSON after applying extras_ignore."
            )

    # 7. Specific source pre-processing (e.g., Rocket Money) - Placeholder
    # This should be minimized by making YAML expressive.
    # schema_id = schema_rules.get('id', '').lower()
    # if 'rocket_money' in schema_id:
    #    # ... Rocket Money specific logic ...

    # 8. Populate DataSourceName (from schema['id']), only if not already set by derived_columns
    # Check if DataSourceName was already populated by derived_columns
    if "DataSourceName" not in transformed_df.columns or transformed_df["DataSourceName"].isnull().all():
        ds_name_val = schema_rules.get("id", "UnknownSchema")
        transformed_df["DataSourceName"] = ds_name_val
        log.debug(
            f"[APPLY_SCHEMA_TRANSFORM] File: {filename} | Schema: {schema_id} | Step: DataSourceName Population from schema ID | Value: {ds_name_val}"
        )
    else:
        log.debug(
            f"[APPLY_SCHEMA_TRANSFORM] File: {filename} | Schema: {schema_id} | Step: DataSourceName Population | Detail: DataSourceName already populated (likely by derived_columns), value: {transformed_df['DataSourceName'].iloc[0] if not transformed_df.empty else 'N/A'}"
        )

    # 9. Add static columns from schema['extra_static_cols']
    extra_static_cols = schema_rules.get("extra_static_cols", {})
    if extra_static_cols:
        for col_name, static_value in extra_static_cols.items():
            transformed_df[col_name] = static_value
            log.debug(f"[APPLY_SCHEMA_TRANSFORM] File: {filename} | Schema: {schema_id} | Step: Static Column | Column: {col_name} | Value: {static_value}")

    # All transformations implemented:
    # - Complex sign_rule (e.g. based on another column's value) ✓ implemented above
    # - Specific source pre-processing ✓ handled via YAML configuration (placeholder at line 1054)

    # Verify apply_schema_transformations returns only canonical + extras
    final_master_cols_missing = [col for col in MASTER_SCHEMA_COLUMNS if col not in transformed_df.columns]
    if final_master_cols_missing:
        log.warning(f"[APPLY_SCHEMA_INTEGRITY] File: {filename} | Schema: {schema_id} | Missing Master Columns After Transformations: {final_master_cols_missing}")
    # else: # No need for an else if all are present, less noise
        # log.debug(f"[APPLY_SCHEMA_INTEGRITY] File: {filename} | Schema: {schema_id} | All Master Columns Present After Transformations.")

    unexpected_survivors = [
        col for col in transformed_df.columns if col not in MASTER_SCHEMA_COLUMNS and col != "Extras"
    ]
    if unexpected_survivors:
        log.warning(f"[APPLY_SCHEMA_INTEGRITY] File: {filename} | Schema: {schema_id} | Unexpected columns survived mapping: {unexpected_survivors}")

    log.debug(
        f"[APPLY_SCHEMA_STATE] File: {filename} | Schema: {schema_id} | Stage: After Transformations | Columns: {list(transformed_df.columns)}"
    )
    return transformed_df


def process_csv_files(
    csv_files: List[Union[str, Path]],
    schema_registry_override_path: Optional[Path] = None,
    merchant_lookup_override_path: Optional[Path] = None,
    debug_mode: bool = False  # Added debug_mode parameter
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
    # schema_reg_path = schema_registry_override_path or SCHEMA_REGISTRY_PATH # Unused
    merchant_lkp_path = merchant_lookup_override_path or MERCHANT_LOOKUP_PATH

    # schema_registry variable was unused. _find_schema handles registry loading.
    # try:
    #     schema_registry = load_and_parse_schema_registry(schema_reg_path)
    # except Exception as exc:
    #     raise FatalSchemaError(f"Failed to load schema registry: {exc}") from exc

    try:
        merchant_rules = load_merchant_lookup_rules(merchant_lkp_path)
    except Exception as exc:
        raise RecoverableFileError(
            f"Failed to load merchant lookup rules: {exc}"
        ) from exc

    all_processed_dfs: List[pd.DataFrame] = []
    schema_ids_found: List[str] = []  # For schema matching smoke test
    
    for csv_file_path_obj in [Path(p) for p in csv_files]:
        filename_for_logs = csv_file_path_obj.name
        log.info(f"[PROCESS_FILE_START] File: {filename_for_logs}")
        
        debug_tracer_instance: Optional[PipelineDebugTracer] = None
        if debug_mode:
            debug_tracer_instance = PipelineDebugTracer(filename_for_logs)

        try:
            raw_df = pd.read_csv(
                csv_file_path_obj, dtype=str
            )  # Read all as string initially
            if raw_df.empty:
                log.warning(f"[PROCESS_FILE_END] File: {filename_for_logs} | Status: Skipped | Reason: CSV file is empty.")
                continue
        except Exception as exc:
            # Log before raising, so the file context is captured
            log.error(f"[PROCESS_FILE_END] File: {filename_for_logs} | Status: Failed | Reason: Failed to read CSV: {exc}")
            raise RecoverableFileError(
                f"Failed to read CSV {filename_for_logs}: {exc}"
            ) from exc
        
        log.debug(f"[SCHEMA_MATCH_INPUT] File: {filename_for_logs} | Headers: {list(raw_df.columns)}")

        # Infer Owner (e.g., from subfolder name "Jordyn"/"Ryan")
        wanted_owners_map = {
            "ryan": "Ryan",
            "jordyn": "Jordyn",
        }  # Map lowercase dir name to capitalized Owner name
        current_path_segment = csv_file_path_obj.parent
        owner = None  # Default if not found by walking

        # Walk up a few levels (e.g., up to 4) to find a directory named Ryan or Jordyn (case-insensitive)
        for _ in range(4):  # Check current parent and up to 3 levels higher
            if not current_path_segment or not current_path_segment.name:
                break  # Should not happen with Path objects, but defensive

            dir_name_lower = current_path_segment.name.lower()
            if dir_name_lower in wanted_owners_map:
                owner = wanted_owners_map[
                    dir_name_lower
                ]  # Assign the capitalized version
                break

            # Stop if we hit a directory named 'BALANCE-pyexcel' (repo root) or filesystem root
            if (
                current_path_segment.name == "BALANCE-pyexcel"
                or current_path_segment == current_path_segment.parent
            ):
                break
            current_path_segment = current_path_segment.parent

        # --- tweak: try filename token before UnknownOwner fallback ---
        if owner is None:
            stem_parts = csv_file_path_obj.stem.split(" - ", 1)
            filename_token = stem_parts[
                0
            ]  # Get the first part (e.g., "Ryan" or "Jordyn")

            if filename_token in {"Ryan", "Jordyn"}:
                owner = filename_token

        if owner is None:
            owner = "UnknownOwner"
        log.debug(f"[PROCESS_FILE_DETAIL] File: {filename_for_logs} | Detail: Inferred Owner '{owner}' from path.")

        # DataSourceDate (file modification date)
        try:
            ds_date = datetime.fromtimestamp(csv_file_path_obj.stat().st_mtime)
        except Exception as e:
            log.warning(
                f"[PROCESS_FILE_WARN] File: {filename_for_logs} | Detail: Could not get file modification date: {e}. Using current time."
            )
            ds_date = datetime.now()
        log.debug(f"[PROCESS_FILE_DETAIL] File: {filename_for_logs} | Detail: DataSourceDate set to {ds_date}")

        # Identify Schema
        # Use raw_df.columns.tolist() for header matching
        from balance_pipeline.schema_types import MatchResult  # Import for cast
        from typing import cast  # Import for cast

        match_result_union = _find_schema(
            list(raw_df.columns)
        )  # _find_schema is aliased to the new engine

        if match_result_union is None:
            log.error(
                f"[SCHEMA_RESULT] File: {filename_for_logs} | Selected schema: None | Reason: No schema could be determined by _find_schema. Skipping file."
            )
            log.info(f"[PROCESS_FILE_END] File: {filename_for_logs} | Status: Skipped | Reason: No schema determined.")
            continue

        match_result = cast(MatchResult, match_result_union)
        schema_object = match_result.schema
        rules_dict = match_result.rules
        missing_required = match_result.missing # This is a set
        extra_unknown = match_result.extras # This is a set

        if debug_mode and debug_tracer_instance: # Log schema matching details
            debug_schema_info = {
                'schema_id': schema_object.name if schema_object else 'None',
                'match_score': match_result.score if hasattr(match_result, 'score') else 'N/A', # If using new schema engine
                'missing_required_in_csv': list(missing_required) if missing_required else [],
                'extra_csv_headers_not_in_schema': list(extra_unknown) if extra_unknown else [],
                'original_csv_headers': list(raw_df.columns)
            }
            log.info(f"[SCHEMA_DEBUG] File: {filename_for_logs} | Details: {json.dumps(debug_schema_info, indent=2)}")
            # Capture raw_df state just after schema identification, before transformations
            debug_tracer_instance.capture_stage("0_SCHEMA_IDENTIFIED_PRE_TRANSFORM", raw_df,
                                                focus_columns=list(raw_df.columns[:5])) # Sample first 5 raw columns

        if schema_object.name == "generic_csv":
            log.warning(
                f"[SCHEMA_RESULT] File: {filename_for_logs} | Selected schema: {schema_object.name} (Fallback) | Reason: Fallback. Missing required: {', '.join(sorted(list(missing_required))) if missing_required else 'None'}, Extra unknown: {', '.join(sorted(list(extra_unknown))) if extra_unknown else 'None'}"
            )
        else:
            log.info(
                f"[SCHEMA_RESULT] File: {filename_for_logs} | Selected schema: {schema_object.name} | Matched with missing: {', '.join(sorted(list(missing_required))) if missing_required else 'None'}, extras: {', '.join(sorted(list(extra_unknown))) if extra_unknown else 'None'}"
            )
        schema_ids_found.append(schema_object.name)

        processed_df = apply_schema_transformations(raw_df, rules_dict, merchant_rules, filename_for_logs, debug_tracer_instance)

        # Ensure OriginalDescription and OriginalMerchant are populated for the cleaner
        # if they are missing but their non-original counterparts (Description, Merchant) exist
        # and likely contain the raw data from source mapping.
        if 'Description' in processed_df.columns and 'OriginalDescription' not in processed_df.columns:
            processed_df['OriginalDescription'] = processed_df['Description']
            log.debug(f"[PROCESS_FILE_PRE_CLEAN] File: {filename_for_logs} | Copied 'Description' to 'OriginalDescription' for cleaner input.")
        elif 'Description' in processed_df.columns and 'OriginalDescription' in processed_df.columns and processed_df['OriginalDescription'].isna().all():
            # If OriginalDescription exists but is all NA, and Description has data, prefer Description's content as raw.
             processed_df['OriginalDescription'] = processed_df['OriginalDescription'].fillna(processed_df['Description'])
             log.debug(f"[PROCESS_FILE_PRE_CLEAN] File: {filename_for_logs} | Filled NA 'OriginalDescription' with 'Description' content for cleaner input.")

        if 'Merchant' in processed_df.columns and 'OriginalMerchant' not in processed_df.columns:
            processed_df['OriginalMerchant'] = processed_df['Merchant']
            log.debug(f"[PROCESS_FILE_PRE_CLEAN] File: {filename_for_logs} | Copied 'Merchant' to 'OriginalMerchant' for cleaner input.")
        elif 'Merchant' in processed_df.columns and 'OriginalMerchant' in processed_df.columns and processed_df['OriginalMerchant'].isna().all():
            processed_df['OriginalMerchant'] = processed_df['OriginalMerchant'].fillna(processed_df['Merchant'])
            log.debug(f"[PROCESS_FILE_PRE_CLEAN] File: {filename_for_logs} | Filled NA 'OriginalMerchant' with 'Merchant' content for cleaner input.")

        # Populate initial metadata fields
        processed_df["Owner"] = owner
        log.debug(f"[PROCESS_FILE_TRANSFORM] File: {filename_for_logs} | Step: Populate Owner | Value: {owner}")
        processed_df["DataSourceDate"] = ds_date
        log.debug(f"[PROCESS_FILE_TRANSFORM] File: {filename_for_logs} | Step: Populate DataSourceDate | Value: {ds_date}")

        # Apply Comprehensive Cleaning (replaces old merchant cleaning)
        if debug_mode and debug_tracer_instance:
            debug_tracer_instance.capture_stage("6_BEFORE_MERCHANT_CLEANING", processed_df,
                                                focus_columns=['Merchant', 'OriginalMerchant', 'Description', 'OriginalDescription'])
        
        if "Merchant" in processed_df.columns and not processed_df.empty:
            pre_clean_blanks = processed_df["Merchant"].isna().sum()
            pre_clean_perc = (pre_clean_blanks / len(processed_df)) * 100 if len(processed_df) > 0 else 0
            log.info(f"[PROCESS_FILE_STATS] File: {filename_for_logs} | Stat: Merchant blanks before clean: {pre_clean_blanks} ({pre_clean_perc:.2f}%)")
        elif not processed_df.empty:
            log.info(f"[PROCESS_FILE_STATS] File: {filename_for_logs} | Stat: Merchant column not present before clean.")
        
        log.info(f"[PROCESS_FILE_TRANSFORM] File: {filename_for_logs} | Step: Applying Comprehensive Cleaning")

        # Initialize the cleaner with your analysis results
        analysis_path = Path('transaction_analysis_results')  # Or 'comprehensive_analysis_results'
        processed_df = apply_comprehensive_cleaning(
            processed_df, 
            analysis_path=analysis_path
        )
        
        if debug_mode and debug_tracer_instance:
            debug_tracer_instance.capture_stage("7_AFTER_MERCHANT_CLEANING", processed_df,
                                                focus_columns=['Merchant', 'OriginalMerchant', 'Description', 'OriginalDescription', 'Category'])


        # Log the improvements
        if "OriginalMerchant" in processed_df.columns:
            log.info(f"[PROCESS_FILE_TRANSFORM] File: {filename_for_logs} | Created OriginalMerchant column")
        if "Description" in processed_df.columns and "OriginalDescription" in processed_df.columns:
            desc_changed = (processed_df["Description"] != processed_df["OriginalDescription"]).sum()
            log.info(f"[PROCESS_FILE_TRANSFORM] File: {filename_for_logs} | Cleaned {desc_changed} descriptions")

        if "Merchant" in processed_df.columns and not processed_df.empty:
            blanks = processed_df["Merchant"].isna().sum()
            percentage_blanks = (blanks / len(processed_df)) * 100 if len(processed_df) > 0 else 0
            log.info(f"[PROCESS_FILE_STATS] File: {filename_for_logs} | Stat: Merchant blanks after clean: {blanks} ({percentage_blanks:.2f}%)")

            # Fallback for Merchant if still largely NA after cleaning
            if blanks > 0 and (blanks / len(processed_df)) > 0.5: # Example threshold: if more than 50% are blank
                log.warning(f"[PROCESS_FILE_WARN] File: {filename_for_logs} | Merchant column has {blanks} NAs after cleaning. Attempting fallback.")
                merchant_na_mask = processed_df["Merchant"].isna()
                if "Description" in processed_df.columns:
                    processed_df.loc[merchant_na_mask, "Merchant"] = processed_df.loc[merchant_na_mask, "Description"]
                    log.info(f"[PROCESS_FILE_TRANSFORM] File: {filename_for_logs} | Merchant Fallback: Used 'Description' for {merchant_na_mask.sum()} NA Merchants.")
                    # Re-check NAs if Description was used
                    merchant_na_mask = processed_df["Merchant"].isna() 
                
                if merchant_na_mask.any() and "OriginalDescription" in processed_df.columns:
                     processed_df.loc[merchant_na_mask, "Merchant"] = processed_df.loc[merchant_na_mask, "OriginalDescription"]
                     log.info(f"[PROCESS_FILE_TRANSFORM] File: {filename_for_logs} | Merchant Fallback: Used 'OriginalDescription' for {merchant_na_mask.sum()} NA Merchants.")
                
                final_blanks_after_fallback = processed_df["Merchant"].isna().sum()
                log.info(f"[PROCESS_FILE_STATS] File: {filename_for_logs} | Stat: Merchant blanks after fallback: {final_blanks_after_fallback}")

        elif processed_df.empty:
            log.info(f"[PROCESS_FILE_STATS] File: {filename_for_logs} | Stat: Merchant blanks after clean: N/A (empty DataFrame)")
        else: # Merchant column not found
            log.info(f"[PROCESS_FILE_STATS] File: {filename_for_logs} | Stat: Merchant column not found after clean, cannot count blanks.")


        # Generate TxnID
        processed_df["TxnID"] = processed_df.apply(_generate_txn_id, axis=1)
        log.debug(f"[PROCESS_FILE_TRANSFORM] File: {filename_for_logs} | Step: TxnID Generation")
        if processed_df["TxnID"].isnull().any():
            log.warning(
                f"[PROCESS_FILE_WARN] File: {filename_for_logs} | Detail: Some TxnIDs are null (this might be due to all hashable fields being empty/NA for a row)."
            )
        
        if debug_mode and debug_tracer_instance:
            debug_tracer_instance.capture_stage("8_AFTER_TXNID_GENERATION", processed_df,
                                                focus_columns=['TxnID', 'Date', 'Amount', 'OriginalDescription', 'Account'])


        # Populate Remaining Master Schema Fields (Defaults)
        log.debug(f"[PROCESS_FILE_TRANSFORM] File: {filename_for_logs} | Step: Populate Default Master Fields (Currency, SharedFlag, etc.)")
        processed_df["Currency"] = "USD"
        if "SharedFlag" not in processed_df.columns:
            processed_df["SharedFlag"] = '?'  # Compatibility: Initialize with '?'
        if "SplitPercent" not in processed_df.columns:
            processed_df["SplitPercent"] = pd.NA  # Compatibility: Initialize with pd.NA

        # Ensure required columns exist based on schema mode
        required_columns = get_required_columns_for_mode()
        cols_added_for_required = []
        
        # In flexible mode, only add core required columns
        # In strict mode, add all master columns as before
        for col in required_columns:
            if col not in processed_df.columns:
                cols_added_for_required.append(col)
                processed_df[col] = pd.NA
                
        if cols_added_for_required:
            if config.SCHEMA_MODE == "flexible":
                log.debug(f"[PROCESS_FILE_TRANSFORM] File: {filename_for_logs} | Step: Ensure Core Columns | Added missing core columns: {cols_added_for_required}")
            else:
                log.debug(f"[PROCESS_FILE_TRANSFORM] File: {filename_for_logs} | Step: Ensure Master Columns | Added missing master columns: {cols_added_for_required}")
        # else: # No need to log if all were present, less noise
            # log.debug(f"[PROCESS_FILE_TRANSFORM] File: {filename_for_logs} | Step: Ensure Master Columns | All master columns already present.")
        
        log.debug(f"[PROCESS_FILE_TRANSFORM] File: {filename_for_logs} | Step: Data Type Coercion for Master Schema")
        dtype_map = {
            "TxnID": str,
            "Owner": str,
            "Date": "datetime64[ns]",
            "PostDate": "datetime64[ns]",
            "OriginalDescription": str,
            "Description": str,
            "OriginalMerchant": str,
            "Merchant": str,
            "Category": str,
            "Amount": float,
            "Tags": str,
            "Institution": str,
            "Account": str,
            "AccountLast4": str,
            "AccountType": str,
            "SharedFlag": bool,
            "SplitPercent": float,
            "StatementStart": "datetime64[ns]",
            "StatementEnd": "datetime64[ns]",
            "StatementPeriodDesc": str,
            "DataSourceName": str,
            "DataSourceDate": "datetime64[ns]",
            "ReferenceNumber": str,
            "Note": str,
            "IgnoredFrom": str,
            "TaxDeductible": bool,
            "CustomName": str,
            "Currency": str,
            "Extras": str,
        }
        for col, dtype_str in dtype_map.items():
            if col in processed_df.columns:
                try:
                    if dtype_str == "datetime64[ns]":
                        processed_df[col] = pd.to_datetime(
                            processed_df[col], errors="coerce"
                        )
                    elif dtype_str == bool:
                        # Handle boolean conversion carefully: map common strings to bool, others to NA
                        # Example: 'true', 'yes', '1' -> True; 'false', 'no', '0' -> False
                        # For simplicity now, direct astype might work if values are already 0/1 or True/False
                        # A more robust approach would be a custom mapping.
                        # Use the new coerce_bool helper
                        processed_df[col] = coerce_bool(processed_df[col])

                    elif dtype_str == float:
                        processed_df[col] = pd.to_numeric(processed_df[col], errors="coerce")
                        if not pd.api.types.is_float_dtype(processed_df[col]):
                            processed_df[col] = processed_df[col].astype(float)
                    else: # str or int
                        if dtype_str == int:
                            processed_df[col] = pd.to_numeric(processed_df[col], errors="coerce").astype("Int64")
                        else: # str
                            processed_df[col] = processed_df[col].astype(str, errors="ignore").fillna(pd.NA)
                            processed_df.loc[processed_df[col].astype(str).str.lower() == "nan", col] = pd.NA
                except Exception as e:
                    log.warning(
                        f"[PROCESS_FILE_WARN] File: {filename_for_logs} | Detail: Could not coerce column '{col}' to type '{dtype_str}': {e}. Column may have mixed types or errors."
                    )

        if config.SCHEMA_MODE == "strict":
            # Preserve original behavior in strict mode
            log.debug(f"[PROCESS_FILE_TRANSFORM] File: {filename_for_logs} | Step: Reindex to Master Schema Columns (Strict Mode)")
            processed_df = processed_df.reindex(
                columns=MASTER_SCHEMA_COLUMNS,
                fill_value=None,
            )
        else:
            # In flexible mode, only reorder to ensure consistent column order
            # but don't add columns that don't exist
            columns_to_retain = get_columns_to_retain(processed_df)
            existing_columns = [col for col in columns_to_retain if col in processed_df.columns]
            
            # Also include any columns not in our predefined lists (like derived columns)
            extra_columns = [col for col in processed_df.columns if col not in columns_to_retain]
            
            final_column_order = existing_columns + extra_columns
            processed_df = processed_df[final_column_order]
            
            log.debug(f"[PROCESS_FILE_TRANSFORM] File: {filename_for_logs} | Step: Reorder Columns (Flexible Mode) | Retained {len(final_column_order)} columns")

        all_processed_dfs.append(processed_df)
        
        # Save the debug report for the current file if a tracer exists
        if debug_tracer_instance:
            debug_tracer_instance.save_report()
            
        log.info(f"[PROCESS_FILE_END] File: {filename_for_logs} | Status: Success | Rows processed: {len(processed_df)}")

    if not all_processed_dfs:
        log.warning("[PROCESS_SUMMARY] No CSV files were processed successfully. Returning an empty DataFrame.")
        log.info(f"[PROCESS_SUMMARY] Schema matching counts: {Counter(schema_ids_found)}")
        return pd.DataFrame(columns=MASTER_SCHEMA_COLUMNS)

    log.info(f"[PROCESS_SUMMARY] Schema matching counts: {Counter(schema_ids_found)}")
    final_df = pd.concat(all_processed_dfs, ignore_index=True)
    log.info(f"[PROCESS_SUMMARY] Consolidated {len(all_processed_dfs)} CSV files into DataFrame with {len(final_df)} total rows.")

    if not final_df.empty and "Merchant" in final_df.columns:
        total_merchant_blanks = final_df["Merchant"].isna().sum()
        total_percentage_blanks = (total_merchant_blanks / len(final_df)) * 100 if len(final_df) > 0 else 0
        log.info(f"[PROCESS_SUMMARY_STATS] Total merchant blanks in final_df: {total_merchant_blanks} ({total_percentage_blanks:.2f}%)")
    elif final_df.empty:
        log.info("[PROCESS_SUMMARY_STATS] Total merchant blanks in final_df: N/A (final DataFrame is empty)")
    else: # Merchant column not found
        log.info("[PROCESS_SUMMARY_STATS] Merchant column not found in final_df, cannot count total blanks.")

    log.debug("[PROCESS_SUMMARY] Sorting final DataFrame.")
    final_df = final_df.sort_values(
        by=["Date", "Owner", "Amount"],
        ascending=[True, True, True],
        na_position="first",
    )

    # Capture final_df state before sharing_status derivation (tied to last file's tracer)
    if debug_mode and debug_tracer_instance and not final_df.empty:
        debug_tracer_instance.capture_stage("FINAL_DF_PRE_SHARING_STATUS", final_df,
                                            focus_columns=['Date', 'Amount', 'Merchant', 'SharedFlag', 'SplitPercent', 'Owner'])

    # Derive 'sharing_status' column
    log.info(f"[PROCESS_SUMMARY] Creating sharing_status for {len(final_df)} rows")
    
    if debug_mode: # Check debug_mode, not debug_tracer_instance as it's per-file
        # These logs are for the final_df, so they run once after concat
        if 'SharedFlag' in final_df.columns:
            log.info(f"[SHARING_DEBUG] Final DF SharedFlag dtype: {final_df['SharedFlag'].dtype}")
            log.info(f"[SHARING_DEBUG] Final DF SharedFlag unique values: {final_df['SharedFlag'].unique() if not final_df['SharedFlag'].empty else 'Column is empty'}")
        else:
            log.info("[SHARING_DEBUG] Final DF SharedFlag column missing.")
        if 'SplitPercent' in final_df.columns:
            log.info(f"[SHARING_DEBUG] Final DF SplitPercent dtype: {final_df['SplitPercent'].dtype}")
            log.info(f"[SHARING_DEBUG] Final DF SplitPercent unique values (sample): {final_df['SplitPercent'].dropna().unique()[:5] if final_df['SplitPercent'].notna().any() else 'All NA or empty'}")
        else:
            log.info("[SHARING_DEBUG] Final DF SplitPercent column missing.")

    # Ensure SharedFlag and SplitPercent columns exist, creating them as NA-filled if not.
    if 'SharedFlag' not in final_df.columns:
        final_df['SharedFlag'] = pd.Series(pd.NA, index=final_df.index, dtype=pd.BooleanDtype())
        log.warning("[PROCESS_SUMMARY_WARN] 'SharedFlag' column was missing. Added as all NA for 'sharing_status' derivation.")
    else:
        # Ensure it's BooleanDtype if it exists
        if not isinstance(final_df['SharedFlag'].dtype, pd.BooleanDtype):
            log.info(f"[PROCESS_SUMMARY_DETAIL] Coercing 'SharedFlag' (dtype: {final_df['SharedFlag'].dtype}) to BooleanDtype for sharing_status derivation.")
            final_df['SharedFlag'] = coerce_bool(final_df['SharedFlag'])

    if 'SplitPercent' not in final_df.columns:
        final_df['SplitPercent'] = pd.Series(pd.NA, index=final_df.index, dtype=pd.Float64Dtype()) # Use nullable float type
        log.warning("[PROCESS_SUMMARY_WARN] 'SplitPercent' column was missing. Added as all NA for 'sharing_status' derivation.")
    else:
        # Ensure SplitPercent is numeric
        final_df['SplitPercent'] = pd.to_numeric(final_df['SplitPercent'], errors='coerce')

    # These logs were moved up to be conditional on debug_mode for the final_df
    # log.debug(f"[PROCESS_SUMMARY_DETAIL] SharedFlag distribution before sharing_status: {final_df['SharedFlag'].value_counts(dropna=False).to_dict()}")
    # log.debug(f"[PROCESS_SUMMARY_DETAIL] SplitPercent non-null count before sharing_status: {final_df['SplitPercent'].notna().sum()}, unique values (sample): {final_df['SplitPercent'].dropna().unique()[:5]}")

    # Define conditions for np.select, handling pd.NA from BooleanDtype comparisons
    # .fillna(False) ensures that NA in SharedFlag doesn't satisfy the condition
    
    # Condition for 'split': SharedFlag is True AND SplitPercent is between 0 and 100 (exclusive)
    cond_split = (
        final_df['SharedFlag'].eq(True).fillna(False) &
        final_df['SplitPercent'].notna() &
        (final_df['SplitPercent'] > 0) &
        (final_df['SplitPercent'] < 100)
    )
    
    # Condition for 'shared': SharedFlag is True (and it's not a 'split' case)
    # This will be evaluated after cond_split.
    cond_shared = final_df['SharedFlag'].eq(True).fillna(False)
    
    # Condition for 'individual': SharedFlag is False
    cond_individual = final_df['SharedFlag'].eq(False).fillna(False)

    conditions = [
        cond_split,
        cond_shared,
        cond_individual
    ]
    choices = ['split', 'shared', 'individual']
    
    # Fixed: Convert pd.NA to None for np.select compatibility
    final_df['sharing_status'] = pd.Series(
        np.select(conditions, choices, default='pending'),  # Changed default to string 'pending'
        dtype=pd.StringDtype(),  # Ensures nullable string type
        index=final_df.index
    )
    
    status_counts = final_df['sharing_status'].value_counts(dropna=False)
    log.debug(f"[PROCESS_SUMMARY_STATS] 'sharing_status' counts: {status_counts.to_dict()}")

    # Capture final_df state after sharing_status derivation (tied to last file's tracer)
    if debug_mode and debug_tracer_instance and 'sharing_status' in final_df.columns and not final_df.empty:
        debug_tracer_instance.capture_stage("FINAL_DF_POST_SHARING_STATUS", final_df,
                                            focus_columns=['Date', 'Amount', 'Merchant', 'sharing_status', 'SharedFlag', 'SplitPercent', 'Owner'])
    
    if debug_mode and debug_tracer_instance: # This debug_tracer_instance is from the last file processed.
                                           # For a global final_df trace, we'd need a different mechanism or log outside loop.
                                           # For now, this will capture the state of the last file's contribution to final_df if needed.
                                           # A better approach for final_df is to log its state directly if debug_mode is on.
        pass # Placeholder - a "FINAL_DF_OVERALL" capture would be complex here.
             # Instead, we rely on the per-file "FINAL_DF_PER_FILE" and direct logs for final_df.

    # Ensure all columns have explicit, non-null data types for Power BI compatibility
    # This prevents PyArrow from writing columns as null type when all values are NA
    # and makes the data compatible with Power BI's stricter requirements.
    log.info("[PROCESS_SUMMARY] Applying defensive data type management for Power BI compatibility.")
    for col in MASTER_SCHEMA_COLUMNS:
        if col in final_df.columns: # Check if column exists in final_df
            is_boolean_col = pd.api.types.is_bool_dtype(final_df[col])

            if final_df[col].isna().all():
                if not is_boolean_col: # If it's all NA AND NOT boolean, then set to empty string
                    final_df[col] = ''
                    log.debug(f"Set all-NA non-boolean column '{col}' to empty strings")
                # else: If it IS boolean and all NA, do nothing. It remains BooleanDtype with pd.NA values,
                # which is correctly handled by PyArrow and Power BI.
            elif not is_numeric_dtype(final_df[col]) and not is_boolean_col: # If not numeric AND NOT boolean
                # Cast to string to ensure clear typing for other non-numeric/non-boolean columns.
                final_df[col] = final_df[col].astype(str)
                log.debug(f"Cast non-numeric, non-boolean column '{col}' to string type")
        else:
            log.warning(f"[PROCESS_SUMMARY_WARN] Column '{col}' from MASTER_SCHEMA_COLUMNS not found in final_df during defensive typing. Skipping.")

# MODIFICATION 3: Final DataFrame Processing (around line 1245)
# Replace the defensive typing section with schema-aware logic:

    # At the end of process_csv_files(), before returning final_df:
    
    log.info("[PROCESS_SUMMARY] Applying defensive data type management for Power BI compatibility.")
    
    if config.SCHEMA_MODE == "strict":
        # Original behavior - process all MASTER_SCHEMA_COLUMNS
        for col in MASTER_SCHEMA_COLUMNS:
            if col in final_df.columns:
                is_boolean_col = pd.api.types.is_bool_dtype(final_df[col])

                if final_df[col].isna().all():
                    if not is_boolean_col:
                        final_df[col] = ''
                        log.debug(f"Set all-NA non-boolean column '{col}' to empty strings")
                elif not is_numeric_dtype(final_df[col]) and not is_boolean_col:
                    final_df[col] = final_df[col].astype(str)
                    log.debug(f"Cast non-numeric, non-boolean column '{col}' to string type")
    else:
        # Flexible mode - remove entirely empty columns before type management
        log.info("[PROCESS_SUMMARY] Flexible mode: Removing empty columns before final output")
        
        # First, ensure data types for columns we're keeping
        for col in final_df.columns:
            if col in config.CORE_REQUIRED_COLUMNS or not final_df[col].isna().all():
                is_boolean_col = pd.api.types.is_bool_dtype(final_df[col])
                
                if final_df[col].isna().all() and not is_boolean_col:
                    final_df[col] = ''
                elif not is_numeric_dtype(final_df[col]) and not is_boolean_col:
                    final_df[col] = final_df[col].astype(str)
        
        # Then remove empty columns (except core required ones)
        final_df = remove_empty_columns(final_df, preserve_columns=config.CORE_REQUIRED_COLUMNS)
        
        log.info(f"[PROCESS_SUMMARY] Final DataFrame in flexible mode has {len(final_df.columns)} columns: {list(final_df.columns)}")

    # If debug_mode was on for any file, the debug_tracer_instance for the *last* file processed
    # will call save_report(). This is okay for now, as each report is per-file.
    # A summary report for final_df could be added if needed.
    if debug_mode: # General check if debug mode was active for the run
        log.info("[PROCESS_SUMMARY] Debug mode was active. Individual file reports may have been saved to 'debug_reports/'.")
        # Example: Capture final_df state if debug_mode is on (simplified)
        if not final_df.empty:
            log.debug(f"[DEBUG_FINAL_DF_SUMMARY] Final DF rows: {len(final_df)}, cols: {len(final_df.columns)}")
            log.debug(f"[DEBUG_FINAL_DF_SUMMARY] Final DF Columns: {list(final_df.columns)}")
            log.debug(f"[DEBUG_FINAL_DF_SUMMARY] Final DF Head:\n{final_df.head().to_string()}")


    return final_df


def load_and_parse_schema_registry(
    yaml_path: Path,
) -> Dict[str, Any]:  # Updated type hint
    """Loads and parses the schema_registry.yml file."""
    log.info(f"Loading schema registry from: {yaml_path}")
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            registry = yaml.safe_load(f)
        if not isinstance(registry, list):  # Expecting a list of schema dicts
            log.error(
                f"Schema registry at {yaml_path} is not a list. Found type: {type(registry)}"
            )
            raise ValueError("Schema registry must be a list of schema definitions.")
        log.info(f"Successfully loaded {len(registry)} schema definitions.")
        return {"schemas": registry}  # Wrap in a dict for easier access if needed
    except FileNotFoundError:
        log.error(f"Schema registry file not found: {yaml_path}")
        raise
    except yaml.YAMLError as e:
        log.error(f"Error parsing YAML from {yaml_path}: {e}")
        raise
    except Exception as e:
        log.error(
            f"An unexpected error occurred while loading schema registry {yaml_path}: {e}"
        )
        raise


def load_merchant_lookup_rules(csv_path: Path) -> List[Tuple[re.Pattern[str], str]]:
    """
    Loads merchant cleaning rules from the merchant_lookup.csv file.
    Similar to _load_merchant_lookup in normalize.py but adapted for this module.
    """
    log.info(f"Loading merchant lookup rules from: {csv_path}")
    rules: List[Tuple[re.Pattern[str], str]] = []  # Updated type hint
    try:
        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = pd.read_csv(f)  # Using pandas to read CSV for simplicity here
            if list(reader.columns) != ["pattern", "canonical"]:
                err_msg = (
                    f"Invalid header in {csv_path}. "
                    f"Expected ['pattern', 'canonical'], got {list(reader.columns)}"
                )
                log.error(err_msg)
                raise ValueError(err_msg)

            for index, row in reader.iterrows():
                pattern_str, canonical_name = row["pattern"], row["canonical"]
                if not isinstance(pattern_str, str) or not isinstance(
                    canonical_name, str
                ):
                    log.warning(
                        f"Skipping row {str(int(cast(Any, index)) + 2)} in {csv_path} due to invalid data types: {row.to_dict()}"  # str(int(cast(Any, index)) + 2)
                    )
                    continue
                try:
                    compiled_regex: re.Pattern[str] = re.compile(
                        pattern_str, re.IGNORECASE
                    )  # Added type hint
                    rules.append((compiled_regex, canonical_name))
                except re.error as e:
                    err_msg = (
                        f"Invalid regex pattern in {csv_path} at row {str(int(cast(Any, index)) + 2)}: "  # str(int(cast(Any, index)) + 2)
                        f"'{pattern_str}'. Error: {e}"
                    )
                    log.error(err_msg)
                    raise ValueError(err_msg) from e
        log.info(
            f"Successfully loaded and compiled {len(rules)} merchant lookup rules from {csv_path}."
        )
    except FileNotFoundError:
        log.error(
            f"Merchant lookup file not found: {csv_path}. Proceeding without custom merchant rules."
        )
        # Return empty list, merchant cleaning will rely on fallback.
    except ValueError as e:  # Catch ValueErrors from header/regex checks
        log.error(f"ValueError during merchant lookup loading: {e}")
        raise
    except Exception as e:
        log.error(
            f"Unexpected error loading merchant lookup {csv_path}: {e}", exc_info=True
        )
        # Fallback to empty list on other errors
    return rules


if __name__ == "__main__":
    # This section can be used for basic testing of the module if run directly.
    # For example, to test loading configurations.
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
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
