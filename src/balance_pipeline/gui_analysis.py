from __future__ import annotations

import contextlib
import logging
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


class AnalysisController:
    """
    Handles data loading and analysis logic for the Dispute Analyzer GUI.

    This class is decoupled from the UI and can be tested independently.
    """

    def __init__(self, output_dir: str | Path = "output") -> None:
        self.output_dir = Path(output_dir)
        self.df: pd.DataFrame | None = None

    def load_data(self) -> None:
        """
        Load the latest cleaned transactions dataset from the output directory.

        Looks for Parquet first, then CSV. Coerces date dtype, ensures
        required columns exist, and derives 'amount_abs' for convenience.

        Raises:
            FileNotFoundError: If no data files are found in the output directory.
            ValueError: If the loaded data is missing required columns.
            Exception: For other pandas or data loading related errors.
        """
        logger.info(f"Searching for data files in '{self.output_dir}'...")

        parquet_files = sorted(
            self.output_dir.glob("*.parquet"), key=lambda p: p.stat().st_mtime, reverse=True
        )
        csv_files = sorted(
            self.output_dir.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True
        )

        try:
            if parquet_files:
                latest_file = parquet_files[0]
                logger.info(f"Loading latest Parquet file: {latest_file.name}")
                self.df = pd.read_parquet(latest_file)
            elif csv_files:
                latest_file = csv_files[0]
                logger.info(f"Loading latest CSV file: {latest_file.name}")
                self.df = pd.read_csv(latest_file)
            else:
                raise FileNotFoundError(
                    f"No cleaned data files (.parquet or .csv) found in '{self.output_dir}'."
                )

            self._validate_and_prepare_dataframe()
            logger.info(f"Successfully loaded and prepared {len(self.df)} transactions.")

        except (FileNotFoundError, ValueError) as e:
            logger.error(f"Error during data loading: {e}")
            raise  # Re-raise the specific, handled exception
        except Exception as e:
            logger.error(f"An unexpected error occurred while loading data: {e}")
            raise ValueError(f"Failed to load or process data file: {e}") from e

    def _validate_and_prepare_dataframe(self) -> None:
        """
        Validates the loaded DataFrame and prepares it for analysis.
        """
        if self.df is None:
            raise ValueError("DataFrame has not been loaded.")

        required_cols = {
            "date", "amount", "merchant_standardized", "description", "potential_refund"
        }
        missing_cols = required_cols - set(self.df.columns)
        if missing_cols:
            raise ValueError(f"Loaded data is missing required columns: {', '.join(missing_cols)}")

        # Ensure 'date' column is datetime
        if not pd.api.types.is_datetime64_any_dtype(self.df["date"]):
            self.df["date"] = pd.to_datetime(self.df["date"], errors="coerce")

        # Coerce NaT to None for better handling, though not strictly required by frontend
        self.df.loc[self.df["date"].isna(), "date"] = None

        # Ensure 'amount_abs' exists
        if "amount_abs" not in self.df.columns:
            self.df["amount_abs"] = self.df["amount"].abs()

        # Ensure 'potential_refund' is a boolean
        self.df["potential_refund"] = self.df["potential_refund"].fillna(False).astype(bool)

    def get_dataframe(self) -> pd.DataFrame:
        """
        Returns the loaded and prepared DataFrame.

        Raises:
            ValueError: If data has not been loaded yet.
        """
        if self.df is None:
            raise ValueError("Data has not been loaded. Call load_data() first.")
        return self.df.copy()

    def get_dashboard_metrics(self) -> dict[str, Any]:
        """Calculates and returns key metrics for the dashboard."""
        if self.df is None:
            return {}

        total_disputes = int(self.df["potential_refund"].sum())
        dispute_amount = float(self.df[self.df["potential_refund"]]["amount"].sum())
        recent_disputes = int(
            self.df[
                (self.df["potential_refund"])
                & (self.df["date"] >= pd.Timestamp.now() - pd.Timedelta(days=30))
            ].shape[0]
        )
        total_refunds = int(self.df[self.df["amount"] > 0].shape[0])

        return {
            "total_disputes": total_disputes,
            "dispute_amount": dispute_amount,
            "recent_disputes": recent_disputes,
            "total_refunds": total_refunds,
        }

    def get_recent_disputes(self, count: int = 20) -> pd.DataFrame:
        """Returns the most recent potential disputes."""
        if self.df is None:
            return pd.DataFrame()
        return self.df[self.df["potential_refund"]].tail(count)

    def find_refunds_by_merchant(self, merchant: str, days: int) -> pd.DataFrame:
        """Finds potential refunds or credits for a given merchant within a time window."""
        if self.df is None or not merchant:
            return pd.DataFrame()

        pat = merchant.strip()
        m = self.df["merchant_standardized"].str.contains(pat, case=False, na=False)
        refund_mask = self.df["potential_refund"]
        date_mask = self.df["date"] >= (pd.Timestamp.now() - pd.Timedelta(days=days))

        # A transaction is a potential refund if it's flagged OR it's a credit
        return self.df[m & (refund_mask | (self.df["amount"] > 0)) & date_mask]

    def find_duplicate_charges(self, days_window: int) -> list[dict[str, Any]]:
        """
        Detects likely duplicate charges by merchant and absolute amount
        within a specified day window.
        """
        if self.df is None:
            return []

        dups = []
        charges = self.df[self.df["amount"] < 0].copy()

        # Group by merchant and absolute amount for efficiency
        for (merchant, amount_abs), group in charges.groupby(["merchant_standardized", "amount_abs"]):
            if len(group) > 1:
                sorted_group = group.sort_values("date")
                # Compare adjacent transactions in the sorted group
                for i in range(len(sorted_group) - 1):
                    t1 = sorted_group.iloc[i]
                    t2 = sorted_group.iloc[i + 1]
                    delta_days = (t2["date"] - t1["date"]).days
                    if 0 <= delta_days <= days_window:
                        dups.append(
                            {
                                "date1": t1["date"],
                                "date2": t2["date"],
                                "merchant": merchant,
                                "amount": -float(amount_abs),
                                "days_apart": delta_days,
                                "description1": t1["description"],
                                "description2": t2["description"],
                            }
                        )
        return dups

    def check_refund_status(self, merchant: str, amount: float, charge_date: pd.Timestamp) -> pd.DataFrame:
        """
        Checks for a matching refund for a specific charge within 60 days.
        """
        if self.df is None:
            return pd.DataFrame()

        start_date = charge_date
        end_date = charge_date + pd.Timedelta(days=60)

        merchant_mask = self.df["merchant_standardized"].str.contains(merchant, case=False, na=False)
        date_mask = (self.df["date"] >= start_date) & (self.df["date"] <= end_date)
        # Check for amounts that are very close to the charge amount
        amount_mask = (self.df["amount"].abs() - abs(amount)).abs() < 0.01
        refund_mask = self.df["amount"] > 0

        return self.df[merchant_mask & date_mask & amount_mask & refund_mask]

    def get_dispute_analysis(self) -> dict[str, Any]:
        """Calculates and returns data for the dispute analysis view."""
        if self.df is None:
            return {}

        disputes = self.df[self.df["potential_refund"]]
        if disputes.empty:
            return {"total_disputes": 0}

        total_disputes = len(disputes)
        total_amount = float(disputes["amount"].sum())
        date_range = f"{disputes['date'].min():%b %Y} - {disputes['date'].max():%b %Y}"

        top_merchants = (
            disputes.groupby("merchant_standardized")
            .agg(Count=("amount", "count"), TotalAmount=("amount", "sum"))
            .round(2)
            .sort_values("Count", ascending=False)
            .head(10)
            .reset_index()
        )

        return {
            "total_disputes": total_disputes,
            "total_amount": total_amount,
            "date_range": date_range,
            "top_merchants": top_merchants.to_dict(orient="records"),
        }

    def perform_advanced_search(self, params: dict[str, Any]) -> pd.DataFrame:
        """Performs an advanced search based on a dictionary of parameters."""
        if self.df is None:
            return pd.DataFrame()

        results = self.df.copy()

        if start_date_str := params.get("start_date"):
            with contextlib.suppress(Exception):
                results = results[results["date"] >= pd.to_datetime(start_date_str)]

        if end_date_str := params.get("end_date"):
            with contextlib.suppress(Exception):
                results = results[results["date"] <= pd.to_datetime(end_date_str)]

        if min_amount_str := params.get("min_amount"):
            with contextlib.suppress(Exception):
                results = results[results["amount_abs"] >= float(min_amount_str)]

        if max_amount_str := params.get("max_amount"):
            with contextlib.suppress(Exception):
                results = results[results["amount_abs"] <= float(max_amount_str)]

        if merchant_str := params.get("merchant"):
            pat = merchant_str.strip()
            results = results[results["merchant_standardized"].str.contains(pat, case=False, na=False)]

        if params.get("only_disputes"):
            results = results[results["potential_refund"]]

        return results.head(100)
