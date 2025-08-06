"""
==============================================================================
Module: normalize.py
Project: BALANCE-pyexcel
Description: Handles the normalization and final preparation of the combined
             transaction DataFrame received from the ingest module. Key tasks
             include cleaning text descriptions, generating a unique and
             deterministic transaction ID (TxnID), setting default flags,
             and ensuring the output DataFrame has a consistent set of columns
             in the correct order.
==============================================================================

Version: 0.1.1 # Updated version reflecting changes
Last Modified: 2025-04-21 # Placeholder date
Author: Your Name / AI Assistant
"""

# ==============================================================================
# 0. IMPORTS
# ==============================================================================
import csv  # For reading merchant lookup CSV
import hashlib  # For generating hashes for TxnID
import logging  # For logging messages
import re  # Added for regex operations
from pathlib import Path  # Ensure Path is imported
from typing import Any  # Added for type hint

import pandas as pd
from balance_pipeline.errors import (
    DataConsistencyError,
    FatalSchemaError,
    RecoverableFileError,
)

from . import config  # Import config module

# Local application imports
from .utils import _clean_desc_single, clean_desc_vectorized  # Updated import

# ==============================================================================
# 1. MODULE LEVEL SETUP & CONSTANTS
# ==============================================================================

# --- Setup Logger ---
# Get a logger specific to this module for targeted logging.
log = logging.getLogger(__name__)

# --- Merchant Lookup Path (configurable for testing) ---
MERCHANT_LOOKUP_PATH: Path = config.MERCHANT_LOOKUP_PATH

# --- Merchant Lookup Cache ---
_merchant_lookup_data: list[tuple[re.Pattern[str], str]] | None = None


def reset_merchant_lookup_cache(new_path: Path | None = None) -> None:
    """
    Resets the merchant lookup cache and optionally sets a new lookup file path.
    This function is primarily intended for testing purposes to allow for
    isolated test runs with different merchant rule sets.
    """
    global _merchant_lookup_data, MERCHANT_LOOKUP_PATH
    _merchant_lookup_data = None  # Clear the cache

    if new_path is not None and isinstance(new_path, Path):
        MERCHANT_LOOKUP_PATH = new_path
        log.info(f"Merchant lookup path set to: {MERCHANT_LOOKUP_PATH}")
    elif new_path is not None: # If new_path is provided but not a Path object
        log.warning(f"Invalid new_path provided to reset_merchant_lookup_cache: {new_path}. Path not changed.")

    # Attempt to reload the rules with the current (possibly new) path
    try:
        _load_merchant_lookup()
    except (ValueError, FatalSchemaError) as ve: # More specific catch for re-raising
        log.error(
            f"Error ({type(ve).__name__}) in merchant lookup file at {MERCHANT_LOOKUP_PATH} during cache reset: {ve}"
        )
        _merchant_lookup_data = [] # Ensure fallback for other parts of the system if test doesn't halt
        raise # Re-raise ValueError or FatalSchemaError to allow tests to catch it
    except RecoverableFileError:
        log.warning(
            f"Merchant lookup file not found at {MERCHANT_LOOKUP_PATH} during cache reset. Cache remains empty."
        )
        _merchant_lookup_data = [] # Ensure fallback to empty list
    except Exception as e: # Catch other, truly unexpected exceptions
        log.error(f"Unexpected generic error during merchant lookup cache reset: {e}", exc_info=True)
        _merchant_lookup_data = [] # Ensure fallback to empty list


