# -*- coding: utf-8 -*-
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
import pandas as pd
import hashlib             # For generating hashes for TxnID
import logging             # For logging messages
from typing import Any, List, Tuple, Optional     # Added for type hint
import re                  # Added for regex operations
import csv                 # For reading merchant lookup CSV

# Local application imports
from .utils import _clean_desc           # Import cleaning function from utils
from .config import MERCHANT_LOOKUP_PATH # Import merchant lookup file path

# ==============================================================================
# 1. MODULE LEVEL SETUP & CONSTANTS
# ==============================================================================

# --- Setup Logger ---
# Get a logger specific to this module for targeted logging.
log = logging.getLogger(__name__)

# --- Merchant Lookup Cache ---
_merchant_lookup_data: Optional[List[Tuple[re.Pattern, str]]] = None

def _load_merchant_lookup() -> List[Tuple[re.Pattern, str]]:
    """
    Loads merchant cleaning rules from a CSV file.
    Validates regex patterns at load time.
    Caches the loaded rules.
    """
    global _merchant_lookup_data
    if _merchant_lookup_data is not None:
        return _merchant_lookup_data

    loaded_rules = []
    try:
        with open(MERCHANT_LOOKUP_PATH, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader) # Skip header row
            if header != ['pattern', 'canonical']:
                log.error(
                    f"Invalid header in {MERCHANT_LOOKUP_PATH}. "
                    f"Expected ['pattern', 'canonical'], got {header}"
                )
                raise ValueError(f"Invalid header in merchant lookup file: {MERCHANT_LOOKUP_PATH}")

            for i, row in enumerate(reader, start=2): # start=2 for 1-based indexing + header
                if not row or len(row) != 2:
                    log.warning(f"Skipping malformed row {i} in {MERCHANT_LOOKUP_PATH}: {row}")
                    continue
                pattern_str, canonical_name = row
                try:
                    compiled_regex = re.compile(pattern_str, re.IGNORECASE)
                    loaded_rules.append((compiled_regex, canonical_name))
                except re.error as e:
                    err_msg = (
                        f"Invalid regex pattern found in {MERCHANT_LOOKUP_PATH} at row {i}: "
                        f"'{pattern_str}'. Error: {e}"
                    )
                    log.error(err_msg)
                    raise ValueError(err_msg) from e
        _merchant_lookup_data = loaded_rules
        log.info(f"Successfully loaded and compiled {len(_merchant_lookup_data)} merchant lookup rules from {MERCHANT_LOOKUP_PATH}.")
    except FileNotFoundError:
        log.error(f"Merchant lookup file not found: {MERCHANT_LOOKUP_PATH}. Proceeding without merchant cleaning rules.")
        _merchant_lookup_data = [] # Ensure it's an empty list so subsequent calls don't try to reload
    except Exception as e: # Catch other potential errors like permission issues
        log.error(f"Failed to load merchant lookup file {MERCHANT_LOOKUP_PATH}: {e}")
        # Raise the error to halt execution if loading fails critically,
        # unless it's a FileNotFoundError which is handled by returning empty rules.
        if not isinstance(e, ValueError): # ValueError is already specific
             raise RuntimeError(f"Critical error loading merchant lookup from {MERCHANT_LOOKUP_PATH}: {e}") from e
        _merchant_lookup_data = [] # Fallback to empty list on other errors too

    return _merchant_lookup_data

# Attempt to load rules at import time to fail fast if there are errors
try:
    _load_merchant_lookup()
except ValueError:
    # ValueError is raised by _load_merchant_lookup for bad regex or header.
    # This ensures the application fails at startup if the rules are invalid.
    log.critical("Failed to initialize merchant lookup due to invalid regex or CSV format. Application will exit.")
    raise # Re-raise the ValueError to stop the application

def clean_merchant(description: str) -> str:
    """
    Cleans the merchant description using rules from merchant_lookup.csv.
    Falls back to a generic cleaning if no rule matches.
    """
    if not isinstance(description, str): # Handle potential non-string inputs
        return str(description)

    rules = _load_merchant_lookup() # Get cached/loaded rules

    for pattern, canonical_name in rules:
        match = pattern.search(description)
        if match:
            return canonical_name # Return the canonical name from the CSV

    # Fallback if no pattern matched: apply _clean_desc and title-case
    cleaned_desc = _clean_desc(description)
    return cleaned_desc.title()

