# -*- coding: utf-8 -*-
"""
==============================================================================
Module: sync.py
Project: BALANCE-pyexcel
Description: Contains functions related to synchronizing user decisions
             (e.g., from the Queue_Review sheet in Excel) back into the main
             transaction dataset.
==============================================================================

Version: 0.1.0
Last Modified: 2025-04-22
Author: Ryan Zimmerman / AI Assistant
"""

# ==============================================================================
# 0. IMPORTS
# ==============================================================================
from __future__ import annotations  # For using type hints before full definition
import pandas as pd
import logging
from typing import TYPE_CHECKING, Any  # Added TYPE_CHECKING

# ==============================================================================
# 1. MODULE LEVEL SETUP
# ==============================================================================

# --- Setup Logger ---
log = logging.getLogger(__name__)

if TYPE_CHECKING:
    Series = pd.Series[Any]  # for static typing only
else:
    Series = pd.Series  # runtime-safe alias

# --- Define constants for column names used in Queue_Review ---
# These should match the exact headers you created in the Excel sheet
# REVIEW: Double-check these match your Queue_Review sheet headers EXACTLY
QUEUE_TXNID_COL = "TxnID"
QUEUE_DECISION_COL = "Set Shared? (Y/N/S for Split)"
QUEUE_SPLIT_COL = "Set Split % (0-100)"

# Define constants for column names in the main Transactions data
TRANS_TXNID_COL = "TxnID"
TRANS_SHARED_FLAG_COL = "SharedFlag"
TRANS_SPLIT_PERC_COL = "SplitPercent"
# Optional: A column to indicate a user reviewed the item
# TRANS_USER_DECISION_COL = "UserDecision" # Need to ensure this exists in FINAL_COLS if used

# ==============================================================================
# 2. PUBLIC FUNCTIONS
# ==============================================================================