def _load_merchant_lookup() -> list[tuple[re.Pattern[str], str]]:
    """
    Loads merchant cleaning rules from a CSV file.
    Validates regex patterns at load time.
    Caches the loaded rules.
    """
    global _merchant_lookup_data, MERCHANT_LOOKUP_PATH # Ensure MERCHANT_LOOKUP_PATH is global here
    if _merchant_lookup_data is not None:
        return _merchant_lookup_data

    loaded_rules = []
    try:
        # Ensure MERCHANT_LOOKUP_PATH is a Path object for `open`
        current_lookup_path = Path(MERCHANT_LOOKUP_PATH)
        with open(current_lookup_path, encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)  # Skip header row
            if header != ["pattern", "canonical"]:
                raise FatalSchemaError(
                    f"Invalid header in merchant lookup file: {current_lookup_path}. Expected ['pattern', 'canonical'], got {header}"
                )

            for i, row in enumerate(
                reader, start=2
            ):  # start=2 for 1-based indexing + header
                if not row or len(row) != 2:
                    log.warning(
                        f"Skipping malformed row {i} in {current_lookup_path}: {row}"
                    )
                    continue
                pattern_str, canonical_name = row
                try:
                    compiled_regex = re.compile(pattern_str, re.IGNORECASE)
                    loaded_rules.append((compiled_regex, canonical_name))
                except re.error as e:
                    err_msg = (
                        f"Invalid regex pattern found in {current_lookup_path} at row {i}: "
                        f"'{pattern_str}'. Error: {e}"
                    )
                    log.error(err_msg)
                    raise ValueError(err_msg) from e # This ValueError will be caught by the initial load block
        _merchant_lookup_data = loaded_rules
        log.info(
            f"Successfully loaded and compiled {len(_merchant_lookup_data)} merchant lookup rules from {current_lookup_path}."
        )
    except FileNotFoundError: # Specific exception for file not found
        log.error(
            f"Merchant lookup file not found: {current_lookup_path}. Merchant cleaning will use fallback logic."
        )
        _merchant_lookup_data = [] # Set to empty list to allow fallback
    except FatalSchemaError as e: # Catch specific schema error for header
        log.critical(f"Fatal schema error in merchant lookup file: {e}")
        _merchant_lookup_data = [] # Fallback on critical error
        raise # Re-raise to be caught by initial load block if desired, or handled by caller
    except ValueError as e:  # Catch ValueErrors from regex compilation
        log.critical(f"Invalid data in merchant lookup file: {e}")
        _merchant_lookup_data = [] # Fallback on critical error
        raise # Re-raise to be caught by initial load block
    except Exception as e: # Catch any other unexpected errors during file processing
        log.error(
            f"Unexpected error loading merchant lookup file {current_lookup_path}: {e}", exc_info=True
        )
        _merchant_lookup_data = [] # Fallback on unexpected error
        # Do not re-raise generic Exception here, allow fallback

    return _merchant_lookup_data


# Attempt to load rules at import time.
# If RecoverableFileError (e.g., file not found) or other non-critical errors occur,
# _merchant_lookup_data will be set to [] by _load_merchant_lookup, allowing fallback.
# Critical errors like ValueError (bad regex/header) will be re-raised by _load_merchant_lookup
# and then caught here to stop the application.
try:
    _load_merchant_lookup()
except ValueError: # Catches re-raised ValueError for bad regex or FatalSchemaError for bad header
    log.critical(
        "Failed to initialize merchant lookup due to invalid regex or CSV format. Application may not function as expected."
    )
    # Depending on desired behavior, you might re-raise to stop the app,
    # or allow it to continue with _merchant_lookup_data as [] (fallback mode).
    # For now, let's allow fallback, as _load_merchant_lookup already sets _merchant_lookup_data = []
    # raise # Uncomment to make these errors fatal at startup
except Exception as e: # Catch any other unexpected error during initial load
    log.critical(f"Unexpected critical error during initial merchant lookup load: {e}", exc_info=True)
    _merchant_lookup_data = [] # Ensure fallback


def clean_merchant(description: str) -> str:
    """
    Cleans the merchant description using rules from merchant_lookup.csv.
    Falls back to a generic cleaning if no rule matches.
    """
    if not isinstance(description, str):
        raise DataConsistencyError(
            f"Expected merchant description as string, got {type(description)}"
        )

    rules = _load_merchant_lookup()  # Get cached/loaded rules

    for pattern, canonical_name in rules:
        match = pattern.search(description)
        if match:
            return canonical_name  # Return the canonical name from the CSV

    # Fallback if no pattern matched: apply _clean_desc_single and title-case
    cleaned_desc = _clean_desc_single(description)
    return cleaned_desc.title()


# --- Constants ---

# Columns used to generate the deterministic Transaction ID (TxnID).
# IMPORTANT: These columns MUST exist and be stable *before* normalization steps
#            within normalize_df might alter them (e.g., cleaning description).
#            Now includes 'Bank' and 'Source' to handle deduplication of aggregator data.
# REVIEW: Confirm these columns are reliably populated by the updated ingest.py
_ID_COLS_FOR_HASH = [  # Changed back to list to fix concatenation error in logging
    "Date",
    "PostDate",  # NEW
    "Amount",
    "Description",
    "Bank",
    "Account",
]

# Defines the exact list and order of columns for the final output DataFrame.
# This ensures consistency regardless of intermediate processing steps.
# Added 'Bank', 'Source', 'Category', 'SplitPercent', and 'CanonMerchant'.
FINAL_COLS = [
    "TxnID",
    "Owner",
    "Date",
    "Account",
    "Bank",
    "Description",
    "CleanDesc",
    "CanonMerchant",
    "Category",  # Added CanonMerchant
    "Amount",
    "SharedFlag",
    "SplitPercent",
    "Source",
]

