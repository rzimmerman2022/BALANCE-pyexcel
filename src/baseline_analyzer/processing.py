from __future__ import annotations

import pandas as pd
import numpy as np
from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Dict, List, Any, Union

# Assuming config.py and loaders.py are in the same directory or accessible via PYTHONPATH
from .config import AnalysisConfig, DataQualityFlag 
# from .loaders import merge_expense_and_ledger_data, merge_rent_data # Not needed directly here if passed as DFs

logger = logging.getLogger(__name__)

# This module will house functions that take DataFrames (potentially from loaders.py)
# and the AnalysisConfig, then perform processing and business logic application.

# Helper function to log data quality issues (can be shared or part of a utility module later)
# For now, keeping it here if processing functions directly call it.
# Alternatively, processing functions can return flags/data for a central logger in the main orchestrator.

def _log_data_quality_issue_processing(
    data_quality_issues_list: List[Dict[str, Any]], # Pass the list to append to
    source: str,
    row_idx: Any,
    row_data: Dict[str, Any],
    flags: List[Union[DataQualityFlag, str]],
    logger_instance: logging.Logger = logger # Allow passing a specific logger
):
    """Log data quality issues for audit trail (processing context)"""
    flag_values = [f.value if isinstance(f, DataQualityFlag) else f for f in flags]

    sanitized_row_data = {}
    for k, v in row_data.items():
        if isinstance(v, (datetime, pd.Timestamp)):
            sanitized_row_data[k] = v.isoformat()
        elif isinstance(v, (list, dict, pd.Series)):
            sanitized_row_data[k] = str(v)
        elif pd.isna(v):
            sanitized_row_data[k] = "NaN"
        else:
            sanitized_row_data[k] = v
    
    issue = {
        "source": source,
        "row_index_in_source_df": str(row_idx),
        "flags": flag_values,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "row_data_sample": {
            k: sanitized_row_data.get(k)
            for k in ["Date", "Payer", "ActualAmount", "AllowedAmount", "Description"]
            if k in sanitized_row_data
        },
    }
    data_quality_issues_list.append(issue)
    logger_instance.warning(
        f"Data quality issue in {source} (index: {row_idx}): {flag_values}. Sample: {issue['row_data_sample']}"
    )

def _update_row_data_quality_flags_processing(
    df: pd.DataFrame, row_idx: Any, new_flags_enums: List[DataQualityFlag]
):
    """Appends new unique flags to the existing flags for a given row (processing context)"""
    if not new_flags_enums:
        return

    new_flag_values = [flag.value for flag in new_flags_enums]

    if "DataQualityFlag" not in df.columns:
        df["DataQualityFlag"] = DataQualityFlag.CLEAN.value

    existing_flags_str = df.loc[row_idx, "DataQualityFlag"]
    
    current_flags_list = []
    if pd.notna(existing_flags_str) and existing_flags_str != DataQualityFlag.CLEAN.value:
        current_flags_list = existing_flags_str.split(",")

    added_new = False
    for flag_val in new_flag_values:
        if flag_val not in current_flags_list:
            current_flags_list.append(flag_val)
            added_new = True

    if added_new:
        if DataQualityFlag.CLEAN.value in current_flags_list and len(current_flags_list) > 1:
            current_flags_list.remove(DataQualityFlag.CLEAN.value)
        df.loc[row_idx, "DataQualityFlag"] = ",".join(sorted(list(set(current_flags_list))))
    elif not current_flags_list and (pd.isna(existing_flags_str) or existing_flags_str == DataQualityFlag.CLEAN.value):
        if pd.isna(existing_flags_str): # Ensure it's not NaN before setting to CLEAN
             df.loc[row_idx, "DataQualityFlag"] = DataQualityFlag.CLEAN.value


def _impute_missing_date_processing(
    df: pd.DataFrame, idx: Any, date_col_name: str, logger_instance: logging.Logger = logger
) -> pd.Timestamp:
    """Impute missing date based on surrounding transactions or fallback (processing context)"""
    if not isinstance(idx, int):
        try:
            idx_pos = df.index.get_loc(idx)
        except KeyError:
            logger_instance.error(f"Cannot find index {idx} in DataFrame for date imputation.")
            return pd.Timestamp.now(tz=timezone.utc).replace(day=1) + pd.offsets.MonthEnd(0)
    else:
        idx_pos = idx

    window = 5
    start_idx = max(0, idx_pos - window)
    end_idx = min(len(df), idx_pos + window + 1)

    if start_idx >= end_idx:
        logger_instance.warning(f"Invalid slice for date imputation for index {idx} (pos {idx_pos}). Falling back.")
        return pd.Timestamp.now(tz=timezone.utc).replace(day=1) + pd.offsets.MonthEnd(0)

    nearby_dates = df.iloc[start_idx:end_idx][date_col_name].dropna()

    if not nearby_dates.empty:
        nearby_dates_ts = pd.to_datetime(nearby_dates, errors="coerce").dropna()
        if not nearby_dates_ts.empty:
            return pd.Timestamp(nearby_dates_ts.astype(np.int64).median())
        else:
            logger_instance.warning(f"Could not convert nearby dates to Timestamps for row {idx}. Falling back.")
    else:
        logger_instance.warning(f"Could not impute date for row {idx} based on neighbors. Falling back to current month-end.")
    
    now = pd.Timestamp.now(tz=timezone.utc)
    return now.replace(day=1) + pd.offsets.MonthEnd(0)


