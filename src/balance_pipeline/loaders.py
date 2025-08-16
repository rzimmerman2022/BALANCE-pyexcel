from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# --- Data Loader V2.3 (as in analyzer.py) ---
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
    ) -> dict[str, Any]:
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


# --- Helper functions for merging data (moved from analyzer.py) ---
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
    # P0 Blueprint: Dedup logic: drop_duplicates(keep="first") assumes concat order guarantees ledger‐first wins.
    # If header detection flips, wrong record kept silently.
    # For now, keeping original logic. Refinement of dedup logic (e.g. more explicit preference) can be a P1 task.
    combined = combined.sort_values(
        by=["Date of Purchase", "Actual Amount", "Source"], ascending=[True, True, True]
    )  # True for Source means ExpenseHistory comes first if not preferring Ledger
    combined = combined.drop_duplicates(
        subset=key_fields, keep="first"
    )  # 'first' will keep TransactionLedger due to prior concat order and sort

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
