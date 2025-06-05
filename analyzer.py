#!/usr/bin/env python3
###############################################################################
# BALANCE-pyexcel – Enhanced Shared Expense Analyzer
#
# Description : Legacy standalone analyzer for expense, ledger, and rent CSVs.
#                Produces a master ledger, analytics, and reports.
# Key Concepts: - Transaction ledger and expense merging
#               - Data quality assessment and reconciliation
#               - Visualization generation with Matplotlib/Plotly
# Public API  : - main()
#               - DataLoaderV23.load_transaction_ledger()
# -----------------------------------------------------------------------------
# Change Log
# Date        Author      Type        Note
# 2025-05-31  Codex       fix         Auto-detect ledger header row & logging
###############################################################################

from __future__ import annotations

"""
Enhanced Shared Expense Analyzer - Institutional Grade
=====================================================
Fortune 500 / Big 4 standard financial reconciliation system with
comprehensive data quality management, triple reconciliation, and
production-ready features.

Author: Financial Analysis System
Date: 2025-05-30 (Revised for v2.4 - Extended dashboard & features)
Version: 2.4
"""

import pandas as pd
import numpy as np
from datetime import datetime, timezone
import logging
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Union
import argparse
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Rectangle
import seaborn as sns
from scipy import stats
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio
import warnings
import unittest
from dataclasses import dataclass, field
from enum import Enum
import re
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    Image,
    PageBreak,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import io
import base64
import psutil  # For performance checking