# --- Constants ---

# Columns used to generate the deterministic Transaction ID (TxnID).
# IMPORTANT: These columns MUST exist and be stable *before* normalization steps
#            within normalize_df might alter them (e.g., cleaning description).
#            Now includes 'Bank' and 'Source' to handle deduplication of aggregator data.
# REVIEW: Confirm these columns are reliably populated by the updated ingest.py
_ID_COLS_FOR_HASH = [ # Changed back to list to fix concatenation error in logging
    "Date",
    "PostDate",          # NEW
    "Amount",
    "Description",
    "Bank",
    "Account",
]

# Defines the exact list and order of columns for the final output DataFrame.
# This ensures consistency regardless of intermediate processing steps.
# Added 'Bank', 'Source', 'Category', 'SplitPercent', and 'CanonMerchant'.
FINAL_COLS = [
    "TxnID", "Owner", "Date", "Account", "Bank",
    "Description", "CleanDesc", "CanonMerchant", "Category", # Added CanonMerchant
    "Amount", "SharedFlag", "SplitPercent", "Source"
]

# ==============================================================================
# 2. HELPER FUNCTIONS (Internal Use Only)
# ==============================================================================

# _strip_accents and _clean_desc moved to utils.py

# ------------------------------------------------------------------------------
# Function: _txn_id
# ------------------------------------------------------------------------------
def _txn_id(row: dict[str, Any]) -> str: # Changed input type to dict for apply lambda
    """Stable 16-char hex id using MD5."""
    # Extract values based on _ID_COLS_FOR_HASH, convert to string, strip whitespace, handle missing keys
    hash_cols_local = _ID_COLS_FOR_HASH.copy() # Use a local copy to potentially modify
    source = row.get('Source')
    # Conditionally add 'Source' to the hash components for specific sources
    if source in ('Rocket', 'Monarch'):
        hash_cols_local.append('Source')
        log.debug(f"Adding 'Source' ({source}) to hash components for TxnID.") # Optional: debug log

    base_parts = [str(row.get(col, "")).strip() for col in hash_cols_local]
    # Join parts with a separator
    hash_input = "|".join(base_parts)
    # Encode to bytes, generate MD5 hash, get hex digest, truncate
    return hashlib.md5(hash_input.encode('utf-8')).hexdigest()[:16]

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
        log.warning("Input DataFrame to normalize_df is empty. Returning empty DataFrame.")
        # Return empty DataFrame with the expected final columns.
        return pd.DataFrame(columns=FINAL_COLS)

    log.info(f"Normalizing {len(df)} rows (Phase 2 - TxnID, Cleaning, Final Cols)...")
    # Work on a copy to avoid modifying the original DataFrame passed in.
    out = df.copy()

    # --- Clean Description ---
    # Apply the text cleaning function to the 'Description' column.
    # Ensure 'Description' exists first for safety.
    if "Description" in out.columns:
        # --- Clean Description ---
        out["CleanDesc"] = out["Description"].apply(_clean_desc)
        log.info("Generated 'CleanDesc' column.")
        # --- Generate Canonical Merchant Name ---
        # Apply the new local clean_merchant function.
        out["CanonMerchant"] = out["Description"].apply(clean_merchant)
        log.info("Generated 'CanonMerchant' column using regex cleaning rules.")
    else:
        # --- Handle Missing Description ---
        log.warning("'Description' column not found, cannot generate 'CleanDesc'. Adding empty column.")
        out["CleanDesc"] = ""
        log.warning("'Description' column not found, cannot generate 'CanonMerchant'. Adding empty column.")
        out["CanonMerchant"] = ""

    # --- Fallback for missing PostDate ---
    # If PostDate is missing or all null after ingest/mapping, use Date as fallback for hash stability
    if "PostDate" not in out.columns or out["PostDate"].isna().all():
        if "Date" in out.columns:
            log.warning("PostDate column missing or all null. Using Date column as fallback for TxnID generation.")
            out["PostDate"] = out["Date"]
        else:
            log.error("PostDate column missing and Date column also missing. Cannot create PostDate fallback.")
            # Allow TxnID generation to fail below if Date is also in _ID_COLS_FOR_HASH

    # --- Generate Transaction ID ---
    # Check if all columns needed for hashing are present.
    missing_id_cols = [col for col in _ID_COLS_FOR_HASH if col not in out.columns]
    if missing_id_cols:
        # Log a critical error if columns needed for ID generation are missing.
        log.error(f"Cannot generate TxnID. Missing required columns from input DataFrame: {missing_id_cols}. Adding 'TxnID' column with None.")
        out["TxnID"] = None
    else:
        # Apply the _txn_id function row by row using a lambda to pass row as dict
        log.info(f"Generating TxnID using columns: {_ID_COLS_FOR_HASH}")
        try:
            # Use apply with lambda to pass row as dictionary
            out["TxnID"] = out.apply(lambda r: _txn_id(r.to_dict()), axis=1)
        except Exception as e:
            log.error(f"Error applying _txn_id function: {e}", exc_info=True)
            out["TxnID"] = None # Set to None on error

        # --- Validate TxnID ---
        if out["TxnID"].isnull().any():
             log.warning("Some TxnIDs could not be generated (returned None).")
        # Check uniqueness (important!)
        if out["TxnID"].notna().any() and not out.loc[out["TxnID"].notna(), "TxnID"].is_unique:
            duplicates = out[out.duplicated(subset=['TxnID'], keep=False) & out["TxnID"].notna()]
            # Changed from critical to warning as deduplication handles this later
            log.warning(f"TxnID collision detected! {len(duplicates)} rows affected. "
                        f"This is expected if the same transaction appears in multiple sources (e.g., Monarch/Rocket) "
                        f"before deduplication. Review columns used if unexpected: {_ID_COLS_FOR_HASH}. "
                        f"Duplicate examples:\n{duplicates[['TxnID'] + list(_ID_COLS_FOR_HASH)].head()}") # Ensure list for concat
             # REVIEW: Decide how to handle collisions - raise error? Flag rows?

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
            log.warning(f"Final column '{col}' was not generated. Adding column with NA values.")
            out[col] = pd.NA

    # Select only the columns specified in FINAL_COLS and in that specific order.
    # Sort the entire DataFrame by 'Date' ascending. Put rows with invalid/missing dates first.
    out = out[FINAL_COLS].sort_values("Date", ascending=True, na_position='first')
    
    # --- Deduplication for aggregator sources (Rocket Money and Monarch) ---
    # Drop duplicate rows based on TxnID - these would be the same transaction appearing in
    # multiple aggregator sources
    initial_row_count = len(out)
    
    # Sort by Source column to prioritize which rows to keep when dropping duplicates
    # Using the preferred source parameter (default 'Rocket') to control which source wins
    # Check if there are any duplicated rows by TxnID with Source column
    if "Source" in out.columns:
        # Log duplicates for debugging
        dupes = out[out.duplicated(subset=["TxnID"], keep=False)]
        if not dupes.empty:
            log.info(f"Found {len(dupes)} rows with duplicated TxnIDs")
            
            # Sort to prioritize the preferred source first
            log.info(f"Using preferred source '{prefer_source}' for deduplication")
            
            # Custom sorting logic that puts the preferred source first and handles NA
            def prefer_source_sorter(source_series):
                # Treat NA as non-preferred (assign 1)
                return [0 if pd.notna(s) and s == prefer_source else 1 for s in source_series]

            # Use the custom sorter to prioritize the preferred source
            out = out.sort_values("Source", key=prefer_source_sorter)
            
            # Count dupes before removal
            dupe_count_before = out.duplicated(subset=["TxnID"], keep=False).sum()
            
            # Remove duplicates, keeping the first occurrence (which will be the preferred source due to sorting)
            out = out.drop_duplicates(subset=["TxnID"], keep="first")
            
            # Calculate how many were removed
            dupe_count_after = initial_row_count - len(out)
            
            if dupe_count_after > 0:
                log.info(f"Removed {dupe_count_after} duplicate transactions from aggregator sources. Prioritized based on Source.")
    
    log.info("Normalization complete. Returning %s rows.", len(out))
    return out

# ==============================================================================
# END OF FILE: normalize.py
# ==============================================================================