def _handle_calculation_notes_in_processed_data(
    df: pd.DataFrame, 
    config: AnalysisConfig, 
    data_quality_issues_list: List[Dict[str, Any]],
    logger_instance: logging.Logger = logger
) -> pd.DataFrame:
    logger_instance.info("Handling '2x to calculate' notes in processed expense descriptions...")
    if "Description" not in df.columns or "AllowedAmount" not in df.columns:
        logger_instance.warning("'Description' or 'AllowedAmount' column not found, skipping '2x' note handling.")
        return df

    # Using DEFAULT_CALCULATION_NOTE_TRIGGER from config module (or AnalysisConfig if moved there)
    # For now, assuming it's accessible via config object or directly imported if it remains a global in config.py
    # Let's assume config.DEFAULT_CALCULATION_NOTE_TRIGGER for this example
    # This needs to be resolved based on where DEFAULT_CALCULATION_NOTE_TRIGGER is defined.
    # If it's a global in config.py, it would be: from .config import DEFAULT_CALCULATION_NOTE_TRIGGER
    # For now, let's hardcode it here and note it for refactoring with config loading.
    calculation_note_trigger = "2x to calculate" # Placeholder, should come from config

    two_x_mask = df["Description"].str.contains(calculation_note_trigger, case=False, na=False)
    modified_indices = []

    for idx in df[two_x_mask].index:
        actual_amount_for_row = df.loc[idx, "ActualAmount"]
        new_allowed_amount = actual_amount_for_row * 2
        original_allowed = df.loc[idx, "AllowedAmount"]

        log_msg = (
            f"Row {idx}: '{calculation_note_trigger}' found. "
            f"Setting AllowedAmount from (ActualAmount * 2): ({actual_amount_for_row} * 2 = {new_allowed_amount}). "
            f"Original AllowedAmount was: {original_allowed}."
        )
        df.loc[idx, "AllowedAmount"] = new_allowed_amount
        modified_indices.append(idx)
        logger_instance.info(log_msg)
        _update_row_data_quality_flags_processing(df, idx, [DataQualityFlag.MANUAL_CALCULATION_NOTE])
        _log_data_quality_issue_processing(
            data_quality_issues_list,
            "expense_2x_note_check",
            idx,
            df.loc[idx].to_dict(),
            [DataQualityFlag.MANUAL_CALCULATION_NOTE],
            logger_instance
        )

    if modified_indices:
        logger_instance.info(
            f"Applied '{calculation_note_trigger}' calculation to 'AllowedAmount' for {len(modified_indices)} rows based on description note."
        )
    return df

def _detect_duplicates_in_processed_data(
    df: pd.DataFrame, 
    data_quality_issues_list: List[Dict[str, Any]],
    logger_instance: logging.Logger = logger
) -> pd.DataFrame:
    logger_instance.info("Detecting potential duplicate transactions in processed data...")
    if df.empty:
        return df

    if "Date" in df.columns and not pd.api.types.is_datetime64_any_dtype(df["Date"]):
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    dup_cols = ["Date", "Payer", "ActualAmount", "Merchant"]
    available_dup_cols = [col for col in dup_cols if col in df.columns]

    if len(available_dup_cols) < 3:
        logger_instance.warning(f"Skipping duplicate detection: Not enough key columns available (need at least 3 from {dup_cols}).")
        return df

    temp_df_for_dup_check = df[available_dup_cols].copy()
    if pd.api.types.is_datetime64_any_dtype(temp_df_for_dup_check["Date"]):
        temp_df_for_dup_check["DateForDup"] = temp_df_for_dup_check["Date"].dt.date
        check_cols_for_dup = ["DateForDup"] + [col for col in available_dup_cols if col != "Date"]
    else:
        check_cols_for_dup = available_dup_cols

    duplicates_mask = temp_df_for_dup_check.duplicated(subset=check_cols_for_dup, keep="first")
    num_duplicates = duplicates_mask.sum()

    if num_duplicates > 0:
        logger_instance.warning(f"Detected {num_duplicates} potential duplicate transactions in merged data.")
        for idx in df[duplicates_mask].index:
            _update_row_data_quality_flags_processing(df, idx, [DataQualityFlag.DUPLICATE_SUSPECTED])
            _log_data_quality_issue_processing(
                data_quality_issues_list,
                "merged_dup_check",
                idx,
                df.loc[idx].to_dict(),
                [DataQualityFlag.DUPLICATE_SUSPECTED],
                logger_instance
            )
    return df


def tag_settlements(df: pd.DataFrame, rules: Dict[str, Any]) -> pd.DataFrame:
    """
    Tag settlement transactions based on rules.
    """
    df = df.copy()
    
    # Get settlement keywords from rules
    settlement_keywords = rules.get("settlement_keywords", ["venmo", "zelle", "cash app", "paypal"])
    
    # Tag settlements based on merchant and description patterns
    is_settlement_merchant = df["Merchant"].str.lower().str.strip().isin(settlement_keywords)
    is_settlement_description = df["Description"].str.contains(
        r"payment\s+(to|from)\s+(ryan|jordyn)", case=False, regex=True, na=False
    )
    is_settlement = is_settlement_merchant | is_settlement_description
    df["TransactionType"] = np.where(is_settlement, "SETTLEMENT", "EXPENSE")
    
    return df