# Configure logging for audit trail
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("financial_analysis_audit.log", mode="w"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Design constants
TABLEAU_COLORBLIND_10 = [
    "#007ACC",
    "#FFB000",
    "#FE6100",
    "#785EF0",
    "#64B200",
    "#FF4B97",
    "#00C1FF",
    "#648FFF",
    "#DC267F",
    "#FFB000",
]


# Configuration
@dataclass
class AnalysisConfig:
    """Configuration parameters for the analysis"""

    RYAN_PCT: float = 0.43
    JORDYN_PCT: float = 0.57
    CONFIDENCE_LEVEL: float = 0.95
    DATA_QUALITY_THRESHOLD: float = 0.90
    OUTLIER_THRESHOLD: float = 5000.0
    RENT_BASELINE: float = 2100.0
    RENT_VARIANCE_THRESHOLD: float = 0.10  # For rent allocation vs baseline
    RENT_BUDGET_VARIANCE_THRESHOLD_PCT: float = 10.0  # For rent history vs allocation
    LIQUIDITY_STRAIN_THRESHOLD: float = 5000.0
    LIQUIDITY_STRAIN_DAYS: int = 60
    CONCENTRATION_RISK_THRESHOLD: float = 0.40
    CURRENCY_PRECISION: int = 2
    MAX_MEMORY_MB: int = 500
    MAX_PROCESSING_TIME_SECONDS: int = 150  # Increased due to more files and processing


class DataQualityFlag(Enum):
    """Enumeration of data quality issues"""

    CLEAN = "CLEAN"
    MISSING_DATE = "MISSING_DATE"
    MISALIGNED_ROW = "MISALIGNED_ROW"
    DUPLICATE_SUSPECTED = "DUPLICATE_SUSPECTED"
    OUTLIER_AMOUNT = "OUTLIER_AMOUNT"
    MANUAL_CALCULATION_NOTE = "MANUAL_CALCULATION_NOTE"
    NEGATIVE_AMOUNT = "NEGATIVE_AMOUNT"
    RENT_VARIANCE_HIGH = "RENT_VARIANCE_HIGH"  # Used for Rent Alloc vs Baseline
    RENT_BUDGET_VARIANCE_HIGH = (
        "RENT_BUDGET_VARIANCE_HIGH"  # Used for Rent Hist vs Alloc
    )
    NON_NUMERIC_VALUE_CLEANED = "NON_NUMERIC_VALUE_CLEANED"
    BALANCE_MISMATCH_WITH_LEDGER = "BALANCE_MISMATCH_WITH_LEDGER"


def build_design_theme():
    """
    Configure consistent design theme for all visualizations.
    Sets Matplotlib rcParams and returns Plotly template.
    """
    # Matplotlib configuration
    plt.rcParams.update(
        {
            "font.family": ["Inter", "DejaVu Sans", "sans-serif"],
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "axes.prop_cycle": plt.cycler("color", TABLEAU_COLORBLIND_10),
            "axes.grid": True,
            "grid.linestyle": "--",
            "grid.alpha": 0.25,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.dpi": 100,
            "savefig.dpi": 300,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )

    # Plotly template
    plotly_template = go.layout.Template()
    plotly_template.layout = go.Layout(
        font=dict(family="Inter, Arial, sans-serif", size=12, color="#333333"),
        title_font=dict(family="Montserrat, Arial Black, sans-serif", size=16),
        colorway=TABLEAU_COLORBLIND_10,
        plot_bgcolor="white",
        paper_bgcolor="white",
        hovermode="x unified",
        hoverlabel=dict(bgcolor="white", font_size=12, font_family="Inter"),
    )

    return plotly_template


# --- Data Loader V2.3 ---
class DataLoaderV23:
    """Handles loading and cleaning of all four CSV file types for v2.4"""

    @staticmethod
    def _money_to_float(series: pd.Series) -> pd.Series:
        """
        Convert money strings to float, handling:
        - Dollar signs and commas
        - Parentheses for negative values (e.g., $(304.61) → -304.61)
        - Empty strings/specific markers → 0
        """
        if series.empty or series.isna().all():
            return pd.Series([], dtype=float)

        str_series = series.astype(str)
        has_parens = str_series.str.contains(r"\(.*\)", regex=True, na=False)

        cleaned = (
            str_series.str.replace(
                r"[\$,\s]", "", regex=True
            )  # Remove $, commas, spaces
            .str.replace(r"[\(\)]", "", regex=True)  # Remove parentheses
            .replace(["", "nan", "None", "-", "inf", "-inf"], "0")
        )  # Handle empty/null/inf

        numeric = pd.to_numeric(cleaned, errors="coerce").fillna(0)
        numeric = numeric * np.where(has_parens, -1, 1)  # Apply negative sign

        return numeric

    @staticmethod
    def _ensure_unique_df_columns(df: pd.DataFrame) -> pd.DataFrame:
        """Guarantee unique column names by suffixing duplicates (.1, .2 …)."""
        if not df.columns.is_unique:
            logger.warning(
                "DataFrame has duplicate column names. Auto-suffixing duplicates: %s",
                df.columns[df.columns.duplicated(keep=False)].tolist(),
            )
            cols = pd.Series(df.columns)
            for dup in cols[cols.duplicated(keep=False)].unique():
                dup_idx = cols[cols == dup].index.tolist()
                for i, idx in enumerate(dup_idx):
                    cols[idx] = f"{dup}.{i}" if i else dup
            df.columns = cols
        return df

    @staticmethod
    def load_expense_history(path: Path) -> pd.DataFrame:
        logger.info(f"Loading Expense History from {path}")
        try:
            raw = pd.read_csv(
                path, header=None, dtype=str
            )  # Read all as string initially
        except Exception as e:
            logger.error(f"Could not read Expense History CSV {path}: {e}")
            return pd.DataFrame()

        header_idx = None
        for idx in range(min(5, len(raw))):
            if "Name" in raw.iloc[idx].astype(str).str.strip().values:
                header_idx = idx
                break

        if header_idx is None:
            logger.warning(
                "Could not find header row with 'Name' column in Expense History. Falling back to first row as headers."
            )
            header_idx = 0

        headers = raw.iloc[header_idx].astype(str).str.strip()
        df = raw.iloc[header_idx + 1 :].copy()
        df.columns = headers
        df = df.reset_index(drop=True)

        unnamed_cols = [col for col in df.columns if "Unnamed" in str(col)]
        df = df.drop(columns=unnamed_cols, errors="ignore")
        df = df.dropna(axis=1, how="all")

        money_cols = ["Actual Amount", "Allowed Amount"]
        for col in money_cols:
            if col in df.columns:
                df[col] = DataLoaderV23._money_to_float(df[col])
            else:  # Ensure column exists if expected
                df[col] = 0.0

        if "Date of Purchase" in df.columns:
            df["Date of Purchase"] = pd.to_datetime(
                df["Date of Purchase"], format="%m/%d/%Y", errors="coerce"
            )
        else:  # Ensure column exists
            df["Date of Purchase"] = pd.NaT

        key_cols = ["Name", "Date of Purchase", "Actual Amount"]
        existing_key_cols = [col for col in key_cols if col in df.columns]
        df = df.dropna(subset=existing_key_cols, how="all")

        df = DataLoaderV23._ensure_unique_df_columns(df)
        logger.info(
            f"Loaded {len(df)} expense records from Expense History after cleaning"
        )
        return df

    @staticmethod
    def load_transaction_ledger(path: Path) -> pd.DataFrame:
        logger.info(f"Loading Transaction Ledger from {path}")
        try:
            raw = pd.read_csv(path, header=None, dtype=str)
        except Exception as e:
            logger.error(f"Could not read Transaction Ledger CSV {path}: {e}")
            return pd.DataFrame()

        if len(raw) < 2:
            logger.error(
                "Transaction Ledger file is too short to contain headers and data."
            )
            return pd.DataFrame()

        header_idx = None
        for idx in range(min(5, len(raw))):
            row_values = raw.iloc[idx].astype(str)
            if (
                row_values.str.contains("Date", case=False).any()
                or row_values.str.contains("Running Balance", case=False).any()
            ):
                header_idx = idx
                break

        if header_idx is None:
            logger.warning(
                "Could not auto-detect header row in Transaction Ledger. Using first row."
            )
            header_idx = 0

        headers = raw.iloc[header_idx].astype(str).str.strip()
        headers = headers.str.replace(r"Unnamed: \d+", "", regex=True).str.strip()

        df = raw.iloc[header_idx + 1 :].copy()
        df.columns = headers
        df = df.reset_index(drop=True)

        df = df.loc[:, ~(df.columns == "")]  # Drop columns with empty string names
        df = df.dropna(axis=1, how="all")

        money_cols = ["Actual Amount", "Running Balance"]
        for col in money_cols:
            if col in df.columns:
                df[col] = DataLoaderV23._money_to_float(df[col])
            else:  # Ensure column exists
                df[col] = 0.0

        if "Date of Purchase" in df.columns:
            df["Date of Purchase"] = pd.to_datetime(
                df["Date of Purchase"], format="%m/%d/%Y", errors="coerce"
            )
        else:  # Ensure column exists
            df["Date of Purchase"] = pd.NaT

        key_cols = ["Name", "Date of Purchase"]
        existing_key_cols = [col for col in key_cols if col in df.columns]
        df = df.dropna(subset=existing_key_cols, how="all")

        df = DataLoaderV23._ensure_unique_df_columns(df)
        logger.info(
            f"Loaded {len(df)} ledger records from Transaction Ledger with running balance"
        )
        return df

    @staticmethod
    def load_rent_allocation(path: Path) -> pd.DataFrame:
        logger.info(f"Loading Rent Allocation from {path}")
        try:
            df = pd.read_csv(path, dtype=str)
        except Exception as e:
            logger.error(f"Could not read Rent Allocation CSV {path}: {e}")
            return pd.DataFrame()

        money_cols = [
            "Tax Base Rent - Residential - 2 bed 2 bath",
            "Tax Garage - 1 Car Attached",
            "Tax Common Area - Common Area Maintenance",
            "Tax Trash - Trash",
            "Tax Management - Management Fee",
            "Tax Rent Control - Rent Control Fee",
            "Conservice",
            "Gross Total",
            "Ryan's Rent (43%)",
            "Jordyn's Rent (57%)",
            "Previous Balance",
            "Rent Difference",
            "Other Adjustments",
            "New Balance",
        ]

        for col in money_cols:
            if col in df.columns:
                df[col] = DataLoaderV23._money_to_float(df[col])
            # Do not add column if missing, as these are specific structure

        if "Month" in df.columns:
            df["Month_Date"] = pd.to_datetime(
                df["Month"], format="%b %Y", errors="coerce"
            )
        else:
            df["Month_Date"] = pd.NaT

        df = DataLoaderV23._ensure_unique_df_columns(df)
        logger.info(f"Loaded {len(df)} rent allocation records")
        return df

    @staticmethod
    def load_rent_history(path: Path) -> pd.DataFrame:
        logger.info(f"Loading Rent History from {path}")
        try:
            df = pd.read_csv(path, dtype=str)
        except Exception as e:
            logger.error(f"Could not read Rent History CSV {path}: {e}")
            return pd.DataFrame()

        if df.empty:
            logger.warning("Rent History file is empty.")
            return pd.DataFrame(
                columns=["LineItem", "Month", "Measure", "Month_Date", "Amount"]
            )

        id_col = df.columns[0]
        tidy = df.melt(id_vars=[id_col], var_name="Month_Measure", value_name="Amount")
        tidy = tidy.rename(columns={id_col: "LineItem"})

        split_data = tidy["Month_Measure"].str.rsplit(" ", n=1, expand=True)
        tidy["Month"] = split_data[0]
        tidy["Measure"] = split_data[1]

        tidy["Month_Date"] = pd.to_datetime(
            tidy["Month"], format="%B %Y", errors="coerce"
        )
        tidy["Amount"] = DataLoaderV23._money_to_float(tidy["Amount"])
        tidy = tidy.drop(columns=["Month_Measure"])
        tidy = tidy[
            (tidy["Amount"] != 0) & tidy["Amount"].notna()
        ]  # Keep only non-zero, non-NA amounts

        tidy = DataLoaderV23._ensure_unique_df_columns(tidy)
        logger.info(f"Loaded {len(tidy)} rent history records (reshaped from matrix)")
        return tidy

    @staticmethod
    def validate_loaded_data(
        expense_hist: pd.DataFrame,
        transaction_ledger: pd.DataFrame,
        rent_alloc: pd.DataFrame,
        rent_hist: pd.DataFrame,
    ) -> Dict[str, Any]:
        validation_results = {
            "expense_history": {
                "rows": len(expense_hist),
                "date_range": (
                    expense_hist["Date of Purchase"].min(),
                    expense_hist["Date of Purchase"].max(),
                )
                if not expense_hist.empty
                and "Date of Purchase" in expense_hist
                and expense_hist["Date of Purchase"].notna().any()
                else (None, None),
                "total_amount": expense_hist["Actual Amount"].sum()
                if "Actual Amount" in expense_hist.columns
                else 0,
            },
            "transaction_ledger": {
                "rows": len(transaction_ledger),
                "has_running_balance": "Running Balance" in transaction_ledger.columns,
                "final_balance": transaction_ledger["Running Balance"].iloc[-1]
                if "Running Balance" in transaction_ledger.columns
                and not transaction_ledger.empty
                else None,
            },
            "rent_allocation": {
                "rows": len(rent_alloc),
                "months_covered": len(rent_alloc["Month"].unique())
                if "Month" in rent_alloc.columns and rent_alloc["Month"].notna().any()
                else 0,
                "avg_gross_rent": rent_alloc["Gross Total"].mean()
                if "Gross Total" in rent_alloc.columns
                and rent_alloc["Gross Total"].notna().any()
                else 0,
            },
            "rent_history": {
                "rows": len(rent_hist),
                "unique_line_items": len(rent_hist["LineItem"].unique())
                if not rent_hist.empty and "LineItem" in rent_hist
                else 0,
                "has_budget_actual": sorted(rent_hist["Measure"].unique().tolist())
                if not rent_hist.empty and "Measure" in rent_hist
                else [],
            },
        }
        logger.info("Data validation summary:")
        for dataset, stats in validation_results.items():
            logger.info(f"  {dataset}: {stats}")
        return validation_results


# --- Helper functions for merging data (can be part of DataLoaderV23 or global) ---
def merge_expense_and_ledger_data(
    expense_hist: pd.DataFrame, transaction_ledger: pd.DataFrame
) -> pd.DataFrame:
    logger.info("Merging expense history and transaction ledger...")
    # --- make absolutely sure both input frames have unique columns ---
    transaction_ledger = DataLoaderV23._ensure_unique_df_columns(transaction_ledger)
    expense_hist = DataLoaderV23._ensure_unique_df_columns(expense_hist)

    # Standardize required columns if they exist, or create them
    for df_ in [expense_hist, transaction_ledger]:
        if "Date of Purchase" not in df_.columns:
            df_["Date of Purchase"] = pd.NaT
        if "Actual Amount" not in df_.columns:
            df_["Actual Amount"] = 0.0
        if "Name" not in df_.columns:
            df_["Name"] = "Unknown"
        if "Merchant" not in df_.columns:
            df_["Merchant"] = "Unknown"

    expense_hist_c = expense_hist.copy()
    transaction_ledger_c = transaction_ledger.copy()

    expense_hist_c["Source"] = "ExpenseHistory"
    transaction_ledger_c["Source"] = "TransactionLedger"

    # Ensure 'Allowed Amount' exists, default to NaN if not present
    if "Allowed Amount" not in expense_hist_c.columns:
        expense_hist_c["Allowed Amount"] = np.nan
    if "Allowed Amount" not in transaction_ledger_c.columns:
        transaction_ledger_c["Allowed Amount"] = np.nan

    # Define key fields for deduplication
    key_fields = ["Name", "Date of Purchase", "Actual Amount", "Merchant"]
    # Ensure key fields exist in both DataFrames for safe deduplication
    for df_ in [expense_hist_c, transaction_ledger_c]:
        for kf in key_fields:
            if kf not in df_.columns:
                logger.warning(
                    f"Key field '{kf}' missing in {df_['Source'].iloc[0] if not df_.empty else 'a dataframe'}. Deduplication might be affected."
                )
                # Add placeholder if critical for concat/drop_duplicates, though ideally columns should align
                if kf == "Name" or kf == "Merchant":
                    df_[kf] = "MissingData"
                elif kf == "Date of Purchase":
                    df_[kf] = pd.NaT
                elif kf == "Actual Amount":
                    df_[kf] = 0.0

    # --- ensure unique columns again before concat after modifications ---
    transaction_ledger_c = DataLoaderV23._ensure_unique_df_columns(transaction_ledger_c)
    expense_hist_c = DataLoaderV23._ensure_unique_df_columns(expense_hist_c)

    dupes = [
        col for col in transaction_ledger_c.columns if col in expense_hist_c.columns
    ]
    logger.debug(f"Columns present in both frames before concat: {dupes}")
    logger.debug(
        f"  Ledger dupes before concat -> {transaction_ledger_c.columns[transaction_ledger_c.columns.duplicated()].tolist()}"
    )
    logger.debug(
        f"  Expense dupes before concat -> {expense_hist_c.columns[expense_hist_c.columns.duplicated()].tolist()}"
    )

    combined = pd.concat(
        [transaction_ledger_c, expense_hist_c], ignore_index=True, sort=False
    )  # Ledger first

    # Fill NaT with a placeholder for sorting/grouping if necessary, or handle before drop_duplicates
    # For drop_duplicates, NaT behaves as a unique value.

    # Round amounts before deduplication if minor float differences are an issue
    if "Actual Amount" in combined.columns:
        combined["Actual Amount"] = combined["Actual Amount"].round(2)

    # Deduplicate, keeping the TransactionLedger version if available
    combined = combined.sort_values(
        by=["Date of Purchase", "Actual Amount", "Source"], ascending=[True, True, True]
    )  # True for Source means ExpenseHistory comes first if not preferring Ledger
    combined = combined.drop_duplicates(
        subset=key_fields, keep="first"
    )  # 'first' will keep TransactionLedger due to prior concat order

    logger.info(
        f"Merged expense and ledger data: {len(combined)} records from "
        f"{len(expense_hist)} (ExpenseHistory) + {len(transaction_ledger)} (TransactionLedger) original."
    )
    return combined


def merge_rent_data(rent_alloc: pd.DataFrame, rent_hist: pd.DataFrame) -> pd.DataFrame:
    logger.info("Merging rent allocation with rent history...")
    if rent_hist.empty or "Month_Date" not in rent_hist.columns:
        logger.warning("No valid rent history data (or Month_Date column) to merge.")
        # Ensure rent_alloc has expected columns even if merge doesn't happen
        if "Total_Actual" not in rent_alloc.columns:
            rent_alloc["Total_Actual"] = np.nan
        if "Total_Budgeted" not in rent_alloc.columns:
            rent_alloc["Total_Budgeted"] = np.nan
        if "Budget_Variance" not in rent_alloc.columns:
            rent_alloc["Budget_Variance"] = np.nan
        if "Budget_Variance_Pct" not in rent_alloc.columns:
            rent_alloc["Budget_Variance_Pct"] = np.nan
        return rent_alloc.copy()

    rent_alloc_c = rent_alloc.copy()
    if "Month_Date" not in rent_alloc_c.columns:
        logger.error(
            "Rent Allocation is missing 'Month_Date' column. Cannot merge with Rent History."
        )
        return rent_alloc_c

    rent_actual = rent_hist[rent_hist["Measure"] == "Actual"].copy()
    rent_budget = rent_hist[rent_hist["Measure"] == "Budgeted"].copy()

    actual_by_month = (
        rent_actual.groupby("Month_Date")["Amount"]
        .sum()
        .reset_index()
        .rename(columns={"Amount": "Total_Actual"})
    )
    budget_by_month = (
        rent_budget.groupby("Month_Date")["Amount"]
        .sum()
        .reset_index()
        .rename(columns={"Amount": "Total_Budgeted"})
    )

    enhanced_rent = rent_alloc_c.merge(actual_by_month, on="Month_Date", how="left")
    enhanced_rent = enhanced_rent.merge(budget_by_month, on="Month_Date", how="left")

    enhanced_rent["Budget_Variance"] = enhanced_rent["Total_Actual"].fillna(
        0
    ) - enhanced_rent["Total_Budgeted"].fillna(0)

    # Avoid division by zero for percentage
    enhanced_rent["Budget_Variance_Pct"] = np.where(
        enhanced_rent["Total_Budgeted"].fillna(0) != 0,
        (
            enhanced_rent["Budget_Variance"]
            / enhanced_rent["Total_Budgeted"].replace(0, np.nan)
        )
        * 100,
        np.nan,  # Or 0 or some other indicator if budget is zero
    )

    logger.info(f"Enhanced rent data with budget analysis: {len(enhanced_rent)} months")
    return enhanced_rent


# --- Main Analyzer Class ---
class EnhancedSharedExpenseAnalyzer:
    """
    Comprehensive financial analyzer implementing institutional-grade standards
    for shared expense reconciliation with full audit trail and risk assessment.
    Version 2.4 - Now properly handles all four data sources!
    """

    def __init__(
        self,
        expense_file: Path,
        ledger_file: Path,
        rent_alloc_file: Path,
        rent_hist_file: Path,
        config: Optional[AnalysisConfig] = None,
    ):
        self.config = config or AnalysisConfig()
        self.expense_file = expense_file
        self.ledger_file = ledger_file
        self.rent_alloc_file = rent_alloc_file
        self.rent_hist_file = rent_hist_file

        self.data_quality_issues: List[Dict[str, Any]] = []
        self.audit_trail: List[
            Dict[str, Any]
        ] = []  # Consider if this is still used or replaced by logging
        self.validation_results: Dict[
            str, Any
        ] = {}  # Allow Any for more detailed validation
        self.alt_texts: Dict[str, str] = {}

        self.start_time = datetime.now(timezone.utc)
        self.memory_usage_mb = 0

        logger.info(f"Initialized analyzer v2.3 with config: {self.config}")
        logger.info(f"Data files:")
        logger.info(f"  - Expense History: {self.expense_file}")
        logger.info(f"  - Transaction Ledger: {self.ledger_file}")
        logger.info(f"  - Rent Allocation: {self.rent_alloc_file}")
        logger.info(f"  - Rent History: {self.rent_hist_file}")

        for file_path, file_name in [
            (self.expense_file, "Expense History"),
            (self.ledger_file, "Transaction Ledger"),
            (self.rent_alloc_file, "Rent Allocation"),
            (self.rent_hist_file, "Rent History"),
        ]:
            if not file_path.exists():
                logger.error(f"{file_name} file not found: {file_path}")
                raise FileNotFoundError(f"{file_name} file not found: {file_path}")

    def _log_data_quality_issue(
        self,
        source: str,
        row_idx: Any,
        row_data: Dict[str, Any],
        flags: List[Union[DataQualityFlag, str]],
    ):
        """Log data quality issues for audit trail"""
        flag_values = [f.value if isinstance(f, DataQualityFlag) else f for f in flags]

        sanitized_row_data = {}
        for k, v in row_data.items():
            if isinstance(v, (datetime, pd.Timestamp)):
                sanitized_row_data[k] = v.isoformat()
            elif isinstance(v, (list, dict, pd.Series)):  # Added pd.Series
                sanitized_row_data[k] = str(v)
            elif pd.isna(v):
                sanitized_row_data[k] = "NaN"
            else:
                sanitized_row_data[k] = v

        issue = {
            "source": source,
            "row_index_in_source_df": str(row_idx),  # str for safety
            "flags": flag_values,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "row_data_sample": {
                k: sanitized_row_data.get(k)
                for k in [
                    "Date",
                    "Payer",
                    "ActualAmount",
                    "AllowedAmount",
                    "Description",
                ]
                if k in sanitized_row_data
            },
        }
        self.data_quality_issues.append(issue)
        logger.warning(
            f"Data quality issue in {source} (index: {row_idx}): {flag_values}. Sample: {issue['row_data_sample']}"
        )

    def _update_row_data_quality_flags(
        self, df: pd.DataFrame, row_idx: Any, new_flags_enums: List[DataQualityFlag]
    ):
        """Appends new unique flags to the existing flags for a given row"""
        if not new_flags_enums:
            return

        new_flag_values = [flag.value for flag in new_flags_enums]

        # Ensure 'DataQualityFlag' column exists
        if "DataQualityFlag" not in df.columns:
            df["DataQualityFlag"] = DataQualityFlag.CLEAN.value

        existing_flags_str = df.loc[row_idx, "DataQualityFlag"]

        current_flags_list = []
        if (
            pd.notna(existing_flags_str)
            and existing_flags_str != DataQualityFlag.CLEAN.value
        ):
            current_flags_list = existing_flags_str.split(",")

        added_new = False
        for flag_val in new_flag_values:
            if flag_val not in current_flags_list:
                current_flags_list.append(flag_val)
                added_new = True

        if added_new:
            if (
                DataQualityFlag.CLEAN.value in current_flags_list
                and len(current_flags_list) > 1
            ):
                current_flags_list.remove(DataQualityFlag.CLEAN.value)
            df.loc[row_idx, "DataQualityFlag"] = ",".join(
                sorted(list(set(current_flags_list)))
            )
        elif not current_flags_list and (
            pd.isna(existing_flags_str)
            or existing_flags_str == DataQualityFlag.CLEAN.value
        ):
            # This case should ideally be handled by initializing with CLEAN.value
            if pd.isna(existing_flags_str):
                df.loc[row_idx, "DataQualityFlag"] = DataQualityFlag.CLEAN.value

    def _impute_missing_date(
        self, df: pd.DataFrame, idx: Any, date_col_name: str
    ) -> pd.Timestamp:
        """Impute missing date based on surrounding transactions or fallback"""
        # Ensure idx is a valid indexer for .iloc
        # If idx is a label, convert it to an integer position
        if not isinstance(idx, int):
            try:
                # Assuming df.index is unique and idx is one of its values
                idx_pos = df.index.get_loc(idx)
            except KeyError:
                logger.error(
                    f"Cannot find index {idx} in DataFrame for date imputation."
                )
                return pd.Timestamp.now(tz=timezone.utc).replace(
                    day=1
                ) + pd.offsets.MonthEnd(0)  # Fallback
        else:
            idx_pos = idx

        window = 5
        start_idx = max(0, idx_pos - window)
        end_idx = min(len(df), idx_pos + window + 1)  # Exclusive end for iloc

        # Check if the slice is valid
        if start_idx >= end_idx:
            logger.warning(
                f"Invalid slice for date imputation for index {idx} (pos {idx_pos}). Falling back."
            )
            return pd.Timestamp.now(tz=timezone.utc).replace(
                day=1
            ) + pd.offsets.MonthEnd(0)

        nearby_dates = df.iloc[start_idx:end_idx][date_col_name].dropna()

        if not nearby_dates.empty:
            # Ensure all dates are Timestamps before median calculation
            nearby_dates_ts = pd.to_datetime(nearby_dates, errors="coerce").dropna()
            if not nearby_dates_ts.empty:
                return pd.Timestamp(nearby_dates_ts.astype(np.int64).median())
            else:
                logger.warning(
                    f"Could not convert nearby dates to Timestamps for row {idx}. Falling back."
                )
        else:
            logger.warning(
                f"Could not impute date for row {idx} based on neighbors. Falling back to current month-end."
            )

        # Fallback if imputation fails
        now = pd.Timestamp.now(tz=timezone.utc)
        return now.replace(day=1) + pd.offsets.MonthEnd(0)

    def _process_expense_data(
        self, expense_hist: pd.DataFrame, transaction_ledger: pd.DataFrame
    ) -> pd.DataFrame:
        logger.info(
            "Processing and merging expense data from Expense History and Transaction Ledger..."
        )

        df = merge_expense_and_ledger_data(expense_hist, transaction_ledger)

        if df.empty:
            logger.warning("Combined expense data is empty. Returning empty DataFrame.")
            # Define essential columns for downstream processes if df is empty
            essential_cols = [
                "Date",
                "ActualAmount",
                "AllowedAmount",
                "Payer",
                "Description",
                "Merchant",
                "TransactionType",
                "DataQualityFlag",
                "IsShared",
                "RyanOwes",
                "JordynOwes",
                "BalanceImpact",
                "AuditNote",
            ]
            return pd.DataFrame(columns=essential_cols)

        # Standardize column names
        rename_map = {
            "Date of Purchase": "Date",
            # 'Actual Amount' is already handled by DataLoaderV23 and merge function
            # 'Allowed Amount' is also handled
            "Name": "Payer",
        }
        df.rename(columns=rename_map, inplace=True)

        # Ensure essential columns exist
        if "Payer" not in df.columns:
            df["Payer"] = "Unknown"
        if "Date" not in df.columns:
            df["Date"] = pd.NaT
        if "ActualAmount" not in df.columns:
            df["ActualAmount"] = 0.0

        # Initialize 'AllowedAmount' if missing, then fill NaNs
        if "AllowedAmount" not in df.columns:
            df["AllowedAmount"] = np.nan  # Initialize
        df["AllowedAmount"] = df["AllowedAmount"].fillna(df["ActualAmount"])
        df["AllowedAmount"] = df["AllowedAmount"].fillna(0)  # Ensure no NaNs remain

        df["DataQualityFlag"] = DataQualityFlag.CLEAN.value  # Initialize
        df["Description"] = df.get("Description", pd.Series(dtype=str)).fillna("")
        df["Merchant"] = df.get("Merchant", pd.Series(dtype=str)).fillna("")

        # --- Settlement Detection ---
        settlement_merchants = ["venmo", "zelle", "cash app", "paypal"]
        is_settlement_merchant = (
            df["Merchant"].str.lower().str.strip().isin(settlement_merchants)
        )
        is_settlement_description = df["Description"].str.contains(
            r"payment\s+(to|from)\s+(ryan|jordyn)", case=False, regex=True, na=False
        )
        is_settlement = is_settlement_merchant | is_settlement_description

        df["TransactionType"] = np.where(is_settlement, "SETTLEMENT", "EXPENSE")

        # --- Handle "2x to calculate" and other calculation notes ---
        df = self._handle_calculation_notes_in_processed_data(df)

        # --- Detect Duplicates (after merging and initial processing) ---
        df = self._detect_duplicates_in_processed_data(df)  # Pass the merged df

        # --- Row-wise data quality checks ---
        for idx, row in df.iterrows():  # use iterrows carefully on large DFs
            quality_flags_for_row = []
            if pd.isna(row["Date"]):
                quality_flags_for_row.append(DataQualityFlag.MISSING_DATE)
                df.loc[idx, "Date"] = self._impute_missing_date(
                    df, idx, "Date"
                )  # df, idx, col_name

            if row["ActualAmount"] > self.config.OUTLIER_THRESHOLD:
                quality_flags_for_row.append(DataQualityFlag.OUTLIER_AMOUNT)
            if row["ActualAmount"] < 0:  # Typically expenses are positive
                quality_flags_for_row.append(DataQualityFlag.NEGATIVE_AMOUNT)
                # Optional: auto-correct or flag for review
                # df.loc[idx, 'ActualAmount'] = abs(row['ActualAmount']) # Example auto-correct
            if row["AllowedAmount"] < 0:
                quality_flags_for_row.append(DataQualityFlag.NEGATIVE_AMOUNT)
                logger.warning(
                    f"Row {idx}: Negative AllowedAmount detected ({row['AllowedAmount']}). Clamping to 0."
                )
                df.loc[idx, "AllowedAmount"] = 0

            if (
                quality_flags_for_row
            ):  # Only log if there are actual new flags for this row
                self._update_row_data_quality_flags(df, idx, quality_flags_for_row)
                self._log_data_quality_issue(
                    "expense_row_check", idx, row.to_dict(), quality_flags_for_row
                )

        # --- Calculations for SETTLEMENTS ---
        df.loc[is_settlement, "AllowedAmount"] = (
            0  # Settlements are not shared expenses
        )
        df.loc[is_settlement, "IsShared"] = False
        df.loc[is_settlement, "RyanOwes"] = 0.0
        df.loc[is_settlement, "JordynOwes"] = 0.0

        # BalanceImpact for settlements
        # Ryan paying Jordyn: Ryan -> Jordyn (+ amount for Jordyn, - amount for Ryan's debt to Jordyn)
        # This means if Ryan pays Jordyn, the balance (Ryan owes Jordyn) decreases.
        ryan_paid_jordyn = (
            is_settlement
            & (df["Payer"].str.lower() == "ryan")
            & (
                df["Description"].str.contains(
                    r"to\s+jordyn", case=False, regex=True, na=False
                )
                | df["Merchant"]
                .str.lower()
                .isin(["venmo to jordyn", "zelle to jordyn"])
            )
        )  # Example refined logic

        jordyn_paid_ryan = (
            is_settlement
            & (df["Payer"].str.lower() == "jordyn")
            & (
                df["Description"].str.contains(
                    r"to\s+ryan", case=False, regex=True, na=False
                )
                | df["Merchant"].str.lower().isin(["venmo to ryan", "zelle to ryan"])
            )
        )

        df.loc[ryan_paid_jordyn, "BalanceImpact"] = -df.loc[
            ryan_paid_jordyn, "ActualAmount"
        ]
        df.loc[jordyn_paid_ryan, "BalanceImpact"] = df.loc[
            jordyn_paid_ryan, "ActualAmount"
        ]

        # --- Calculations for regular EXPENSES (non-settlements) ---
        non_settlement_mask = ~is_settlement
        df.loc[non_settlement_mask, "PersonalPortion"] = (
            df.loc[non_settlement_mask, "ActualAmount"]
            - df.loc[non_settlement_mask, "AllowedAmount"]
        ).round(self.config.CURRENCY_PRECISION)
        df.loc[non_settlement_mask, "IsShared"] = (
            df.loc[non_settlement_mask, "AllowedAmount"] > 0.005
        )  # Threshold for sharing

        # Initialize owe columns for non-settlements
        df.loc[non_settlement_mask, "RyanOwes"] = 0.0
        df.loc[non_settlement_mask, "JordynOwes"] = 0.0
        # Initialize BalanceImpact for non-settlements before calculation
        df.loc[non_settlement_mask, "BalanceImpact"] = 0.0

        # Who owes what for SHARED non-settlement expenses
        paid_by_ryan_shared_mask = (
            non_settlement_mask & df["IsShared"] & (df["Payer"].str.lower() == "ryan")
        )
        paid_by_jordyn_shared_mask = (
            non_settlement_mask & df["IsShared"] & (df["Payer"].str.lower() == "jordyn")
        )

        df.loc[paid_by_ryan_shared_mask, "JordynOwes"] = (
            df.loc[paid_by_ryan_shared_mask, "AllowedAmount"] * self.config.JORDYN_PCT
        ).round(self.config.CURRENCY_PRECISION)
        df.loc[paid_by_jordyn_shared_mask, "RyanOwes"] = (
            df.loc[paid_by_jordyn_shared_mask, "AllowedAmount"] * self.config.RYAN_PCT
        ).round(self.config.CURRENCY_PRECISION)

        # BalanceImpact for shared non-settlement expenses
        # If Ryan paid for a shared item, Jordyn owes Ryan. This means Jordyn's debt to Ryan increases.
        # If BalanceImpact > 0 means Ryan owes Jordyn.
        # So, if Ryan paid, JordynOwes increases, BalanceImpact for "Ryan owes Jordyn" DECREASES (becomes more negative or less positive)
        df.loc[paid_by_ryan_shared_mask, "BalanceImpact"] = -df.loc[
            paid_by_ryan_shared_mask, "JordynOwes"
        ]
        df.loc[paid_by_jordyn_shared_mask, "BalanceImpact"] = df.loc[
            paid_by_jordyn_shared_mask, "RyanOwes"
        ]

        df["AuditNote"] = df.apply(self._create_expense_audit_note, axis=1)

        logger.info(
            f"Processed {len(df)} combined expense records. Detected {is_settlement.sum()} settlements."
        )
        return df

    def _handle_calculation_notes_in_processed_data(
        self, df: pd.DataFrame
    ) -> pd.DataFrame:
        logger.info(
            "Handling '2x to calculate' notes in processed expense descriptions..."
        )
        if "Description" not in df.columns or "AllowedAmount" not in df.columns:
            logger.warning(
                "'Description' or 'AllowedAmount' column not found, skipping '2x' note handling."
            )
            return df

        # This assumes 'AllowedAmount' might have come from CSV or defaulted to 'ActualAmount'
        # We need to know if 'AllowedAmount' was explicitly provided or if it's a default
        # DataLoaderV23 sets 'AllowedAmount' from CSV, then merge_expense_and_ledger_data might take it.
        # For this simplified version, let's assume if '2x' is present, and 'AllowedAmount' == 'ActualAmount',
        # it's a candidate for doubling, unless 'AllowedAmount' was explicitly non-zero and different from 'ActualAmount' originally.
        # This is complex. The original `_handle_calculation_notes` had `was_allowed_amount_explicitly_provided`.
        # Let's simplify: if '2x to calculate' is in description, double 'ActualAmount' to get 'AllowedAmount' for that row.

        two_x_mask = df["Description"].str.contains(
            "2x to calculate", case=False, na=False
        )
        modified_indices = []

        for idx in df[two_x_mask].index:
            actual_amount_for_row = df.loc[idx, "ActualAmount"]
            new_allowed_amount = actual_amount_for_row * 2
            original_allowed = df.loc[idx, "AllowedAmount"]

            log_msg = (
                f"Row {idx}: '2x to calculate' found. "
                f"Setting AllowedAmount from (ActualAmount * 2): ({actual_amount_for_row} * 2 = {new_allowed_amount}). "
                f"Original AllowedAmount was: {original_allowed}."
            )
            df.loc[idx, "AllowedAmount"] = new_allowed_amount
            modified_indices.append(idx)
            logger.info(log_msg)
            self._update_row_data_quality_flags(
                df, idx, [DataQualityFlag.MANUAL_CALCULATION_NOTE]
            )
            self._log_data_quality_issue(
                "expense_2x_note_check",
                idx,
                df.loc[idx].to_dict(),
                [DataQualityFlag.MANUAL_CALCULATION_NOTE],
            )

        if modified_indices:
            logger.info(
                f"Applied '2x' calculation to 'AllowedAmount' for {len(modified_indices)} rows based on description note."
            )
        return df

    def _detect_duplicates_in_processed_data(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Detecting potential duplicate transactions in processed data...")
        if df.empty:
            return df

        # Ensure 'Date' is datetime for proper duplicate checking on date part
        if "Date" in df.columns and not pd.api.types.is_datetime64_any_dtype(
            df["Date"]
        ):
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

        dup_cols = ["Date", "Payer", "ActualAmount", "Merchant"]
        available_dup_cols = [col for col in dup_cols if col in df.columns]

        if len(available_dup_cols) < 3:  # Need at least Date, Payer, Amount
            logger.warning(
                f"Skipping duplicate detection: Not enough key columns available (need at least 3 from {dup_cols})."
            )
            return df

        # For duplicate checking, consider only the date part if 'Date' is datetime
        temp_df_for_dup_check = df[available_dup_cols].copy()
        if pd.api.types.is_datetime64_any_dtype(temp_df_for_dup_check["Date"]):
            temp_df_for_dup_check["DateForDup"] = temp_df_for_dup_check["Date"].dt.date
            check_cols_for_dup = ["DateForDup"] + [
                col for col in available_dup_cols if col != "Date"
            ]
        else:  # If Date is not datetime (e.g., already string or object), use as is
            check_cols_for_dup = available_dup_cols

        duplicates_mask = temp_df_for_dup_check.duplicated(
            subset=check_cols_for_dup, keep="first"
        )

        num_duplicates = duplicates_mask.sum()
        if num_duplicates > 0:
            logger.warning(
                f"Detected {num_duplicates} potential duplicate transactions in merged data."
            )
            for idx in df[
                duplicates_mask
            ].index:  # df.index should be unique after reset_index in merge
                self._update_row_data_quality_flags(
                    df, idx, [DataQualityFlag.DUPLICATE_SUSPECTED]
                )
                self._log_data_quality_issue(
                    "merged_dup_check",
                    idx,
                    df.loc[idx].to_dict(),
                    [DataQualityFlag.DUPLICATE_SUSPECTED],
                )
        return df

    def _process_rent_data(
        self, rent_alloc: pd.DataFrame, rent_hist: pd.DataFrame
    ) -> pd.DataFrame:
        logger.info(
            "Processing rent data with budget analysis from Rent Allocation and Rent History..."
        )

        df = merge_rent_data(rent_alloc, rent_hist)
        if df.empty:
            logger.warning("Combined rent data is empty. Returning empty DataFrame.")
            essential_cols = [
                "Date",
                "GrossTotal",
                "RyanRentPortion",
                "TransactionType",
                "Payer",
                "IsShared",
                "ActualAmount",
                "AllowedAmount",
                "DataQualityFlag",
                "RyanOwes",
                "JordynOwes",
                "BalanceImpact",
                "Description",
                "AuditNote",
                "Month_Display",
            ]
            return pd.DataFrame(columns=essential_cols)

        # Standardize column names for main analyzer
        rename_map = {
            "Month_Date": "Date",  # This is critical, Month_Date from loader becomes 'Date'
            "Month": "Month_Display",  # Original 'Month' string for display
            # 'Gross Total' is already used directly
            # "Ryan's Rent (43%)" -> "RyanRentPortion"
            # "Jordyn's Rent (57%)" -> "JordynRentPortion"
        }
        # Check if these specific columns to rename exist, as they come from Rent_Allocation_xxxx.csv
        if "Ryan's Rent (43%)" in df.columns:
            rename_map["Ryan's Rent (43%)"] = "RyanRentPortion"
        if "Jordyn's Rent (57%)" in df.columns:
            rename_map["Jordyn's Rent (57%)"] = "JordynRentPortion"
        if (
            "Gross Total" in df.columns
        ):  # Ensure this is also mapped if needed by downstream
            rename_map["Gross Total"] = "GrossTotal"

        df.rename(columns=rename_map, inplace=True)

        # Ensure critical columns exist after rename
        if "Date" not in df.columns:
            df["Date"] = pd.NaT
        if "GrossTotal" not in df.columns:
            df["GrossTotal"] = 0.0
        if "RyanRentPortion" not in df.columns:
            df["RyanRentPortion"] = 0.0
        if "Month_Display" not in df.columns:
            df["Month_Display"] = "Unknown"

        df["TransactionType"] = "RENT"
        df["Payer"] = "Jordyn"  # Assumption: Jordyn pays rent initially
        df["IsShared"] = True
        df["ActualAmount"] = df["GrossTotal"]
        df["AllowedAmount"] = df["GrossTotal"]
        df["DataQualityFlag"] = DataQualityFlag.CLEAN.value  # Initialize

        # Check for high rent baseline variance (original check from _load_and_clean_rent_data)
        if self.config.RENT_BASELINE > 0:
            variance = (
                df["GrossTotal"] - self.config.RENT_BASELINE
            ).abs() / self.config.RENT_BASELINE
            high_variance_baseline_mask = variance > self.config.RENT_VARIANCE_THRESHOLD
            for idx in df[high_variance_baseline_mask].index:
                self._update_row_data_quality_flags(
                    df, idx, [DataQualityFlag.RENT_VARIANCE_HIGH]
                )
                self._log_data_quality_issue(
                    "rent_baseline_variance",
                    idx,
                    df.loc[idx].to_dict(),
                    [DataQualityFlag.RENT_VARIANCE_HIGH],
                )

        # Check for budget variance issues (from Rent History)
        if "Budget_Variance_Pct" in df.columns:
            high_variance_budget_mask = (
                df["Budget_Variance_Pct"].abs()
                > self.config.RENT_BUDGET_VARIANCE_THRESHOLD_PCT
            )
            for idx in df[high_variance_budget_mask].index:
                self._update_row_data_quality_flags(
                    df, idx, [DataQualityFlag.RENT_BUDGET_VARIANCE_HIGH]
                )
                self._log_data_quality_issue(
                    "rent_budget_variance",
                    idx,
                    df.loc[idx].to_dict(),
                    [DataQualityFlag.RENT_BUDGET_VARIANCE_HIGH],
                )

        df["RyanOwes"] = df["RyanRentPortion"]
        df["JordynOwes"] = 0.0  # Jordyn paid, so she owes 0 of her own payment
        df["BalanceImpact"] = df["RyanOwes"]  # Positive means Ryan owes Jordyn for rent

        df["Description"] = df.apply(
            lambda r: f"Rent for {r.get('Month_Display', 'Unknown Month')}", axis=1
        )
        df["AuditNote"] = df.apply(self._create_enhanced_rent_audit_note, axis=1)

        logger.info(f"Processed {len(df)} combined rent records.")
        return df

    def _create_rent_audit_note(self, row: pd.Series) -> str:
        """Base audit note for rent transactions (to be enhanced). Copied from original for base functionality."""
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
            logger.error(
                f"Error creating rent audit note for row {row.name if hasattr(row, 'name') else 'UNKNOWN'}: {e}"
            )
            return f"Error in audit note. Quality: {row.get('DataQualityFlag', DataQualityFlag.CLEAN.value)}"

    def _create_enhanced_rent_audit_note(self, row: pd.Series) -> str:
        base_note = self._create_rent_audit_note(row)  # Use the existing base note

        budget_note_parts = []
        if "Total_Budgeted" in row and pd.notna(row["Total_Budgeted"]):
            budget_note_parts.append(f"Budgeted: ${row['Total_Budgeted']:,.2f}")
        if "Total_Actual" in row and pd.notna(row["Total_Actual"]):
            budget_note_parts.append(f"Actual: ${row['Total_Actual']:,.2f}")

        if "Budget_Variance" in row and pd.notna(row["Budget_Variance"]):
            variance = row["Budget_Variance"]
            variance_pct = row.get("Budget_Variance_Pct", 0)
            if abs(variance) > 0.01:  # Only add if there's a notable variance
                budget_note_parts.append(
                    f"Variance: ${variance:+.2f} ({variance_pct:+.1f}%)"
                )

        if budget_note_parts:
            full_budget_note = " | Budget Info: " + ", ".join(budget_note_parts)
            # Insert before "Quality:"
            if " Quality:" in base_note:
                base_note = base_note.replace(
                    " Quality:", full_budget_note + " Quality:"
                )
            else:  # Append if "Quality:" not found
                base_note += full_budget_note

        return base_note

    def _create_expense_audit_note(self, row: pd.Series) -> str:
        """Create audit note for expense transactions. Copied from original."""
        try:
            actual_amount = row.get("ActualAmount", 0.0)
            allowed_amount = row.get(
                "AllowedAmount", 0.0
            )  # This should be set before calling
            payer = row.get("Payer", "N/A")
            desc = str(row.get("Description", "")).strip()
            quality = row.get("DataQualityFlag", DataQualityFlag.CLEAN.value)
            trans_type = row.get("TransactionType", "EXPENSE")

            actual_amount_f = float(actual_amount) if pd.notna(actual_amount) else 0.0
            allowed_amount_f = (
                float(allowed_amount) if pd.notna(allowed_amount) else 0.0
            )
            personal_portion = actual_amount_f - allowed_amount_f

            explanation = ""
            if trans_type == "SETTLEMENT":
                explanation = (
                    f"{payer} paid ${actual_amount_f:,.2f} | SETTLEMENT PAYMENT."
                )
            elif (
                not row.get("IsShared", False) or abs(allowed_amount_f) < 0.01
            ):  # Check IsShared flag
                explanation = f"{payer} paid ${actual_amount_f:,.2f} | PERSONAL EXPENSE – not shared."
            elif abs(personal_portion) < 0.01:  # Full amount shared
                explanation = f"{payer} paid ${actual_amount_f:,.2f} | FULLY SHARED."
            else:  # Partially shared
                reason = (
                    f"REASON: {desc}"
                    if desc
                    else "REASON: no specific note for partial share."
                )
                explanation = (
                    f"{payer} paid ${actual_amount_f:,.2f} | PARTIALLY SHARED: "
                    f"only ${allowed_amount_f:,.2f} is shared. {reason}"
                )

            return f"{explanation} | DataQuality: {quality}"
        except Exception as e:
            logger.error(
                f"Error creating expense audit note for row {row.name if hasattr(row, 'name') else 'UNKNOWN'}: {e}"
            )
            return f"Error in audit note. Quality: {row.get('DataQualityFlag', DataQualityFlag.CLEAN.value)}"

    def _validate_against_ledger_balance(
        self, master_ledger: pd.DataFrame, transaction_ledger: pd.DataFrame
    ):
        logger.info(
            "Validating master ledger's running balance against transaction ledger's..."
        )

        if (
            transaction_ledger.empty
            or "Running Balance" not in transaction_ledger.columns
            or transaction_ledger["Running Balance"].isna().all()
        ):
            logger.warning(
                "Transaction ledger is empty or missing valid 'Running Balance' data. Skipping ledger balance validation."
            )
            self.validation_results["ledger_balance_match"] = "Skipped - No Ledger Data"
            return

        # Ensure transaction_ledger is sorted by date to get the correct final balance
        # Assuming 'Date of Purchase' is the relevant date column in transaction_ledger
        if "Date of Purchase" in transaction_ledger.columns:
            ledger_sorted = transaction_ledger.sort_values(by="Date of Purchase").copy()
            ledger_final_balance = (
                ledger_sorted["Running Balance"].iloc[-1]
                if not ledger_sorted.empty
                else 0.0
            )
        else:  # Fallback if no date column for sorting, just take last row
            ledger_final_balance = (
                transaction_ledger["Running Balance"].iloc[-1]
                if not transaction_ledger.empty
                else 0.0
            )
            logger.warning(
                "Transaction Ledger has no 'Date of Purchase' column, using last row for final balance without date sorting."
            )

        our_final_balance = (
            master_ledger["RunningBalance"].iloc[-1]
            if not master_ledger.empty and "RunningBalance" in master_ledger
            else 0.0
        )

        difference = abs(ledger_final_balance - our_final_balance)

        if difference > 0.01:  # More than 1 cent difference
            msg = (
                f"Running balance mismatch! Ledger: ${ledger_final_balance:,.2f}, "
                f"Calculated: ${our_final_balance:,.2f}, Diff: ${difference:,.2f}"
            )
            logger.warning(msg)
            self.validation_results["ledger_balance_match"] = (
                f"Mismatch (Diff: ${difference:,.2f})"
            )
            self._log_data_quality_issue(
                "balance_validation",
                "final_balances",
                {
                    "ledger_balance": ledger_final_balance,
                    "calculated_balance": our_final_balance,
                    "difference": difference,
                },
                [DataQualityFlag.BALANCE_MISMATCH_WITH_LEDGER],
            )
        else:
            logger.info("✓ Running balance matches transaction ledger's final balance.")
            self.validation_results["ledger_balance_match"] = "Matched"

    def _analyze_rent_budget_variance(self, rent_df: pd.DataFrame) -> Dict[str, Any]:
        logger.info("Analyzing rent budget variance...")
        analysis: Dict[str, Any] = {}  # Ensure type

        if (
            "Budget_Variance" not in rent_df.columns
            or rent_df["Budget_Variance"].isna().all()
        ):
            return {"message": "No budget data available or all variances are NaN"}

        variance_data = rent_df[
            rent_df["Budget_Variance"].notna()
        ].copy()  # Work with non-NaN variance data

        if not variance_data.empty:
            month_col = (
                "Month_Display" if "Month_Display" in variance_data.columns else "Date"
            )  # Prefer Month_Display

            # Ensure the month column for idxmax/idxmin is string for proper display
            variance_data[month_col] = variance_data[month_col].astype(str)

            analysis = {
                "total_budget_variance": round(
                    variance_data["Budget_Variance"].sum(), 2
                ),
                "avg_monthly_variance": round(
                    variance_data["Budget_Variance"].mean(), 2
                ),
                "months_over_budget": len(
                    variance_data[variance_data["Budget_Variance"] > 0.005]
                ),  # Small threshold
                "months_under_budget": len(
                    variance_data[variance_data["Budget_Variance"] < -0.005]
                ),
                "largest_overrun": {},
                "largest_underrun": {},
            }
            if not variance_data[variance_data["Budget_Variance"] > 0.005].empty:
                analysis["largest_overrun"] = {
                    "month": variance_data.loc[
                        variance_data["Budget_Variance"].idxmax(), month_col
                    ],
                    "amount": round(variance_data["Budget_Variance"].max(), 2),
                }
            if not variance_data[variance_data["Budget_Variance"] < -0.005].empty:
                analysis["largest_underrun"] = {
                    "month": variance_data.loc[
                        variance_data["Budget_Variance"].idxmin(), month_col
                    ],
                    "amount": round(variance_data["Budget_Variance"].min(), 2),
                }
            logger.info(f"Rent budget variance analysis: {analysis}")
        else:
            analysis = {"message": "No non-NaN budget variance data to analyze."}
            logger.info(analysis["message"])

        return analysis

    def analyze(self) -> Dict[str, Any]:
        """Execute comprehensive analysis pipeline with all four data sources"""
        try:
            logger.info("Starting analysis pipeline v2.3...")

            loader = DataLoaderV23()
            expense_hist_raw = loader.load_expense_history(self.expense_file)
            transaction_ledger_raw = loader.load_transaction_ledger(self.ledger_file)
            rent_alloc_raw = loader.load_rent_allocation(self.rent_alloc_file)
            rent_hist_raw = loader.load_rent_history(self.rent_hist_file)

            data_sources_summary = loader.validate_loaded_data(
                expense_hist_raw, transaction_ledger_raw, rent_alloc_raw, rent_hist_raw
            )

            # Check if critical data is missing
            if expense_hist_raw.empty and transaction_ledger_raw.empty:
                logger.error(
                    "Both Expense History and Transaction Ledger are empty or failed to load. Cannot proceed."
                )
                raise ValueError("Critical expense data sources are missing.")
            if rent_alloc_raw.empty:
                logger.warning(
                    "Rent Allocation data is empty. Rent-related analysis will be significantly impacted."
                )

            expense_df = self._process_expense_data(
                expense_hist_raw, transaction_ledger_raw
            )
            rent_df = self._process_rent_data(rent_alloc_raw, rent_hist_raw)

            master_ledger = self._create_master_ledger(rent_df, expense_df)

            if not transaction_ledger_raw.empty:  # Only validate if ledger was loaded
                self._validate_against_ledger_balance(
                    master_ledger, transaction_ledger_raw
                )

            reconciliation_results = self._triple_reconciliation(master_ledger)
            analytics_results = self._perform_advanced_analytics(
                master_ledger
            )  # This also needs master_ledger

            if not rent_df.empty and "Budget_Variance" in rent_df.columns:
                analytics_results["rent_budget_analysis"] = (
                    self._analyze_rent_budget_variance(rent_df)
                )

            risk_assessment = self._comprehensive_risk_assessment(
                master_ledger, analytics_results
            )
            visualizations = self._create_visualizations_v22(
                master_ledger, analytics_results, reconciliation_results
            )  # Pass master_ledger
            recommendations = self._generate_recommendations(
                analytics_results, risk_assessment, reconciliation_results
            )

            self._validate_results_summary(
                reconciliation_results, master_ledger
            )  # Renamed to avoid conflict
            output_paths = self._generate_outputs(
                master_ledger,
                reconciliation_results,
                analytics_results,
                risk_assessment,
                recommendations,
                visualizations,
            )
            self._check_performance()

            final_results = {
                "reconciliation": reconciliation_results,
                "analytics": analytics_results,
                "risk_assessment": risk_assessment,
                "recommendations": recommendations,
                "data_quality_score": self._calculate_data_quality_score(master_ledger),
                "data_quality_issues_summary": self._summarize_data_quality_issues(
                    master_ledger
                ),
                "validation_summary": self.validation_results,  # Use the populated dict
                "output_paths": output_paths,
                "data_sources_summary": data_sources_summary,
                "performance_metrics": {
                    "processing_time_seconds": round(
                        (datetime.now(timezone.utc) - self.start_time).total_seconds(),
                        2,
                    ),
                    "memory_usage_mb": round(self.memory_usage_mb, 2),
                    "total_transactions": len(master_ledger)
                    if not master_ledger.empty
                    else 0,
                },
            }
            logger.info("Analysis pipeline v2.3 completed successfully.")
            logging.shutdown()
            return final_results
        except Exception as e:
            logger.error(f"Analysis failed in v2.3 pipeline: {str(e)}", exc_info=True)
            if self.data_quality_issues:
                try:
                    output_dir = Path("analysis_output")
                    output_dir.mkdir(exist_ok=True)
                    error_df = pd.DataFrame(self.data_quality_issues)
                    error_path = (
                        output_dir / "data_quality_issues_PARTIAL_FAILURE_v2.3.csv"
                    )
                    error_df.to_csv(error_path, index=False)
                    logger.info(f"Partial data quality issues logged to {error_path}")
                except Exception as log_e:
                    logger.error(
                        f"Could not write partial data quality log during failure: {log_e}"
                    )
            raise

    def _explode_audit(self, audit_note: str) -> Tuple[str, str, str, str]:
        """Parse audit note into structured components. Copied from original."""
        if pd.isna(audit_note) or not str(audit_note).strip():
            return ("<NA>", "<NA>", "<NA>", "<NA>")

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

        quality_match = re.search(r"DataQuality: (\w+)", audit_str)
        data_quality = quality_match.group(1) if quality_match else "CLEAN"

        return (who_paid, share_type, shared_reason, data_quality)

    def _create_master_ledger(
        self, rent_df: pd.DataFrame, expense_df: pd.DataFrame
    ) -> pd.DataFrame:
        logger.info(
            "Creating master ledger v2.3 from processed rent and expense data..."
        )

        # Ensure essential columns are present in both DataFrames before concat
        # Columns expected by concat and downstream processes:
        # Date, TransactionType, Payer, Description, ActualAmount, AllowedAmount, IsShared,
        # RyanOwes, JordynOwes, BalanceImpact, AuditNote, DataQualityFlag, Merchant (optional for rent)

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

        # Ensure rent_df has 'Merchant' or fill with a placeholder
        if "Merchant" not in rent_df.columns:
            rent_df["Merchant"] = "Landlord/Property"  # Default for rent

        for df_iter, name in [(rent_df, "rent_df"), (expense_df, "expense_df")]:
            if df_iter.empty:
                logger.warning(
                    f"{name} is empty. It will not contribute to master ledger."
                )
                # Create an empty df with common_cols to allow concat if one is empty
                # This is tricky, if one is empty, it should just be skipped by concat basically
                # For now, let's assume if one is empty, concat handles it.
                continue
            for col in common_cols:
                if col not in df_iter.columns:
                    logger.warning(
                        f"Column '{col}' missing in {name}. Adding as NaN/0/False."
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
                    else:  # String columns like TransactionType, Payer, Description, AuditNote, DataQualityFlag, Merchant
                        df_iter[col] = pd.NA  # Use pd.NA for string/object columns

        # Filter out completely empty dataframes before concat to avoid issues with all-NA columns
        dfs_to_concat = []
        if not rent_df.empty:
            dfs_to_concat.append(rent_df[common_cols])
        if not expense_df.empty:
            dfs_to_concat.append(expense_df[common_cols])

        if not dfs_to_concat:
            logger.error(
                "Both processed rent and expense DataFrames are empty. Master ledger cannot be created."
            )
            return pd.DataFrame(
                columns=common_cols
                + [
                    "RunningBalance",
                    "TransactionID",
                    "DataLineage",
                    "Who_Paid_Text",
                    "Share_Type",
                    "Shared_Reason",
                    "DataQuality_Audit",
                ]
            )

        master = pd.concat(dfs_to_concat, ignore_index=True, sort=False)

        # Convert Date to datetime if it's not already, crucial for sorting
        if "Date" in master.columns:
            master["Date"] = pd.to_datetime(master["Date"], errors="coerce")
        else:  # Should not happen if columns are ensured
            master["Date"] = pd.NaT
            logger.error("Master ledger is missing 'Date' column after concat.")

        # Handle NaT in Date column before sorting: either drop or fill
        # For financial ledger, rows with no date are problematic.
        if master["Date"].isna().any():
            logger.warning(
                f"{master['Date'].isna().sum()} transactions have missing dates in master ledger. They will be sorted to the beginning or end."
            )
            # Optionally, impute again or drop:
            # master = master.dropna(subset=['Date'])

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

        master["RunningBalance"] = (
            master["BalanceImpact"].cumsum().round(self.config.CURRENCY_PRECISION)
        )
        master["TransactionID"] = master.apply(self._generate_transaction_id, axis=1)
        master["DataLineage"] = master.apply(
            lambda row: f"Source: {row.get('TransactionType','NA')} | OriginalIndex(PostProc): {row.name} | Processing: v2.3",
            axis=1,
        )

        # Audit split columns
        audit_components = (
            master["AuditNote"].astype(str).apply(self._explode_audit)
        )  # Ensure AuditNote is str
        master[
            ["Who_Paid_Text", "Share_Type", "Shared_Reason", "DataQuality_Audit"]
        ] = pd.DataFrame(audit_components.tolist(), index=master.index)
        master["DataQualityFlag"] = master["DataQualityFlag"].fillna(
            DataQualityFlag.CLEAN.value
        )

        logger.info(f"Created master ledger v2.3 with {len(master)} transactions.")
        if not master.empty and master["Date"].notna().any():
            logger.info(f"Date range: {master['Date'].min()} to {master['Date'].max()}")
        else:
            logger.warning(
                "Master ledger is empty or contains no valid dates after processing."
            )
        return master

    def _generate_transaction_id(self, row: pd.Series) -> str:
        """Generate unique transaction ID. Copied from original."""
        date_str = (
            row["Date"].isoformat()
            if isinstance(row.get("Date"), (datetime, pd.Timestamp))
            and pd.notna(row.get("Date"))
            else str(row.get("Date", "NoDate"))
        )
        # Use .get for safety, provide defaults
        key_data = (
            f"{date_str}_"
            f"{row.get('Payer','NA')}_"
            f"{row.get('Merchant','NA')}_"
            f"{row.get('Description','NoDesc')[:20]}_"  # Add part of description for more uniqueness
            f"{row.get('ActualAmount',0.0):.2f}_"
            f"{row.get('AllowedAmount',0.0):.2f}_"
            f"{row.get('BalanceImpact',0.0):.2f}"
        )
        return hashlib.md5(key_data.encode()).hexdigest()[:16]  # Slightly longer ID

    # --- All other analysis, visualization, and reporting methods from the original script ---
    # --- These methods are assumed to largely work with the processed master_ledger ---
    # --- Minor adjustments might be needed based on column name changes or data types ---

    def _triple_reconciliation(self, master_ledger: pd.DataFrame) -> Dict[str, Any]:
        """Perform triple reconciliation. Based on original."""
        logger.info("Performing triple reconciliation...")
        if master_ledger.empty or "BalanceImpact" not in master_ledger.columns:
            logger.warning(
                "Master ledger is empty or missing 'BalanceImpact'. Reconciliation will yield zero values."
            )
            return {
                "method1_running_balance": 0,
                "method2_variance_ryan_vs_fair": 0,
                "method3_category_sum_ryan_vs_fair": 0,
                "reconciled": True,
                "max_difference": 0,
                "total_shared_amount": 0,
                "ryan_total_fair_share": 0,
                "jordyn_total_fair_share": 0,
                "ryan_actually_paid_for_shared": 0,
                "jordyn_actually_paid_for_shared": 0,
                "ryan_net_variance_from_fair_share": 0,
                "jordyn_net_variance_from_fair_share": 0,
                "category_details": [],
                "final_balance_reported": 0,
                "who_owes_whom": "No transactions",
                "amount_owed": 0,
            }

        # Method 1: Final Running Balance
        # This directly reflects "Ryan owes Jordyn" if positive.
        method1_balance = (
            master_ledger["RunningBalance"].iloc[-1] if not master_ledger.empty else 0.0
        )

        # Method 2: Ryan's Net Position vs. Fair Share of Total Shared Expenses
        # Total shared expenses * Ryan's percentage = Ryan's fair share obligation.
        # Ryan's payments towards shared - Ryan's fair share obligation = Ryan's position.
        # If Ryan paid MORE than his fair share, this value is positive (Jordyn owes Ryan for overpayment).
        # If Ryan paid LESS than his fair share, this value is negative (Ryan owes Jordyn for underpayment).
        # This should be the INVERSE of method1_balance.
        shared_only = master_ledger[master_ledger["IsShared"] == True].copy()
        if shared_only.empty:  # If no shared transactions, M2 and M3 are zero.
            method2_balance = 0.0
            method3_balance = 0.0
            total_shared_amount = 0.0
            ryan_total_fair_share = 0.0
            jordyn_total_fair_share = 0.0
            ryan_actually_paid_for_shared = 0.0
            jordyn_actually_paid_for_shared = 0.0
            category_balances_info = []
        else:
            total_shared_amount = shared_only["AllowedAmount"].sum()
            ryan_total_fair_share = total_shared_amount * self.config.RYAN_PCT
            jordyn_total_fair_share = total_shared_amount * self.config.JORDYN_PCT

            ryan_actually_paid_for_shared = shared_only[
                shared_only["Payer"].str.lower() == "ryan"
            ]["AllowedAmount"].sum()
            jordyn_actually_paid_for_shared = shared_only[
                shared_only["Payer"].str.lower() == "jordyn"
            ]["AllowedAmount"].sum()

            # Ryan's variance: if positive, Ryan overpaid his share (Jordyn owes Ryan)
            # if negative, Ryan underpaid his share (Ryan owes Jordyn)
            method2_balance = ryan_actually_paid_for_shared - ryan_total_fair_share

            # Method 3: Sum of Ryan's Net Position by Category (Rent, Expenses)
            # This should also equal method2_balance.
            category_balances_info = []
            method3_balance_accumulator = 0.0
            for trans_type in ["RENT", "EXPENSE"]:  # Assuming these are the main types
                type_data = shared_only[shared_only["TransactionType"] == trans_type]
                if not type_data.empty:
                    type_total_shared = type_data["AllowedAmount"].sum()
                    type_ryan_fair_share_cat = type_total_shared * self.config.RYAN_PCT

                    type_ryan_paid_cat = type_data[
                        type_data["Payer"].str.lower() == "ryan"
                    ]["AllowedAmount"].sum()
                    type_jordyn_paid_cat = type_data[
                        type_data["Payer"].str.lower() == "jordyn"
                    ]["AllowedAmount"].sum()

                    type_ryan_variance_cat = (
                        type_ryan_paid_cat - type_ryan_fair_share_cat
                    )
                    method3_balance_accumulator += type_ryan_variance_cat

                    category_balances_info.append(
                        {
                            "Category": trans_type,
                            "TotalShared": round(type_total_shared, 2),
                            "RyanPaidShared": round(type_ryan_paid_cat, 2),
                            "JordynPaidShared": round(type_jordyn_paid_cat, 2),
                            "RyanFairShare": round(type_ryan_fair_share_cat, 2),
                            "RyanVarianceForCategory": round(type_ryan_variance_cat, 2),
                        }
                    )
            method3_balance = method3_balance_accumulator

        # Reconciliation Check:
        # M1 (RunningBalance: Ryan owes Jordyn if > 0)
        # M2 (RyanPaymentVariance: Ryan overpaid if > 0, so Jordyn owes Ryan if >0)
        # M3 (CategorySumOfRyanPaymentVariance: Same as M2)
        # So, M1 should be approx -M2 and M1 should be approx -M3.
        # And M2 should be approx M3.
        tolerance = 0.015  # Increased tolerance slightly for complex calcs
        reconciled_1_2 = abs(method1_balance + method2_balance) <= tolerance
        reconciled_2_3 = abs(method2_balance - method3_balance) <= tolerance
        all_reconciled = reconciled_1_2 and reconciled_2_3

        final_balance_to_report = method1_balance  # M1 is the direct running balance
        who_owes = (
            "Ryan owes Jordyn"
            if final_balance_to_report > 0.005
            else "Jordyn owes Ryan"
            if final_balance_to_report < -0.005
            else "Settled"
        )
        amount_owed_val = abs(final_balance_to_report)

        logger.info(f"Triple Reconciliation Results (v2.3 logic):")
        logger.info(
            f"  M1 (Running Balance): ${method1_balance:,.2f} ({'Ryan owes Jordyn' if method1_balance > 0 else 'Jordyn owes Ryan' if method1_balance < 0 else 'Settled'})"
        )
        logger.info(
            f"  M2 (Ryan's Net Payment vs Fair Share): ${method2_balance:,.2f} ({'Jordyn owes Ryan' if method2_balance > 0 else 'Ryan owes Jordyn' if method2_balance < 0 else 'Settled'})"
        )
        logger.info(
            f"  M3 (Category Sum of Ryan's Net Payment vs Fair Share): ${method3_balance:,.2f} ({'Jordyn owes Ryan' if method3_balance > 0 else 'Ryan owes Jordyn' if method3_balance < 0 else 'Settled'})"
        )
        logger.info(f"  All Reconciled (M1 ~ -M2, M2 ~ M3): {all_reconciled}")
        if not all_reconciled:
            logger.error(
                f"Reconciliation discrepancy! M1+M2 diff: {method1_balance + method2_balance:.4f}, M2-M3 diff: {method2_balance - method3_balance:.4f}"
            )

        return {
            "method1_running_balance": round(method1_balance, 2),
            "method2_variance_ryan_vs_fair": round(method2_balance, 2),
            "method3_category_sum_ryan_vs_fair": round(method3_balance, 2),
            "reconciled": all_reconciled,
            "max_difference": round(
                max(
                    abs(method1_balance + method2_balance),
                    abs(method2_balance - method3_balance),
                ),
                2,
            ),
            "total_shared_amount": round(total_shared_amount, 2),
            "ryan_total_fair_share": round(ryan_total_fair_share, 2),
            "jordyn_total_fair_share": round(jordyn_total_fair_share, 2),
            "ryan_actually_paid_for_shared": round(ryan_actually_paid_for_shared, 2),
            "jordyn_actually_paid_for_shared": round(
                jordyn_actually_paid_for_shared, 2
            ),
            "ryan_net_variance_from_fair_share": round(
                method2_balance, 2
            ),  # M2 is this value
            "jordyn_net_variance_from_fair_share": round(
                (jordyn_actually_paid_for_shared - jordyn_total_fair_share), 2
            ),
            "category_details": category_balances_info,
            "final_balance_reported": round(final_balance_to_report, 2),
            "who_owes_whom": who_owes,
            "amount_owed": round(amount_owed_val, 2),
        }

    def _perform_advanced_analytics(
        self, master_ledger: pd.DataFrame
    ) -> Dict[str, Any]:
        """Run advanced analytics. Based on original."""
        logger.info("Running advanced analytics...")
        analytics: Dict[str, Any] = {}  # Ensure type
        if master_ledger.empty or master_ledger["Date"].isna().all():
            logger.warning(
                "Master ledger is empty or has no valid dates for advanced analytics."
            )
            return {"error": "No data for advanced analytics"}

        # Ensure Date is datetime
        master_ledger["Date"] = pd.to_datetime(master_ledger["Date"], errors="coerce")
        valid_dates_ledger = master_ledger.dropna(subset=["Date"])
        if valid_dates_ledger.empty:
            logger.warning(
                "Master ledger has no valid dates after coercion for advanced analytics."
            )
            return {"error": "No valid dates for advanced analytics"}

        # Monthly cash flow for shared items by payer
        shared_ledger = valid_dates_ledger[valid_dates_ledger["IsShared"] == True]
        if not shared_ledger.empty:
            # Ensure Payer column exists
            if "Payer" not in shared_ledger.columns:
                shared_ledger["Payer"] = "Unknown"

            monthly_cash_flow = (
                shared_ledger.groupby([pd.Grouper(key="Date", freq="ME"), "Payer"])[
                    "AllowedAmount"
                ]
                .sum()
                .unstack(fill_value=0)
                .round(self.config.CURRENCY_PRECISION)
            )
            analytics["monthly_payments_by_payer_for_shared_items"] = (
                monthly_cash_flow.to_dict("index")
            )  # More JSON friendly
        else:
            analytics["monthly_payments_by_payer_for_shared_items"] = {}

        # Liquidity strain points
        liquidity_issues = []
        if (
            "RunningBalance" in valid_dates_ledger.columns
            and "TransactionID" in valid_dates_ledger.columns
        ):
            high_balance_transactions = valid_dates_ledger[
                valid_dates_ledger["RunningBalance"].abs()
                > self.config.LIQUIDITY_STRAIN_THRESHOLD
            ]
            for idx, row in high_balance_transactions.iterrows():
                liquidity_issues.append(
                    {
                        "date": row["Date"].strftime("%Y-%m-%d")
                        if pd.notna(row["Date"])
                        else "N/A",
                        "running_balance": round(row["RunningBalance"], 2),
                        "transaction_id": row["TransactionID"],
                        "description": row.get("Description", "N/A"),
                    }
                )
        analytics["potential_liquidity_strain_points"] = liquidity_issues

        # Expense category analysis (Pareto)
        expense_only_df = valid_dates_ledger[
            (valid_dates_ledger["TransactionType"] == "EXPENSE")
            & (valid_dates_ledger["IsShared"] == True)
        ].copy()
        if not expense_only_df.empty and "Merchant" in expense_only_df.columns:
            expense_only_df["Category"] = expense_only_df["Merchant"].apply(
                self._categorize_merchant
            )
            category_summary = (
                expense_only_df.groupby("Category")["AllowedAmount"]
                .agg(["sum", "count", "mean"])
                .round(self.config.CURRENCY_PRECISION)
            )
            if not category_summary.empty:
                category_totals = category_summary["sum"].sort_values(ascending=False)
                pareto_cumsum_pct = (
                    (category_totals.cumsum() / category_totals.sum() * 100)
                    if category_totals.sum() != 0
                    else pd.Series(dtype=float)
                )
                pareto_80_categories = (
                    pareto_cumsum_pct[pareto_cumsum_pct <= 80].index.tolist()
                    if not pareto_cumsum_pct.empty
                    else []
                )
                analytics["expense_category_analysis"] = {
                    "summary_table": category_summary.reset_index().to_dict(
                        "records"
                    ),  # More JSON friendly
                    "pareto_80_categories_list": pareto_80_categories,
                    "pareto_80_amount_sum": round(
                        category_totals.loc[pareto_80_categories].sum(), 2
                    )
                    if pareto_80_categories
                    else 0.0,
                }
        else:
            analytics["expense_category_analysis"] = {
                "message": "No shared expenses with merchant data for category analysis."
            }

        # Monthly shared spending trend
        monthly_shared_spending = shared_ledger.resample("ME", on="Date")[
            "AllowedAmount"
        ].sum()
        if len(monthly_shared_spending) >= 3:
            x = np.arange(len(monthly_shared_spending))
            y = monthly_shared_spending.values
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
            analytics["monthly_shared_spending_trend"] = {
                "slope_per_month": round(slope, 2),
                "r_squared": round(r_value**2, 4) if pd.notna(r_value) else 0.0,
                "p_value": round(p_value, 4) if pd.notna(p_value) else 1.0,
                "trend_significant": (p_value < 0.05) if pd.notna(p_value) else False,
                "monthly_values": {
                    d.strftime("%Y-%m"): round(val, 2)
                    for d, val in monthly_shared_spending.items()
                },
            }
            # Forecast
            future_x = np.arange(
                len(monthly_shared_spending), len(monthly_shared_spending) + 3
            )
            forecast_values = slope * future_x + intercept
            # Ensure start date for forecast is valid
            if not monthly_shared_spending.index.empty:
                forecast_start_date = (
                    monthly_shared_spending.index.max() + pd.DateOffset(months=1)
                )
                forecast_dates = pd.date_range(
                    start=forecast_start_date, periods=3, freq="ME"
                )
                analytics["monthly_shared_spending_forecast"] = dict(
                    zip(
                        [d.strftime("%Y-%m") for d in forecast_dates],
                        np.round(forecast_values, 2),
                    )
                )
            else:
                analytics["monthly_shared_spending_forecast"] = {
                    "message": "Not enough data for forecast (source index empty)."
                }

        else:
            analytics["monthly_shared_spending_trend"] = {
                "message": "Not enough monthly data points (need at least 3) for trend."
            }
            analytics["monthly_shared_spending_forecast"] = {
                "message": "Not enough data for forecast."
            }

        # Month-end running balance stats
        if "RunningBalance" in valid_dates_ledger.columns:
            month_end_balances = valid_dates_ledger.resample("ME", on="Date")[
                "RunningBalance"
            ].last()
            if not month_end_balances.empty:
                analytics["month_end_running_balance_stats"] = {
                    "mean": round(month_end_balances.mean(), 2),
                    "std_dev": round(month_end_balances.std(), 2),
                    "min": round(month_end_balances.min(), 2),
                    "max": round(month_end_balances.max(), 2),
                    "median": round(month_end_balances.median(), 2),
                }
            else:
                analytics["month_end_running_balance_stats"] = {
                    "message": "No data for running balance stats."
                }
        else:
            analytics["month_end_running_balance_stats"] = {
                "message": "RunningBalance column not available."
            }

        logger.info("Advanced analytics completed.")
        return analytics

    def _comprehensive_risk_assessment(
        self, master_ledger: pd.DataFrame, analytics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform comprehensive risk assessment. Based on original."""
        logger.info("Performing comprehensive risk assessment...")
        risks: Dict[str, Any] = {
            "overall_risk_level": "LOW",
            "details": [],
        }  # Ensure type for details
        if master_ledger.empty:
            risks["details"].append(
                {
                    "risk_type": "Data Availability",
                    "assessment": "No data to assess risks.",
                    "level": "HIGH",
                }
            )
            risks["overall_risk_level"] = "HIGH"
            return risks

        dq_score = self._calculate_data_quality_score(master_ledger)
        if dq_score < self.config.DATA_QUALITY_THRESHOLD * 100:
            level = "HIGH" if dq_score < 70 else "MEDIUM"
            risks["details"].append(
                {
                    "risk_type": "Data Quality",
                    "assessment": f"Data quality score ({dq_score:.1f}%) is below threshold ({self.config.DATA_QUALITY_THRESHOLD*100:.1f}%). Review issues.",
                    "level": level,
                }
            )

        if (
            "potential_liquidity_strain_points" in analytics
            and analytics["potential_liquidity_strain_points"]
        ):
            strain_count = len(analytics["potential_liquidity_strain_points"])
            risks["details"].append(
                {
                    "risk_type": "Liquidity Strain",
                    "assessment": f"{strain_count} instance(s) where running balance exceeded ${self.config.LIQUIDITY_STRAIN_THRESHOLD:,.0f}. Regular settlements advised.",
                    "level": "MEDIUM"
                    if strain_count > 0
                    else "LOW",  # Should this be HIGH if many?
                }
            )

        trend_info = analytics.get("monthly_shared_spending_trend", {})
        if trend_info.get("slope_per_month", 0) > 100 and trend_info.get(
            "trend_significant", False
        ):  # Example threshold
            risks["details"].append(
                {
                    "risk_type": "Spending Trend",
                    "assessment": f"Shared spending shows a significant increasing trend of ${trend_info['slope_per_month']:.2f}/month. Monitor habits.",
                    "level": "MEDIUM",
                }
            )

        # Rent budget variance risk
        rent_budget_analysis = analytics.get("rent_budget_analysis", {})
        if "total_budget_variance" in rent_budget_analysis:
            if (
                abs(rent_budget_analysis.get("avg_monthly_variance", 0)) > 200
            ):  # Example: if avg variance is high
                risks["details"].append(
                    {
                        "risk_type": "Rent Budget Adherence",
                        "assessment": f"Average monthly rent variance is ${rent_budget_analysis['avg_monthly_variance']:,.2f}. "
                        f"Largest overrun: {rent_budget_analysis.get('largest_overrun',{}).get('amount',0):,.2f} "
                        f"in {rent_budget_analysis.get('largest_overrun',{}).get('month','N/A')}.",
                        "level": "MEDIUM",
                    }
                )

        # Ledger balance match risk
        if self.validation_results.get("ledger_balance_match") not in [
            "Matched",
            "Skipped - No Ledger Data",
            None,
        ]:
            risks["details"].append(
                {
                    "risk_type": "Ledger Balance Mismatch",
                    "assessment": f"Calculated running balance does not match transaction ledger's. Mismatch details: {self.validation_results['ledger_balance_match']}",
                    "level": "HIGH",
                }
            )

        high_risk_count = sum(1 for r in risks["details"] if r.get("level") == "HIGH")
        medium_risk_count = sum(
            1 for r in risks["details"] if r.get("level") == "MEDIUM"
        )

        if high_risk_count > 0:
            risks["overall_risk_level"] = "HIGH"
        elif medium_risk_count > 0:
            risks["overall_risk_level"] = "MEDIUM"

        if not risks["details"]:  # If no specific risks were added
            risks["details"].append(
                {
                    "risk_type": "General",
                    "assessment": "No major specific risks identified.",
                    "level": "LOW",
                }
            )

        logger.info(
            f"Risk assessment completed. Overall level: {risks['overall_risk_level']}"
        )
        return risks

    def _create_visualizations_v22(
        self,
        master_ledger: pd.DataFrame,
        analytics: Dict[str, Any],
        reconciliation: Dict[str, Any],
    ) -> Dict[str, str]:
        """Create all v2.2 visualizations. Based on original.
        Ensure master_ledger['Date'] is datetime.
        """
        logger.info("Creating v2.2 visualizations...")
        output_dir = Path("analysis_output")
        output_dir.mkdir(exist_ok=True)
        viz_paths: Dict[str, str] = {}

        theme = build_design_theme()  # Ensure theme is built

        if master_ledger.empty or master_ledger["Date"].isna().all():
            logger.warning(
                "Cannot create visualizations: Master ledger is empty or has no valid dates."
            )
            # Create a placeholder "no data" image/html if desired
            return viz_paths

        # Ensure Date column is datetime
        master_ledger["Date"] = pd.to_datetime(master_ledger["Date"], errors="coerce")
        # Drop rows where Date could not be parsed if critical for a plot type
        # plot_ledger = master_ledger.dropna(subset=['Date']) # Use this for plotting if NaTs are an issue

        # --- Visualization methods (copied from original, ensure they use master_ledger correctly) ---
        # 1. Running Balance Timeline
        try:
            path, alt = self._build_running_balance_timeline(
                master_ledger.copy(), output_dir
            )  # Pass copy
            viz_paths["running-balance-timeline"] = str(path)
            self.alt_texts["running-balance-timeline"] = alt
        except Exception as e:
            logger.error(f"Failed running balance timeline: {e}", exc_info=True)

        # 2. Waterfall Category Impact
        try:
            path, alt = self._build_waterfall_category_impact(
                master_ledger.copy(), output_dir, theme
            )
            viz_paths["waterfall-category-impact"] = str(path)
            self.alt_texts["waterfall-category-impact"] = alt
        except Exception as e:
            logger.error(f"Failed waterfall chart: {e}", exc_info=True)

        # 3. Monthly Shared Trend
        try:
            path, alt = self._build_monthly_shared_trend(
                master_ledger.copy(), analytics, output_dir
            )
            viz_paths["monthly-shared-trend"] = str(path)
            self.alt_texts["monthly-shared-trend"] = alt
        except Exception as e:
            logger.error(f"Failed monthly trend: {e}", exc_info=True)

        # 4. Liquidity Heatmap (Payer vs Transaction Type)
        try:
            path, alt = self._build_payer_type_heatmap(
                master_ledger.copy(), output_dir, theme
            )  # Renamed for clarity
            viz_paths["payer-type-heatmap"] = str(path)
            self.alt_texts["payer-type-heatmap"] = alt
        except Exception as e:
            logger.error(f"Failed payer-type heatmap: {e}", exc_info=True)

        # 5. Calendar Heatmaps
        try:
            calendar_paths = self._build_calendar_heatmaps(
                master_ledger.copy(), output_dir
            )
            for month_key, (path, alt) in calendar_paths.items():
                viz_paths[f"calendar-heatmap-{month_key}"] = str(path)
                self.alt_texts[f"calendar-heatmap-{month_key}"] = alt
        except Exception as e:
            logger.error(f"Failed calendar heatmaps: {e}", exc_info=True)

        # 6. Treemap Shared Spending
        try:
            path, alt = self._build_treemap_shared_spending(
                master_ledger.copy(), output_dir, theme
            )  # Removed analytics dep
            viz_paths["treemap-shared-spending"] = str(path)
            self.alt_texts["treemap-shared-spending"] = alt
        except Exception as e:
            logger.error(f"Failed treemap: {e}", exc_info=True)

        # 7. Anomaly Scatter
        try:
            path, alt = self._build_anomaly_scatter(master_ledger.copy(), output_dir)
            viz_paths["anomaly-scatter"] = str(path)
            self.alt_texts["anomaly-scatter"] = alt
        except Exception as e:
            logger.error(f"Failed anomaly scatter: {e}", exc_info=True)

        # 8. Pareto Concentration
        try:
            path, alt = self._build_pareto_concentration(
                master_ledger.copy(), output_dir
            )  # Removed analytics dep
            viz_paths["pareto-concentration"] = str(path)
            self.alt_texts["pareto-concentration"] = alt
        except Exception as e:
            logger.error(f"Failed pareto chart: {e}", exc_info=True)

        # 9. Sankey Settlements
        try:
            path, alt = self._build_sankey_settlements(
                master_ledger.copy(), output_dir, theme
            )
            viz_paths["sankey-settlements"] = str(path)
            self.alt_texts["sankey-settlements"] = alt
        except Exception as e:
            logger.error(f"Failed sankey diagram: {e}", exc_info=True)

        # 10. Data Quality Table
        try:
            path, alt = self._build_data_quality_table_viz(
                master_ledger.copy(), output_dir, theme
            )  # Renamed for clarity
            viz_paths["data-quality-table-viz"] = str(path)
            self.alt_texts["data-quality-table-viz"] = alt
        except Exception as e:
            logger.error(f"Failed data quality table viz: {e}", exc_info=True)

        logger.info(f"Created {len(viz_paths)} visualizations for v2.3.")
        return viz_paths

    # --- Visualization Builder Methods (from original, ensure they use master_ledger.copy() or are robust to NaT in Date) ---
    def _build_running_balance_timeline(
        self, ledger_df: pd.DataFrame, output_dir: Path
    ) -> Tuple[Path, str]:
        ledger_df = ledger_df.dropna(subset=["Date", "RunningBalance"])
        if ledger_df.empty:
            return output_dir / "no_data.png", "No data for running balance timeline."

        fig, ax = plt.subplots(figsize=(12, 6))
        ledger_df.plot(
            x="Date",
            y="RunningBalance",
            ax=ax,
            legend=None,
            color=TABLEAU_COLORBLIND_10[0],
        )

        # Liquidity bands (ensure RunningBalance doesn't have NaNs that break max/min)
        min_bal, max_bal = (
            ledger_df["RunningBalance"].min(),
            ledger_df["RunningBalance"].max(),
        )
        if pd.notna(min_bal) and pd.notna(max_bal):
            ax.axhspan(
                -self.config.LIQUIDITY_STRAIN_THRESHOLD,
                self.config.LIQUIDITY_STRAIN_THRESHOLD,
                alpha=0.05,
                color="green",
                label="Normal Range",
            )
            ax.axhspan(
                self.config.LIQUIDITY_STRAIN_THRESHOLD,
                max_bal + 1000,
                alpha=0.15,
                color="red",
                label="Ryan Liquidity Strain Potential",
            )  # Jordyn owes Ryan more
            ax.axhspan(
                min_bal - 1000,
                -self.config.LIQUIDITY_STRAIN_THRESHOLD,
                alpha=0.15,
                color="orange",
                label="Jordyn Liquidity Strain Potential",
            )  # Ryan owes Jordyn more

        ax.axhline(0, color="grey", linestyle="--", linewidth=0.8, alpha=0.5)

        # Annotate largest impacts
        if "BalanceImpact" in ledger_df.columns:
            top5 = ledger_df.iloc[
                ledger_df["BalanceImpact"].abs().nlargest(5).index
            ]  # Use .iloc with index
            for _, row in top5.iterrows():
                if pd.notna(row["Date"]) and pd.notna(
                    row["RunningBalance"]
                ):  # Check for NaT/NaN
                    desc_short = (
                        str(row.get("Description", ""))[:20] + "..."
                        if len(str(row.get("Description", ""))) > 20
                        else str(row.get("Description", ""))
                    )
                    ax.annotate(
                        f"{desc_short}\n${row['BalanceImpact']:,.0f}",
                        xy=(row["Date"], row["RunningBalance"]),
                        xytext=(0, 20 if row["BalanceImpact"] > 0 else -30),
                        textcoords="offset points",
                        ha="center",
                        fontsize=8,
                        arrowprops=dict(
                            arrowstyle="->", lw=0.5, color="black", alpha=0.5
                        ),
                    )

        ax.set_title(
            "Running Balance Over Time (Ryan owes Jordyn when > 0)",
            fontsize=14,
            fontweight="bold",
        )
        ax.set_ylabel("Balance ($)")
        ax.set_xlabel("Date")
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"${x:,.0f}"))
        ax.legend(loc="best", framealpha=0.9)  # Changed to 'best'
        plt.tight_layout()
        path = output_dir / "running_balance_timeline.png"
        plt.savefig(path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        alt_text = f"Running balance timeline. Liquidity strain zones at ±${self.config.LIQUIDITY_STRAIN_THRESHOLD:,.0f}."
        return path, alt_text

    def _build_waterfall_category_impact(
        self, ledger_df: pd.DataFrame, output_dir: Path, theme
    ) -> Tuple[Path, str]:
        if ledger_df.empty or "BalanceImpact" not in ledger_df.columns:
            return output_dir / "no_data.html", "No data for waterfall chart."

        ledger_df["MerchantCategory"] = ledger_df.apply(
            lambda row: str(row.get("TransactionType", "Other"))
            if str(row.get("TransactionType", "Other")) == "RENT"
            else self._categorize_merchant(row.get("Merchant", "Other")),
            axis=1,
        )
        category_impacts = (
            ledger_df.groupby("MerchantCategory")["BalanceImpact"]
            .sum()
            .sort_values(ascending=False)
        )
        if category_impacts.empty:
            return output_dir / "no_data.html", "No category impacts for waterfall."

        x_labels = list(category_impacts.index)
        y_values = list(category_impacts.values)

        # Add total if there are items
        if x_labels:
            x_labels.append("Final Balance")  # Changed from 'Total' to 'Final Balance'
            # The waterfall total should be the sum of all impacts, which is the final balance.
            # Or, if we are showing contributions to the final balance, the sum is the final balance.
            # For balance impact, the sum of all BalanceImpacts IS the final RunningBalance.
            y_values.append(ledger_df["BalanceImpact"].sum())

        fig = go.Figure(
            go.Waterfall(
                name="Balance Impact",
                orientation="v",
                measure=["relative"] * (len(x_labels) - 1) + ["total"]
                if x_labels
                else [],  # last one is total
                x=x_labels,
                textposition="outside",
                text=[f"${val:,.0f}" for val in y_values],
                y=y_values,
                connector={"line": {"color": "rgb(63, 63, 63)"}},
                increasing={
                    "marker": {"color": TABLEAU_COLORBLIND_10[1]}
                },  # Green for positive impact (Ryan gets money/owes less)
                decreasing={
                    "marker": {"color": TABLEAU_COLORBLIND_10[0]}
                },  # Red for negative impact (Ryan pays/owes more)
                totals={"marker": {"color": "#2E2E2E"}},
            )
        )
        fig.update_layout(
            title="Cumulative Balance Impact by Category",
            yaxis_title="Balance Impact ($)",
            template=theme,
            height=600,
            showlegend=False,
        )
        path = output_dir / "waterfall_category_impact.html"
        fig.write_html(str(path))
        alt_text = f"Waterfall chart of balance impact by category. Final balance ${ledger_df['BalanceImpact'].sum():,.0f}."
        return path, alt_text

    def _build_monthly_shared_trend(
        self, ledger_df: pd.DataFrame, analytics: Dict[str, Any], output_dir: Path
    ) -> Tuple[Path, str]:
        # This plot uses pre-calculated analytics trend data
        trend_data = analytics.get("monthly_shared_spending_trend", {})
        monthly_values_dict = trend_data.get("monthly_values", {})
        if not monthly_values_dict:
            return output_dir / "no_data.png", "No monthly trend data available."

        monthly_shared_series = pd.Series(monthly_values_dict).sort_index()
        if len(monthly_shared_series) < 3:
            return (
                output_dir / "no_data.png",
                "Insufficient data for trend plot (need at least 3 months).",
            )

        fig, ax = plt.subplots(figsize=(12, 7))
        x_labels = [
            d for d in monthly_shared_series.index
        ]  # Dates are already YYYY-MM strings
        x_pos = np.arange(len(x_labels))
        ax.bar(
            x_pos,
            monthly_shared_series.values,
            color=TABLEAU_COLORBLIND_10[2],
            alpha=0.8,
        )
        for i, val in enumerate(monthly_shared_series.values):
            ax.text(
                x_pos[i], val + 50, f"${val:,.0f}", ha="center", va="bottom", fontsize=9
            )

        slope = trend_data.get("slope_per_month", 0)
        p_value = trend_data.get("p_value", 1.0)
        # Recalculate regression line for plotting based on the series
        if len(x_pos) >= 2:  # Need at least 2 points for linregress for plotting
            current_slope, intercept, _, _, _ = stats.linregress(
                x_pos, monthly_shared_series.values
            )
            regression_line = current_slope * x_pos + intercept
            ax.plot(
                x_pos,
                regression_line,
                color=TABLEAU_COLORBLIND_10[0],
                linewidth=2,
                label=f"Trend: ${slope:+.0f}/month (p={p_value:.3f})",
            )

        ax.set_xticks(x_pos)
        ax.set_xticklabels(x_labels, rotation=45, ha="right")
        ax.set_xlabel("Month")
        ax.set_ylabel("Total Shared Spending ($)")
        ax.set_title(
            f'Monthly Shared Spending Trend (${slope:+.0f}/month, {"sig." if p_value < 0.05 else "not sig."})',
            fontsize=14,
            fontweight="bold",
        )
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"${x:,.0f}"))
        ax.legend()
        plt.tight_layout()
        path = output_dir / "monthly_shared_trend.png"
        plt.savefig(path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        alt_text = f"Monthly shared spending trend: ${slope:+.0f}/month change."
        return path, alt_text

    def _build_payer_type_heatmap(
        self, ledger_df: pd.DataFrame, output_dir: Path, theme
    ) -> Tuple[Path, str]:
        # Renamed from _build_liquidity_heatmap as it shows spending by payer/type, not liquidity directly
        if (
            ledger_df.empty
            or "AllowedAmount" not in ledger_df.columns
            or "Payer" not in ledger_df.columns
            or "TransactionType" not in ledger_df.columns
        ):
            return output_dir / "no_data.html", "No data for payer-type heatmap."

        shared_df = ledger_df[ledger_df["IsShared"] == True]
        if shared_df.empty:
            return (
                output_dir / "no_data.html",
                "No shared transactions for payer-type heatmap.",
            )

        pivot_data = shared_df.pivot_table(
            values="AllowedAmount",
            index="Payer",
            columns="TransactionType",
            aggfunc="sum",
            fill_value=0,
        )
        if pivot_data.empty:
            return output_dir / "no_data.html", "Pivot data empty for heatmap."

        fig = go.Figure(
            data=go.Heatmap(
                z=pivot_data.values,
                x=pivot_data.columns,
                y=pivot_data.index,
                colorscale="Blues",
                text=[[f"${val:,.0f}" for val in row] for row in pivot_data.values],
                texttemplate="%{text}",
                textfont={"size": 12},
                hovertemplate="Payer: %{y}<br>Type: %{x}<br>Shared Amount: $%{z:,.0f}<extra></extra>",
            )
        )
        fig.update_layout(
            title="Shared Spending by Payer and Transaction Type",
            template=theme,
            height=400,
        )
        path = output_dir / "payer_type_heatmap.html"
        fig.write_html(str(path))
        alt_text = f"Heatmap of shared spending by payer and transaction type. Total ${pivot_data.values.sum():,.0f}."
        return path, alt_text

    def _build_calendar_heatmaps(
        self, ledger_df: pd.DataFrame, output_dir: Path
    ) -> Dict[str, Tuple[Path, str]]:
        calendar_paths = {}
        if (
            ledger_df.empty
            or "Date" not in ledger_df.columns
            or "AllowedAmount" not in ledger_df.columns
        ):
            return calendar_paths

        shared_only = ledger_df[
            (ledger_df["IsShared"] == True) & ledger_df["Date"].notna()
        ].copy()
        if shared_only.empty:
            return calendar_paths

        shared_only["YearMonth"] = shared_only["Date"].dt.to_period("M")

        for year_month_period in shared_only["YearMonth"].unique():
            year_month_str = str(year_month_period)  # For filename/key
            month_data = shared_only[
                shared_only["YearMonth"] == year_month_period
            ].copy()
            if month_data.empty:
                continue

            daily_spending = month_data.groupby(month_data["Date"].dt.date)[
                "AllowedAmount"
            ].sum()
            if daily_spending.empty:
                continue

            # Create full calendar grid for the specific month
            start_date = year_month_period.start_time
            end_date = year_month_period.end_time

            # Create a matrix for the month
            # Rows are weeks (0-5), columns are days of week (0-6, Mon-Sun)
            # Correctly map day of month to its position in the grid
            # This is a complex calendar plotting logic. Using a library like `calmap` might be better.
            # Simplified approach for illustration (may not be perfect calendar layout)

            all_days_in_month = pd.Series(
                index=pd.date_range(start=start_date, end=end_date, freq="D"),
                dtype=float,
            ).fillna(0)
            daily_spending.index = pd.to_datetime(
                daily_spending.index
            )  # Ensure datetime index
            # Merge spending into all_days_in_month
            all_days_in_month = all_days_in_month.add(daily_spending, fill_value=0)

            # Prepare data for heatmap (example using seaborn for simplicity, calmap is better)
            # This part needs a proper calendar layout generation.
            # For now, let's just plot a simple daily bar for the month as placeholder for robust calendar.
            fig, ax = plt.subplots(figsize=(12, 6))
            all_days_in_month.plot(kind="bar", ax=ax, color=TABLEAU_COLORBLIND_10[4])
            ax.set_title(
                f"Daily Shared Spending - {year_month_str}",
                fontsize=14,
                fontweight="bold",
            )
            ax.set_ylabel("Shared Spending ($)")
            ax.set_xlabel("Day of Month")
            ax.xaxis.set_major_formatter(
                plt.FixedFormatter(all_days_in_month.index.strftime("%d"))
            )  # Show day number
            plt.tight_layout()

            path = output_dir / f"calendar_heatmap_{year_month_str}.png"
            plt.savefig(path, dpi=300, bbox_inches="tight")
            plt.close(fig)
            alt_text = f"Daily shared spending for {year_month_str}. Total ${all_days_in_month.sum():,.0f}."
            calendar_paths[year_month_str] = (path, alt_text)
        return calendar_paths

    def _build_treemap_shared_spending(
        self, ledger_df: pd.DataFrame, output_dir: Path, theme
    ) -> Tuple[Path, str]:
        if ledger_df.empty or "AllowedAmount" not in ledger_df.columns:
            return output_dir / "no_data.html", "No data for treemap."

        shared_df = ledger_df[ledger_df["IsShared"] == True].copy()
        if shared_df.empty:
            return output_dir / "no_data.html", "No shared transactions for treemap."

        category_data = []
        # Rent
        rent_total = shared_df[shared_df["TransactionType"] == "RENT"][
            "AllowedAmount"
        ].sum()
        if rent_total > 0:
            category_data.append(
                {"Category": "RENT", "Amount": rent_total, "Parent": ""}
            )

        # Expenses by category
        expense_df = shared_df[shared_df["TransactionType"] == "EXPENSE"].copy()
        if not expense_df.empty and "Merchant" in expense_df.columns:
            expense_df["Category"] = expense_df["Merchant"].apply(
                self._categorize_merchant
            )
            category_totals = expense_df.groupby("Category")["AllowedAmount"].sum()

            for cat, amount in category_totals.items():
                if amount > 0:
                    category_data.append(
                        {"Category": cat, "Amount": amount, "Parent": "EXPENSES"}
                    )

            total_expenses = category_totals.sum()
            if total_expenses > 0:  # Add parent node for expenses if any exist
                category_data.append(
                    {"Category": "EXPENSES", "Amount": total_expenses, "Parent": ""}
                )

        if not category_data:
            return output_dir / "no_data.html", "No categories for treemap."

        labels = [item["Category"] for item in category_data]
        parents = [item["Parent"] for item in category_data]
        values = [item["Amount"] for item in category_data]

        total_overall_amount = sum(
            d["Amount"] for d in category_data if d["Parent"] == ""
        )
        text = [
            f"${item['Amount']:,.0f}<br>{(item['Amount']/total_overall_amount*100 if total_overall_amount else 0):.1f}%"
            for item in category_data
        ]

        fig = go.Figure(
            go.Treemap(
                labels=labels,
                parents=parents,
                values=values,
                text=text,
                textinfo="label+text",
                marker_colorscale="Blues",
                line=dict(width=1),  # Simplified marker
            )
        )
        fig.update_layout(
            title="Distribution of Shared Spending",
            template=theme,
            height=600,
            margin=dict(t=50, l=0, r=0, b=0),
        )
        path = output_dir / "treemap_shared_spending.html"
        fig.write_html(str(path))
        alt_text = f"Treemap of shared spending. Total ${total_overall_amount:,.0f}."
        return path, alt_text

    def _build_anomaly_scatter(
        self, ledger_df: pd.DataFrame, output_dir: Path
    ) -> Tuple[Path, str]:
        if (
            ledger_df.empty
            or "AllowedAmount" not in ledger_df.columns
            or "BalanceImpact" not in ledger_df.columns
        ):
            return output_dir / "no_data.png", "No data for anomaly scatter plot."

        plot_df = ledger_df.dropna(
            subset=["AllowedAmount", "BalanceImpact", "DataQualityFlag"]
        )
        if plot_df.empty:
            return (
                output_dir / "no_data.png",
                "No valid data points for anomaly scatter plot.",
            )

        fig, ax = plt.subplots(figsize=(12, 8))
        unique_flags = plot_df["DataQualityFlag"].unique()
        flag_colors = {
            flag: TABLEAU_COLORBLIND_10[i % len(TABLEAU_COLORBLIND_10)]
            for i, flag in enumerate(unique_flags)
        }

        for flag_val in unique_flags:
            subset = plot_df[plot_df["DataQualityFlag"] == flag_val]
            ax.scatter(
                subset["AllowedAmount"],
                subset["BalanceImpact"],
                label=flag_val,
                alpha=0.6,
                s=50,
                color=flag_colors[flag_val],
            )

        # Label top outliers by abs balance impact
        if not plot_df.empty and "BalanceImpact" in plot_df.columns:
            threshold_pct = 99
            # Ensure there are enough points for percentile calculation
            if len(plot_df["BalanceImpact"].abs().dropna()) > 0:
                threshold_value = np.percentile(
                    plot_df["BalanceImpact"].abs().dropna(), threshold_pct
                )
                outliers = plot_df[plot_df["BalanceImpact"].abs() > threshold_value]
                for _, row in outliers.iterrows():
                    desc_short = (
                        str(row.get("Description", ""))[:15] + "..."
                        if len(str(row.get("Description", ""))) > 15
                        else str(row.get("Description", ""))
                    )
                    ax.annotate(
                        desc_short,
                        xy=(row["AllowedAmount"], row["BalanceImpact"]),
                        xytext=(5, 5),
                        textcoords="offset points",
                        fontsize=8,
                        alpha=0.7,
                    )

        ax.axhline(0, color="grey", linestyle="--", alpha=0.5)
        ax.axvline(0, color="grey", linestyle="--", alpha=0.5)
        ax.set_xlabel("Allowed Amount ($)")
        ax.set_ylabel("Balance Impact ($)")
        ax.set_title(
            "Transaction Anomaly Detection (colored by data quality flag)",
            fontsize=14,
            fontweight="bold",
        )
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"${x:,.0f}"))
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"${x:,.0f}"))
        ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left", framealpha=0.9)
        plt.tight_layout()
        path = output_dir / "anomaly_scatter.png"
        plt.savefig(path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        alt_text = f"Anomaly scatter plot of transactions."
        return path, alt_text

    def _build_pareto_concentration(
        self, ledger_df: pd.DataFrame, output_dir: Path
    ) -> Tuple[Path, str]:
        if ledger_df.empty or "AllowedAmount" not in ledger_df.columns:
            return output_dir / "no_data.png", "No data for Pareto chart."

        shared_only = ledger_df[ledger_df["IsShared"] == True].copy()
        if shared_only.empty:
            return (
                output_dir / "no_data.png",
                "No shared transactions for Pareto chart.",
            )

        shared_only["Category"] = shared_only.apply(
            lambda row: str(row.get("TransactionType", "Other"))
            if str(row.get("TransactionType", "Other")) == "RENT"
            else self._categorize_merchant(row.get("Merchant", "Other")),
            axis=1,
        )
        category_totals = (
            shared_only.groupby("Category")["AllowedAmount"]
            .sum()
            .sort_values(ascending=False)
        )
        if category_totals.empty or category_totals.sum() == 0:
            return output_dir / "no_data.png", "No category totals for Pareto."

        fig, ax1 = plt.subplots(figsize=(12, 7))
        x_pos = np.arange(len(category_totals))
        ax1.bar(
            x_pos, category_totals.values, color=TABLEAU_COLORBLIND_10[3], alpha=0.8
        )
        for i, val in enumerate(category_totals.values):
            ax1.text(
                x_pos[i],
                val + (category_totals.values.max() * 0.02),
                f"${val:,.0f}",
                ha="center",
                va="bottom",
                fontsize=9,
                rotation=30,
            )  # Adjust offset

        ax1.set_xlabel("Category")
        ax1.set_ylabel("Total Shared Amount ($)", color=TABLEAU_COLORBLIND_10[3])
        ax1.tick_params(axis="y", labelcolor=TABLEAU_COLORBLIND_10[3])
        ax1.set_xticks(x_pos)
        ax1.set_xticklabels(category_totals.index, rotation=45, ha="right")
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"${x:,.0f}"))

        ax2 = ax1.twinx()
        cumulative_pct = category_totals.cumsum() / category_totals.sum() * 100
        ax2.plot(
            x_pos,
            cumulative_pct.values,
            color=TABLEAU_COLORBLIND_10[1],
            marker="o",
            lw=2,
            ms=6,
            label="Cumulative %",
        )
        ax2.axhline(80, color="red", linestyle="--", alpha=0.7, label="80% Threshold")

        idx_80 = np.where(cumulative_pct.values >= 80)[0]
        if len(idx_80) > 0:
            x_80, y_80 = idx_80[0], cumulative_pct.values[idx_80[0]]
            ax2.plot(x_80, y_80, "ro", markersize=10)  # Red dot at 80% crossover
            ax2.annotate(
                f"{x_80 + 1} cat.\nreach 80%",
                xy=(x_80, y_80),
                xytext=(x_80 + 0.5, y_80 - 10),
                arrowprops=dict(arrowstyle="->", color="red", lw=1),
            )

        ax2.set_ylabel("Cumulative Percentage (%)", color=TABLEAU_COLORBLIND_10[1])
        ax2.tick_params(axis="y", labelcolor=TABLEAU_COLORBLIND_10[1])
        ax2.set_ylim(0, 105)
        ax1.set_title(
            "Pareto Analysis of Shared Spending by Category",
            fontsize=14,
            fontweight="bold",
        )
        ax2.legend(loc="center right")
        plt.tight_layout()
        path = output_dir / "pareto_concentration.png"
        plt.savefig(path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        alt_text = f"Pareto chart of shared spending concentration."
        return path, alt_text

    def _build_sankey_settlements(
        self, ledger_df: pd.DataFrame, output_dir: Path, theme
    ) -> Tuple[Path, str]:
        if ledger_df.empty:
            return output_dir / "no_data.html", "No data for Sankey diagram."

        shared_expenses = ledger_df[ledger_df["IsShared"] == True].copy()
        settlements = ledger_df[ledger_df["TransactionType"] == "SETTLEMENT"].copy()

        # Amounts paid by each for shared items
        ryan_paid_shared = shared_expenses[
            shared_expenses["Payer"].str.lower() == "ryan"
        ]["AllowedAmount"].sum()
        jordyn_paid_shared = shared_expenses[
            shared_expenses["Payer"].str.lower() == "jordyn"
        ]["AllowedAmount"].sum()
        total_shared = ryan_paid_shared + jordyn_paid_shared

        # Ryan's fair share of total shared expenses
        ryan_fair_share = total_shared * self.config.RYAN_PCT
        jordyn_fair_share = total_shared * self.config.JORDYN_PCT

        # Settlement flows (actual payments made as settlements)
        # If Ryan Payer, ActualAmount is positive, Description "to Jordyn" -> Ryan paid Jordyn
        ryan_paid_jordyn_settle = settlements[
            (settlements["Payer"].str.lower() == "ryan")
            & (
                settlements["Description"].str.contains(
                    r"to\s+jordyn", case=False, regex=True, na=False
                )
            )
        ]["ActualAmount"].sum()

        jordyn_paid_ryan_settle = settlements[
            (settlements["Payer"].str.lower() == "jordyn")
            & (
                settlements["Description"].str.contains(
                    r"to\s+ryan", case=False, regex=True, na=False
                )
            )
        ]["ActualAmount"].sum()

        # Nodes: Ryan, Jordyn, Shared Pool, Ryan's Share Pot, Jordyn's Share Pot
        labels = [
            "Ryan Pays",
            "Jordyn Pays",
            "Shared Expense Pool",
            "Ryan's Fair Share",
            "Jordyn's Fair Share",
            "Ryan Final Position",
            "Jordyn Final Position",
        ]

        source_indices, target_indices, values, link_labels = [], [], [], []

        # Flows into Shared Expense Pool
        if ryan_paid_shared > 0:
            source_indices.append(0)
            target_indices.append(2)
            values.append(ryan_paid_shared)
            link_labels.append(f"${ryan_paid_shared:,.0f}")
        if jordyn_paid_shared > 0:
            source_indices.append(1)
            target_indices.append(2)
            values.append(jordyn_paid_shared)
            link_labels.append(f"${jordyn_paid_shared:,.0f}")

        # Flows from Shared Pool to Fair Shares
        if ryan_fair_share > 0:  # From Shared Pool to Ryan's Fair Share
            source_indices.append(2)
            target_indices.append(3)
            values.append(ryan_fair_share)
            link_labels.append(f"Ryan's Share ${ryan_fair_share:,.0f}")
        if jordyn_fair_share > 0:  # From Shared Pool to Jordyn's Fair Share
            source_indices.append(2)
            target_indices.append(4)
            values.append(jordyn_fair_share)
            link_labels.append(f"Jordyn's Share ${jordyn_fair_share:,.0f}")

        # This Sankey representation is complex. Simpler: Who paid what for shared, then who settled whom.
        # Simplified:
        # Nodes: Ryan, Jordyn, Shared Expenses
        # Links: Ryan -> Shared, Jordyn -> Shared
        # Links: Ryan -> Jordyn (Settle), Jordyn -> Ryan (Settle)

        simple_labels = ["Ryan", "Jordyn", "Shared Expenses Bucket"]
        simple_source, simple_target, simple_values, simple_link_labels = [], [], [], []
        node_colors = [
            TABLEAU_COLORBLIND_10[0],
            TABLEAU_COLORBLIND_10[1],
            TABLEAU_COLORBLIND_10[2],
        ]
        link_colors_list = []

        # Payments to shared expenses
        if ryan_paid_shared > 0:
            simple_source.append(0)
            simple_target.append(2)
            simple_values.append(ryan_paid_shared)
            simple_link_labels.append(f"Ryan paid to Shared: ${ryan_paid_shared:,.0f}")
            link_colors_list.append("rgba(0,122,204,0.4)")  # Ryan's color
        if jordyn_paid_shared > 0:
            simple_source.append(1)
            simple_target.append(2)
            simple_values.append(jordyn_paid_shared)
            simple_link_labels.append(
                f"Jordyn paid to Shared: ${jordyn_paid_shared:,.0f}"
            )
            link_colors_list.append("rgba(255,176,0,0.4)")  # Jordyn's color

        # Settlement payments
        if ryan_paid_jordyn_settle > 0:  # Ryan (0) paid Jordyn (1)
            simple_source.append(0)
            simple_target.append(1)
            simple_values.append(ryan_paid_jordyn_settle)
            simple_link_labels.append(
                f"Ryan settled Jordyn: ${ryan_paid_jordyn_settle:,.0f}"
            )
            link_colors_list.append("rgba(0,122,204,0.6)")  # Darker Ryan color
        if jordyn_paid_ryan_settle > 0:  # Jordyn (1) paid Ryan (0)
            simple_source.append(1)
            simple_target.append(0)
            simple_values.append(jordyn_paid_ryan_settle)
            simple_link_labels.append(
                f"Jordyn settled Ryan: ${jordyn_paid_ryan_settle:,.0f}"
            )
            link_colors_list.append("rgba(255,176,0,0.6)")  # Darker Jordyn color

        if not simple_values:  # No flows to plot
            return output_dir / "no_data.html", "No flow data for Sankey diagram."

        fig = go.Figure(
            data=[
                go.Sankey(
                    node=dict(
                        pad=15,
                        thickness=20,
                        line=dict(color="black", width=0.5),
                        label=simple_labels,
                        color=node_colors,
                    ),
                    link=dict(
                        source=simple_source,
                        target=simple_target,
                        value=simple_values,
                        label=simple_link_labels,
                        color=link_colors_list,
                    ),
                )
            ]
        )
        fig.update_layout(
            title_text="Flow of Shared Expenses and Settlements",
            font_size=12,
            template=theme,
            height=500,
        )
        path = output_dir / "sankey_settlements.html"
        fig.write_html(str(path))
        alt_text = f"Sankey diagram of expense and settlement flows. Total shared paid: ${total_shared:,.0f}."
        return path, alt_text

    def _build_data_quality_table_viz(
        self, ledger_df: pd.DataFrame, output_dir: Path, theme
    ) -> Tuple[Path, str]:
        # Renamed from _build_data_quality_table for clarity (it's a visualization)
        if ledger_df.empty or "DataQualityFlag" not in ledger_df.columns:
            return output_dir / "no_data.html", "No data for data quality table."

        # Filter for rows with issues OR high impact transactions
        flagged_rows = ledger_df[
            ledger_df["DataQualityFlag"] != DataQualityFlag.CLEAN.value
        ].copy()

        high_impact_rows = pd.DataFrame()
        if "BalanceImpact" in ledger_df.columns and not ledger_df.empty:
            # Ensure BalanceImpact is numeric and no NaNs before percentile
            valid_impacts = ledger_df["BalanceImpact"].dropna()
            if (
                not valid_impacts.empty and len(valid_impacts) > 10
            ):  # Need enough data for percentile
                threshold_98 = np.percentile(valid_impacts.abs(), 98)
                high_impact_rows = ledger_df[
                    ledger_df["BalanceImpact"].abs() > threshold_98
                ].copy()

        combined = pd.concat([flagged_rows, high_impact_rows]).drop_duplicates()
        if combined.empty:
            return (
                output_dir / "no_data.html",
                "No data quality issues or high impact transactions found for table.",
            )

        display_cols = [
            "Date",
            "TransactionType",
            "Payer",
            "Description",
            "ActualAmount",
            "AllowedAmount",
            "BalanceImpact",
            "DataQualityFlag",
        ]
        # Ensure all display_cols exist in combined
        final_display_cols = [col for col in display_cols if col in combined.columns]
        display_df = combined[final_display_cols].copy()

        if "Date" in display_df.columns:
            display_df["Date"] = pd.to_datetime(display_df["Date"]).dt.strftime(
                "%Y-%m-%d"
            )

        for col in ["ActualAmount", "AllowedAmount", "BalanceImpact"]:
            if col in display_df.columns:
                display_df[col] = display_df[col].apply(
                    lambda x: f"${x:,.2f}" if pd.notna(x) else "$0.00"
                )

        fig = go.Figure(
            data=[
                go.Table(
                    header=dict(
                        values=list(display_df.columns),
                        fill_color="#007ACC",
                        font=dict(color="white", size=12),
                        align="left",
                    ),
                    cells=dict(
                        values=[display_df[col] for col in display_df.columns],
                        fill_color=[
                            [
                                "#f0f0f0" if i % 2 == 0 else "white"
                                for i in range(len(display_df))
                            ]
                        ],
                        align="left",
                        font_size=11,
                    ),
                )
            ]
        )
        fig.update_layout(
            title=f"Data Quality Issues & High-Impact Transactions ({len(display_df)} rows)",
            template=theme,
            height=600,
        )
        path = output_dir / "data_quality_table_viz.html"
        fig.write_html(str(path))
        alt_text = f"Table of {len(display_df)} transactions with data quality issues or high balance impact."
        return path, alt_text

    def _generate_recommendations(
        self,
        analytics: Dict[str, Any],
        risk_assessment: Dict[str, Any],
        reconciliation: Dict[str, Any],
    ) -> List[str]:
        """Generate recommendations. Based on original, enhanced for v2.3."""
        logger.info("Generating recommendations...")
        recommendations = []

        if reconciliation.get("amount_owed", 0) > 50:  # Threshold for settlement
            recommendations.append(
                f"Outstanding Balance: {reconciliation['who_owes_whom']} ${reconciliation['amount_owed']:,.2f}. Consider settling soon."
            )
        if not reconciliation.get("reconciled", True):
            recommendations.append(
                "CRITICAL RECONCILIATION ISSUE: Triple reconciliation methods show discrepancies. Review calculations and data immediately."
            )

        if self.validation_results.get("ledger_balance_match") not in [
            "Matched",
            "Skipped - No Ledger Data",
            None,
        ]:
            recommendations.append(
                f"CRITICAL LEDGER MISMATCH: Calculated balance differs from Transaction Ledger. Details: {self.validation_results['ledger_balance_match']}. Investigate data entry."
            )

        overall_risk = risk_assessment.get("overall_risk_level", "LOW")
        if overall_risk == "HIGH":
            recommendations.append(
                "High overall risk identified. Prioritize addressing detailed risk factors (see risk report/log for specifics)."
            )
        elif overall_risk == "MEDIUM":
            recommendations.append(
                "Medium overall risk identified. Review detailed risk factors and plan mitigation actions."
            )

        for risk_detail in risk_assessment.get("details", []):
            if risk_detail.get("level") in ["HIGH", "MEDIUM"]:
                recommendations.append(
                    f"Risk Alert ({risk_detail.get('risk_type', 'Risk')} - {risk_detail.get('level')}): {risk_detail.get('assessment', '')}"
                )

        trend_info = analytics.get("monthly_shared_spending_trend", {})
        if trend_info.get("slope_per_month", 0) > 100 and trend_info.get(
            "trend_significant", False
        ):  # Example
            recommendations.append(
                f"Spending Trend: Shared spending shows a significant increasing trend of ~${trend_info['slope_per_month']:.0f}/month. Review spending patterns."
            )

        rent_budget_analysis = analytics.get("rent_budget_analysis", {})
        if (
            "avg_monthly_variance" in rent_budget_analysis
            and abs(rent_budget_analysis.get("avg_monthly_variance", 0)) > 50
        ):  # Example
            recommendations.append(
                f"Rent Budget: Rent shows an average monthly variance of ${rent_budget_analysis['avg_monthly_variance']:,.2f} from budget. "
                f"Largest overrun was ${rent_budget_analysis.get('largest_overrun',{}).get('amount',0):,.2f}. Review rent charges."
            )

        if not recommendations:
            recommendations.append(
                "No specific high-priority recommendations at this time. Financials appear stable. Continue good practices."
            )

        logger.info(f"Generated {len(recommendations)} recommendations.")
        return recommendations

    def _calculate_data_quality_score(self, master_ledger: pd.DataFrame) -> float:
        """Calculate data quality score. Based on original."""
        if master_ledger.empty or "DataQualityFlag" not in master_ledger.columns:
            return 0.0
        clean_rows = (
            master_ledger["DataQualityFlag"] == DataQualityFlag.CLEAN.value
        ).sum()
        total_rows = len(master_ledger)
        score = (clean_rows / total_rows * 100) if total_rows > 0 else 0.0
        logger.info(
            f"Data Quality Score: {score:.2f}% ({clean_rows} clean rows out of {total_rows})"
        )
        return score

    def _summarize_data_quality_issues(
        self, master_ledger: pd.DataFrame
    ) -> Dict[str, int]:
        """Summarizes the count of each data quality flag type. Based on original."""
        if master_ledger.empty or "DataQualityFlag" not in master_ledger.columns:
            return {"No data quality flags to summarize.": 0}

        flag_counts: Dict[str, int] = {}
        # Iterate over each row's DataQualityFlag string
        for flags_str_per_row in master_ledger["DataQualityFlag"].dropna():
            if flags_str_per_row != DataQualityFlag.CLEAN.value:
                # Split comma-separated flags for that row
                individual_flags_in_row = flags_str_per_row.split(",")
                for flag in individual_flags_in_row:
                    if (
                        flag and flag != DataQualityFlag.CLEAN.value
                    ):  # Ensure flag is not empty string
                        flag_counts[flag] = flag_counts.get(flag, 0) + 1
        return flag_counts if flag_counts else {"All Clear": len(master_ledger)}

    def _validate_results_summary(
        self, reconciliation: Dict[str, Any], master_ledger: pd.DataFrame
    ) -> None:
        """Validate analysis results and populate self.validation_results. Renamed from _validate_results."""
        logger.info("Validating analysis results summary...")
        self.validation_results["reconciliation_match_strict"] = reconciliation.get(
            "reconciled", False
        )

        if (
            not master_ledger.empty
            and "BalanceImpact" in master_ledger.columns
            and "RunningBalance" in master_ledger.columns
        ):
            # Ensure columns are numeric and not all NaN before sum/iloc
            if (
                master_ledger["BalanceImpact"].notna().any()
                and master_ledger["RunningBalance"].notna().any()
            ):
                sum_balance_impacts = master_ledger["BalanceImpact"].sum()
                final_running_balance = master_ledger["RunningBalance"].iloc[-1]
                self.validation_results["balance_impact_sum_vs_running_balance"] = (
                    abs(sum_balance_impacts - final_running_balance) < 0.015
                )  # Small tolerance
            else:
                self.validation_results["balance_impact_sum_vs_running_balance"] = (
                    "Skipped - NaN in financial columns"
                )
        else:  # If ledger empty or columns missing
            self.validation_results["balance_impact_sum_vs_running_balance"] = (
                True  # Or "Skipped"
            )

        quality_score = self._calculate_data_quality_score(master_ledger)
        self.validation_results["data_quality_acceptable"] = (
            quality_score >= self.config.DATA_QUALITY_THRESHOLD * 100
        )

        # This check is now done in _validate_against_ledger_balance and result stored in self.validation_results
        # self.validation_results['ledger_balance_match'] is set there.

        if (
            "Who_Paid_Text" in master_ledger.columns
        ):  # Check if audit columns were created
            self.validation_results["audit_columns_exist"] = all(
                col in master_ledger.columns
                for col in [
                    "Who_Paid_Text",
                    "Share_Type",
                    "Shared_Reason",
                    "DataQuality_Audit",
                ]
            )
        else:
            self.validation_results["audit_columns_exist"] = False

        all_passed_numeric = sum(
            1 for v in self.validation_results.values() if isinstance(v, bool) and v
        )
        total_numeric_checks = sum(
            1 for v in self.validation_results.values() if isinstance(v, bool)
        )

        logger.info(
            f"Validation checks completed. {all_passed_numeric}/{total_numeric_checks} boolean checks passed."
        )
        for k, v in self.validation_results.items():
            logger.info(f"  Validation - {k}: {v}")

        if not all(
            v for v in self.validation_results.values() if isinstance(v, bool)
        ):  # If any boolean check is False
            failed_checks = [
                k
                for k, v in self.validation_results.items()
                if isinstance(v, bool) and not v
            ]
            logger.error(
                f"Some critical validations FAILED: {', '.join(failed_checks)}"
            )

    def _check_performance(self) -> None:
        """Check performance metrics. Based on original."""
        logger.info("Checking performance metrics...")
        elapsed_seconds = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        if elapsed_seconds > self.config.MAX_PROCESSING_TIME_SECONDS:
            logger.warning(
                f"Processing time ({elapsed_seconds:.1f}s) EXCEEDED limit ({self.config.MAX_PROCESSING_TIME_SECONDS}s)."
            )

        try:
            process = psutil.Process()
            self.memory_usage_mb = process.memory_info().rss / (1024 * 1024)
            if self.memory_usage_mb > self.config.MAX_MEMORY_MB:
                logger.warning(
                    f"Memory usage ({self.memory_usage_mb:.1f}MB) EXCEEDED limit ({self.config.MAX_MEMORY_MB}MB)."
                )
        except Exception as e:
            logger.error(f"Could not get memory usage: {e}")
            self.memory_usage_mb = -1  # Indicate error
        logger.info(
            f"Performance: Time={elapsed_seconds:.2f}s, Memory={self.memory_usage_mb:.2f}MB"
        )

    def _categorize_merchant(self, merchant: Optional[str]) -> str:
        """Categorize merchant. Based on original."""
        if pd.isna(merchant) or not isinstance(merchant, str) or not merchant.strip():
            return "Other/Unspecified"

        merchant_lower = merchant.lower()
        # More specific categories first
        categories = {
            "Groceries": [
                "fry",
                "safeway",
                "walmart",
                "target",
                "costco",
                "trader joe",
                "whole foods",
                "kroger",
                "albertsons",
                "grocery",
                "sprouts",
            ],
            "Utilities": [
                "electric",
                "gas",
                "water",
                "internet",
                "phone",
                "cox",
                "srp",
                "aps",
                "centurylink",
                "utility",
                "conservice",
                "google fi",
                "t-mobile",
                "verizon",
            ],
            "Dining Out": [
                "restaurant",
                "cafe",
                "coffee",
                "starbucks",
                "pizza",
                "sushi",
                "mcdonald",
                "chipotle",
                "subway",
                "doordash",
                "grubhub",
                "uber eats",
                "postmates",
                "culinary dropout",
                "bar",
            ],
            "Transport": [
                "uber",
                "lyft",
                "gas station",
                "shell",
                "chevron",
                "circle k",
                "qt",
                "auto repair",
                "fuel",
                "parking",
                "toll",
                "bird",
                "lime",
                "waymo",
            ],
            "Entertainment": [
                "movie",
                "theater",
                "netflix",
                "spotify",
                "hulu",
                "disney",
                "concert",
                "event",
                "game",
                "amc",
                "cinemark",
                "ticketmaster",
                "steam",
            ],
            "Healthcare": [
                "pharmacy",
                "cvs",
                "walgreens",
                "doctor",
                "medical",
                "dental",
                "clinic",
                "hospital",
                "optometrist",
                "vision",
            ],
            "Shopping": [
                "amazon",
                "best buy",
                "macys",
                "nordstrom",
                "online store",
                "retail",
                "clothing",
                "electronics",
                "home goods",
                "ikea",
            ],
            "Travel": [
                "airline",
                "hotel",
                "airbnb",
                "expedia",
                "booking.com",
                "southwest",
                "delta",
                "united",
            ],
            "Services": [
                "haircut",
                "gym",
                "consulting",
                "legal",
                "accounting",
                "cleaning",
            ],
            "Rent": [
                "rent",
                "property management",
                "landlord",
            ],  # Though rent is usually its own TransactionType
        }
        for category, keywords in categories.items():
            if any(keyword in merchant_lower for keyword in keywords):
                return category
        return "Other Expenses"

    def _generate_outputs(
        self,
        master_ledger: pd.DataFrame,
        reconciliation: Dict[str, Any],
        analytics: Dict[str, Any],
        risk_assessment: Dict[str, Any],
        recommendations: List[str],
        visualizations: Dict[str, str],
    ) -> Dict[str, str]:
        """Generate all output files v2.3. Based on original."""
        logger.info("Generating output files v2.3...")
        output_dir = Path("analysis_output")
        output_dir.mkdir(exist_ok=True)
        output_paths: Dict[str, str] = {}

        master_ledger_export = master_ledger.copy()
        # Ensure Date is string for CSV if preferred, or keep as datetime and let to_csv handle format
        if "Date" in master_ledger_export.columns:
            master_ledger_export["Date"] = pd.to_datetime(
                master_ledger_export["Date"]
            ).dt.strftime("%Y-%m-%d")

        # Alias columns for user-friendly export
        master_ledger_export["Category_Display"] = master_ledger_export[
            "TransactionType"
        ]  # Basic category
        master_ledger_export["Amount_Charged_Display"] = master_ledger_export[
            "ActualAmount"
        ]
        master_ledger_export["Shared_Amount_Display"] = master_ledger_export[
            "AllowedAmount"
        ]
        master_ledger_export["Cumulative_Balance_Display"] = master_ledger_export[
            "RunningBalance"
        ]

        # 1. Master Ledger CSV
        if not master_ledger_export.empty:
            ledger_path = output_dir / "master_ledger_v2.3.csv"

            # DEBUG: Inspect coffee transaction before writing to CSV
            logger.info(
                "DEBUG: Coffee transaction in master_ledger_export before CSV write:"
            )
            coffee_debug_pre_csv = master_ledger_export[
                master_ledger_export["Description"].str.contains(
                    "coffee", na=False, case=False
                )
            ]
            if not coffee_debug_pre_csv.empty:
                logger.info(
                    coffee_debug_pre_csv[
                        [
                            "Date",
                            "Description",
                            "ActualAmount",
                            "AllowedAmount",
                            "Shared_Amount_Display",
                        ]
                    ].to_string()
                )
            else:
                logger.info(
                    "DEBUG: Coffee transaction not found in master_ledger_export before CSV write."
                )

            master_ledger_export.to_csv(
                ledger_path, index=False
            )  # date_format not needed if already string
            output_paths["master_ledger"] = str(ledger_path)
            logger.info(f"Saved: {ledger_path}")

            # 2. Line-by-line reconciliation CSV (more user friendly)
            recon_csv_path = output_dir / "line_by_line_reconciliation_v2.3.csv"
            recon_cols = [
                "Date",
                "Category_Display",
                "Payer",
                "Description",
                "Amount_Charged_Display",
                "Shared_Amount_Display",
                "RyanOwes",
                "JordynOwes",
                "BalanceImpact",
                "Cumulative_Balance_Display",
                "Who_Paid_Text",
                "Share_Type",
                "Shared_Reason",
                "DataQuality_Audit",
                "DataQualityFlag",
                "TransactionID",
            ]
            # Ensure all recon_cols exist
            final_recon_cols = [
                col for col in recon_cols if col in master_ledger_export.columns
            ]
            master_ledger_export[final_recon_cols].to_csv(recon_csv_path, index=False)
            output_paths["reconciliation_csv"] = str(recon_csv_path)
            logger.info(f"Saved: {recon_csv_path}")

        # 3. Executive Summary CSV
        summary_data = {
            "Overall Balance": f"${reconciliation.get('amount_owed', 0):,.2f} ({reconciliation.get('who_owes_whom', 'N/A')})",
            "Total Shared Processed": f"${reconciliation.get('total_shared_amount', 0):,.2f}",
            "Data Quality Score": f"{self._calculate_data_quality_score(master_ledger):.1f}%",
            "Overall Risk Level": risk_assessment.get("overall_risk_level", "N/A"),
            "Triple Reconciliation Matched": "YES"
            if reconciliation.get("reconciled", False)
            else "NO",
            "Ledger Balance Matched": str(
                self.validation_results.get("ledger_balance_match", "N/A")
            ),
            "Processing Time (s)": f"{(datetime.now(timezone.utc) - self.start_time).total_seconds():.1f}",
            "Total Transactions Analyzed": len(master_ledger)
            if not master_ledger.empty
            else 0,
        }
        # Add source data summary
        if (
            "data_sources_summary" in analytics
        ):  # It was put in final_results, not analytics directly
            src_summary = (
                self.analyze_results.get("data_sources_summary", {})
                if hasattr(self, "analyze_results")
                else {}
            )  # Access through attribute if needed
            for src_name, details in src_summary.items():
                summary_data[f"Source - {src_name} rows"] = details.get("rows", 0)

        summary_df = pd.DataFrame(
            list(summary_data.items()), columns=["Metric", "Value"]
        )
        exec_path = output_dir / "executive_summary_v2.3.csv"
        summary_df.to_csv(exec_path, index=False)
        output_paths["executive_summary_csv"] = str(exec_path)
        logger.info(f"Saved: {exec_path}")

        # 4. Alt-texts JSON
        alt_text_path = output_dir / "alt_texts_v2.3.json"
        with open(alt_text_path, "w") as f:
            json.dump(self.alt_texts, f, indent=2)
        output_paths["alt_texts"] = str(alt_text_path)
        logger.info(f"Saved: {alt_text_path} with {len(self.alt_texts)} entries")

        # 5. Data Quality Issues Log CSV
        if self.data_quality_issues:
            error_df = pd.DataFrame(self.data_quality_issues)
            # Convert any complex objects in row_data_sample to string for CSV
            if "row_data_sample" in error_df.columns:
                error_df["row_data_sample"] = error_df["row_data_sample"].astype(str)
            error_path = output_dir / "data_quality_issues_log_v2.3.csv"
            error_df.to_csv(error_path, index=False)
            output_paths["data_quality_log"] = str(error_path)
            logger.info(f"Saved: {error_path}")

        # 6. Excel Report
        excel_path = output_dir / "financial_analysis_report_v2.3.xlsx"
        try:
            with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
                summary_df.to_excel(writer, sheet_name="Executive Summary", index=False)
                if not master_ledger_export.empty:
                    # Write only a subset of columns to Excel for readability if ledger is too wide
                    excel_ledger_cols = [
                        col
                        for col in final_recon_cols
                        if col in master_ledger_export.columns
                    ]  # Use recon_cols as a base
                    master_ledger_export[excel_ledger_cols].to_excel(
                        writer, sheet_name="Master Ledger Highlights", index=False
                    )

                pd.DataFrame(
                    list(reconciliation.items()), columns=["Metric", "Value"]
                ).to_excel(writer, sheet_name="Reconciliation Details", index=False)
                if (
                    "category_details" in reconciliation
                    and reconciliation["category_details"]
                ):
                    pd.DataFrame(reconciliation["category_details"]).to_excel(
                        writer, sheet_name="Recon Category Breakdown", index=False
                    )
                if "expense_category_analysis" in analytics and isinstance(
                    analytics["expense_category_analysis"].get("summary_table"), list
                ):
                    pd.DataFrame(
                        analytics["expense_category_analysis"]["summary_table"]
                    ).to_excel(writer, sheet_name="Expense Category Stats", index=False)
                if "details" in risk_assessment and risk_assessment["details"]:
                    pd.DataFrame(risk_assessment["details"]).to_excel(
                        writer, sheet_name="Risk Assessment Details", index=False
                    )
                pd.DataFrame(recommendations, columns=["Recommendations"]).to_excel(
                    writer, sheet_name="Recommendations", index=False
                )

                visual_index_data = [
                    {
                        "Visualization": k,
                        "Filename": Path(v).name,
                        "Alt Text": self.alt_texts.get(k, "N/A"),
                    }
                    for k, v in visualizations.items()
                ]
                pd.DataFrame(visual_index_data).to_excel(
                    writer, sheet_name="Visual Index", index=False
                )
            output_paths["excel_report"] = str(excel_path)
            logger.info(f"Saved: {excel_path}")
        except Exception as e_excel:
            logger.error(f"Failed to generate Excel report: {e_excel}", exc_info=True)

        # 7. Dashboard HTML
        try:
            dashboard_path = self._generate_dashboard_html(
                visualizations, output_dir
            )  # Renamed
            output_paths["dashboard"] = str(dashboard_path)
            logger.info(f"Saved: {dashboard_path}")
        except Exception as e_dash:
            logger.error(f"Failed to generate dashboard: {e_dash}", exc_info=True)

        # 8. Executive PDF
        try:
            pdf_path = self._generate_executive_summary_pdf(
                summary_data, visualizations, recommendations, output_dir
            )  # Renamed
            output_paths["executive_pdf"] = str(pdf_path)
            logger.info(f"Saved: {pdf_path}")
        except Exception as e_pdf:
            logger.error(f"Failed to generate executive PDF: {e_pdf}", exc_info=True)

        logger.info(
            f"Generated {len(output_paths)} output files in {output_dir.resolve()}"
        )
        return output_paths

    def _generate_dashboard_html(
        self, visualizations: Dict[str, str], output_dir: Path
    ) -> Path:
        """Generate HTML dashboard. Based on original."""
        # (Ensure this method from original is included here)
        # For brevity, assuming the HTML structure is complex and copied from original.
        # Key is that it iterates `visualizations` and `self.alt_texts`.
        html_content = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>Shared Expense Analysis Dashboard v2.3</title>
<style>body{font-family:'Inter',Arial,sans-serif;margin:20px;background-color:#f5f5f5;}
.container{max-width:1400px;margin:0 auto;background-color:white;padding:30px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.1);}
h1{font-family:'Montserrat',sans-serif;text-align:center;margin-bottom:30px;}
.nav{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:20px;padding-bottom:15px;border-bottom:1px solid #eee;}
.nav-item{padding:8px 15px;background-color:#007ACC;color:white;text-decoration:none;border-radius:5px;font-size:14px;}
.section{margin-bottom:30px;padding-top:20px;} .section h2{margin-bottom:15px;border-bottom:1px solid #ddd;padding-bottom:8px;}
.visual-container{border:1px solid #ddd;padding:10px;background:#fafafa;min-height:400px;display:flex;align-items:center;justify-content:center;}
iframe,img{max-width:100%;height:auto;border:none;border-radius:5px;}
.timestamp{text-align:center;color:#666;font-size:12px;margin-top:30px;}</style></head><body><div class="container"><h1>Expense Dashboard v2.3</h1><div class="nav">
"""
        for viz_name in sorted(visualizations.keys()):
            display_name = viz_name.replace("-", " ").title()
            html_content += f'<a href="#{viz_name}" class="nav-item">{display_name}</a>'
        html_content += '</div><div class="sections">'
        for viz_name, viz_path_str in sorted(visualizations.items()):
            viz_path = Path(viz_path_str)
            display_name = viz_name.replace("-", " ").title()
            alt = self.alt_texts.get(viz_name, "Visualization")
            html_content += f'<div class="section" id="{viz_name}"><h2>{display_name}</h2><div class="visual-container">'
            if viz_path.suffix == ".html":
                html_content += f'<iframe src="{viz_path.name}" title="{alt}" style="width:100%;height:600px;"></iframe>'
            elif viz_path.suffix == ".png":
                html_content += f'<img src="{viz_path.name}" alt="{alt}">'
            else:
                html_content += f"<p>Cannot display {viz_path.name}</p>"
            html_content += "</div></div>"
        html_content += f'</div><div class="timestamp">Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div></div></body></html>'

        dashboard_path = output_dir / "dashboard_v2.3.html"
        with open(dashboard_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        return dashboard_path

    def _generate_executive_summary_pdf(
        self,
        summary_data: Dict[str, str],
        visualizations: Dict[str, str],
        recommendations: List[str],
        output_dir: Path,
    ) -> Path:
        """Generate executive PDF report. Based on original."""
        # (Ensure this method from original is included here)
        # For brevity, assuming ReportLab logic is complex and copied.
        pdf_path = output_dir / "executive_report_v2.3.pdf"
        doc = SimpleDocTemplate(
            str(pdf_path),
            pagesize=landscape(A4),
            topMargin=0.5 * inch,
            bottomMargin=0.5 * inch,
            leftMargin=0.5 * inch,
            rightMargin=0.5 * inch,
        )
        story = []
        styles = getSampleStyleSheet()
        styles.add(
            ParagraphStyle(name="Justify", alignment=TA_LEFT)
        )  # TA_LEFT for normal text
        styles.add(
            ParagraphStyle(
                name="H1Custom",
                fontSize=20,
                leading=22,
                alignment=TA_CENTER,
                spaceAfter=20,
                textColor=colors.HexColor("#007ACC"),
            )
        )
        styles.add(
            ParagraphStyle(
                name="H2Custom",
                fontSize=16,
                leading=18,
                alignment=TA_LEFT,
                spaceAfter=10,
                textColor=colors.HexColor("#005A99"),
            )
        )

        story.append(
            Paragraph(
                "Shared Expense Analysis - Executive Summary v2.3", styles["H1Custom"]
            )
        )
        story.append(
            Paragraph(
                f"Report Date: {datetime.now().strftime('%B %d, %Y')}", styles["Normal"]
            )
        )
        story.append(Spacer(1, 0.2 * inch))

        story.append(Paragraph("Key Metrics", styles["H2Custom"]))
        metrics_table_data = [["Metric", "Value"]] + [
            [k, str(v)] for k, v in summary_data.items()
        ]  # Ensure v is str

        # Create table with specific column widths
        table_width = A4[1] - 1 * inch  # landscape A4 width minus margins
        col_widths = [
            table_width * 0.4,
            table_width * 0.6,
        ]  # 40% for metric, 60% for value

        metrics_table = Table(metrics_table_data, colWidths=col_widths)
        metrics_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#007ACC")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(metrics_table)
        story.append(PageBreak())

        story.append(Paragraph("Key Recommendations", styles["H2Custom"]))
        for i, rec in enumerate(recommendations, 1):
            story.append(Paragraph(f"{i}. {rec}", styles["Normal"]))
        story.append(PageBreak())

        story.append(Paragraph("Visualizations Overview", styles["H2Custom"]))
        for viz_name, viz_path_str in sorted(visualizations.items()):
            viz_path = Path(viz_path_str)
            if viz_path.suffix == ".png":  # Only embed PNGs in PDF
                story.append(
                    Paragraph(viz_name.replace("-", " ").title(), styles["Heading3"])
                )
                try:
                    img = Image(viz_path)
                    img_width_pts, img_height_pts = img.imageWidth, img.imageHeight

                    # Frame dimensions from ReportLab error message for 'normal' frame on 'Later' template
                    # Frame: 'normal'(757.8897637795277 x 511.27559055118115*)
                    target_frame_width = 757.8897637795277
                    target_frame_height = 511.27559055118115
                    safety_margin = 5  # points, increased for more tolerance

                    available_width = target_frame_width - safety_margin
                    available_height = target_frame_height - safety_margin

                    scale_w = 1.0
                    if img_width_pts > available_width:
                        scale_w = available_width / img_width_pts

                    scale_h = 1.0
                    if img_height_pts > available_height:
                        scale_h = available_height / img_height_pts

                    final_scale_factor = min(scale_w, scale_h)

                    if final_scale_factor < 1.0:  # Only scale down
                        img.drawWidth = img_width_pts * final_scale_factor
                        img.drawHeight = img_height_pts * final_scale_factor
                    # else: Image is small enough, use its original dimensions (implicitly handled by Image class)

                    story.append(img)
                except Exception as img_err:
                    story.append(
                        Paragraph(
                            f"[Could not load image: {viz_path.name} - {img_err}]",
                            styles["Italic"],
                        )
                    )

                alt = self.alt_texts.get(viz_name, "")
                if alt:
                    story.append(Paragraph(f"<i>{alt}</i>", styles["Italic"]))
                story.append(Spacer(1, 0.2 * inch))

        try:
            doc.build(story)
        except Exception as pdf_build_err:
            logger.error(f"Error building PDF: {pdf_build_err}", exc_info=True)
            # Fallback: create a simple text file if PDF fails
            fallback_path = output_dir / "executive_report_fallback.txt"
            with open(fallback_path, "w") as f:
                f.write("PDF Generation Failed. Summary Data:\n")
                for k, v in summary_data.items():
                    f.write(f"{k}: {v}\n")
                f.write("\nRecommendations:\n")
                for rec in recommendations:
                    f.write(f"- {rec}\n")
            return fallback_path

        return pdf_path


# --- Unit Tests (Original structure, would need update for 4 files) ---
class TestEnhancedAnalyzer(unittest.TestCase):
    def setUp(self):
        self.config = AnalysisConfig()  # Use default config for tests
        self.test_dir = Path("test_analyzer_data_v23")
        self.test_dir.mkdir(exist_ok=True)

        # Create dummy files for testing the 4-file setup
        self.expense_fixture_path = self.test_dir / "test_expenses.csv"
        # Adjusted to list of lists for precise CSV structure control
        # load_expense_history looks for 'Name' in cell values to find header
        exp_fixture_header = [
            "Date of Purchase",
            "Name",
            "Actual Amount",
            "Allowed Amount",
            "Merchant",
            "Description",
        ]
        exp_data_list = [
            [
                "Junk Row 1",
                "Junk",
                "Junk",
                "Junk",
                "Junk",
                "Junk",
            ],  # Simulating a non-header row
            exp_fixture_header,  # This row should be identified as the header by load_expense_history
            ["01/05/2024", "Ryan", "$100.00", "$100.00", "Groceries", "Weekly food"],
            ["01/10/2024", "Jordyn", "$50.00", "$50.00", "Gas", "Fuel"],
            [
                "01/15/2024",
                "Ryan",
                "$20.00",
                "",
                "Coffee",
                "Morning coffee 2x to calculate",
            ],  # Test blank allowed
        ]
        pd.DataFrame(exp_data_list).to_csv(
            self.expense_fixture_path, index=False, header=False
        )

        self.ledger_fixture_path = self.test_dir / "test_ledger.csv"
        # Adjusted to list of lists for precise CSV structure control
        # load_transaction_ledger expects headers at raw.iloc[1]
        ledger_fixture_header = [
            "Date of Purchase",
            "Name",
            "Actual Amount",
            "Running Balance",
            "Merchant",
            "Description",
        ]
        ledg_data_list = [
            [
                "Some Title or Junk Row 0",
                None,
                None,
                None,
                None,
                None,
            ],  # This is raw.iloc[0]
            ledger_fixture_header,  # This is raw.iloc[1], used as headers by load_transaction_ledger
            [
                "01/05/2024",
                "Ryan",
                "$100.00",
                "$100.00",
                "Groceries",
                "Ledger Groceries",
            ],
            ["01/10/2024", "Jordyn", "$50.00", "$150.00", "Gas", "Ledger Gas"],
        ]
        pd.DataFrame(ledg_data_list).to_csv(
            self.ledger_fixture_path, index=False, header=False
        )

        self.rent_alloc_fixture_path = self.test_dir / "test_rent_alloc.csv"
        rent_a_data = {
            "Month": ["Jan 2024", "Feb 2024"],
            "Gross Total": ["$2,000.00", "$2,010.00"],
            "Ryan's Rent (43%)": ["$860.00", "$864.30"],
            "Jordyn's Rent (57%)": ["$1,140.00", "$1,145.70"],
        }
        pd.DataFrame(rent_a_data).to_csv(self.rent_alloc_fixture_path, index=False)

        self.rent_hist_fixture_path = self.test_dir / "test_rent_hist.csv"
        rent_h_data = {
            "Cost Type": ["Base Rent", "Utilities"],
            "January 2024 Budgeted": ["$1800.00", "$150.00"],
            "January 2024 Actual": ["$1850.00", "$160.00"],
            "February 2024 Budgeted": ["$1800.00", "$150.00"],
            "February 2024 Actual": ["$1800.00", "$140.00"],
        }
        pd.DataFrame(rent_h_data).to_csv(self.rent_hist_fixture_path, index=False)

        # Minimal config for testing
        self.config.MAX_PROCESSING_TIME_SECONDS = 300  # Allow more time for tests

    def tearDown(self):
        logging.shutdown()  # Close logging handlers to release file locks
        # Clean up test files and directory
        for p in [
            self.expense_fixture_path,
            self.ledger_fixture_path,
            self.rent_alloc_fixture_path,
            self.rent_hist_fixture_path,
        ]:
            p.unlink(missing_ok=True)

        log_file = Path("financial_analysis_audit.log")
        if log_file.exists():
            try:
                log_file.unlink()
            except PermissionError:
                logger.warning(
                    f"Could not delete {log_file} during teardown, likely still in use."
                )

        output_dir = Path("analysis_output")
        if output_dir.exists():
            for item in output_dir.iterdir():
                item.unlink(missing_ok=True)  # Delete files in output
            try:
                output_dir.rmdir()  # Delete directory if empty
            except OSError:
                logger.warning(
                    f"Could not remove output_dir {output_dir} during teardown, it might not be empty."
                )

        if self.test_dir.exists():
            try:
                self.test_dir.rmdir()
            except OSError:
                logger.warning(
                    f"Could not remove test_dir {self.test_dir} during teardown, it might not be empty."
                )

    def test_full_analysis_run_v23_fixtures(self):
        """Test the full v2.3 analysis pipeline with 4 fixture files"""
        analyzer = EnhancedSharedExpenseAnalyzer(
            self.expense_fixture_path,
            self.ledger_fixture_path,
            self.rent_alloc_fixture_path,
            self.rent_hist_fixture_path,
            self.config,
        )
        results = {}
        try:
            results = analyzer.analyze()
            self.assertIn("reconciliation", results)
            self.assertIn("output_paths", results)
            self.assertIn(
                "master_ledger", results["output_paths"]
            )  # Check specific output

            # Basic checks
            self.assertGreater(
                results["data_sources_summary"]["expense_history"]["rows"], 0
            )
            self.assertGreater(
                results["data_sources_summary"]["rent_allocation"]["rows"], 0
            )

            # Check 2x calculation from expense fixture
            master_ledger_df = pd.read_csv(results["output_paths"]["master_ledger"])
            coffee_transaction = master_ledger_df[
                master_ledger_df["Description"].str.contains("coffee", na=False)
            ]
            self.assertFalse(
                coffee_transaction.empty,
                "Coffee transaction not found in master ledger",
            )
            # Original Actual Amount for coffee was $20. Allowed should be $40 due to "2x"
            self.assertAlmostEqual(
                coffee_transaction["AllowedAmount"].iloc[0],
                40.00,
                places=2,
                msg="2x calculation for coffee expense incorrect in master ledger",
            )

            # Check rent budget variance analysis exists
            self.assertIn("rent_budget_analysis", results["analytics"])
            self.assertGreater(
                results["analytics"]["rent_budget_analysis"].get(
                    "total_budget_variance", -9999
                ),
                -1000,
            )  # Check it's calculated

            # Check ledger balance match validation was attempted
            self.assertIn("ledger_balance_match", results["validation_summary"])

        except Exception as e:
            logger.error(
                f"Test 'test_full_analysis_run_v23_fixtures' FAILED. Exception: {e}",
                exc_info=True,
            )
            # If results were populated before error, log them for debugging
            if (
                results
                and "output_paths" in results
                and "data_quality_log" in results["output_paths"]
            ):
                logger.error(
                    f"Data quality log available at: {results['output_paths']['data_quality_log']}"
                )
            self.fail(f"Full analysis run failed with v2.3 fixture data: {e}")


# --- Main execution block ---
def main():
    logger.info("Enhanced Shared Expense Analyzer - Institutional Grade (v2.3)")
    logger.info("-" * 80)

    parser = argparse.ArgumentParser(
        description="Enhanced Shared Expense Analyzer v2.3"
    )
    parser.add_argument(
        "--expense",
        type=Path,
        default=Path("Expense_History_20250527.csv"),
        help="Path to expense history CSV.",
    )
    parser.add_argument(
        "--ledger",
        type=Path,
        default=Path("Transaction_Ledger_20250527.csv"),
        help="Path to transaction ledger CSV.",
    )
    parser.add_argument(
        "--rent",
        type=Path,
        default=Path("Rent_Allocation_20250527.csv"),
        help="Path to rent allocation CSV.",
    )
    parser.add_argument(
        "--rent-hist",
        type=Path,
        default=Path("Rent_History_20250527.csv"),
        help="Path to rent history CSV.",
    )
    parser.add_argument(
        "--run_tests", action="store_true", help="Run unit tests instead of analysis."
    )

    # Add config overrides as arguments
    parser.add_argument("--ryan_pct", type=float, help="Ryan's percentage (e.g., 0.43)")
    parser.add_argument(
        "--jordyn_pct", type=float, help="Jordyn's percentage (e.g., 0.57)"
    )
    parser.add_argument(
        "--rent_baseline", type=float, help="Baseline monthly rent amount"
    )

    args = parser.parse_args()

    if args.run_tests:
        logger.info("Running Unit Tests for v2.3...")
        suite = unittest.TestSuite()
        suite.addTest(unittest.makeSuite(TestEnhancedAnalyzer))
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        if not result.wasSuccessful():
            logger.error("--- UNIT TEST FAILED ---")
            # Potentially exit with error code if tests fail in a CI/CD environment
            # sys.exit(1)
        return

    # --- Configuration Setup ---
    config = AnalysisConfig()
    if args.ryan_pct is not None:
        config.RYAN_PCT = args.ryan_pct
    if args.jordyn_pct is not None:
        config.JORDYN_PCT = args.jordyn_pct
    if args.rent_baseline is not None:
        config.RENT_BASELINE = args.rent_baseline
    # Validate percentages sum to 1
    if not np.isclose(config.RYAN_PCT + config.JORDYN_PCT, 1.0):
        logger.error(
            "Error: Ryan's percentage (%s) and Jordyn's percentage (%s) do not sum to 1.0.",
            config.RYAN_PCT,
            config.JORDYN_PCT,
        )
        logger.critical("Percentages do not sum to 1.0. Aborting.")
        return

    # Validate all files exist before initializing analyzer
    files_to_check = [
        (args.expense, "Expense History"),
        (args.ledger, "Transaction Ledger"),
        (args.rent, "Rent Allocation"),
        (args.rent_hist, "Rent History"),
    ]
    all_files_found = True
    for file_path, file_name in files_to_check:
        if not file_path.exists():
            logger.error("%s file not found at %s", file_name, file_path.resolve())
            logger.critical(f"{file_name} file not found: {file_path.resolve()}")
            all_files_found = False
    if not all_files_found:
        logger.error(
            "One or more required data files were not found. Please check paths and try again."
        )
        return

    logger.info(
        "Using Configuration: Ryan Pct=%.2f%%, Jordyn Pct=%.2f%%, Rent Baseline=$%s",
        config.RYAN_PCT * 100,
        config.JORDYN_PCT * 100,
        f"{config.RENT_BASELINE:,.2f}",
    )
    logger.info("Using files:")
    logger.info("  - Expense History: %s", args.expense.resolve())
    logger.info("  - Transaction Ledger: %s", args.ledger.resolve())
    logger.info("  - Rent Allocation: %s", args.rent.resolve())
    logger.info("  - Rent History: %s", args.rent_hist.resolve())

    analyzer = EnhancedSharedExpenseAnalyzer(
        args.expense, args.ledger, args.rent, args.rent_hist, config
    )

    try:
        results = analyzer.analyze()
        # Store results on analyzer instance if needed by _generate_outputs or other methods
        analyzer.analyze_results = results

        logger.info("=" * 80)
        logger.info("ANALYSIS COMPLETE - Version 2.3")
        logger.info("=" * 80)

        logger.info(
            "Final Balance Reported: $%s",
            f"{results['reconciliation']['final_balance_reported']:,.2f}",
        )
        logger.info("Who Owes Whom: %s", results["reconciliation"]["who_owes_whom"])
        logger.info(
            "Amount Owed: $%s",
            f"{results['reconciliation']['amount_owed']:,.2f}",
        )
        logger.info(
            "Data Quality Score: %.1f%%",
            results["data_quality_score"],
        )
        logger.info(
            "Overall Risk Level: %s",
            results["risk_assessment"]["overall_risk_level"],
        )

        logger.info("Validation Summary:")
        for k, v_val in results.get("validation_summary", {}).items():
            logger.info("  - %s: %s", k, v_val)

        logger.info("Data Sources Summary:")
        for src, details in results.get("data_sources_summary", {}).items():
            logger.info(
                "  - %s: %s rows loaded. Date Range: %s - %s",
                src.replace("_", " ").title(),
                details.get("rows", 0),
                details.get("date_range", (None, None))[0],
                details.get("date_range", (None, None))[1],
            )

        logger.info("Key Data Quality Flags Found (Count):")
        dq_summary = results.get("data_quality_issues_summary", {})
        if dq_summary and not ("All Clear" in dq_summary and len(dq_summary) == 1):
            for flag, count in dq_summary.items():
                if flag != "All Clear":
                    logger.info("  - %s: %s", flag, count)
        else:
            logger.info("  - All Clear or no specific data quality flags raised.")

        logger.info("Output Files Generated In 'analysis_output' directory:")
        for name, path_str in results.get("output_paths", {}).items():
            logger.info(
                "  - %s: %s", name.replace("_", " ").title(), Path(path_str).name
            )

        logger.info("Full logs available in: financial_analysis_audit.log")
        dashboard_path = results.get("output_paths", {}).get("dashboard")
        pdf_path = results.get("output_paths", {}).get("executive_pdf")
        if dashboard_path:
            logger.info("Interactive dashboard: %s", Path(dashboard_path).resolve())
        if pdf_path:
            logger.info("Executive PDF report: %s", Path(pdf_path).resolve())

    except FileNotFoundError as fnf_err:  # Should be caught by pre-check now
        logger.error("ANALYSIS FAILED - File Not Found: %s", fnf_err)
        logger.critical(
            f"Analysis aborted due to FileNotFoundError: {fnf_err}", exc_info=True
        )
    except ValueError as val_err:  # For other data-related issues
        logger.error("ANALYSIS FAILED - Data Validation Error: %s", val_err)
        logger.critical(f"Analysis aborted due to ValueError: {val_err}", exc_info=True)
    except Exception as e:
        logger.error("ANALYSIS FAILED - An unexpected error occurred: %s", e)
        logger.critical(
            f"Analysis aborted due to an unexpected error: {e}", exc_info=True
        )
        logger.error(
            "Check 'financial_analysis_audit.log' for detailed error information."
        )


if __name__ == "__main__":
    main()