# ------------------------------------------------------------------------------
# Function: sync_review_decisions
# ------------------------------------------------------------------------------
def sync_review_decisions(
    df_transactions: pd.DataFrame, df_queue_review: pd.DataFrame
) -> pd.DataFrame:
    """
    Reads decisions from the Queue_Review data and merges them back into the
    main Transactions DataFrame based on matching TxnID.

    Args:
        df_transactions (pd.DataFrame): The main DataFrame containing all transactions,
                                        including columns like 'TxnID', 'SharedFlag', 'SplitPercent'.
        df_queue_review (pd.DataFrame): The DataFrame read from the Queue_Review sheet,
                                        containing at least 'TxnID' and the decision columns
                                        (defined by QUEUE_DECISION_COL, QUEUE_SPLIT_COL).

    Returns:
        pd.DataFrame: A copy of the df_transactions DataFrame with 'SharedFlag' and
                      'SplitPercent' updated based on the decisions found in df_queue_review.

    Workflow:
    1. Validate inputs.
    2. Select and clean relevant columns from df_queue_review.
    3. Standardize decision values (Y/N/S -> SharedFlag, % -> SplitPercent).
    4. Merge decisions into a copy of df_transactions using TxnID.
    5. Apply the updates from the merged columns to the original columns.
    6. Return the updated DataFrame.
    """
    log.info(
        f"Starting sync process. Transactions: {len(df_transactions)} rows, Queue: {len(df_queue_review)} rows."
    )

    # --- Input Validation (Basic) ---
    if df_transactions.empty:
        log.warning("Input transactions DataFrame is empty. Returning unchanged.")
        return df_transactions.copy()
    if df_queue_review.empty:
        log.info(
            "Queue review DataFrame is empty. No decisions to sync. Returning unchanged transactions."
        )
        return df_transactions.copy()

    # Check for necessary columns
    required_trans_cols = [TRANS_TXNID_COL, TRANS_SHARED_FLAG_COL, TRANS_SPLIT_PERC_COL]
    required_queue_cols = [QUEUE_TXNID_COL, QUEUE_DECISION_COL, QUEUE_SPLIT_COL]

    if not all(col in df_transactions.columns for col in required_trans_cols):
        log.error(
            f"Transactions DataFrame missing required columns for sync. Need: {required_trans_cols}"
        )
        # Optionally raise an error or return unchanged
        return df_transactions.copy()
    if not all(col in df_queue_review.columns for col in required_queue_cols):
        log.error(
            f"Queue Review DataFrame missing required columns for sync. Need: {required_queue_cols}"
        )
        # Return unchanged as we can't process decisions
        return df_transactions.copy()

    # --- Prepare DataFrame Copy ---
    # Work on a copy to avoid modifying the original DataFrame directly (good practice)
    df_updated_transactions = df_transactions.copy()

    # --- Prepare Queue Decisions ---
    log.info("Preparing decisions from Queue_Review...")

    # Filter to only rows with actual decisions (non-empty)
    # and standardize the values
    df_queue_filtered = df_queue_review.copy()

    # 1. Filter out rows where QUEUE_DECISION_COL is empty or NaN
    df_queue_filtered = df_queue_filtered[
        df_queue_filtered[QUEUE_DECISION_COL].notna()
        & (df_queue_filtered[QUEUE_DECISION_COL] != "")
    ]

    # 2. Extract and validate SharedFlag decisions
    # Only accept Y, N, or S (case-insensitive)
    def standardize_decision(val: Any) -> str | None:
        # First, handle original None or NaN values directly
        if pd.isna(val):
            return None

        s_val = str(val).strip()  # Convert to string and strip whitespace

        if not s_val:  # Check if string is empty after stripping
            return None

        s_val_upper = s_val.upper()
        if s_val_upper in ["Y", "N", "S"]:
            return s_val_upper
        else:
            log.warning(
                f"Invalid decision value: '{val}'. Expected Y, N, or S. Ignoring."
            )
            return None

    # Create new column with standardized values
    df_queue_filtered["SharedFlag_update"] = df_queue_filtered[
        QUEUE_DECISION_COL
    ].apply(standardize_decision)

    # 3. Handle split percentages
    # Only relevant when SharedFlag is 'S', should be between 0 and 100
    def validate_split_percent(row: Series) -> float | None:  # row is a Series
        if row["SharedFlag_update"] != "S":
            return None

        val_from_queue = row[QUEUE_SPLIT_COL]

        if pd.isna(
            val_from_queue
        ):  # Handles if original cell was empty or unparseable by pd.read_excel's dtype=str
            log.warning(
                f"Missing split percentage for split decision on TxnID: {row[QUEUE_TXNID_COL]}. Using 50%."
            )
            return 50.0

        numeric_val = pd.to_numeric(val_from_queue, errors="coerce")

        if pd.isna(numeric_val):  # pd.to_numeric failed to parse
            log.warning(
                f"Invalid split percentage format (could not convert to number) for TxnID: {row[QUEUE_TXNID_COL]}: '{val_from_queue}'. Using 50%."
            )
            return 50.0

        # At this point, numeric_val is a float (or an int that can be safely converted to float)
        val = float(numeric_val)

        # Clamp to range 0-100
        if val < 0:
            log.warning(
                f"Split percentage ({val}) below 0 for TxnID: {row[QUEUE_TXNID_COL]}. Clamping to 0."
            )
            return 0.0
        elif val > 100:
            log.warning(
                f"Split percentage ({val}) above 100 for TxnID: {row[QUEUE_TXNID_COL]}. Clamping to 100."
            )
            return 100.0
        return val

    df_queue_filtered["SplitPercent_update"] = df_queue_filtered.apply(
        validate_split_percent, axis=1
    )

    # 4. Remove rows where we couldn't standardize the decision
    df_queue_filtered = df_queue_filtered[
        df_queue_filtered["SharedFlag_update"].notna()
    ]

    # 5. Select only relevant columns for merging
    df_processed_decisions = df_queue_filtered[
        [QUEUE_TXNID_COL, "SharedFlag_update", "SplitPercent_update"]
    ]

    log.info(
        f"Processed {len(df_processed_decisions)} valid decisions from Queue_Review."
    )

    # --- Merge Decisions ---
    log.info("Merging decisions into transactions...")

    # Merge on TxnID, using left join to keep all transactions
    merged_df = pd.merge(
        df_updated_transactions,
        df_processed_decisions,
        how="left",
        left_on=TRANS_TXNID_COL,
        right_on=QUEUE_TXNID_COL,
    )

    # --- Apply Updates ---
    log.info("Applying synced decisions...")

    # Update SharedFlag where we have valid decisions
    mask_update_shared = merged_df["SharedFlag_update"].notna()
    if mask_update_shared.any():
        merged_df.loc[mask_update_shared, TRANS_SHARED_FLAG_COL] = merged_df.loc[
            mask_update_shared, "SharedFlag_update"
        ]
        log.info(f"Updated SharedFlag for {mask_update_shared.sum()} transactions.")

    # Update SplitPercent where applicable (when SharedFlag is 'S')
    mask_update_split = merged_df["SplitPercent_update"].notna()
    if mask_update_split.any():
        merged_df.loc[mask_update_split, TRANS_SPLIT_PERC_COL] = merged_df.loc[
            mask_update_split, "SplitPercent_update"
        ]
        log.info(f"Updated SplitPercent for {mask_update_split.sum()} transactions.")

    # Remove the temporary columns used for updating
    final_df = merged_df.drop(
        columns=["SharedFlag_update", "SplitPercent_update"], errors="ignore"
    )

    # --- Final Steps ---
    log.info("Sync process complete.")
    return final_df


# ==============================================================================
# END OF FILE: sync.py
# ==============================================================================