def apply_two_x_rule(df: pd.DataFrame, config: AnalysisConfig, 
                     data_quality_issues_list: List[Dict[str, Any]],
                     logger_instance: logging.Logger = logger) -> pd.DataFrame:
    """
    Apply 2x calculation rule for transactions with special notes.
    """
    df = df.copy()
    calculation_note_trigger = "2x to calculate"
    
    two_x_mask = df["Description"].str.contains(calculation_note_trigger, case=False, na=False)
    modified_indices = []

    for idx in df[two_x_mask].index:
        actual_amount_for_row = df.loc[idx, "ActualAmount"]
        new_allowed_amount = actual_amount_for_row * 2
        df.loc[idx, "AllowedAmount"] = new_allowed_amount
        modified_indices.append(idx)
        
        _update_row_data_quality_flags_processing(df, idx, [DataQualityFlag.MANUAL_CALCULATION_NOTE])
        _log_data_quality_issue_processing(
            data_quality_issues_list, "expense_2x_note_check", idx, df.loc[idx].to_dict(),
            [DataQualityFlag.MANUAL_CALCULATION_NOTE], logger_instance
        )

    if modified_indices:
        logger_instance.info(f"Applied 2x calculation to {len(modified_indices)} rows")
    
    return df


def detect_duplicates(df: pd.DataFrame, 
                     data_quality_issues_list: List[Dict[str, Any]],
                     logger_instance: logging.Logger = logger) -> pd.DataFrame:
    """
    Detect and flag potential duplicate transactions.
    """
    df = df.copy()
    
    if df.empty:
        return df

    # Ensure Date column is datetime
    if "Date" in df.columns and not pd.api.types.is_datetime64_any_dtype(df["Date"]):
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    dup_cols = ["Date", "Payer", "ActualAmount", "Merchant"]
    available_dup_cols = [col for col in dup_cols if col in df.columns]

    if len(available_dup_cols) < 3:
        logger_instance.warning(f"Skipping duplicate detection: insufficient columns")
        return df

    temp_df = df[available_dup_cols].copy()
    if pd.api.types.is_datetime64_any_dtype(temp_df["Date"]):
        temp_df["DateForDup"] = temp_df["Date"].dt.date
        check_cols = ["DateForDup"] + [col for col in available_dup_cols if col != "Date"]
    else:
        check_cols = available_dup_cols

    duplicates_mask = temp_df.duplicated(subset=check_cols, keep="first")
    
    for idx in df[duplicates_mask].index:
        _update_row_data_quality_flags_processing(df, idx, [DataQualityFlag.DUPLICATE_SUSPECTED])
        _log_data_quality_issue_processing(
            data_quality_issues_list, "duplicate_check", idx, df.loc[idx].to_dict(),
            [DataQualityFlag.DUPLICATE_SUSPECTED], logger_instance
        )
    
    return df


def flag_row_quality(df: pd.DataFrame, config: AnalysisConfig,
                    data_quality_issues_list: List[Dict[str, Any]],
                    logger_instance: logging.Logger = logger) -> pd.DataFrame:
    """
    Flag data quality issues for individual rows.
    """
    df = df.copy()
    
    for idx, row in df.iterrows():
        quality_flags = []
        
        # Check for missing date
        if pd.isna(row["Date"]):
            quality_flags.append(DataQualityFlag.MISSING_DATE)
            df.loc[idx, "Date"] = _impute_missing_date_processing(df, idx, "Date", logger_instance)

        # Check for outlier amounts
        if row["ActualAmount"] > config.OUTLIER_THRESHOLD:
            quality_flags.append(DataQualityFlag.OUTLIER_AMOUNT)
            
        # Check for negative amounts
        if row["ActualAmount"] < 0:
            quality_flags.append(DataQualityFlag.NEGATIVE_AMOUNT)
        if row["AllowedAmount"] < 0:
            quality_flags.append(DataQualityFlag.NEGATIVE_AMOUNT)
            logger_instance.warning(f"Row {idx}: Negative AllowedAmount clamped to 0")
            df.loc[idx, "AllowedAmount"] = 0
        
        if quality_flags:
            _update_row_data_quality_flags_processing(df, idx, quality_flags)
            _log_data_quality_issue_processing(
                data_quality_issues_list, "row_quality_check", idx, row.to_dict(), 
                quality_flags, logger_instance
            )
    
    return df


