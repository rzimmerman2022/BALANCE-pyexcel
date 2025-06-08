#!/usr/bin/env python3
###############################################################################
# BALANCE-pyexcel – Debug Runner
#
# Description : Standalone script to run the core balance calculations with
#                extensive logging. Useful when analyzer.py is too large to
#                debug directly.
# Key Concepts: - Modular data loading
#               - Detailed logging
# Public API  : - main()
# -----------------------------------------------------------------------------
# Change Log
# Date        Author      Type        Note
# 2025-06-09  Codex       add         Initial version
###############################################################################
# mypy: ignore-errors
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from typing import Any, TYPE_CHECKING
import importlib

if TYPE_CHECKING:  # pragma: no cover - typing only
    AnalysisConfig = Any
    import pandas as pd
else:
    AnalysisConfig = importlib.import_module("analyzer").AnalysisConfig

try:  # pragma: no cover - prefer helper modules if available
    from core_calculations import CoreCalculator  # type: ignore
except Exception:  # Fallback to heavy analyzer implementation
    import importlib

    EnhancedSharedExpenseAnalyzer = importlib.import_module(
        "analyzer"
    ).EnhancedSharedExpenseAnalyzer  # type: ignore

    class CoreCalculator:
        """Thin wrapper using analyzer for triple reconciliation."""

        def __init__(self, config: AnalysisConfig) -> None:
            self._helper = EnhancedSharedExpenseAnalyzer(
                Path(""), Path(""), Path(""), Path(""), config=config
            )
            self.config = config

        def triple_reconciliation(self, master_ledger: "pd.DataFrame") -> dict:
            return self._helper._triple_reconciliation(master_ledger)


try:  # pragma: no cover - prefer helper modules if available
    from data_loader_temp import load_all_data  # type: ignore
except Exception:
    import importlib

    DataLoaderV23 = importlib.import_module("analyzer").DataLoaderV23  # type: ignore

    def load_all_data(
        expense_path: Path,
        ledger_path: Path,
        alloc_path: Path,
        hist_path: Path,
    ) -> tuple["pd.DataFrame", "pd.DataFrame", "pd.DataFrame", "pd.DataFrame"]:
        return (
            DataLoaderV23.load_expense_history(expense_path),
            DataLoaderV23.load_transaction_ledger(ledger_path),
            DataLoaderV23.load_rent_allocation(alloc_path),
            DataLoaderV23.load_rent_history(hist_path),
        )


logger = logging.getLogger(__name__)


def main() -> None:
    """Execute the extracted balance calculation with verbose logging."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(
                f"debug_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            ),
            logging.StreamHandler(),
        ],
    )
    logger.info("=== DEBUG RUN STARTED ===")

    config = AnalysisConfig()
    logger.info("Configuration: %s", config.__dict__)

    expense_file = Path("data/Expense_History_20250527.csv")
    ledger_file = Path("data/Transaction_Ledger_20250527.csv")
    rent_alloc_file = Path("data/Rent_Allocation_20250527.csv")
    rent_hist_file = Path("data/Rent_History_20250527.csv")

    for file_path in [expense_file, ledger_file, rent_alloc_file, rent_hist_file]:
        if not file_path.exists():
            logger.error("File not found: %s", file_path)
            return
        size_kb = file_path.stat().st_size / 1024
        logger.info("Found file: %s (%.1f KB)", file_path, size_kb)

    if not CoreCalculator or not load_all_data:
        logger.error("Required modules not available; cannot run calculation")
        return

    expense_df, ledger_df, rent_alloc_df, rent_hist_df = load_all_data(
        expense_file, ledger_file, rent_alloc_file, rent_hist_file
    )

    logger.info(
        "Loaded data shapes: Expenses=%s Ledger=%s RentAlloc=%s RentHist=%s",
        expense_df.shape,
        ledger_df.shape,
        rent_alloc_df.shape,
        rent_hist_df.shape,
    )

    # TODO: Insert processing and master ledger creation steps here as needed.
    master_ledger = ledger_df  # Placeholder for simplified flow

    calculator = CoreCalculator(config)
    result = calculator.triple_reconciliation(master_ledger)

    logger.info("=== FINAL RESULTS ===")
    logger.info("Who owes whom: %s", result.get("who_owes_whom"))
    logger.info("Amount owed: $%s", result.get("amount_owed"))
    logger.info(
        "Reconciliation status: %s", "PASSED" if result.get("reconciled") else "FAILED"
    )

    Path("final_balance_result.json").write_text(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