# ==============================================================================
# 2. HELPER FUNCTIONS (Internal Use Only)
# ==============================================================================

# _strip_accents and _clean_desc moved to utils.py


# ------------------------------------------------------------------------------
# Function: _txn_id
# ------------------------------------------------------------------------------
def _txn_id(row: dict[str, Any]) -> str:  # Changed input type to dict for apply lambda
    """Stable 16-char hex id using MD5."""
    # Extract values based on _ID_COLS_FOR_HASH, convert to string, strip whitespace, handle missing keys
    # Source is not included in TxnID hash components to allow for cross-source deduplication.
    # Deduplication logic will use the 'Source' column and 'prefer_source' to pick the record to keep.
    base_parts = [str(row.get(col, "")).strip() for col in _ID_COLS_FOR_HASH]
    # Join parts with a separator
    hash_input = "|".join(base_parts)
    # Encode to bytes, generate MD5 hash, get hex digest, truncate
    return hashlib.md5(hash_input.encode("utf-8")).hexdigest()[:16]


# ==============================================================================
# 3. PUBLIC API FUNCTION
# ==============================================================================


# ------------------------------------------------------------------------------
# Function: normalize_df
# ------------------------------------------------------------------------------
def normalize_df(df: pd.DataFrame, prefer_source: str = "Rocket") -> pd.DataFrame:
    """
    Normalizes the ingested DataFrame after initial processing by ingest.py.

    This function focuses on:
    - Cleaning the description text (`CleanDesc`).
    - Generating the unique transaction ID (`TxnID`).
    - Adding default flags (`SharedFlag`).
    - Ensuring the final set of standard columns (`FINAL_COLS`) exists and
      is correctly ordered.
    - Sorting the DataFrame by Date.

    Args:
        df (pd.DataFrame): The DataFrame produced by `ingest.load_folder`,
                           expected to contain columns like 'Owner', 'Date', 'Amount',
                           'Description', 'Account', 'Category'.

    Returns:
        pd.DataFrame: The normalized DataFrame ready for further analysis or display,
                      containing columns specified in FINAL_COLS.
    """
    # --- Handle Empty Input ---
    if df.empty:
        log.warning(
            "Input DataFrame to normalize_df is empty. Returning empty DataFrame."
        )
        # Return empty DataFrame with the expected final columns.
        return pd.DataFrame(columns=FINAL_COLS)

    log.info(f"Normalizing {len(df)} rows (Phase 2 - TxnID, Cleaning, Final Cols)...")
    # Work on a copy to avoid modifying the original DataFrame passed in.
    out = df.copy()

    # --- Clean Description (Vectorized) ---
    if "Description" in out.columns:
        out["CleanDesc"] = clean_desc_vectorized(out["Description"])
        log.info("Generated 'CleanDesc' column using vectorized approach.")
        # --- Generate Canonical Merchant Name (still uses apply due to regex iteration) ---
        out["CanonMerchant"] = out["Description"].apply(clean_merchant)
        log.info("Generated 'CanonMerchant' column using regex cleaning rules (apply).")
    else:
        log.warning(
            "'Description' column not found. Adding empty 'CleanDesc' and 'CanonMerchant' columns."
        )
        out["CleanDesc"] = pd.Series(
            dtype="object"
        )  # Ensure correct dtype for empty series
        out["CanonMerchant"] = pd.Series(dtype="object")

    # --- Fallback for missing PostDate ---
    # If PostDate is missing or all null after ingest/mapping, use Date as fallback for hash stability
    if "PostDate" not in out.columns or out["PostDate"].isna().all():
        if "Date" in out.columns:
            log.warning(
                "PostDate column missing or all null. Using Date column as fallback for TxnID generation."
            )
            out["PostDate"] = out["Date"]
        else:
            log.error(
                "PostDate column missing and Date column also missing. Cannot create PostDate fallback."
            )
            # Allow TxnID generation to fail below if Date is also in _ID_COLS_FOR_HASH

    # --- Generate Transaction ID ---
    # Check if all columns needed for hashing are present.
    missing_id_cols = [col for col in _ID_COLS_FOR_HASH if col not in out.columns]
    if missing_id_cols:
        log.error(
            f"Cannot generate TxnID. Missing required ID columns: {missing_id_cols}. Adding 'TxnID' as None."
        )
        out["TxnID"] = None
    else:
        log.info(f"Generating TxnID using base columns: {_ID_COLS_FOR_HASH}")
        # Vectorized approach for TxnID generation

        # Prepare components for hashing
        hash_components = []
        for col in _ID_COLS_FOR_HASH:  # Use the original _ID_COLS_FOR_HASH
            hash_components.append(out[col].astype(str).str.strip())

        # Base hash input: join components with '|'
        hash_input_series = pd.Series(
            ["|".join(elements) for elements in zip(*hash_components, strict=False)], index=out.index
        )

        # Apply MD5 hashing
        # This part still uses .apply, but operates on already constructed strings
        try:
            out["TxnID"] = hash_input_series.apply(
                lambda x: hashlib.md5(x.encode("utf-8")).hexdigest()[:16]
            )
            log.info(
                "Generated 'TxnID' column using vectorized string operations and apply for hash."
            )
        except Exception as e:
            log.error(
                f"Error generating TxnID with vectorized approach: {e}", exc_info=True
            )
            out["TxnID"] = None

        # --- Validate TxnID ---
        if out["TxnID"].isnull().any():
            log.warning("Some TxnIDs could not be generated (returned None).")
        if (
            out["TxnID"].notna().any()
            and not out.loc[out["TxnID"].notna(), "TxnID"].is_unique
        ):
            duplicates = out[
                out.duplicated(subset=["TxnID"], keep=False) & out["TxnID"].notna()
            ]
            log.warning(
                f"TxnID collision detected! {len(duplicates)} rows affected. "
                f"This is expected if the same transaction appears in multiple sources (e.g., Monarch/Rocket) "
                f"before deduplication. Review columns used if unexpected. "
                f"Duplicate examples:\n{duplicates[['TxnID'] + _ID_COLS_FOR_HASH].head()}"
            )

    # --- Add Default Shared Flag ---
    # Initialize the 'SharedFlag' column with '?' indicating it needs review.
    # This column will be updated later by classification rules or manual tagging.
    out["SharedFlag"] = "?"
    log.info("Added default 'SharedFlag' column.")

    # Initialize 'SplitPercent' with NA (null) as it's populated during sync.
    out["SplitPercent"] = pd.NA
    log.info("Added default 'SplitPercent' column with NA.")

    # --- Final Column Selection and Sorting ---
    log.info(f"Selecting and ordering final columns: {FINAL_COLS}")
    # Ensure all columns listed in FINAL_COLS exist in the DataFrame.
    # Add any missing columns and fill them with NA (Pandas' null value).
    for col in FINAL_COLS:
        if col not in out.columns:
            log.warning(
                f"Final column '{col}' was not generated. Adding column with NA values."
            )
            out[col] = pd.NA

    # Select only the columns specified in FINAL_COLS and in that specific order.
    # Sort the entire DataFrame by 'Date' ascending. Put rows with invalid/missing dates first.
    out = out[FINAL_COLS].sort_values("Date", ascending=True, na_position="first")

    # --- Deduplication for aggregator sources (Rocket Money and Monarch) ---
    # Drop duplicate rows based on TxnID - these would be the same transaction appearing in
    # multiple aggregator sources
    initial_row_count = len(out)

    if (
        "Source" in out.columns
        and "TxnID" in out.columns
        and out["TxnID"].notna().any()
    ):
        # Create a temporary sort key column for deduplication
        # Lower number means higher priority (0 for preferred, 1 for others, 2 for NA Source)
        out["_sort_key_for_dedupe"] = 2  # Default for NA or non-matching
        out.loc[out["Source"] == prefer_source, "_sort_key_for_dedupe"] = 0
        out.loc[
            (out["Source"] != prefer_source) & pd.notna(out["Source"]),
            "_sort_key_for_dedupe",
        ] = 1

        # Sort by TxnID and the deduplication key.
        # The original index is not a valid column name for sorting here.
        # Stability of sort (for items with same TxnID and _sort_key_for_dedupe)
        # will preserve original relative order if mergesort (default for multiple keys) is used.
        out = out.sort_values(by=["TxnID", "_sort_key_for_dedupe"], kind="mergesort")

        num_duplicates_before = out.duplicated(subset=["TxnID"], keep=False).sum()
        if num_duplicates_before > 0:
            log.info(
                f"Found {num_duplicates_before} potential duplicate entries based on TxnID before deduplication by preferred source ('{prefer_source}')."
            )

        out = out.drop_duplicates(subset=["TxnID"], keep="first")
        out = out.drop(columns=["_sort_key_for_dedupe"])  # Remove temporary sort key

        num_removed = initial_row_count - len(out)
        if num_removed > 0:
            log.info(
                f"Removed {num_removed} duplicate transactions from aggregator sources, prioritizing '{prefer_source}'."
            )
    else:
        log.info(
            "Skipping source-based deduplication: 'Source' or 'TxnID' column missing, or no TxnIDs generated."
        )

    log.info("Normalization complete. Returning %s rows.", len(out))
    return out


# ==============================================================================
# END OF FILE: normalize.py
# ==============================================================================