def _create_expense_audit_note(row: pd.Series, config: AnalysisConfig) -> str:
    """Create audit note for expense transactions."""
    try:
        actual_amount = row.get("ActualAmount", 0.0)
        allowed_amount = row.get("AllowedAmount", 0.0)
        payer = row.get("Payer", "N/A")
        desc = str(row.get("Description", "")).strip()
        quality = row.get("DataQualityFlag", DataQualityFlag.CLEAN.value)
        trans_type = row.get("TransactionType", "EXPENSE")

        actual_amount_f = float(actual_amount) if pd.notna(actual_amount) else 0.0
        allowed_amount_f = float(allowed_amount) if pd.notna(allowed_amount) else 0.0
        personal_portion = actual_amount_f - allowed_amount_f

        explanation = ""
        if trans_type == "SETTLEMENT":
            explanation = f"{payer} paid ${actual_amount_f:,.2f} | SETTLEMENT PAYMENT."
        elif not row.get("IsShared", False) or abs(allowed_amount_f) < 0.01:
            explanation = f"{payer} paid ${actual_amount_f:,.2f} | PERSONAL EXPENSE – not shared."
        elif abs(personal_portion) < 0.01:
            explanation = f"{payer} paid ${actual_amount_f:,.2f} | FULLY SHARED."
        else:
            reason = (f"REASON: {desc}" if desc else "REASON: no specific note for partial share.")
            explanation = (
                f"{payer} paid ${actual_amount_f:,.2f} | PARTIALLY SHARED: "
                f"only ${allowed_amount_f:,.2f} is shared. {reason}"
            )
        return f"{explanation} | DataQuality: {quality}"
    except Exception as e:
        logger.error(f"Error creating expense audit note for row {row.name if hasattr(row, 'name') else 'UNKNOWN'}: {e}")
        return f"Error in audit note. Quality: {row.get('DataQualityFlag', DataQualityFlag.CLEAN.value)}"


def calc_budget_variance(df: pd.DataFrame, config: AnalysisConfig,
                        data_quality_issues_list: List[Dict[str, Any]],
                        logger_instance: logging.Logger = logger) -> pd.DataFrame:
    """
    Calculate budget variance for rent data.
    """
    df = df.copy()
    
    # Check baseline variance
    if config.RENT_BASELINE > 0 and "GrossTotal" in df.columns:
        variance = (df["GrossTotal"] - config.RENT_BASELINE).abs() / config.RENT_BASELINE
        high_variance_mask = variance > config.RENT_VARIANCE_THRESHOLD
        
        for idx in df[high_variance_mask].index:
            _update_row_data_quality_flags_processing(df, idx, [DataQualityFlag.RENT_VARIANCE_HIGH])
            _log_data_quality_issue_processing(
                data_quality_issues_list, "rent_baseline_variance", idx, df.loc[idx].to_dict(), 
                [DataQualityFlag.RENT_VARIANCE_HIGH], logger_instance
            )

    # Check budget variance if available
    if "Budget_Variance_Pct" in df.columns:
        high_budget_variance_mask = df["Budget_Variance_Pct"].abs() > config.RENT_BUDGET_VARIANCE_THRESHOLD_PCT
        
        for idx in df[high_budget_variance_mask].index:
            _update_row_data_quality_flags_processing(df, idx, [DataQualityFlag.RENT_BUDGET_VARIANCE_HIGH])
            _log_data_quality_issue_processing(
                data_quality_issues_list, "rent_budget_variance", idx, df.loc[idx].to_dict(),
                [DataQualityFlag.RENT_BUDGET_VARIANCE_HIGH], logger_instance
            )
    
    return df


