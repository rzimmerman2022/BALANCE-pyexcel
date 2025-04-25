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
import re                  # For regular expression operations (used in _clean_desc)
import unicodedata         # For handling Unicode normalization (removing accents)
import hashlib             # For generating SHA-256 hashes for TxnID
import logging             # For logging messages

# ==============================================================================
# 1. MODULE LEVEL SETUP & CONSTANTS
# ==============================================================================

# --- Setup Logger ---
# Get a logger specific to this module for targeted logging.
log = logging.getLogger(__name__)

# --- Constants ---

# Columns used to generate the deterministic Transaction ID (TxnID).
# IMPORTANT: These columns MUST exist and be stable *before* normalization steps
#            within normalize_df might alter them (e.g., cleaning description).
#            Now includes 'Bank' and 'Source' to handle deduplication of aggregator data.
# REVIEW: Confirm these columns are reliably populated by the updated ingest.py
_ID_COLS_FOR_HASH = ["Date", "Amount", "Description", "Bank", "Account"]

# Defines the exact list and order of columns for the final output DataFrame.
# This ensures consistency regardless of intermediate processing steps.
# Added 'Bank', 'Source', 'Category', and 'SplitPercent' based on recent updates.
FINAL_COLS = [
    "TxnID", "Owner", "Date", "Account", "Bank", 
    "Description", "CleanDesc", "Category",
    "Amount", "SharedFlag", "SplitPercent", "Source"
]

# ==============================================================================
# 2. HELPER FUNCTIONS (Internal Use Only)
# ==============================================================================

# ------------------------------------------------------------------------------
# Function: _strip_accents
# ------------------------------------------------------------------------------
def _strip_accents(txt: str | None) -> str:
    """Removes accent marks from characters in a string."""
    if pd.isna(txt):
        # Handle missing or NaN input gracefully.
        return ""
    try:
        # Normalize Unicode text into 'NFD' form (Canonical Decomposition),
        # which separates base characters from their accent marks.
        # Then, filter out characters in the 'Mn' (Mark, Nonspacing) category.
        txt = str(txt) # Ensure input is string
        return "".join(
            ch for ch in unicodedata.normalize("NFD", txt)
            if unicodedata.category(ch) != "Mn"
        )
    except TypeError: # Catch potential errors if input isn't string-like
        log.warning(f"Could not strip accents from non-string input: {type(txt)}. Returning empty string.")
        return ""

# ------------------------------------------------------------------------------
# Function: _clean_desc
# ------------------------------------------------------------------------------
def _clean_desc(desc: str | None) -> str:
    """Cleans description text for easier matching and analysis."""
    if pd.isna(desc):
        # Handle missing or NaN input.
        return ""

    try:
        # 1. Remove accents (using helper function above).
        # 2. Convert to uppercase for case-insensitive matching later.
        desc = _strip_accents(str(desc)).upper()
        # 3. Replace sequences of non-alphanumeric characters (excluding space) with a single space.
        #    This helps remove punctuation and symbols while preserving word separation.
        desc = re.sub(r"[^A-Z0-9 ]+", " ", desc)
        # 4. Replace multiple consecutive spaces with a single space.
        desc = re.sub(r"\s+", " ", desc)
        # 5. Remove leading/trailing whitespace.
        return desc.strip()
    except Exception as e:
        log.warning(f"Error cleaning description: '{desc}'. Error: {e}. Returning original.")
        return str(desc or '') # Return original string or empty if error


