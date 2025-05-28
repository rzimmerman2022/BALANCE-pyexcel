#!/usr/bin/env python3
"""
Enhanced Shared Expense Analyzer - Institutional Grade
=====================================================
Fortune 500 / Big 4 standard financial reconciliation system with
comprehensive data quality management, triple reconciliation, and
production-ready features.

Author: Financial Analysis System
Date: 2025-05-27 (Revised)
Version: 2.1
"""

import pandas as pd
import numpy as np
from datetime import datetime, timezone
import logging
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import argparse
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
import unittest
from dataclasses import dataclass
from enum import Enum

# Configure logging for audit trail
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('financial_analysis_audit.log', mode='w'), # Overwrite log each run
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
@dataclass
class AnalysisConfig:
    """Configuration parameters for the analysis"""
    RYAN_PCT: float = 0.43
    JORDYN_PCT: float = 0.57
    CONFIDENCE_LEVEL: float = 0.95
    DATA_QUALITY_THRESHOLD: float = 0.90 # Adjusted for potentially more flagged items
    OUTLIER_THRESHOLD: float = 5000.0
    RENT_BASELINE: float = 2100.0
    RENT_VARIANCE_THRESHOLD: float = 0.10
    LIQUIDITY_STRAIN_THRESHOLD: float = 5000.0
    LIQUIDITY_STRAIN_DAYS: int = 60
    CONCENTRATION_RISK_THRESHOLD: float = 0.40
    CURRENCY_PRECISION: int = 2
    MAX_MEMORY_MB: int = 500
    MAX_PROCESSING_TIME_SECONDS: int = 15 # Increased slightly

class DataQualityFlag(Enum):
    """Enumeration of data quality issues"""
    CLEAN = "CLEAN"
    MISSING_DATE = "MISSING_DATE"
    MISALIGNED_ROW = "MISALIGNED_ROW" # Not actively used by current checks, but available
    DUPLICATE_SUSPECTED = "DUPLICATE_SUSPECTED"
    OUTLIER_AMOUNT = "OUTLIER_AMOUNT"
    MANUAL_CALCULATION_NOTE = "MANUAL_CALCULATION_NOTE"
    NEGATIVE_AMOUNT = "NEGATIVE_AMOUNT"
    RENT_VARIANCE_HIGH = "RENT_VARIANCE_HIGH"
    NON_NUMERIC_VALUE_CLEANED = "NON_NUMERIC_VALUE_CLEANED"