def expense_pipeline(df: pd.DataFrame, config: AnalysisConfig, rules: Dict[str, Any],
                    data_quality_issues_list: List[Dict[str, Any]],
                    logger_instance: logging.Logger = logger) -> pd.DataFrame:
    """
    Main expense processing pipeline orchestrator.
    Coordinates all expense processing steps with debug snapshots.
    """
    logger_instance.info("Starting expense processing pipeline...")
    
    if df.empty:
        logger_instance.warning("Empty expense data")
        return pd.DataFrame(columns=[
            "Date", "ActualAmount", "AllowedAmount", "Payer", "Description", "Merchant",
            "TransactionType", "DataQualityFlag", "IsShared", "RyanOwes", "JordynOwes",
            "BalanceImpact", "AuditNote"
        ])

    # Data preparation
    rename_map = {"Date of Purchase": "Date", "Name": "Payer"}
    df.rename(columns=rename_map, inplace=True)
    
    for col in ["Payer", "Description", "Merchant"]:
        if col not in df.columns: df[col] = ""
        df[col] = df[col].fillna("")

    if "Date" not in df.columns: df["Date"] = pd.NaT
    if "ActualAmount" not in df.columns: df["ActualAmount"] = 0.0
    if "AllowedAmount" not in df.columns: df["AllowedAmount"] = np.nan
    
    df["AllowedAmount"] = df["AllowedAmount"].fillna(df["ActualAmount"]).fillna(0)
    df["DataQualityFlag"] = DataQualityFlag.CLEAN.value

    # Step 1: Tag settlements
    df = tag_settlements(df, rules)
    if config.debug_mode:
        Path("debug_output").mkdir(exist_ok=True)
        df.to_csv("debug_output/03a_settlements_tagged.csv", index=False)

    # Step 2: Apply 2x rule  
    df = apply_two_x_rule(df, config, data_quality_issues_list, logger_instance)
    if config.debug_mode:
        df.to_csv("debug_output/03b_two_x_applied.csv", index=False)

    # Step 3: Detect duplicates
    df = detect_duplicates(df, data_quality_issues_list, logger_instance)
    if config.debug_mode:
        df.to_csv("debug_output/03c_duplicates_flagged.csv", index=False)

    # Step 4: Flag row quality issues
    df = flag_row_quality(df, config, data_quality_issues_list, logger_instance)
    if config.debug_mode:
        df.to_csv("debug_output/03d_quality_flagged.csv", index=False)

    # Final calculations using rules
    payer_split = rules.get("payer_split", {"ryan_pct": 0.43, "jordyn_pct": 0.57})
    ryan_pct = payer_split.get("ryan_pct", config.RYAN_PCT)
    jordyn_pct = payer_split.get("jordyn_pct", config.JORDYN_PCT)

    is_settlement = (df["TransactionType"] == "SETTLEMENT")
    
    # Settlement calculations
    df.loc[is_settlement, "AllowedAmount"] = 0
    df.loc[is_settlement, "IsShared"] = False
    df.loc[is_settlement, "RyanOwes"] = 0.0
    df.loc[is_settlement, "JordynOwes"] = 0.0

    # Non-settlement calculations
    non_settlement_mask = ~is_settlement
    df.loc[non_settlement_mask, "IsShared"] = (df.loc[non_settlement_mask, "AllowedAmount"] > 0.005)
    df.loc[non_settlement_mask, "RyanOwes"] = 0.0
    df.loc[non_settlement_mask, "JordynOwes"] = 0.0
    df.loc[non_settlement_mask, "BalanceImpact"] = 0.0

    # Shared expense calculations
    paid_by_ryan_shared = non_settlement_mask & df["IsShared"] & (df["Payer"].str.lower() == "ryan")
    paid_by_jordyn_shared = non_settlement_mask & df["IsShared"] & (df["Payer"].str.lower() == "jordyn")

    df.loc[paid_by_ryan_shared, "JordynOwes"] = (df.loc[paid_by_ryan_shared, "AllowedAmount"] * jordyn_pct).round(config.CURRENCY_PRECISION)
    df.loc[paid_by_jordyn_shared, "RyanOwes"] = (df.loc[paid_by_jordyn_shared, "AllowedAmount"] * ryan_pct).round(config.CURRENCY_PRECISION)

    df.loc[paid_by_ryan_shared, "BalanceImpact"] = -df.loc[paid_by_ryan_shared, "JordynOwes"]
    df.loc[paid_by_jordyn_shared, "BalanceImpact"] = df.loc[paid_by_jordyn_shared, "RyanOwes"]

    # Settlement balance impacts
    settlement_keywords = rules.get("settlement_keywords", [])
    ryan_paid_jordyn = is_settlement & (df["Payer"].str.lower() == "ryan") & \
                       (df["Description"].str.contains(r"to\s+jordyn", case=False, regex=True, na=False))
    jordyn_paid_ryan = is_settlement & (df["Payer"].str.lower() == "jordyn") & \
                       (df["Description"].str.contains(r"to\s+ryan", case=False, regex=True, na=False))

    df.loc[ryan_paid_jordyn, "BalanceImpact"] = -df.loc[ryan_paid_jordyn, "ActualAmount"]
    df.loc[jordyn_paid_ryan, "BalanceImpact"] = df.loc[jordyn_paid_ryan, "ActualAmount"]

    # Create audit notes
    df["AuditNote"] = df.apply(lambda row: _create_expense_audit_note(row, config), axis=1)

    logger_instance.info(f"Processed {len(df)} expense records, {is_settlement.sum()} settlements")
    return df


def rent_pipeline(df: pd.DataFrame, config: AnalysisConfig, rules: Dict[str, Any],
                 data_quality_issues_list: List[Dict[str, Any]],
                 logger_instance: logging.Logger = logger) -> pd.DataFrame:
    """
    Main rent processing pipeline orchestrator.
    Coordinates all rent processing steps with debug snapshots.
    """
    logger_instance.info("Starting rent processing pipeline...")
    
    if df.empty:
        logger_instance.warning("Empty rent data")
        return pd.DataFrame(columns=[
            "Date", "GrossTotal", "RyanRentPortion", "TransactionType", "Payer", "IsShared",
            "ActualAmount", "AllowedAmount", "DataQualityFlag", "RyanOwes", "JordynOwes",
            "BalanceImpact", "Description", "AuditNote", "Month_Display"
        ])

    # Data preparation
    rename_map = {
        "Month_Date": "Date", "Month": "Month_Display",
        "Ryan's Rent (43%)": "RyanRentPortion", 
        "Jordyn's Rent (57%)": "JordynRentPortion",
        "Gross Total": "GrossTotal"
    }
    actual_rename_map = {k: v for k, v in rename_map.items() if k in df.columns}
    df.rename(columns=actual_rename_map, inplace=True)
    
    if "Date" not in df.columns: df["Date"] = pd.NaT
    if "GrossTotal" not in df.columns: df["GrossTotal"] = 0.0
    if "RyanRentPortion" not in df.columns: df["RyanRentPortion"] = 0.0
    if "Month_Display" not in df.columns: df["Month_Display"] = "Unknown"

    df["TransactionType"] = "RENT"
    df["Payer"] = "Jordyn"
    df["IsShared"] = True
    df["ActualAmount"] = df["GrossTotal"]
    df["AllowedAmount"] = df["GrossTotal"]
    df["DataQualityFlag"] = DataQualityFlag.CLEAN.value

    # Calculate budget variance
    df = calc_budget_variance(df, config, data_quality_issues_list, logger_instance)
    if config.debug_mode:
        Path("debug_output").mkdir(exist_ok=True)
        df.to_csv("debug_output/03e_rent_budget_variance.csv", index=False)

    # Final calculations
    df["RyanOwes"] = df["RyanRentPortion"]
    df["JordynOwes"] = 0.0
    df["BalanceImpact"] = df["RyanOwes"]
    df["Description"] = df.apply(lambda r: f"Rent for {r.get('Month_Display', 'Unknown')}", axis=1)
    df["AuditNote"] = df.apply(lambda row: _create_enhanced_rent_audit_note(row, config), axis=1)

    logger_instance.info(f"Processed {len(df)} rent records")
    return df