# ------------------------------------------------------------------------------
# Function: _txn_id
# ------------------------------------------------------------------------------
def _txn_id(row: pd.Series) -> str | None:
    """
    Generates a unique and deterministic Transaction ID (TxnID) using SHA-256 hashing.

    Combines values from predefined stable columns (_ID_COLS_FOR_HASH)
    into a single string, hashes it, and returns a truncated hexadecimal representation.
    Includes 'Owner' to prevent collisions between users.

    Args:
        row (pd.Series): A row representing a transaction. Must contain columns
                         specified in _ID_COLS_FOR_HASH.

    Returns:
        str | None: The truncated SHA-256 hash (16 characters), or None if an error occurs.
    """
    try:
        # --- Prepare components for hashing ---
        # Ensure consistent string formatting for reliable hashing.

        # Date: Format as YYYY-MM-DD, handle NaT (Not a Time).
        date_obj = pd.to_datetime(row.get("Date"), errors='coerce')
        date_str = date_obj.strftime('%Y-%m-%d') if pd.notna(date_obj) else ''

        # Amount: Format to exactly 2 decimal places, handle NaN.
        amount_val = pd.to_numeric(row.get("Amount"), errors='coerce')
        amount_str = f"{amount_val:.2f}" if pd.notna(amount_val) else ''

        # Description: Use the *original* Description for stability before cleaning. Handle None/NA.
        desc_str = str(row.get("Description", "") or "")

        # Bank: Convert to string, handle None/NA.
        bank_str = str(row.get("Bank", "") or "").lower()

        # Account: Convert to string, handle None/NA.
        acct_str = str(row.get("Account", "") or "")

        # --- Combine into a single string ---
        # Use a clear separator (e.g., '|') to prevent ambiguity.
        # Order matters: ensure consistent column order based on _ID_COLS_FOR_HASH.
        base_parts = [date_str, amount_str, desc_str, bank_str, acct_str]
        base = "|".join(base_parts)

        # --- Generate Hash ---
        # Encode the string to bytes (UTF-8 standard) as required by hashlib.
        # Generate SHA-256 hash and get its hexadecimal representation.
        # Truncate to 16 characters for brevity (increases collision chance slightly, but usually acceptable).
        # REVIEW: Consider using the full hash if absolute minimum collision risk is paramount.
        return hashlib.sha256(base.encode('utf-8')).hexdigest()[:16]

    except KeyError as e:
        # Log if a required column for hashing is missing from the row.
        log.error(f"Missing column required for TxnID generation: {e}. Row index: {row.name}. Available columns: {row.index.tolist()}")
        return None
    except Exception as e:
        # Log any other unexpected error during hash generation.
        log.error(f"Unexpected error generating TxnID for row {row.name}: {e}", exc_info=True)
        return None

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
        out["CleanDesc"] = out["Description"].apply(_clean_desc)
        log.info("Generated 'CleanDesc' column.")
    else:
        log.warning("'Description' column not found, cannot generate 'CleanDesc'. Adding empty column.")
        out["CleanDesc"] = "" # Add empty column if source missing

    # --- Generate Transaction ID ---
    # Check if all columns needed for hashing are present.
    missing_id_cols = [col for col in _ID_COLS_FOR_HASH if col not in out.columns]
    if missing_id_cols:
        # Log a critical error if columns needed for ID generation are missing.
        log.error(f"Cannot generate TxnID. Missing required columns from input DataFrame: {missing_id_cols}. Adding 'TxnID' column with None.")
        out["TxnID"] = None
    else:
        # Apply the _txn_id function row by row. axis=1 passes each row as a Series.
        log.info(f"Generating TxnID using columns: {_ID_COLS_FOR_HASH}")
        out["TxnID"] = out.apply(_txn_id, axis=1)

        # --- Validate TxnID ---
        if out["TxnID"].isnull().any():
             log.warning("Some TxnIDs could not be generated (returned None).")
        # Check uniqueness (important!)
        if out["TxnID"].notna().any() and not out.loc[out["TxnID"].notna(), "TxnID"].is_unique:
            duplicates = out[out.duplicated(subset=['TxnID'], keep=False) & out["TxnID"].notna()]
            log.critical(f"CRITICAL: TxnID collision detected! {len(duplicates)} rows affected. "
                         f"Review ID generation logic and columns: {_ID_COLS_FOR_HASH}. "
                         f"Duplicate examples:\n{duplicates[['TxnID'] + _ID_COLS_FOR_HASH].head()}")
            # REVIEW: Decide how to handle collisions - raise error? Flag rows?

    # --- Add Default Shared Flag ---
    # Initialize the 'SharedFlag' column with '?' indicating it needs review.
    # This column will be updated later by classification rules or manual tagging.
    out["SharedFlag"] = "?"
    log.info("Added default 'SharedFlag' column.")

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
            
            # Custom sorting logic that puts the preferred source first in the sort order
            def prefer_source_sorter(source_series):
                return [0 if s == prefer_source else 1 for s in source_series]
                
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