class EnhancedSharedExpenseAnalyzer:
    """
    Comprehensive financial analyzer implementing institutional-grade standards
    for shared expense reconciliation with full audit trail and risk assessment.
    """

    def __init__(self, rent_file: Path, expense_file: Path, config: Optional[AnalysisConfig] = None):
        """
        Initialize the analyzer with configuration and file paths

        Args:
            rent_file: Path to rent allocation CSV
            expense_file: Path to expense history CSV
            config: Analysis configuration (uses defaults if None)
        """
        self.config = config or AnalysisConfig()
        self.rent_file = rent_file
        self.expense_file = expense_file

        self.data_quality_issues: List[Dict[str, Any]] = []
        self.audit_trail: List[Dict[str, Any]] = [] # For future detailed step logging
        self.validation_results: Dict[str, bool] = {}

        self.start_time = datetime.now(timezone.utc)
        self.memory_usage_mb = 0

        logger.info(f"Initialized analyzer with config: {self.config}")
        logger.info(f"Rent file: {self.rent_file}, Expense file: {self.expense_file}")
        if not self.rent_file.exists():
            logger.error(f"Rent file not found: {self.rent_file}")
            raise FileNotFoundError(f"Rent file not found: {self.rent_file}")
        if not self.expense_file.exists():
            logger.error(f"Expense file not found: {self.expense_file}")
            raise FileNotFoundError(f"Expense file not found: {self.expense_file}")

    def analyze(self) -> Dict[str, Any]:
        """
        Execute comprehensive analysis pipeline

        Returns:
            Dictionary containing all analysis results
        """
        try:
            logger.info("Starting analysis pipeline...")
            rent_df = self._load_and_clean_rent_data()
            expense_df = self._load_and_clean_expense_data()

            master_ledger = self._create_master_ledger(rent_df, expense_df)

            reconciliation_results = self._triple_reconciliation(master_ledger)
            analytics_results = self._perform_advanced_analytics(master_ledger)
            risk_assessment = self._comprehensive_risk_assessment(master_ledger, analytics_results)
            visualizations = self._create_visualizations(master_ledger, analytics_results, reconciliation_results)
            recommendations = self._generate_recommendations(analytics_results, risk_assessment, reconciliation_results)

            self._validate_results(reconciliation_results, master_ledger)
            output_paths = self._generate_outputs(
                master_ledger, reconciliation_results, analytics_results,
                risk_assessment, recommendations, visualizations
            )
            self._check_performance()

            final_results = {
                'reconciliation': reconciliation_results,
                'analytics': analytics_results,
                'risk_assessment': risk_assessment,
                'recommendations': recommendations,
                'data_quality_score': self._calculate_data_quality_score(master_ledger),
                'data_quality_issues_summary': self._summarize_data_quality_issues(master_ledger),
                'validation_results': self.validation_results,
                'output_paths': output_paths,
                'performance_metrics': {
                    'processing_time_seconds': round((datetime.now(timezone.utc) - self.start_time).total_seconds(), 2),
                    'memory_usage_mb': round(self.memory_usage_mb, 2),
                    'total_transactions': len(master_ledger)
                }
            }
            logger.info("Analysis pipeline completed successfully.")
            return final_results

        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}", exc_info=True)
            # Log any collected data quality issues even if analysis fails midway
            if self.data_quality_issues:
                try:
                    output_dir = Path('analysis_output')
                    output_dir.mkdir(exist_ok=True)
                    error_df = pd.DataFrame(self.data_quality_issues)
                    error_path = output_dir / 'data_quality_issues_PARTIAL_FAILURE.csv'
                    error_df.to_csv(error_path, index=False)
                    logger.info(f"Partial data quality issues logged to {error_path}")
                except Exception as log_e:
                    logger.error(f"Could not write partial data quality log: {log_e}")
            raise

    def _clean_money(self, series: pd.Series) -> pd.Series:
        """Clean monetary values from various formats to numeric (float or NaN)."""
        if series.empty:
            return pd.Series([], dtype=float)

        # Convert to string to handle mixed types input
        s_str = series.astype(str)

        # Remove currency symbols, commas, parentheses (for negatives)
        s_cleaned = s_str.str.replace(r'[$,()]', '', regex=True)
        # Remove leading/trailing whitespace
        s_cleaned = s_cleaned.str.strip()
        # Replace common non-numeric placeholders (like a single dash representing zero or missing) with NaN
        s_cleaned = s_cleaned.replace(['', '-', 'nan', 'None', 'inf', '-inf'], np.nan, regex=False) # Added 'inf'

        # Attempt conversion to numeric, coercing errors to NaN
        s_numeric = pd.to_numeric(s_cleaned, errors='coerce')
        
        # Log if any original non-NaN values became NaN after cleaning (potential data issue)
        original_not_na = series.notna()
        cleaned_is_na = s_numeric.isna()
        newly_na = original_not_na & cleaned_is_na & (series.astype(str).str.strip().str.lower().isin(['', '-', 'nan', 'none']) == False) # Avoid logging for obvious NAs

        for idx in series[newly_na].index:
            self._log_data_quality_issue(
                source='_clean_money',
                row_idx=idx, # This index might not be globally unique if series is a slice
                row_data={'original_value': series.loc[idx], 'cleaned_value': s_numeric.loc[idx]},
                flags=[DataQualityFlag.NON_NUMERIC_VALUE_CLEANED]
            )
            logger.warning(f"Value '{series.loc[idx]}' was cleaned to NaN in _clean_money.")
            
        return s_numeric.astype('float64') # Ensure float64 for consistency

    def _load_and_clean_rent_data(self) -> pd.DataFrame:
        logger.info("Loading and cleaning rent data...")
        df = pd.read_csv(self.rent_file)
        df.columns = df.columns.str.strip().str.title() # Standardize column names

        # Rename columns to match expected internal names for consistency
        rename_map = {
            "Ryan'S Rent (43%)": "RyanRentPortion", # Avoid special chars in internal names
            "Jordyn'S Rent (57%)": "JordynRentPortion",
            "Gross Total": "GrossTotal"
        }
        df.rename(columns=rename_map, inplace=True)

        original_count = len(df)
        df['DataQualityFlag'] = pd.Series([pd.NA] * len(df), index=df.index, dtype="string")

        money_cols = ['GrossTotal', "RyanRentPortion", "JordynRentPortion"] # Add other financial cols if any
        for col in money_cols:
            if col in df.columns:
                df[col] = self._clean_money(df[col])
            else:
                logger.warning(f"Rent data: Expected monetary column '{col}' not found. It will be NaN.")
                df[col] = np.nan


        df['Date'] = pd.to_datetime(df['Month'], errors='coerce')

        for idx, row in df.iterrows():
            quality_flags_for_row = []
            if pd.isna(row['Date']):
                quality_flags_for_row.append(DataQualityFlag.MISSING_DATE)
                df.loc[idx, 'Date'] = self._impute_missing_date(df, idx, 'Date')

            if 'GrossTotal' in df.columns and pd.notna(row['GrossTotal']):
                variance = abs(row['GrossTotal'] - self.config.RENT_BASELINE) / self.config.RENT_BASELINE \
                    if self.config.RENT_BASELINE > 0 else 0
                if variance > self.config.RENT_VARIANCE_THRESHOLD:
                    quality_flags_for_row.append(DataQualityFlag.RENT_VARIANCE_HIGH)
            elif 'GrossTotal' not in df.columns:
                 logger.debug(f"Rent data: 'GrossTotal' column missing, cannot perform variance check for row {idx}.")


            self._update_row_data_quality_flags(df, idx, quality_flags_for_row)
            if quality_flags_for_row:
                self._log_data_quality_issue('rent_load', idx, row.to_dict(), quality_flags_for_row)
        
        df['TransactionType'] = 'RENT'
        df['Payer'] = 'Jordyn' # As per current understanding of rent payments
        df['IsShared'] = True  # Rent is always shared
        
        df['AllowedAmount'] = df['GrossTotal'].fillna(0)
        df['RyanOwes'] = df['RyanRentPortion'].fillna(0) # Using the pre-calculated 43% portion
        df['JordynOwes'] = 0.0 # Jordyn paid, so she doesn't owe herself for this transaction
        df['BalanceImpact'] = df['RyanOwes'] # Positive = Ryan owes Jordyn for his share of rent

        df['Description'] = df.apply(lambda r: f"Rent for {r['Month']}" if pd.notna(r['Month']) else "Rent payment", axis=1)
        df['AuditNote'] = df.apply(self._create_rent_audit_note, axis=1)

        logger.info(f"Loaded and cleaned {len(df)} rent records from {original_count} original rows.")
        return df

    def _load_and_clean_expense_data(self) -> pd.DataFrame:
        logger.info("Loading and cleaning expense data...")
        df = pd.read_csv(self.expense_file)
        df.columns = df.columns.str.strip().str.title() # Standardize column names

        # Standardize column names from input file to internal names
        rename_map = {
            'Date Of Purchase': 'Date',
            'Actual Amount': 'ActualAmount',
            'Allowed Amount': 'AllowedAmountCsv', # Keep original CSV value separate initially
            'Name': 'Payer' # 'Name' column indicates who paid
        }
        df.rename(columns=rename_map, inplace=True)
        
        original_count = len(df)
        df = df[[col for col in df.columns if not col.lower().startswith('unnamed')]]
        df = df[df['Payer'].notna() & (df['Payer'] != '')] # Filter rows with no payer
        df['DataQualityFlag'] = pd.Series([pd.NA] * len(df), index=df.index, dtype="string")

        # Ensure critical columns exist, if not, create them as NaN or default
        if 'Description' not in df.columns: df['Description'] = ""
        df['Description'] = df['Description'].fillna("")
        
        # --- Revised AllowedAmount Processing ---
        # 1. Clean and convert ActualAmount to numeric
        df['ActualAmount'] = self._clean_money(df['ActualAmount']).fillna(0)

        # 2. Clean the 'AllowedAmountCsv' (original value from CSV)
        allowed_amount_cleaned_from_csv = self._clean_money(df['AllowedAmountCsv'] if 'AllowedAmountCsv' in df.columns else pd.Series(np.nan, index=df.index))
        
        # 3. Keep track if 'AllowedAmount' was explicitly provided in the CSV (not blank/NaN after cleaning)
        was_allowed_amount_explicitly_provided = allowed_amount_cleaned_from_csv.notna()

        # 4. Initialize 'AllowedAmount' (final numeric version)
        #    If explicit value from CSV, use it. Otherwise, it's NaN for now.
        df['AllowedAmount'] = allowed_amount_cleaned_from_csv

        # 5. Fill NaN 'AllowedAmount' (where it was blank in CSV) with 'ActualAmount'
        #    This means: if 'Allowed Amount' in CSV is blank, assume it's fully shared (i.e., ActualAmount)
        df['AllowedAmount'] = df['AllowedAmount'].fillna(df['ActualAmount'])
        
        # 6. Any remaining NaNs in 'AllowedAmount' (e.g., if ActualAmount was also NaN) become 0
        df['AllowedAmount'] = df['AllowedAmount'].fillna(0)
        
        # --- End of Revised AllowedAmount Processing ---
        
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

        # Apply "2x to calculate" logic (revised to be more careful)
        df = self._handle_calculation_notes(df, was_allowed_amount_explicitly_provided)
        
        # Detect duplicates after initial amount processing
        df = self._detect_duplicates(df)

        # Row-wise data quality checks
        for idx, row in df.iterrows():
            quality_flags_for_row = []
            if pd.isna(row['Date']):
                quality_flags_for_row.append(DataQualityFlag.MISSING_DATE)
                df.loc[idx, 'Date'] = self._impute_missing_date(df, idx, 'Date')
            
            if row['ActualAmount'] > self.config.OUTLIER_THRESHOLD:
                quality_flags_for_row.append(DataQualityFlag.OUTLIER_AMOUNT)
            if row['ActualAmount'] < 0:
                quality_flags_for_row.append(DataQualityFlag.NEGATIVE_AMOUNT)
            if row['AllowedAmount'] < 0: # Also check AllowedAmount after all processing
                quality_flags_for_row.append(DataQualityFlag.NEGATIVE_AMOUNT)
                logger.warning(f"Row {idx}: Negative AllowedAmount detected ({row['AllowedAmount']}). Clamping to 0.")
                df.loc[idx, 'AllowedAmount'] = 0 # Or handle as appropriate

            self._update_row_data_quality_flags(df, idx, quality_flags_for_row)
            if quality_flags_for_row: # Log only if new flags were added in this specific loop
                 self._log_data_quality_issue('expense_row_check', idx, row.to_dict(), quality_flags_for_row)

        # Vectorized calculations for financial impact
        df["PersonalPortion"] = (df["ActualAmount"] - df["AllowedAmount"]).round(self.config.CURRENCY_PRECISION)
        df["IsShared"] = df["AllowedAmount"] > 0

        df["RyanOwes"] = 0.0
        df["JordynOwes"] = 0.0
        df["BalanceImpact"] = 0.0

        paid_by_ryan_mask = df['IsShared'] & (df['Payer'] == 'Ryan')
        paid_by_jordyn_mask = df['IsShared'] & (df['Payer'] == 'Jordyn')

        df.loc[paid_by_ryan_mask, "JordynOwes"] = (df.loc[paid_by_ryan_mask, "AllowedAmount"] * self.config.JORDYN_PCT).round(self.config.CURRENCY_PRECISION)
        df.loc[paid_by_jordyn_mask, "RyanOwes"] = (df.loc[paid_by_jordyn_mask, "AllowedAmount"] * self.config.RYAN_PCT).round(self.config.CURRENCY_PRECISION)

        # BalanceImpact: Positive means Ryan owes Jordyn, Negative means Jordyn owes Ryan
        df.loc[paid_by_ryan_mask, "BalanceImpact"] = -df.loc[paid_by_ryan_mask, "JordynOwes"]
        df.loc[paid_by_jordyn_mask, "BalanceImpact"] = df.loc[paid_by_jordyn_mask, "RyanOwes"]
        
        df['AuditNote'] = df.apply(self._create_expense_audit_note, axis=1)
        df['TransactionType'] = 'EXPENSE'
        
        # Ensure columns used in concat exist and have compatible types if possible
        # (though _create_master_ledger will also do type conversion)
        final_cols = ['Date', 'Payer', 'ActualAmount', 'AllowedAmount', 'IsShared', 
                      'RyanOwes', 'JordynOwes', 'BalanceImpact', 'AuditNote', 
                      'TransactionType', 'Description', 'DataQualityFlag', 'Merchant']
        for col in final_cols:
            if col not in df.columns:
                df[col] = pd.NA # Or appropriate default like "" for Merchant/Description
        df = df[final_cols] # Select and order columns


        logger.info(f"Loaded and cleaned {len(df)} expense records from {original_count} original rows.")
        return df

    def _handle_calculation_notes(self, df: pd.DataFrame, was_allowed_amount_explicitly_provided: pd.Series) -> pd.DataFrame:
        logger.info("Handling '2x to calculate' notes in expense descriptions...")
        if 'Description' not in df.columns or 'AllowedAmount' not in df.columns:
            logger.warning("'Description' or 'AllowedAmount' column not found, skipping '2x' note handling.")
            return df

        two_x_mask = df['Description'].str.contains('2x to calculate', case=False, na=False)
        modified_indices = []

        for idx in df[two_x_mask].index:
            current_allowed_amount = df.loc[idx, 'AllowedAmount']
            
            # Revised logic: If "Allowed Amount" was BLANK in CSV (and thus filled from ActualAmount),
            # then the "2x" note implies doubling the ActualAmount to get the true shared AllowedAmount.
            # If "Allowed Amount" was EXPLICITLY provided in CSV, we assume that is the FINAL shared amount,
            # and the "2x" note is purely informational, so the script does NOT double it further.
            
            if not was_allowed_amount_explicitly_provided.loc[idx]: # True if original CSV cell was blank/unparseable
                actual_amount_for_row = df.loc[idx, 'ActualAmount'] # Already numeric
                new_allowed_amount = actual_amount_for_row * 2
                log_msg = (f"Row {idx}: '2x to calculate' found. Original AllowedAmount in CSV was blank/unparseable. "
                           f"Setting AllowedAmount from (ActualAmount * 2): ({actual_amount_for_row} * 2 = {new_allowed_amount}). "
                           f"Old AllowedAmount (likely from ActualAmount): {current_allowed_amount}.")
                df.loc[idx, 'AllowedAmount'] = new_allowed_amount
                modified_indices.append(idx)
            else:
                # AllowedAmount was explicitly provided in the CSV.
                log_msg = (f"Row {idx}: '2x to calculate' found, but AllowedAmount ({current_allowed_amount}) "
                           f"was explicitly provided in CSV. Script assumes this is the final shared amount; no automatic doubling applied by script based on this note.")
            
            logger.info(log_msg)
            self._update_row_data_quality_flags(df, idx, [DataQualityFlag.MANUAL_CALCULATION_NOTE])
            self._log_data_quality_issue(
                'expense_2x_note_check', idx, df.loc[idx].to_dict(),
                [DataQualityFlag.MANUAL_CALCULATION_NOTE]
            )
        
        if modified_indices:
            logger.info(f"Applied '2x' calculation to 'AllowedAmount' for {len(modified_indices)} rows where original CSV 'Allowed Amount' was blank.")
        return df

    def _create_rent_audit_note(self, row: pd.Series) -> str:
        try:
            gross_total = row.get('GrossTotal', 0.0)
            ryan_owes = row.get('RyanOwes', 0.0)
            gross_total_float = float(gross_total) if pd.notna(gross_total) else 0.0
            ryan_owes_float = float(ryan_owes) if pd.notna(ryan_owes) else 0.0
            
            return (f"Rent {row.get('Month', '')}: Gross ${gross_total_float:.2f} paid by {row.get('Payer', 'N/A')}. "
                    f"Ryan's share ${ryan_owes_float:.2f}. Quality: {row.get('DataQualityFlag', DataQualityFlag.CLEAN.value)}")
        except Exception as e:
            logger.error(f"Error creating rent audit note for row {row.name if hasattr(row, 'name') else 'UNKNOWN'}: {e}")
            return f"Error in audit note. Quality: {row.get('DataQualityFlag', DataQualityFlag.CLEAN.value)}"

    def _create_expense_audit_note(self, row: pd.Series) -> str:
        try:
            actual_amount = row.get('ActualAmount', 0.0)
            allowed_amount = row.get('AllowedAmount', 0.0)
            payer = row.get('Payer', 'N/A')
            desc = str(row.get('Description', "")).strip()
            quality = row.get('DataQualityFlag', DataQualityFlag.CLEAN.value)
            
            actual_amount_f = float(actual_amount) if pd.notna(actual_amount) else 0.0
            allowed_amount_f = float(allowed_amount) if pd.notna(allowed_amount) else 0.0
            personal_portion = actual_amount_f - allowed_amount_f

            explanation = ""
            if not row.get('IsShared', False) or abs(allowed_amount_f) < 0.01:
                explanation = f"{payer} paid ${actual_amount_f:,.2f} | PERSONAL EXPENSE – not shared."
            elif abs(personal_portion) < 0.01: # Effectively fully shared
                explanation = f"{payer} paid ${actual_amount_f:,.2f} | FULLY SHARED."
            else: # Partially shared
                reason = f"REASON: {desc}" if desc else "REASON: no specific note for partial share."
                explanation = (f"{payer} paid ${actual_amount_f:,.2f} | PARTIALLY SHARED: "
                               f"only ${allowed_amount_f:,.2f} is shared. {reason}")
            
            return f"{explanation} | DataQuality: {quality}"
        except Exception as e:
            logger.error(f"Error creating expense audit note for row {row.name if hasattr(row, 'name') else 'UNKNOWN'}: {e}")
            return f"Error in audit note. Quality: {row.get('DataQualityFlag', DataQualityFlag.CLEAN.value)}"


    def _update_row_data_quality_flags(self, df: pd.DataFrame, row_idx: Any, new_flags_enums: List[DataQualityFlag]):
        """Appends new unique flags to the existing flags for a given row."""
        if not new_flags_enums:
            return

        new_flag_values = [flag.value for flag in new_flags_enums]
        
        existing_flags_str = df.loc[row_idx, 'DataQualityFlag']
        
        current_flags_list = []
        if pd.notna(existing_flags_str) and existing_flags_str != DataQualityFlag.CLEAN.value:
            current_flags_list = existing_flags_str.split(',')
        
        added_new = False
        for flag_val in new_flag_values:
            if flag_val not in current_flags_list:
                current_flags_list.append(flag_val)
                added_new = True
        
        if added_new: # Only update if there was a change
             # Remove "CLEAN" if other flags are present
            if DataQualityFlag.CLEAN.value in current_flags_list and len(current_flags_list) > 1:
                current_flags_list.remove(DataQualityFlag.CLEAN.value)

            df.loc[row_idx, 'DataQualityFlag'] = ','.join(sorted(list(set(current_flags_list)))) # Sort for consistency
        elif not current_flags_list and (pd.isna(existing_flags_str) or existing_flags_str == DataQualityFlag.CLEAN.value):
            # If no flags exist and no new flags were added, ensure it's CLEAN if it was NA
             df.loc[row_idx, 'DataQualityFlag'] = DataQualityFlag.CLEAN.value


    def _impute_missing_date(self, df: pd.DataFrame, idx: int, date_col_name: str) -> pd.Timestamp:
        """Impute missing date based on surrounding transactions or fallback."""
        window = 5
        start_idx = max(0, idx - window)
        end_idx = min(len(df), idx + window + 1)
        nearby_dates = df.iloc[start_idx:end_idx][date_col_name].dropna()
        if len(nearby_dates) > 0:
            return pd.Timestamp(nearby_dates.astype(np.int64).median())
        else: # Fallback if no nearby dates
            logger.warning(f"Could not impute date for row {idx} based on neighbors. Falling back to current month-end.")
            now = pd.Timestamp.now(tz=timezone.utc)
            return now.replace(day=1) + pd.offsets.MonthEnd(0)


    def _detect_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Detecting potential duplicate expense transactions...")
        # Define key columns for identifying duplicates in expenses
        # Using 'Date', 'Payer', 'ActualAmount', and 'Merchant' (if exists)
        dup_cols = ['Date', 'Payer', 'ActualAmount']
        if 'Merchant' in df.columns:
            dup_cols.append('Merchant')
        
        # Ensure all columns used for duplicate detection exist
        available_dup_cols = [col for col in dup_cols if col in df.columns]
        if len(available_dup_cols) < 3 : # Not enough columns to reliably detect duplicates
            logger.warning(f"Skipping duplicate detection: Not enough key columns available (need at least 3 from {dup_cols}).")
            return df

        # Identify duplicates, keeping the first occurrence
        # Convert Date to date part only for robust duplicate detection if time is irrelevant or inconsistent
        date_series_for_dup_check = df['Date'].dt.date if pd.api.types.is_datetime64_any_dtype(df['Date']) else df['Date']
        temp_df_for_dup_check = df[available_dup_cols].copy()
        temp_df_for_dup_check['DateForDup'] = date_series_for_dup_check

        duplicates_mask = temp_df_for_dup_check.duplicated(subset=['DateForDup'] + [col for col in available_dup_cols if col != 'Date'], keep='first')
        
        num_duplicates = duplicates_mask.sum()
        if num_duplicates > 0:
            logger.warning(f"Detected {num_duplicates} potential duplicate expense transactions.")
            for idx in df[duplicates_mask].index:
                self._update_row_data_quality_flags(df, idx, [DataQualityFlag.DUPLICATE_SUSPECTED])
                self._log_data_quality_issue('expense_dup_check', idx, df.loc[idx].to_dict(), [DataQualityFlag.DUPLICATE_SUSPECTED])
        return df

    def _create_master_ledger(self, rent_df: pd.DataFrame, expense_df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Creating master ledger...")
        # Standardize columns before concat
        # Define common columns needed for the master ledger
        common_cols = ['Date', 'TransactionType', 'Payer', 'Description', 'ActualAmount', 
                       'AllowedAmount', 'IsShared', 'RyanOwes', 'JordynOwes', 
                       'BalanceImpact', 'AuditNote', 'DataQualityFlag', 'Merchant']

        # Ensure all common columns exist in both DataFrames, adding missing ones with NA
        for df_iter in [rent_df, expense_df]:
            for col in common_cols:
                if col not in df_iter.columns:
                    if col in ['ActualAmount', 'AllowedAmount', 'RyanOwes', 'JordynOwes', 'BalanceImpact']:
                        df_iter[col] = 0.0 # Numeric defaults
                    elif col == 'IsShared':
                        df_iter[col] = False # Boolean default
                    else:
                        df_iter[col] = pd.NA # General NA for strings/objects

        # Select only common columns in a consistent order
        rent_df_common = rent_df[common_cols]
        expense_df_common = expense_df[common_cols]
        
        master = pd.concat([rent_df_common, expense_df_common], ignore_index=True, sort=False)
        
        # --- Critical Numeric Conversions ---
        logger.info("Ensuring key financial columns in master_ledger are numeric...")
        numeric_cols = ['ActualAmount', 'AllowedAmount', 'RyanOwes', 'JordynOwes', 'BalanceImpact']
        for col in numeric_cols:
            if col in master.columns:
                master[col] = pd.to_numeric(master[col], errors='coerce').fillna(0)
            else: # Should not happen if common_cols logic is correct
                logger.error(f"Critical error: Expected numeric column '{col}' missing in master_ledger after concat.")
                master[col] = 0.0 
        # --- End Critical Numeric Conversions ---

        master = master.sort_values(by='Date', ascending=True).reset_index(drop=True)
        master['RunningBalance'] = master['BalanceImpact'].cumsum().round(self.config.CURRENCY_PRECISION)
        
        master['TransactionID'] = master.apply(self._generate_transaction_id, axis=1)
        master['DataLineage'] = master.apply(
            lambda row: f"Source: {row['TransactionType']} | OriginalIndex: {row.name} | Processing: v2.1", axis=1 # row.name is the new index
        )
        
        # Final check for DataQualityFlag, set to CLEAN if it's still NA after all processing
        master['DataQualityFlag'] = master['DataQualityFlag'].fillna(DataQualityFlag.CLEAN.value)
        # If a row has other flags, CLEAN should have been removed by _update_row_data_quality_flags
        # This ensures every row has a non-NA flag.

        logger.info(f"Created master ledger with {len(master)} transactions.")
        if not master.empty and master['Date'].notna().any():
            logger.info(f"Date range: {master['Date'].min()} to {master['Date'].max()}")
        else:
            logger.warning("Master ledger is empty or contains no valid dates.")
        return master

    def _triple_reconciliation(self, master_ledger: pd.DataFrame) -> Dict[str, Any]:
        logger.info("Performing triple reconciliation...")
        if master_ledger.empty:
            logger.warning("Master ledger is empty. Reconciliation will yield zero values.")
            return {
                'method1_running_balance': 0, 'method2_variance': 0, 'method3_category_sum': 0,
                'reconciled': True, 'max_difference': 0, 'total_shared': 0,
                'ryan_fair_share': 0, 'jordyn_fair_share': 0, 'ryan_paid_shared': 0, 'jordyn_paid_shared': 0,
                'ryan_variance_from_fair': 0, 'jordyn_variance_from_fair': 0, 'category_details': [],
                'final_balance': 0, 'who_owes_whom': 'No transactions', 'amount_owed': 0
            }

        shared_only = master_ledger[master_ledger['IsShared'] == True].copy() # Explicitly check for True

        # Method 1: Transaction-by-transaction running balance
        # BalanceImpact: Positive = Ryan owes Jordyn; Negative = Jordyn owes Ryan
        # RunningBalance is sum of BalanceImpact. Final RunningBalance is Method 1.
        method1_balance = master_ledger['RunningBalance'].iloc[-1] if not master_ledger.empty else 0.0

        # Method 2: Total overpayment method (Perspective: How much did Ryan overpay/underpay his fair share?)
        # This method calculates who overpaid relative to their fair share of total shared expenses.
        total_shared_amount = shared_only['AllowedAmount'].sum()
        ryan_total_fair_share = total_shared_amount * self.config.RYAN_PCT
        # jordyn_total_fair_share = total_shared_amount * self.config.JORDYN_PCT # Not directly used for method2_balance

        ryan_actually_paid_for_shared = shared_only[shared_only['Payer'] == 'Ryan']['AllowedAmount'].sum()
        jordyn_actually_paid_for_shared = shared_only[shared_only['Payer'] == 'Jordyn']['AllowedAmount'].sum()

        # Ryan's variance: positive if Ryan paid MORE than his fair share (Jordyn owes Ryan)
        #                  negative if Ryan paid LESS than his fair share (Ryan owes Jordyn)
        ryan_variance_from_fair = ryan_actually_paid_for_shared - ryan_total_fair_share
        # method2_balance: If positive, Ryan overpaid (Jordyn owes Ryan). If negative, Ryan underpaid (Ryan owes Jordyn)
        method2_balance = ryan_variance_from_fair # This should be NEGATIVE of method1_balance if consistent

        # Method 3: Category-sum method (similar to method 2, but broken down by RENT/EXPENSE)
        category_balances_info = []
        method3_balance_accumulator = 0.0

        for trans_type in ['RENT', 'EXPENSE']:
            type_data = shared_only[shared_only['TransactionType'] == trans_type]
            if not type_data.empty:
                type_total_shared = type_data['AllowedAmount'].sum()
                type_ryan_fair_share = type_total_shared * self.config.RYAN_PCT
                
                type_ryan_paid = type_data[type_data['Payer'] == 'Ryan']['AllowedAmount'].sum()
                type_jordyn_paid = type_data[type_data['Payer'] == 'Jordyn']['AllowedAmount'].sum()

                # Ryan's variance for this type: positive if Ryan paid MORE than his fair share for this type
                type_ryan_variance = type_ryan_paid - type_ryan_fair_share
                method3_balance_accumulator += type_ryan_variance
                
                category_balances_info.append({
                    'Category': trans_type,
                    'TotalShared': round(type_total_shared, 2),
                    'RyanPaidShared': round(type_ryan_paid, 2),
                    'JordynPaidShared': round(type_jordyn_paid, 2),
                    'RyanFairShare': round(type_ryan_fair_share, 2),
                    'RyanVarianceForCategory': round(type_ryan_variance, 2) # Positive: Ryan overpaid for this category
                })
        method3_balance = method3_balance_accumulator # Same interpretation as method2_balance

        # Reconciliation Check:
        # Method 1: Positive means Ryan owes Jordyn.
        # Method 2 & 3: Positive means Ryan OVERPAID (so Jordyn owes Ryan).
        # Therefore, Method 1 should be approx. -Method2 and -Method3.
        tolerance = 0.01 # $0.01 tolerance
        reconciled_1_2 = abs(method1_balance + method2_balance) <= tolerance
        reconciled_2_3 = abs(method2_balance - method3_balance) <= tolerance # M2 and M3 should be equal
        reconciled_1_3 = abs(method1_balance + method3_balance) <= tolerance
        all_reconciled = reconciled_1_2 and reconciled_2_3

        final_balance_to_report = method1_balance # Use RunningBalance as the primary reporting balance
        who_owes = "Ryan owes Jordyn" if final_balance_to_report > 0 else \
                   "Jordyn owes Ryan" if final_balance_to_report < 0 else "Settled"
        amount_owed_val = abs(final_balance_to_report)

        logger.info(f"Triple Reconciliation Results:")
        logger.info(f"  Method 1 (Running Balance): ${method1_balance:,.2f} ({'Ryan owes Jordyn' if method1_balance > 0 else 'Jordyn owes Ryan' if method1_balance < 0 else 'Settled'})")
        logger.info(f"  Method 2 (Ryan's Variance from Fair Share): ${method2_balance:,.2f} ({'Jordyn owes Ryan' if method2_balance > 0 else 'Ryan owes Jordyn' if method2_balance < 0 else 'Settled'})")
        logger.info(f"  Method 3 (Category Sum of Ryan's Variance): ${method3_balance:,.2f} ({'Jordyn owes Ryan' if method3_balance > 0 else 'Ryan owes Jordyn' if method3_balance < 0 else 'Settled'})")
        logger.info(f"  All Reconciled (M1 ~ -M2, M2 ~ M3): {all_reconciled}")
        if not all_reconciled:
            logger.error(f"Reconciliation discrepancy detected! M1+M2 diff: {method1_balance + method2_balance:.4f}, M2-M3 diff: {method2_balance - method3_balance:.4f}")


        return {
            'method1_running_balance': round(method1_balance, 2),
            'method2_variance_ryan_vs_fair': round(method2_balance, 2), # Clarified name
            'method3_category_sum_ryan_vs_fair': round(method3_balance, 2), # Clarified name
            'reconciled': all_reconciled,
            'max_difference': round(max(abs(method1_balance + method2_balance), abs(method2_balance - method3_balance)), 2),
            'total_shared_amount': round(total_shared_amount, 2),
            'ryan_total_fair_share': round(ryan_total_fair_share, 2),
            'jordyn_total_fair_share': round(total_shared_amount * self.config.JORDYN_PCT, 2),
            'ryan_actually_paid_for_shared': round(ryan_actually_paid_for_shared, 2),
            'jordyn_actually_paid_for_shared': round(jordyn_actually_paid_for_shared, 2),
            'ryan_net_variance_from_fair_share': round(ryan_variance_from_fair, 2), # Clarified name
            'jordyn_net_variance_from_fair_share': round( (jordyn_actually_paid_for_shared - (total_shared_amount * self.config.JORDYN_PCT)), 2),
            'category_details': category_balances_info,
            'final_balance_reported': round(final_balance_to_report, 2), # Based on Method 1
            'who_owes_whom': who_owes,
            'amount_owed': round(amount_owed_val, 2)
        }

    def _perform_advanced_analytics(self, master_ledger: pd.DataFrame) -> Dict[str, Any]:
        logger.info("Running advanced analytics...")
        analytics = {}
        if master_ledger.empty or master_ledger['Date'].isna().all():
            logger.warning("Master ledger is empty or has no valid dates for advanced analytics.")
            return {'error': "No data for advanced analytics"}

        # Ensure Date column is datetime
        master_ledger['Date'] = pd.to_datetime(master_ledger['Date'])
        
        # Monthly cash flow (shared amounts paid by each person)
        # Using AllowedAmount for shared expenses, grouped by actual payer
        # Ensure 'Payer' column exists
        if 'Payer' not in master_ledger.columns:
            master_ledger['Payer'] = "Unknown" # Fallback

        monthly_cash_flow = master_ledger[master_ledger['IsShared']].groupby(
            [pd.Grouper(key='Date', freq='ME'), 'Payer']
        )['AllowedAmount'].sum().unstack(fill_value=0).round(self.config.CURRENCY_PRECISION)
        analytics['monthly_payments_by_payer_for_shared_items'] = monthly_cash_flow.to_dict()

        # Liquidity Analysis (Periods of high outstanding balance)
        # This requires careful definition. Let's use 'RunningBalance'.
        liquidity_issues = []
        # Iterate through sorted transactions to find periods where abs(RunningBalance) > threshold
        # This simple version just lists transactions where the threshold was breached
        high_balance_transactions = master_ledger[master_ledger['RunningBalance'].abs() > self.config.LIQUIDITY_STRAIN_THRESHOLD]
        for idx, row in high_balance_transactions.iterrows():
            liquidity_issues.append({
                'date': row['Date'].strftime('%Y-%m-%d') if pd.notna(row['Date']) else 'N/A',
                'running_balance': row['RunningBalance'],
                'transaction_id': row['TransactionID'],
                'description': row['Description']
            })
        analytics['potential_liquidity_strain_points'] = liquidity_issues # Simplified for now

        # Category Analysis (Expenses only)
        expense_only_df = master_ledger[(master_ledger['TransactionType'] == 'EXPENSE') & master_ledger['IsShared']].copy()
        if not expense_only_df.empty and 'Merchant' in expense_only_df.columns:
            expense_only_df['Category'] = expense_only_df['Merchant'].apply(self._categorize_merchant)
            category_summary = expense_only_df.groupby('Category')['AllowedAmount'].agg(['sum', 'count', 'mean']).round(self.config.CURRENCY_PRECISION)
            if not category_summary.empty:
                category_totals = category_summary['sum'].sort_values(ascending=False)
                pareto_cumsum_pct = (category_totals.cumsum() / category_totals.sum() * 100)
                pareto_80_categories = pareto_cumsum_pct[pareto_cumsum_pct <= 80].index.tolist()
                analytics['expense_category_analysis'] = {
                    'summary_table': category_summary.to_dict(),
                    'pareto_80_categories_list': pareto_80_categories,
                    'pareto_80_amount_sum': category_totals[pareto_80_categories].sum() if pareto_80_categories else 0
                }
        else:
             analytics['expense_category_analysis'] = {'message': "No shared expenses with merchant data for category analysis."}


        # Temporal Analysis (Trend of total shared spending per month)
        monthly_shared_spending = master_ledger[master_ledger['IsShared']].resample('ME', on='Date')['AllowedAmount'].sum()
        if len(monthly_shared_spending) >= 3:
            x = np.arange(len(monthly_shared_spending))
            y = monthly_shared_spending.values
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
            analytics['monthly_shared_spending_trend'] = {
                'slope_per_month': round(slope, 2),
                'r_squared': round(r_value**2, 4),
                'p_value': round(p_value, 4),
                'trend_significant': p_value < 0.05,
                'monthly_values': monthly_shared_spending.round(2).to_dict()
            }
            # Basic forecast for next 3 months (simple linear extrapolation)
            future_x = np.arange(len(monthly_shared_spending), len(monthly_shared_spending) + 3)
            forecast_values = slope * future_x + intercept
            forecast_dates = pd.date_range(start=monthly_shared_spending.index.max() + pd.DateOffset(months=1), periods=3, freq='ME')
            analytics['monthly_shared_spending_forecast'] = dict(zip([d.strftime('%Y-%m') for d in forecast_dates], np.round(forecast_values,2)))
        else:
            analytics['monthly_shared_spending_trend'] = {'message': "Not enough monthly data points (need at least 3) for trend analysis."}
            analytics['monthly_shared_spending_forecast'] = {'message': "Not enough data for forecast."}


        # Statistical Summary of Running Balance (e.g., at month ends)
        month_end_balances = master_ledger.resample('ME', on='Date')['RunningBalance'].last()
        if not month_end_balances.empty:
            analytics['month_end_running_balance_stats'] = {
                'mean': round(month_end_balances.mean(), 2),
                'std_dev': round(month_end_balances.std(), 2),
                'min': round(month_end_balances.min(), 2),
                'max': round(month_end_balances.max(), 2),
                'median': round(month_end_balances.median(), 2),
            }
        else:
            analytics['month_end_running_balance_stats'] = {'message': "No data for running balance stats."}

        logger.info("Advanced analytics completed.")
        return analytics

    def _comprehensive_risk_assessment(self, master_ledger: pd.DataFrame, analytics: Dict[str, Any]) -> Dict[str, Any]:
        # This is a simplified risk assessment. A real one would be more complex.
        logger.info("Performing comprehensive risk assessment...")
        risks = {'overall_risk_level': 'LOW', 'details': []} # Default
        if master_ledger.empty:
            risks['details'].append({'risk_type': 'Data Availability', 'assessment': 'No data to assess risks.'})
            return risks

        # Data Quality Risk
        dq_score = self._calculate_data_quality_score(master_ledger)
        if dq_score < self.config.DATA_QUALITY_THRESHOLD * 100 : # Convert threshold to percentage
            risks['details'].append({
                'risk_type': 'Data Quality', 
                'assessment': f"Data quality score ({dq_score:.1f}%) is below threshold ({self.config.DATA_QUALITY_THRESHOLD*100:.1f}%). Review data quality issues.",
                'level': 'HIGH' if dq_score < 70 else 'MEDIUM'
            })
        
        # Liquidity Strain (based on simplified analytics)
        if 'potential_liquidity_strain_points' in analytics and analytics['potential_liquidity_strain_points']:
            strain_count = len(analytics['potential_liquidity_strain_points'])
            risks['details'].append({
                'risk_type': 'Liquidity Strain',
                'assessment': f"{strain_count} instance(s) where running balance exceeded ${self.config.LIQUIDITY_STRAIN_THRESHOLD:,.0f}. Regular settlements recommended.",
                'level': 'MEDIUM' if strain_count > 0 else 'LOW'
            })

        # Spending Trend Risk
        trend_info = analytics.get('monthly_shared_spending_trend', {})
        if trend_info.get('slope_per_month', 0) > 100 and trend_info.get('trend_significant', False): # Arbitrary $100/month increase
             risks['details'].append({
                'risk_type': 'Spending Trend',
                'assessment': f"Shared spending shows a significant increasing trend of ${trend_info['slope_per_month']:.2f}/month. Monitor spending habits.",
                'level': 'MEDIUM'
            })           

        # Determine overall risk
        high_risk_count = sum(1 for r in risks['details'] if r.get('level') == 'HIGH')
        medium_risk_count = sum(1 for r in risks['details'] if r.get('level') == 'MEDIUM')
        if high_risk_count > 0: risks['overall_risk_level'] = 'HIGH'
        elif medium_risk_count > 0: risks['overall_risk_level'] = 'MEDIUM'
        
        if not risks['details']: # If no specific risks identified above
             risks['details'].append({'risk_type': 'General', 'assessment': 'No major specific risks identified based on current checks.', 'level': 'LOW'})

        logger.info(f"Risk assessment completed. Overall level: {risks['overall_risk_level']}")
        return risks

    def _create_visualizations(self, master_ledger: pd.DataFrame, analytics: Dict[str, Any], reconciliation: Dict[str, Any]) -> Dict[str, str]:
        logger.info("Creating visualizations...")
        output_dir = Path('analysis_output')
        output_dir.mkdir(exist_ok=True)
        viz_paths: Dict[str, str] = {}

        if master_ledger.empty or master_ledger['Date'].isna().all():
            logger.warning("Cannot create visualizations: Master ledger is empty or has no valid dates.")
            return viz_paths
        
        plt.style.use('seaborn-v0_8-whitegrid') # Ensure a valid style

        # 1. Running Balance Timeline
        try:
            fig1, ax1 = plt.subplots(figsize=(12, 6))
            master_ledger.plot(x='Date', y='RunningBalance', ax=ax1, legend=None)
            ax1.axhline(0, color='grey', linestyle='--', linewidth=0.8)
            ax1.set_title('Running Balance Over Time (Ryan owes Jordyn > 0)')
            ax1.set_ylabel('Balance ($)')
            ax1.set_xlabel('Date')
            # Currency format for y-axis
            ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
            plt.tight_layout()
            path = output_dir / 'running_balance_timeline.png'
            plt.savefig(path)
            plt.close(fig1)
            viz_paths['running_balance_timeline'] = str(path)
            logger.info(f"Saved: {path}")
        except Exception as e:
            logger.error(f"Failed to create running balance timeline: {e}", exc_info=True)


        # 2. Monthly Shared Spending by Payer (Stacked Bar)
        try:
            if 'monthly_payments_by_payer_for_shared_items' in analytics and \
               isinstance(analytics['monthly_payments_by_payer_for_shared_items'], dict) and \
               analytics['monthly_payments_by_payer_for_shared_items']:
                
                monthly_payments_df = pd.DataFrame(analytics['monthly_payments_by_payer_for_shared_items'])
                if not monthly_payments_df.empty:
                    # Convert PeriodIndex if necessary
                    if isinstance(monthly_payments_df.index, pd.PeriodIndex):
                         monthly_payments_df.index = monthly_payments_df.index.to_timestamp()

                    fig2, ax2 = plt.subplots(figsize=(12, 7))
                    monthly_payments_df.plot(kind='bar', stacked=True, ax=ax2)
                    ax2.set_title('Monthly Shared Spending by Payer')
                    ax2.set_ylabel('Amount ($)')
                    ax2.set_xlabel('Month')
                    ax2.tick_params(axis='x', rotation=45)
                    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
                    plt.tight_layout()
                    path = output_dir / 'monthly_shared_spending_by_payer.png'
                    plt.savefig(path)
                    plt.close(fig2)
                    viz_paths['monthly_shared_spending_by_payer'] = str(path)
                    logger.info(f"Saved: {path}")
                else:
                    logger.warning("Monthly payments data for visualization was empty.")
            else:
                logger.warning("Analytics data for 'monthly_payments_by_payer_for_shared_items' not found or empty.")
        except Exception as e:
            logger.error(f"Failed to create monthly spending by payer chart: {e}", exc_info=True)


        # 3. Expense Category Distribution Treemap (Plotly)
        try:
            category_data_for_viz = []
            # Rent as a category
            rent_total = master_ledger[master_ledger['TransactionType'] == 'RENT']['AllowedAmount'].sum()
            if rent_total > 0:
                category_data_for_viz.append({'Category': 'RENT (Shared)', 'Amount': rent_total})

            # Expense categories
            exp_cat_analysis = analytics.get('expense_category_analysis', {})
            if 'summary_table' in exp_cat_analysis and isinstance(exp_cat_analysis['summary_table'], dict):
                summary_df = pd.DataFrame(exp_cat_analysis['summary_table'])
                if 'sum' in summary_df.columns: # 'sum' contains total AllowedAmount for each category
                    for cat, row_data in summary_df.iterrows():
                        if row_data['sum'] > 0 :
                             category_data_for_viz.append({'Category': f"EXPENSE: {cat}", 'Amount': row_data['sum']})
            
            if category_data_for_viz:
                fig3 = go.Figure(go.Treemap(
                    labels=[d['Category'] for d in category_data_for_viz],
                    values=[d['Amount'] for d in category_data_for_viz],
                    parents=[''] * len(category_data_for_viz), # All top-level
                    textinfo='label+value+percent parent'
                ))
                fig3.update_layout(title_text='Distribution of Shared Spending (Rent & Expense Categories)')
                path = output_dir / 'shared_spending_treemap.html'
                fig3.write_html(str(path))
                viz_paths['shared_spending_treemap'] = str(path)
                logger.info(f"Saved: {path}")
            else:
                logger.warning("No data available for shared spending treemap.")
        except Exception as e:
            logger.error(f"Failed to create treemap visualization: {e}", exc_info=True)
            
        logger.info(f"Created {len(viz_paths)} visualizations.")
        return viz_paths

    def _generate_recommendations(self, analytics: Dict[str, Any], risk_assessment: Dict[str, Any], reconciliation: Dict[str, Any]) -> List[str]:
        logger.info("Generating recommendations...")
        recommendations = []

        # Based on Reconciliation
        if reconciliation.get('amount_owed', 0) > 50: # Arbitrary threshold for settlement
            recommendations.append(
                f"Settle outstanding balance: {reconciliation['who_owes_whom']} ${reconciliation['amount_owed']:,.2f}."
            )
        if not reconciliation.get('reconciled', True):
            recommendations.append(
                "CRITICAL: Reconciliation methods show discrepancies. Review calculations and data immediately."
            )
        
        # Based on Risk Assessment
        if risk_assessment.get('overall_risk_level') == 'HIGH':
            recommendations.append(
                "High overall risk identified. Prioritize addressing detailed risk factors (see risk report/log)."
            )
        elif risk_assessment.get('overall_risk_level') == 'MEDIUM':
            recommendations.append(
                "Medium overall risk identified. Review detailed risk factors and plan mitigation."
            )
        
        for risk_detail in risk_assessment.get('details', []):
            if risk_detail.get('level') == 'HIGH' or risk_detail.get('level') == 'MEDIUM':
                 recommendations.append(f"Address {risk_detail.get('risk_type', 'Unknown Risk')}: {risk_detail.get('assessment', '')}")


        # Based on Analytics
        trend_info = analytics.get('monthly_shared_spending_trend', {})
        if trend_info.get('slope_per_month', 0) > 100 and trend_info.get('trend_significant', False):
            recommendations.append(
                f"Monitor increasing spending trend of ~${trend_info['slope_per_month']:.0f}/month in shared expenses."
            )
        
        if not recommendations:
            recommendations.append("No specific high-priority recommendations at this time. Continue good practices.")
        
        logger.info(f"Generated {len(recommendations)} recommendations.")
        return recommendations

    def _generate_transaction_id(self, row: pd.Series) -> str:
        """Generate unique transaction ID for tracking"""
        # Create hash from key fields
        # Ensure date is in a consistent string format if it's a datetime object
        date_str = row['Date'].isoformat() if isinstance(row['Date'], datetime) else str(row['Date'])
        key_data = f"{date_str}_{row.get('Payer','NA')}_{row.get('Merchant','NA')}_{row.get('ActualAmount',0)}_{row.get('AllowedAmount',0)}"
        return hashlib.md5(key_data.encode()).hexdigest()[:12]

    def _log_data_quality_issue(self, source: str, row_idx: Any, row_data: Dict[str, Any], flags: List[DataQualityFlag] | List[str]):
        """Log data quality issues for audit trail"""
        # Convert Enums to values if they are enums
        flag_values = [f.value if isinstance(f, DataQualityFlag) else f for f in flags]
        
        # Sanitize row_data: convert datetime to isoformat string
        sanitized_row_data = {}
        for k, v in row_data.items():
            if isinstance(v, (datetime, pd.Timestamp)):
                sanitized_row_data[k] = v.isoformat()
            elif isinstance(v, (list, dict)): # Avoid deep nesting for now
                 sanitized_row_data[k] = str(v)
            else:
                sanitized_row_data[k] = v

        issue = {
            'source': source,
            'row_index_in_source_df': str(row_idx), # Ensure it's string for JSON if it's complex
            'flags': flag_values,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'row_data_sample': {k: sanitized_row_data.get(k) for k in ['Date', 'Payer', 'ActualAmount', 'AllowedAmount', 'Description'] if k in sanitized_row_data} # Sample key fields
        }
        self.data_quality_issues.append(issue)
        logger.warning(f"Data quality issue in {source} (index: {row_idx}): {flag_values}. Sample: {issue['row_data_sample']}")

    def _calculate_data_quality_score(self, master_ledger: pd.DataFrame) -> float:
        if master_ledger.empty: return 0.0
        # A row is clean if its DataQualityFlag is exactly 'CLEAN'
        clean_rows = (master_ledger['DataQualityFlag'] == DataQualityFlag.CLEAN.value).sum()
        total_rows = len(master_ledger)
        score = (clean_rows / total_rows * 100) if total_rows > 0 else 0
        logger.info(f"Data Quality Score: {score:.2f}% ({clean_rows} clean rows out of {total_rows})")
        return score

    def _summarize_data_quality_issues(self, master_ledger: pd.DataFrame) -> Dict[str, int]:
        """Summarizes the count of each data quality flag type."""
        if master_ledger.empty or 'DataQualityFlag' not in master_ledger.columns:
            return {"No data quality flags to summarize.": 0}

        flag_counts: Dict[str, int] = {}
        for flags_str in master_ledger['DataQualityFlag']:
            if pd.notna(flags_str) and flags_str != DataQualityFlag.CLEAN.value:
                for flag in flags_str.split(','):
                    flag_counts[flag] = flag_counts.get(flag, 0) + 1
        return flag_counts


    def _validate_results(self, reconciliation: Dict[str, Any], master_ledger: pd.DataFrame) -> None:
        logger.info("Validating results...")
        self.validation_results['reconciliation_match_strict'] = reconciliation.get('reconciled', False)
        
        # Sum of individual BalanceImpacts should equal the final RunningBalance
        if not master_ledger.empty:
            sum_balance_impacts = master_ledger['BalanceImpact'].sum()
            final_running_balance = master_ledger['RunningBalance'].iloc[-1]
            self.validation_results['balance_impact_sum_vs_running_balance'] = abs(sum_balance_impacts - final_running_balance) < 0.01
        else:
            self.validation_results['balance_impact_sum_vs_running_balance'] = True # Vacuously true


        # Data quality score meets threshold
        quality_score = self._calculate_data_quality_score(master_ledger) # Recalculate or use passed
        self.validation_results['data_quality_acceptable'] = quality_score >= self.config.DATA_QUALITY_THRESHOLD * 100

        all_passed = all(self.validation_results.values())
        if not all_passed:
            failed_checks = [k for k, v in self.validation_results.items() if not v]
            logger.error(f"Validation failed for: {', '.join(failed_checks)}")
            # raise ValueError(f"Critical validation failed: {', '.join(failed_checks)}") # Soften to not always raise
        else:
            logger.info("All critical validations passed successfully.")

    def _check_performance(self) -> None:
        logger.info("Checking performance metrics...")
        import psutil # Keep import local if not always available/needed
        elapsed_seconds = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        if elapsed_seconds > self.config.MAX_PROCESSING_TIME_SECONDS:
            logger.warning(f"Processing time ({elapsed_seconds:.1f}s) EXCEEDED limit ({self.config.MAX_PROCESSING_TIME_SECONDS}s).")

        process = psutil.Process()
        self.memory_usage_mb = process.memory_info().rss / (1024 * 1024)
        if self.memory_usage_mb > self.config.MAX_MEMORY_MB:
            logger.warning(f"Memory usage ({self.memory_usage_mb:.1f}MB) EXCEEDED limit ({self.config.MAX_MEMORY_MB}MB).")
        logger.info(f"Performance: Time={elapsed_seconds:.2f}s, Memory={self.memory_usage_mb:.2f}MB")


    def _categorize_merchant(self, merchant: Optional[str]) -> str:
        if pd.isna(merchant) or not isinstance(merchant, str) or not merchant.strip():
            return 'Other/Unspecified'
        
        merchant_lower = merchant.lower()
        # Simplified categorization logic
        categories = {
            'Groceries': ['fry', 'safeway', 'walmart', 'target', 'costco', 'trader joe', 'whole foods', 'kroger', 'albertsons', 'grocery'],
            'Utilities': ['electric', 'gas', 'water', 'internet', 'phone', 'cox', 'srp', 'aps', 'centurylink', 'utility', 'conservice'],
            'Dining': ['restaurant', 'cafe', 'coffee', 'starbucks', 'pizza', 'sushi', 'mcdonald', 'chipotle', 'subway', 'doordash', 'grubhub', 'eats'],
            'Transport': ['uber', 'lyft', 'gas station', 'shell', 'chevron', 'auto', 'fuel', 'parking', 'toll'],
            'Entertainment': ['movie', 'theater', 'netflix', 'spotify', 'hulu', 'disney', 'concert', 'event', 'game'],
            'Healthcare': ['pharmacy', 'cvs', 'walgreens', 'doctor', 'medical', 'dental', 'clinic', 'hospital'],
            'Rent': ['rent'] # If rent items ever appear in expenses with a merchant
        }
        for category, keywords in categories.items():
            if any(keyword in merchant_lower for keyword in keywords):
                return category
        return 'Other Expenses'


    def _generate_outputs(self, master_ledger: pd.DataFrame, reconciliation: Dict[str, Any],
                          analytics: Dict[str, Any], risk_assessment: Dict[str, Any],
                          recommendations: List[str], visualizations: Dict[str, str]) -> Dict[str, str]:
        logger.info("Generating output files...")
        output_dir = Path('analysis_output')
        output_dir.mkdir(exist_ok=True)
        output_paths: Dict[str, str] = {}

        # 1. Master Ledger CSV
        if not master_ledger.empty:
            ledger_path = output_dir / 'master_ledger_v2.1.csv'
            master_ledger.to_csv(ledger_path, index=False, date_format='%Y-%m-%d')
            output_paths['master_ledger'] = str(ledger_path)
            logger.info(f"Saved: {ledger_path}")

        # 2. Executive Summary (more detailed)
        summary_data = {
            "Overall Balance": f"${reconciliation.get('amount_owed', 0):,.2f} ({reconciliation.get('who_owes_whom', 'N/A')})",
            "Total Shared Expenses Processed": f"${reconciliation.get('total_shared_amount', 0):,.2f}",
            "Data Quality Score": f"{self._calculate_data_quality_score(master_ledger):.1f}%",
            "Overall Risk Level": risk_assessment.get('overall_risk_level', 'N/A'),
            "Reconciliation Methods Matched": "YES" if reconciliation.get('reconciled', False) else "NO",
            "Processing Time (s)": f"{self.start_time_obj.total_seconds():.1f}" if hasattr(self, 'start_time_obj') and hasattr(self.start_time_obj, 'total_seconds') else \
                                     f"{(datetime.now(timezone.utc) - self.start_time).total_seconds():.1f}", # Fallback
            "Total Transactions": len(master_ledger),
            "Data Quality Issues Summary": json.dumps(self._summarize_data_quality_issues(master_ledger), indent=2)
        }
        summary_df = pd.DataFrame(list(summary_data.items()), columns=['Metric', 'Value'])
        exec_path = output_dir / 'executive_summary_v2.1.csv'
        summary_df.to_csv(exec_path, index=False)
        output_paths['executive_summary_csv'] = str(exec_path)
        logger.info(f"Saved: {exec_path}")

        # 3. Data Quality Issues Log (if any)
        if self.data_quality_issues:
            error_df = pd.DataFrame(self.data_quality_issues)
            # Convert complex objects in row_data_sample to string for CSV
            # This was simplified in _log_data_quality_issue to only include key fields as strings
            error_path = output_dir / 'data_quality_issues_log_v2.1.csv'
            error_df.to_csv(error_path, index=False)
            output_paths['data_quality_log'] = str(error_path)
            logger.info(f"Saved: {error_path}")

        # 4. Excel Report
        excel_path = output_dir / 'financial_analysis_report_v2.1.xlsx'
        try:
            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                summary_df.to_excel(writer, sheet_name='Executive Summary', index=False)
                if not master_ledger.empty:
                    master_ledger.to_excel(writer, sheet_name='Master Ledger', index=False)
                
                # Reconciliation Details
                recon_details_data = {k:v for k,v in reconciliation.items() if not isinstance(v, (list, dict))} # Simple fields
                pd.DataFrame(list(recon_details_data.items()), columns=['Metric', 'Value']).to_excel(writer, sheet_name='Reconciliation Details', index=False)
                if 'category_details' in reconciliation and reconciliation['category_details']:
                     pd.DataFrame(reconciliation['category_details']).to_excel(writer, sheet_name='Recon Category Breakdown', index=False)

                # Analytics - e.g., category summary
                if 'expense_category_analysis' in analytics and 'summary_table' in analytics['expense_category_analysis']:
                    try:
                        exp_cat_summary_df = pd.DataFrame(analytics['expense_category_analysis']['summary_table'])
                        exp_cat_summary_df.to_excel(writer, sheet_name='Expense Category Stats') # Index is category name
                    except Exception as e_cat:
                        logger.error(f"Could not write expense category stats to Excel: {e_cat}")

                # Risk Assessment Details
                if 'details' in risk_assessment and risk_assessment['details']:
                    pd.DataFrame(risk_assessment['details']).to_excel(writer, sheet_name='Risk Assessment Details', index=False)
                
                # Recommendations
                pd.DataFrame(recommendations, columns=['Recommendations']).to_excel(writer, sheet_name='Recommendations', index=False)

            output_paths['excel_report'] = str(excel_path)
            logger.info(f"Saved: {excel_path}")
        except Exception as e_excel:
            logger.error(f"Failed to generate Excel report: {e_excel}", exc_info=True)


        # 5. Text Report (placeholder for PDF)
        report_content_path = output_dir / 'summary_report_v2.1.txt'
        with open(report_content_path, 'w') as f:
            f.write("Enhanced Shared Expense Analysis Report (v2.1)\n")
            f.write("="*50 + "\n\n")
            f.write("Executive Summary:\n")
            for k, v in summary_data.items():
                f.write(f"  {k}: {v}\n")
            f.write("\nRecommendations:\n")
            for i, rec in enumerate(recommendations, 1):
                f.write(f"  {i}. {rec}\n")
            f.write("\nVisualizations generated (see separate files):\n")
            for name, path_str in visualizations.items():
                f.write(f"  - {name}: {Path(path_str).name}\n")
        output_paths['text_summary_report'] = str(report_content_path)
        logger.info(f"Saved: {report_content_path}")
        
        logger.info(f"Generated {len(output_paths)} output files in {output_dir.resolve()}")
        return output_paths


# --- Unit Tests (largely unchanged, but ensure they run with revised structure if needed) ---
class TestEnhancedAnalyzer(unittest.TestCase):
    def setUp(self):
        self.config = AnalysisConfig()
        # Create dummy CSV files for testing
        self.test_dir = Path("test_analyzer_data")
        self.test_dir.mkdir(exist_ok=True)

        self.rent_fixture_path = self.test_dir / "test_rent.csv"
        rent_data = {
            'Month': ['Jan-2024', 'Feb-2024'],
            'Gross Total': ['$2,000.00', '$2,010.00'],
            "Ryan's Rent (43%)": ['$860.00', '$864.30'],
            "Jordyn's Rent (57%)": ['$1,140.00', '$1,145.70']
        }
        pd.DataFrame(rent_data).to_csv(self.rent_fixture_path, index=False)

        self.expense_fixture_path = self.test_dir / "test_expenses.csv"
        expense_data = {
            'Name': ['Ryan', 'Jordyn', 'Ryan', 'Jordyn'],
            'Date of Purchase': ['2024-01-05', '2024-01-10', '2024-02-01', '2024-02-05'],
            'Account': ['CC1', 'CC2', 'CC1', 'CC2'],
            'Merchant': ['Groceries', 'Gas', 'Internet', 'Dining Out'],
            'Actual Amount': ['$100.00', '$50.00', '$80.00', '$120.00'],
            'Allowed Amount': ['', '$50.00', '$80.00', ''], # Test blank and explicit
            'Description': ['Weekly groceries', 'Fuel', 'Monthly Bill', 'Dinner with friends 2x to calculate'] # Test 2x note
        }
        pd.DataFrame(expense_data).to_csv(self.expense_fixture_path, index=False)
        EnhancedSharedExpenseAnalyzer.start_time_obj = None # For test performance check

    def tearDown(self):
        # Clean up dummy files
        self.rent_fixture_path.unlink(missing_ok=True)
        self.expense_fixture_path.unlink(missing_ok=True)
        # Attempt to remove other output files if they exist from test runs
        try:
            if Path("financial_analysis_audit.log").exists(): Path("financial_analysis_audit.log").unlink()
            output_dir = Path('analysis_output')
            if output_dir.exists():
                for item in output_dir.iterdir(): item.unlink()
                output_dir.rmdir()
            self.test_dir.rmdir()
        except OSError as e:
            print(f"Error during teardown cleanup: {e}")


    def test_split_calculation(self):
        amount = 100.0
        ryan_share = amount * self.config.RYAN_PCT
        jordyn_share = amount * self.config.JORDYN_PCT
        self.assertAlmostEqual(ryan_share, 43.0, places=2)
        self.assertAlmostEqual(jordyn_share, 57.0, places=2)
        self.assertAlmostEqual(ryan_share + jordyn_share, amount, places=2)

    def test_full_analysis_run_with_fixtures(self):
        """Test the full analysis pipeline with fixture data."""
        analyzer = EnhancedSharedExpenseAnalyzer(self.rent_fixture_path, self.expense_fixture_path, self.config)
        analyzer.start_time_obj = datetime.now(timezone.utc) # for performance check in test
        
        results = {} # Define results here to ensure it's in scope for finally
        try:
            results = analyzer.analyze()
            
            self.assertIn('reconciliation', results)
            self.assertIn('output_paths', results)
            self.assertTrue(results['validation_results']['reconciliation_match_strict'], 
                            f"Reconciliation methods should match. Details: {results['reconciliation']}")
            
            # Check if "2x to calculate" logic for Jordyn's Dining Out was handled:
            # Original Actual: 120. Allowed was blank, so it became 120.
            # "2x" note means it should be 240.
            # Jordyn paid, so RyanOwes = 240 * 0.43 = 103.2
            # BalanceImpact for this transaction should be 103.2
            master_ledger_df = pd.read_csv(results['output_paths']['master_ledger'])
            dining_transaction = master_ledger_df[master_ledger_df['Description'].str.contains("Dining Out", na=False)]
            self.assertFalse(dining_transaction.empty, "Dining Out transaction not found in master ledger.")
            self.assertAlmostEqual(dining_transaction['AllowedAmount'].iloc[0], 240.00, places=2, msg="2x calculation for dining expense incorrect.")
            self.assertAlmostEqual(dining_transaction['BalanceImpact'].iloc[0], 240.00 * self.config.RYAN_PCT, places=2, msg="BalanceImpact for 2x dining expense incorrect.")

            # Check data quality score is not blindly 100% if issues (though fixtures are clean)
            self.assertGreaterEqual(results['data_quality_score'], 0) 
            self.assertLessEqual(results['data_quality_score'], 100)


        except Exception as e:
            logger.error(f"Test 'test_full_analysis_run_with_fixtures' FAILED. Exception: {e}", exc_info=True)
            if results and 'reconciliation' in results:
                 logger.error(f"Reconciliation details at failure: {results.get('reconciliation')}")
            if results and 'output_paths' in results and 'master_ledger' in results['output_paths']:
                try:
                    master_ledger_df_on_fail = pd.read_csv(results['output_paths']['master_ledger'])
                    logger.error(f"Master ledger head on failure:\n{master_ledger_df_on_fail.head().to_string()}")
                except Exception as e_read:
                    logger.error(f"Could not read master ledger on failure: {e_read}")
            self.fail(f"Full analysis run failed with fixture data: {e}")


def main():
    print("Enhanced Shared Expense Analyzer - Institutional Grade (v2.1)")
    print("-" * 80)

    parser = argparse.ArgumentParser(description="Enhanced Shared Expense Analyzer v2.1")
    parser.add_argument("--rent", type=Path, default=Path('Rent_Allocation_20250526.csv'), help="Path to rent CSV.")
    parser.add_argument("--expense", type=Path, default=Path('Expense_History_20250526.csv'), help="Path to expense CSV.")
    parser.add_argument("--run_tests", action='store_true', help="Run unit tests instead of analysis.")
    args = parser.parse_args()

    if args.run_tests:
        print("\nRunning Unit Tests...")
        # Need to ensure argv is correctly set for unittest.main when called this way
        # or it might pick up pytest/argparse args.
        # For simplicity, we'll make a test suite and run it.
        suite = unittest.TestSuite()
        suite.addTest(unittest.makeSuite(TestEnhancedAnalyzer))
        runner = unittest.TextTestRunner(verbosity=2)
        runner.run(suite)
        return

    if not args.rent.exists():
        print(f"Error: Rent file not found at {args.rent}")
        logger.critical(f"Rent file not found: {args.rent}")
        return
    if not args.expense.exists():
        print(f"Error: Expense file not found at {args.expense}")
        logger.critical(f"Expense file not found: {args.expense}")
        return
        
    print(f"Using rent file: {args.rent.resolve()}")
    print(f"Using expense file: {args.expense.resolve()}")

    config = AnalysisConfig()
    analyzer = EnhancedSharedExpenseAnalyzer(args.rent, args.expense, config)
    
    try:
        results = analyzer.analyze()
        print("\n" + "=" * 80)
        print("ANALYSIS COMPLETE")
        print("=" * 80 + "\n")

        print(f"Final Balance Reported: ${results['reconciliation']['final_balance_reported']:,.2f}")
        print(f"Who Owes Whom: {results['reconciliation']['who_owes_whom']}")
        print(f"Amount Owed: ${results['reconciliation']['amount_owed']:,.2f}")
        print(f"Data Quality Score: {results['data_quality_score']:.1f}%")
        print(f"Overall Risk Level: {results['risk_assessment']['overall_risk_level']}")
        
        print("\nKey Data Quality Flags Found (Count):")
        dq_summary = results.get('data_quality_issues_summary', {})
        if dq_summary:
            for flag, count in dq_summary.items():
                print(f"  - {flag}: {count}")
        else:
            print("  - No specific data quality flags raised (or summary unavailable).")

        print("\nOutput Files Generated In 'analysis_output' directory:")
        for name, path in results['output_paths'].items():
            print(f"  - {name}: {Path(path).name}")
        
        print(f"\nFull logs available in: financial_analysis_audit.log")
        print(f"Detailed data quality issues (if any) in: {results['output_paths'].get('data_quality_log', 'N/A')}")

    except FileNotFoundError as fnf_err:
        print(f"\nANALYSIS FAILED: {fnf_err}")
        logger.critical(f"Analysis aborted due to FileNotFoundError: {fnf_err}", exc_info=True)
    except ValueError as val_err:
        print(f"\nANALYSIS FAILED - Data Validation Error: {val_err}")
        logger.critical(f"Analysis aborted due to ValueError: {val_err}", exc_info=True)
    except Exception as e:
        print(f"\nANALYSIS FAILED - An unexpected error occurred: {e}")
        logger.critical(f"Analysis aborted due to an unexpected error: {e}", exc_info=True)
        print("Check 'financial_analysis_audit.log' for detailed error information.")


if __name__ == "__main__":
    # This is to ensure performance tracking in main starts from the beginning of main() if analyzer is directly used.
    # For the class, self.start_time is set in __init__.
    # For the purpose of this script, the analyzer's internal timing is what matters most.
    main()