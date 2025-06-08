from __future__ import annotations

import pandas as pd
import numpy as np
import logging
from typing import Dict, Any

# Assuming config.py is in the same directory or accessible via PYTHONPATH
from .config import AnalysisConfig

logger = logging.getLogger(__name__)

def triple_reconciliation(
    master_ledger: pd.DataFrame, 
    config: AnalysisConfig,
    logger_instance: logging.Logger = logger
) -> Dict[str, Any]:
    """
    Perform triple reconciliation based on the master ledger.
    M1: Final Running Balance.
    M2: Variance of Ryan's actual payments for shared items vs. his fair share of total shared.
    M3: Sum of Ryan's variance (actual paid vs. fair share) for each category (RENT, EXPENSE).
    
    Expected: M1 ≈ -M2 and M1 ≈ -M3. M2 ≈ M3.
    A positive M1 (RunningBalance) means Ryan owes Jordyn.
    A positive M2/M3 (Ryan's Net Payment Variance) means Ryan overpaid his share, so Jordyn owes Ryan.
    """
    logger_instance.info("Performing triple reconciliation...")
    if master_ledger.empty or "BalanceImpact" not in master_ledger.columns:
        logger_instance.warning(
            "Master ledger is empty or missing 'BalanceImpact'. Reconciliation will yield zero/default values."
        )
        return {
            "method1_running_balance": 0.0,
            "method2_variance_ryan_vs_fair": 0.0,
            "method3_category_sum_ryan_vs_fair": 0.0,
            "reconciled": True, # Or False if we consider no data a failure
            "max_difference": 0.0,
            "total_shared_amount": 0.0,
            "ryan_total_fair_share": 0.0,
            "jordyn_total_fair_share": 0.0,
            "ryan_actually_paid_for_shared": 0.0,
            "jordyn_actually_paid_for_shared": 0.0,
            "ryan_net_variance_from_fair_share": 0.0,
            "jordyn_net_variance_from_fair_share": 0.0,
            "category_details": [],
            "final_balance_reported": 0.0,
            "who_owes_whom": "No transactions or data",
            "amount_owed": 0.0,
        }

    # Method 1: Final Running Balance
    method1_balance = master_ledger["RunningBalance"].iloc[-1] if not master_ledger.empty else 0.0

    # --- Method 2 & 3 Calculations ---
    shared_only = master_ledger[master_ledger["IsShared"] == True].copy()
    
    total_shared_amount = 0.0
    ryan_total_fair_share = 0.0
    jordyn_total_fair_share = 0.0
    ryan_actually_paid_for_shared = 0.0
    jordyn_actually_paid_for_shared = 0.0
    method2_balance = 0.0
    method3_balance_accumulator = 0.0
    category_balances_info = []

    if not shared_only.empty and "AllowedAmount" in shared_only.columns and "Payer" in shared_only.columns:
        total_shared_amount = shared_only["AllowedAmount"].sum()
        ryan_total_fair_share = total_shared_amount * config.RYAN_PCT
        jordyn_total_fair_share = total_shared_amount * config.JORDYN_PCT

        ryan_actually_paid_for_shared = shared_only[
            shared_only["Payer"].str.lower() == "ryan"
        ]["AllowedAmount"].sum()
        jordyn_actually_paid_for_shared = shared_only[
            shared_only["Payer"].str.lower() == "jordyn"
        ]["AllowedAmount"].sum()

        # M2: Ryan's variance: if positive, Ryan overpaid his share (Jordyn owes Ryan)
        method2_balance = ryan_actually_paid_for_shared - ryan_total_fair_share

        # M3: Sum of Ryan's Net Position by Category
        for trans_type in shared_only["TransactionType"].unique(): # Iterate over actual types present
            type_data = shared_only[shared_only["TransactionType"] == trans_type]
            if not type_data.empty:
                type_total_shared = type_data["AllowedAmount"].sum()
                type_ryan_fair_share_cat = type_total_shared * config.RYAN_PCT
                
                type_ryan_paid_cat = type_data[
                    type_data["Payer"].str.lower() == "ryan"
                ]["AllowedAmount"].sum()
                type_jordyn_paid_cat = type_data[ # For info, not directly in M3 calc
                    type_data["Payer"].str.lower() == "jordyn"
                ]["AllowedAmount"].sum()

                type_ryan_variance_cat = type_ryan_paid_cat - type_ryan_fair_share_cat
                method3_balance_accumulator += type_ryan_variance_cat

                category_balances_info.append({
                    "Category": trans_type,
                    "TotalShared": round(type_total_shared, config.CURRENCY_PRECISION),
                    "RyanPaidShared": round(type_ryan_paid_cat, config.CURRENCY_PRECISION),
                    "JordynPaidShared": round(type_jordyn_paid_cat, config.CURRENCY_PRECISION),
                    "RyanFairShare": round(type_ryan_fair_share_cat, config.CURRENCY_PRECISION),
                    "RyanVarianceForCategory": round(type_ryan_variance_cat, config.CURRENCY_PRECISION),
                })
    
    method3_balance = method3_balance_accumulator

    # Reconciliation Check
    tolerance = 0.015  # 1.5 cents
    reconciled_1_2 = abs(method1_balance + method2_balance) <= tolerance
    reconciled_2_3 = abs(method2_balance - method3_balance) <= tolerance
    all_reconciled = reconciled_1_2 and reconciled_2_3

    final_balance_to_report = method1_balance
    who_owes = (
        "Ryan owes Jordyn" if final_balance_to_report > 0.005 else
        "Jordyn owes Ryan" if final_balance_to_report < -0.005 else
        "Settled"
    )
    amount_owed_val = abs(final_balance_to_report)

    logger_instance.info("Triple Reconciliation Results:")
    logger_instance.info(f"  M1 (Running Balance): ${method1_balance:,.2f} ({'Ryan owes Jordyn' if method1_balance > 0 else 'Jordyn owes Ryan' if method1_balance < 0 else 'Settled'})")
    logger_instance.info(f"  M2 (Ryan's Net Payment vs Fair Share): ${method2_balance:,.2f} ({'Jordyn owes Ryan' if method2_balance > 0 else 'Ryan owes Jordyn' if method2_balance < 0 else 'Settled'})")
    logger_instance.info(f"  M3 (Category Sum of Ryan's Net Payment vs Fair Share): ${method3_balance:,.2f} ({'Jordyn owes Ryan' if method3_balance > 0 else 'Ryan owes Jordyn' if method3_balance < 0 else 'Settled'})")
    logger_instance.info(f"  All Reconciled (M1 ≈ -M2, M2 ≈ M3): {all_reconciled}")
    if not all_reconciled:
        logger_instance.error(
            f"Reconciliation discrepancy! M1-(-M2) diff: {method1_balance + method2_balance:.4f}, M2-M3 diff: {method2_balance - method3_balance:.4f}"
        )

    return {
        "method1_running_balance": round(method1_balance, config.CURRENCY_PRECISION),
        "method2_variance_ryan_vs_fair": round(method2_balance, config.CURRENCY_PRECISION),
        "method3_category_sum_ryan_vs_fair": round(method3_balance, config.CURRENCY_PRECISION),
        "reconciled": all_reconciled,
        "max_difference": round(max(abs(method1_balance + method2_balance), abs(method2_balance - method3_balance)), config.CURRENCY_PRECISION),
        "total_shared_amount": round(total_shared_amount, config.CURRENCY_PRECISION),
        "ryan_total_fair_share": round(ryan_total_fair_share, config.CURRENCY_PRECISION),
        "jordyn_total_fair_share": round(jordyn_total_fair_share, config.CURRENCY_PRECISION),
        "ryan_actually_paid_for_shared": round(ryan_actually_paid_for_shared, config.CURRENCY_PRECISION),
        "jordyn_actually_paid_for_shared": round(jordyn_actually_paid_for_shared, config.CURRENCY_PRECISION),
        "ryan_net_variance_from_fair_share": round(method2_balance, config.CURRENCY_PRECISION),
        "jordyn_net_variance_from_fair_share": round((jordyn_actually_paid_for_shared - jordyn_total_fair_share), config.CURRENCY_PRECISION),
        "category_details": category_balances_info,
        "final_balance_reported": round(final_balance_to_report, config.CURRENCY_PRECISION),
        "who_owes_whom": who_owes,
        "amount_owed": round(amount_owed_val, config.CURRENCY_PRECISION),
    }
