from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime

import pandas as pd

# Assuming config.py is in the same directory or accessible via PYTHONPATH
from .config import AnalysisConfig, DataQualityFlag

logger = logging.getLogger(__name__)


def _explode_audit(audit_note: str) -> tuple[str, str, str, str]:
    """Parse audit note into structured components."""
    if pd.isna(audit_note) or not str(audit_note).strip():
        return ("<NA>", "<NA>", "<NA>", "<NA>")  # XML escaped for safety

    audit_str = str(audit_note)
    who_paid_match = re.search(r"paid by (\w+)", audit_str, re.IGNORECASE)
    who_paid = who_paid_match.group(1) if who_paid_match else "<NA>"

    if "FULLY SHARED" in audit_str:
        share_type = "FULLY_SHARED"
    elif "PARTIALLY SHARED" in audit_str:
        share_type = "PARTIALLY_SHARED"
    elif "PERSONAL EXPENSE" in audit_str:
        share_type = "PERSONAL"
    else:
        share_type = "SHARED" if "share" in audit_str.lower() else "<NA>"

    reason_match = re.search(r"REASON: ([^|]+)", audit_str)
    shared_reason = reason_match.group(1).strip() if reason_match else "<NA>"

    quality_match = re.search(
        r"DataQuality: ([\w,]+)", audit_str
    )  # Allow comma in quality flags
    data_quality = (
        quality_match.group(1) if quality_match else DataQualityFlag.CLEAN.value
    )

    return (who_paid, share_type, shared_reason, data_quality)


def _generate_transaction_id(row: pd.Series, date_col: str = "Date") -> str:
    """Generate unique transaction ID."""
    date_val = row.get(date_col)
    date_str = (
        date_val.isoformat()
        if isinstance(date_val, (datetime, pd.Timestamp)) and pd.notna(date_val)
        else str(date_val if pd.notna(date_val) else "NoDate")
    )

    key_data = (
        f"{date_str}_"
        f"{row.get('Payer','NA')}_"
        f"{row.get('Merchant','NA')}_"
        f"{str(row.get('Description','NoDesc'))[:20]}_"
        f"{row.get('ActualAmount',0.0):.2f}_"
        f"{row.get('AllowedAmount',0.0):.2f}_"
        f"{row.get('BalanceImpact',0.0):.2f}"
    )
    return hashlib.sha256(key_data.encode()).hexdigest()[:32]