def process_expense_data(
    merged_expense_ledger_df: pd.DataFrame, 
    config: AnalysisConfig,
    data_quality_issues_list: List[Dict[str, Any]], # To be populated by helper functions
    logger_instance: logging.Logger = logger
) -> pd.DataFrame:
    logger_instance.info("Processing merged expense and ledger data...")
    df = merged_expense_ledger_df.copy() # Work on a copy

    if df.empty:
        logger_instance.warning("Combined expense data is empty. Returning empty DataFrame.")
        essential_cols = [
            "Date", "ActualAmount", "AllowedAmount", "Payer", "Description", "Merchant",
            "TransactionType", "DataQualityFlag", "IsShared", "RyanOwes", "JordynOwes",
            "BalanceImpact", "AuditNote",
        ]
        return pd.DataFrame(columns=essential_cols)

    rename_map = {"Date of Purchase": "Date", "Name": "Payer"}
    df.rename(columns=rename_map, inplace=True)

    for col in ["Payer", "Description", "Merchant"]: # Ensure string columns exist and are strings
        if col not in df.columns: df[col] = ""
        df[col] = df[col].fillna("")

    if "Date" not in df.columns: df["Date"] = pd.NaT
    if "ActualAmount" not in df.columns: df["ActualAmount"] = 0.0
    
    if "AllowedAmount" not in df.columns: df["AllowedAmount"] = np.nan
    df["AllowedAmount"] = df["AllowedAmount"].fillna(df["ActualAmount"])
    df["AllowedAmount"] = df["AllowedAmount"].fillna(0)

    df["DataQualityFlag"] = DataQualityFlag.CLEAN.value

    # --- Settlement Detection ---
    # Using DEFAULT_SETTLEMENT_KEYWORDS from config module
    # For now, assume config.DEFAULT_SETTLEMENT_KEYWORDS
    settlement_keywords = ["venmo", "zelle", "cash app", "paypal"] # Placeholder

    is_settlement_merchant = df["Merchant"].str.lower().str.strip().isin(settlement_keywords)
    is_settlement_description = df["Description"].str.contains(
        r"payment\s+(to|from)\s+(ryan|jordyn)", case=False, regex=True, na=False
    )
    is_settlement = is_settlement_merchant | is_settlement_description
    df["TransactionType"] = np.where(is_settlement, "SETTLEMENT", "EXPENSE")

    df = _handle_calculation_notes_in_processed_data(df, config, data_quality_issues_list, logger_instance)
    df = _detect_duplicates_in_processed_data(df, data_quality_issues_list, logger_instance)

    for idx, row in df.iterrows():
        quality_flags_for_row = []
        if pd.isna(row["Date"]):
            quality_flags_for_row.append(DataQualityFlag.MISSING_DATE)
            df.loc[idx, "Date"] = _impute_missing_date_processing(df, idx, "Date", logger_instance)

        if row["ActualAmount"] > config.OUTLIER_THRESHOLD:
            quality_flags_for_row.append(DataQualityFlag.OUTLIER_AMOUNT)
        if row["ActualAmount"] < 0:
            quality_flags_for_row.append(DataQualityFlag.NEGATIVE_AMOUNT)
        if row["AllowedAmount"] < 0: # Should be caught by earlier fillna(0) if from NaN, but check explicit negatives
            quality_flags_for_row.append(DataQualityFlag.NEGATIVE_AMOUNT)
            logger_instance.warning(f"Row {idx}: Negative AllowedAmount detected ({row['AllowedAmount']}). Clamping to 0.")
            df.loc[idx, "AllowedAmount"] = 0
        
        if quality_flags_for_row:
            _update_row_data_quality_flags_processing(df, idx, quality_flags_for_row)
            _log_data_quality_issue_processing(
                data_quality_issues_list, "expense_row_check", idx, row.to_dict(), quality_flags_for_row, logger_instance
            )
    
    # --- Calculations ---
    df.loc[is_settlement, "AllowedAmount"] = 0
    df.loc[is_settlement, "IsShared"] = False
    df.loc[is_settlement, "RyanOwes"] = 0.0
    df.loc[is_settlement, "JordynOwes"] = 0.0

    ryan_paid_jordyn = is_settlement & (df["Payer"].str.lower() == "ryan") & \
                       (df["Description"].str.contains(r"to\s+jordyn", case=False, regex=True, na=False) | \
                        df["Merchant"].str.lower().isin([f"{k} to jordyn" for k in settlement_keywords]))
    jordyn_paid_ryan = is_settlement & (df["Payer"].str.lower() == "jordyn") & \
                       (df["Description"].str.contains(r"to\s+ryan", case=False, regex=True, na=False) | \
                        df["Merchant"].str.lower().isin([f"{k} to ryan" for k in settlement_keywords]))

    df.loc[ryan_paid_jordyn, "BalanceImpact"] = -df.loc[ryan_paid_jordyn, "ActualAmount"]
    df.loc[jordyn_paid_ryan, "BalanceImpact"] = df.loc[jordyn_paid_ryan, "ActualAmount"]

    non_settlement_mask = ~is_settlement
    df.loc[non_settlement_mask, "PersonalPortion"] = (df.loc[non_settlement_mask, "ActualAmount"] - df.loc[non_settlement_mask, "AllowedAmount"]).round(config.CURRENCY_PRECISION)
    df.loc[non_settlement_mask, "IsShared"] = (df.loc[non_settlement_mask, "AllowedAmount"] > 0.005)
    
    df.loc[non_settlement_mask, "RyanOwes"] = 0.0
    df.loc[non_settlement_mask, "JordynOwes"] = 0.0
    df.loc[non_settlement_mask, "BalanceImpact"] = 0.0 # Initialize for non-settlements

    paid_by_ryan_shared_mask = non_settlement_mask & df["IsShared"] & (df["Payer"].str.lower() == "ryan")
    paid_by_jordyn_shared_mask = non_settlement_mask & df["IsShared"] & (df["Payer"].str.lower() == "jordyn")

    df.loc[paid_by_ryan_shared_mask, "JordynOwes"] = (df.loc[paid_by_ryan_shared_mask, "AllowedAmount"] * config.JORDYN_PCT).round(config.CURRENCY_PRECISION)
    df.loc[paid_by_jordyn_shared_mask, "RyanOwes"] = (df.loc[paid_by_jordyn_shared_mask, "AllowedAmount"] * config.RYAN_PCT).round(config.CURRENCY_PRECISION)

    df.loc[paid_by_ryan_shared_mask, "BalanceImpact"] = -df.loc[paid_by_ryan_shared_mask, "JordynOwes"]
    df.loc[paid_by_jordyn_shared_mask, "BalanceImpact"] = df.loc[paid_by_jordyn_shared_mask, "RyanOwes"]
    
    df["AuditNote"] = df.apply(lambda row: _create_expense_audit_note(row, config), axis=1)
    
    logger_instance.info(f"Processed {len(df)} combined expense records. Detected {is_settlement.sum()} settlements.")
    return df


