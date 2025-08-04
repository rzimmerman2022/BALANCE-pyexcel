#!/usr/bin/env python3
###############################################################################
# BALANCE-pyexcel – Temporary Data Loader
#
# Description : Simplified helpers to load the four core CSV files.
# Key Concepts: - Thin wrapper around DataLoaderV23
# Public API  : - load_all_data()
# -----------------------------------------------------------------------------
# Change Log
# Date        Author      Type        Note
# 2025-06-10  Codex       add         Extracted from analyzer.py
###############################################################################

from __future__ import annotations

from pathlib import Path
from typing import Any, Tuple, TYPE_CHECKING

import pandas as pd
import importlib

if TYPE_CHECKING:  # pragma: no cover - for typing only
    DataLoaderV23 = Any
else:
    DataLoaderV23 = importlib.import_module("analyzer").DataLoaderV23


def load_all_data(
    expense_path: Path,
    ledger_path: Path,
    rent_alloc_path: Path,
    rent_hist_path: Path,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load all CSV data sources using DataLoaderV23."""
    expense_df = DataLoaderV23.load_expense_history(expense_path)
    ledger_df = DataLoaderV23.load_transaction_ledger(ledger_path)
    rent_alloc_df = DataLoaderV23.load_rent_allocation(rent_alloc_path)
    rent_hist_df = DataLoaderV23.load_rent_history(rent_hist_path)

    DataLoaderV23.validate_loaded_data(
        expense_df, ledger_df, rent_alloc_df, rent_hist_df
    )
    return expense_df, ledger_df, rent_alloc_df, rent_hist_df