def create_master_ledger(
    processed_rent_df: pd.DataFrame,
    processed_expense_df: pd.DataFrame,
    config: AnalysisConfig,
    logger_instance: logging.Logger = logger,
) -> pd.DataFrame:
    logger_instance.info(
        "Creating master ledger from processed rent and expense data..."
    )

    common_cols = [
        "Date",
        "TransactionType",
        "Payer",
        "Description",
        "ActualAmount",
        "AllowedAmount",
        "IsShared",
        "RyanOwes",
        "JordynOwes",
        "BalanceImpact",
        "AuditNote",
        "DataQualityFlag",
        "Merchant",
    ]

    # Prepare rent_df
    rent_df_c = processed_rent_df.copy()
    if "Merchant" not in rent_df_c.columns and not rent_df_c.empty:
        rent_df_c["Merchant"] = "Landlord/Property"

    # Prepare expense_df
    expense_df_c = processed_expense_df.copy()

    # Ensure common columns exist in both DataFrames
    for df_iter, name in [
        (rent_df_c, "processed_rent_df"),
        (expense_df_c, "processed_expense_df"),
    ]:
        if df_iter.empty:
            logger_instance.warning(
                f"{name} is empty. It will not contribute to master ledger."
            )
            # Create an empty df with common_cols to allow concat if one is empty and the other is not
            # This ensures concat doesn't fail if one df is empty but the other has data.
            if name == "processed_rent_df":
                rent_df_c = pd.DataFrame(columns=common_cols)
            if name == "processed_expense_df":
                expense_df_c = pd.DataFrame(columns=common_cols)
            continue  # Skip further column checks for this empty df

        for col in common_cols:
            if col not in df_iter.columns:
                logger_instance.warning(
                    f"Column '{col}' missing in {name}. Adding as default."
                )
                if col in [
                    "ActualAmount",
                    "AllowedAmount",
                    "RyanOwes",
                    "JordynOwes",
                    "BalanceImpact",
                ]:
                    df_iter[col] = 0.0
                elif col == "IsShared":
                    df_iter[col] = False
                elif col == "Date":
                    df_iter[col] = pd.NaT
                else:  # String columns
                    df_iter[col] = pd.NA

    dfs_to_concat = []
    if not rent_df_c.empty:
        dfs_to_concat.append(rent_df_c[common_cols])  # Select only common_cols
    if not expense_df_c.empty:
        dfs_to_concat.append(expense_df_c[common_cols])  # Select only common_cols

    if not dfs_to_concat:
        logger_instance.error(
            "Both processed rent and expense DataFrames are effectively empty. Master ledger cannot be created."
        )
        # Define all expected columns for an empty master ledger
        all_master_ledger_cols = common_cols + [
            "RunningBalance",
            "TransactionID",
            "DataLineage",
            "Who_Paid_Text",
            "Share_Type",
            "Shared_Reason",
            "DataQuality_Audit",
        ]
        return pd.DataFrame(columns=all_master_ledger_cols)

    master = pd.concat(dfs_to_concat, ignore_index=True, sort=False)

    if "Date" in master.columns:
        master["Date"] = pd.to_datetime(master["Date"], errors="coerce")
    else:
        master["Date"] = pd.NaT  # Should not happen if common_cols logic is correct
        logger_instance.error(
            "Master ledger is missing 'Date' column after concat, this is unexpected."
        )

    if master["Date"].isna().any():
        logger_instance.warning(
            f"{master['Date'].isna().sum()} transactions have missing/invalid dates in master ledger. "
            "They will be sorted to the beginning or end depending on na_position."
        )

    master = master.sort_values(
        by="Date", ascending=True, na_position="first"
    ).reset_index(drop=True)

    numeric_cols = [
        "ActualAmount",
        "AllowedAmount",
        "RyanOwes",
        "JordynOwes",
        "BalanceImpact",
    ]
    for col in numeric_cols:
        if col in master.columns:
            master[col] = pd.to_numeric(master[col], errors="coerce").fillna(0)
        else:  # Should not happen
            master[col] = 0.0
            logger_instance.error(
                f"Numeric column '{col}' unexpectedly missing in master ledger. Defaulting to 0."
            )

    master["RunningBalance"] = (
        master["BalanceImpact"].cumsum().round(config.CURRENCY_PRECISION)
    )
    master["TransactionID"] = master.apply(
        lambda row: _generate_transaction_id(row, date_col="Date"), axis=1
    )

    # P0 Blueprint: Data-lineage Column
    # Add LineageStep column that appends mini‑codes (L1, P2, S3) every time a row changes;
    # For now, this is a placeholder. True lineage tracking would involve more complex state management
    # or passing lineage info from previous steps.
    master["DataLineage"] = master.apply(
        lambda row: f"SourceType: {row.get('TransactionType','NA')} | LedgerGenIndex: {row.name} | Stage: MasterLedgerBuild_v{config.RYAN_PCT}_{config.JORDYN_PCT}",  # Example
        axis=1,
    )

    # Audit split columns
    # Ensure 'AuditNote' exists and is string type before applying _explode_audit
    if "AuditNote" not in master.columns:
        master["AuditNote"] = ""  # Initialize if missing
    master["AuditNote"] = master["AuditNote"].astype(str).fillna("")

    audit_components = master["AuditNote"].apply(_explode_audit)
    master[["Who_Paid_Text", "Share_Type", "Shared_Reason", "DataQuality_Audit"]] = (
        pd.DataFrame(audit_components.tolist(), index=master.index)
    )

    if (
        "DataQualityFlag" not in master.columns
    ):  # Should be present from processing step
        master["DataQualityFlag"] = DataQualityFlag.CLEAN.value
    master["DataQualityFlag"] = master["DataQualityFlag"].fillna(
        DataQualityFlag.CLEAN.value
    )

    logger_instance.info(f"Created master ledger with {len(master)} transactions.")
    if not master.empty and master["Date"].notna().any():
        logger_instance.info(
            f"Date range: {master['Date'].min()} to {master['Date'].max()}"
        )
    elif not master.empty:
        logger_instance.warning("Master ledger created, but all 'Date' values are NaT.")
    else:
        logger_instance.warning("Master ledger is empty after processing.")

    return master