def _create_rent_audit_note(row: pd.Series, config: AnalysisConfig) -> str:
    """Base audit note for rent transactions."""
    try:
        gross_total = row.get("GrossTotal", 0.0)
        ryan_owes = row.get("RyanOwes", 0.0)
        gross_total_float = float(gross_total) if pd.notna(gross_total) else 0.0
        ryan_owes_float = float(ryan_owes) if pd.notna(ryan_owes) else 0.0
        month_display = row.get("Month_Display", row.get("Date", "Unknown Month"))
        if isinstance(month_display, pd.Timestamp):
            month_display = month_display.strftime("%b %Y")

        return (
            f"Rent {month_display}: Gross ${gross_total_float:,.2f} paid by {row.get('Payer', 'N/A')}. "
            f"Ryan's share ${ryan_owes_float:,.2f}. Quality: {row.get('DataQualityFlag', DataQualityFlag.CLEAN.value)}"
        )
    except Exception as e:
        logger.error(f"Error creating rent audit note for row {row.name if hasattr(row, 'name') else 'UNKNOWN'}: {e}")
        return f"Error in audit note. Quality: {row.get('DataQualityFlag', DataQualityFlag.CLEAN.value)}"

def _create_enhanced_rent_audit_note(row: pd.Series, config: AnalysisConfig) -> str:
    base_note = _create_rent_audit_note(row, config)
    budget_note_parts = []
    if "Total_Budgeted" in row and pd.notna(row["Total_Budgeted"]):
        budget_note_parts.append(f"Budgeted: ${row['Total_Budgeted']:,.2f}")
    if "Total_Actual" in row and pd.notna(row["Total_Actual"]):
        budget_note_parts.append(f"Actual: ${row['Total_Actual']:,.2f}")

    if "Budget_Variance" in row and pd.notna(row["Budget_Variance"]):
        variance = row["Budget_Variance"]
        variance_pct = row.get("Budget_Variance_Pct", 0)
        if abs(variance) > 0.01:
            budget_note_parts.append(f"Variance: ${variance:+.2f} ({variance_pct:+.1f}%)")

    if budget_note_parts:
        full_budget_note = " | Budget Info: " + ", ".join(budget_note_parts)
        if " Quality:" in base_note:
            base_note = base_note.replace(" Quality:", full_budget_note + " Quality:")
        else:
            base_note += full_budget_note
    return base_note


