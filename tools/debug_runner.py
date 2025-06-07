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
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from analyzer import AnalysisConfig

try:
    from core_calculations import CoreCalculator
    from data_loader_temp import load_all_data
except ImportError:  # pragma: no cover - optional modules
    CoreCalculator = None
    load_all_data = None


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
