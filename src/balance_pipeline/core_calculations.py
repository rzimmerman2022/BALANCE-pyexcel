#!/usr/bin/env python3
###############################################################################
# BALANCE-pyexcel – Core Calculations
#
# Description : Extracted calculation utilities for debug_runner.
# Key Concepts: - Triple reconciliation
# Public API  : - CoreCalculator.triple_reconciliation()
# -----------------------------------------------------------------------------
# Change Log
# Date        Author      Type        Note
# 2025-06-10  Codex       add         Extracted from analyzer.py
###############################################################################

from __future__ import annotations

from typing import Any, Dict, TYPE_CHECKING
import logging

import pandas as pd
import importlib

if TYPE_CHECKING:  # pragma: no cover - used only for typing
    AnalysisConfig = Any
else:  # pragma: no cover - runtime import
    AnalysisConfig = importlib.import_module("analyzer").AnalysisConfig

logger = logging.getLogger(__name__)


class CoreCalculator:
    """Provide core balance calculations used for debugging."""

    def __init__(self, config: AnalysisConfig) -> None:
        self.config = config

    def triple_reconciliation(self, master_ledger: pd.DataFrame) -> Dict[str, Any]:
        """Perform the triple reconciliation calculation."""
        if master_ledger.empty or "BalanceImpact" not in master_ledger.columns:
            logger.warning(
                "Master ledger is empty or missing 'BalanceImpact'. "
                "Reconciliation will yield zero values."
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

        method1_balance = (
            master_ledger["RunningBalance"].iloc[-1] if not master_ledger.empty else 0.0
        )

        shared_only = master_ledger[master_ledger["IsShared"]].copy()
        if shared_only.empty:
            method2_balance = 0.0
            method3_balance = 0.0
            total_shared_amount = 0.0
            ryan_total_fair_share = 0.0
            jordyn_total_fair_share = 0.0
            ryan_actually_paid_for_shared = 0.0
            jordyn_actually_paid_for_shared = 0.0
            category_balances_info: list[Dict[str, Any]] = []
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

            method2_balance = ryan_actually_paid_for_shared - ryan_total_fair_share

            category_balances_info = []
            method3_balance_accumulator = 0.0
            for trans_type in ["RENT", "EXPENSE"]:
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

        tolerance = 0.015
        reconciled_1_2 = abs(method1_balance + method2_balance) <= tolerance
        reconciled_2_3 = abs(method2_balance - method3_balance) <= tolerance
        all_reconciled = reconciled_1_2 and reconciled_2_3

        final_balance_to_report = method1_balance
        who_owes = (
            "Ryan owes Jordyn"
            if final_balance_to_report > 0.005
            else "Jordyn owes Ryan"
            if final_balance_to_report < -0.005
            else "Settled"
        )
        amount_owed_val = abs(final_balance_to_report)

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
            "ryan_net_variance_from_fair_share": round(method2_balance, 2),
            "jordyn_net_variance_from_fair_share": round(
                jordyn_actually_paid_for_shared - jordyn_total_fair_share, 2
            ),
            "category_details": category_balances_info,
            "final_balance_reported": round(final_balance_to_report, 2),
            "who_owes_whom": who_owes,
            "amount_owed": round(amount_owed_val, 2),
        }