def process_rent_data(
    merged_rent_df: pd.DataFrame, 
    config: AnalysisConfig,
    data_quality_issues_list: List[Dict[str, Any]], # To be populated
    logger_instance: logging.Logger = logger
) -> pd.DataFrame:
    logger_instance.info("Processing merged rent data with budget analysis...")
    df = merged_rent_df.copy()

    if df.empty:
        logger_instance.warning("Combined rent data is empty. Returning empty DataFrame.")
        essential_cols = [
            "Date", "GrossTotal", "RyanRentPortion", "TransactionType", "Payer", "IsShared",
            "ActualAmount", "AllowedAmount", "DataQualityFlag", "RyanOwes", "JordynOwes",
            "BalanceImpact", "Description", "AuditNote", "Month_Display",
        ]
        return pd.DataFrame(columns=essential_cols)

    rename_map = {
        "Month_Date": "Date", "Month": "Month_Display",
        "Ryan's Rent (43%)": "RyanRentPortion", 
        "Jordyn's Rent (57%)": "JordynRentPortion",
        "Gross Total": "GrossTotal"
    }
    # Only rename if column exists to avoid KeyError
    actual_rename_map = {k: v for k, v in rename_map.items() if k in df.columns}
    df.rename(columns=actual_rename_map, inplace=True)
    
    if "Date" not in df.columns: df["Date"] = pd.NaT
    if "GrossTotal" not in df.columns: df["GrossTotal"] = 0.0
    if "RyanRentPortion" not in df.columns: df["RyanRentPortion"] = 0.0 # Calculate if missing?
    if "Month_Display" not in df.columns: df["Month_Display"] = "Unknown"


    df["TransactionType"] = "RENT"
    df["Payer"] = "Jordyn"  # Assumption
    df["IsShared"] = True
    df["ActualAmount"] = df["GrossTotal"]
    df["AllowedAmount"] = df["GrossTotal"]
    df["DataQualityFlag"] = DataQualityFlag.CLEAN.value

    if config.RENT_BASELINE > 0 and "GrossTotal" in df.columns:
        variance = (df["GrossTotal"] - config.RENT_BASELINE).abs() / config.RENT_BASELINE
        high_variance_baseline_mask = variance > config.RENT_VARIANCE_THRESHOLD
        for idx in df[high_variance_baseline_mask].index:
            _update_row_data_quality_flags_processing(df, idx, [DataQualityFlag.RENT_VARIANCE_HIGH])
            _log_data_quality_issue_processing(
                data_quality_issues_list, "rent_baseline_variance", idx, df.loc[idx].to_dict(), 
                [DataQualityFlag.RENT_VARIANCE_HIGH], logger_instance
            )

    if "Budget_Variance_Pct" in df.columns:
        high_variance_budget_mask = df["Budget_Variance_Pct"].abs() > config.RENT_BUDGET_VARIANCE_THRESHOLD_PCT
        for idx in df[high_variance_budget_mask].index:
            _update_row_data_quality_flags_processing(df, idx, [DataQualityFlag.RENT_BUDGET_VARIANCE_HIGH])
            _log_data_quality_issue_processing(
                data_quality_issues_list, "rent_budget_variance", idx, df.loc[idx].to_dict(),
                [DataQualityFlag.RENT_BUDGET_VARIANCE_HIGH], logger_instance
            )

    df["RyanOwes"] = df["RyanRentPortion"] # Assumes RyanRentPortion is correctly calculated or loaded
    df["JordynOwes"] = 0.0
    df["BalanceImpact"] = df["RyanOwes"]

    df["Description"] = df.apply(lambda r: f"Rent for {r.get('Month_Display', 'Unknown Month')}", axis=1)
    df["AuditNote"] = df.apply(lambda row: _create_enhanced_rent_audit_note(row, config), axis=1)

    logger_instance.info(f"Processed {len(df)} combined rent records.")
    return df


def build_baseline() -> pd.DataFrame:
    """
    Placeholder for the main function to build the baseline snapshot.
    This function will orchestrate loading, processing, and assembling
    the data required for baseline_snapshot.csv.
    """
    logger.info("build_baseline() called. Placeholder implementation.")
    # In a real implementation, this would involve:
    # 1. Loading necessary data (e.g., using functions from a loaders.py within baseline_analyzer)
    # 2. Applying specific configurations or rules for the baseline
    # 3. Running relevant processing steps (e.g., simplified versions of expense/rent pipelines)
    # 4. Assembling the final DataFrame for the snapshot.
    
    # For now, returning an empty DataFrame with expected columns for the CLI to work.
    # The actual columns will depend on what 'baseline_snapshot.csv' should contain.
    # Example columns:
    # return pd.DataFrame(columns=["Date", "Description", "Amount", "Category", "Status"])
    
    # For P0, the user's plan implies `build_baseline().to_csv("baseline_snapshot.csv", index=False)`
    # So, it needs to return a DataFrame.
    # Let's return a very simple DataFrame for now.
    data = {'col1': [1, 2], 'col2': ['A', 'B']}
    return pd.DataFrame(data)
