from __future__ import annotations

import logging
from typing import Any

import pandas as pd

# Assuming config.py is in the same directory or accessible via PYTHONPATH
from .config import AnalysisConfig

logger = logging.getLogger(__name__)

def calc_m1_running_balance(df: pd.DataFrame) -> float:
    """
    Calculate M1: Final Running Balance from master ledger.
    """
    if df.empty or "RunningBalance" not in df.columns:
        return 0.0
    return float(df["RunningBalance"].iloc[-1])


def calc_m2_fair_share(df: pd.DataFrame, config: AnalysisConfig) -> dict[str, Any]:
    """
    Calculate M2: Ryan's variance from fair share of total shared expenses.
    Returns variance calculation details.
    """
    if df.empty:
        return {
            "variance": 0.0,
            "total_shared": 0.0,
            "ryan_fair_share": 0.0,
            "ryan_actually_paid": 0.0
        }

    shared_only = df[df["IsShared"] == True].copy()
    
    if shared_only.empty or "AllowedAmount" not in shared_only.columns:
        return {
            "variance": 0.0,
            "total_shared": 0.0,
            "ryan_fair_share": 0.0,
            "ryan_actually_paid": 0.0
        }

    total_shared_amount = shared_only["AllowedAmount"].sum()
    ryan_fair_share = total_shared_amount * config.RYAN_PCT
    
    ryan_actually_paid = shared_only[
        shared_only["Payer"].str.lower() == "ryan"
    ]["AllowedAmount"].sum()
    
    variance = ryan_actually_paid - ryan_fair_share
    
    return {
        "variance": float(variance),
        "total_shared": float(total_shared_amount),
        "ryan_fair_share": float(ryan_fair_share),
        "ryan_actually_paid": float(ryan_actually_paid)
    }


def calc_m3_category_sum(df: pd.DataFrame, config: AnalysisConfig) -> dict[str, Any]:
    """
    Calculate M3: Sum of Ryan's variance by category.
    Returns category breakdown and total variance.
    """
    if df.empty:
        return {
            "variance": 0.0,
            "category_details": []
        }

    shared_only = df[df["IsShared"] == True].copy()
    
    if shared_only.empty or "AllowedAmount" not in shared_only.columns:
        return {
            "variance": 0.0,
            "category_details": []
        }

    total_variance = 0.0
    category_details = []

    for trans_type in shared_only["TransactionType"].unique():
        type_data = shared_only[shared_only["TransactionType"] == trans_type]
        
        if not type_data.empty:
            type_total_shared = type_data["AllowedAmount"].sum()
            type_ryan_fair_share = type_total_shared * config.RYAN_PCT
            
            type_ryan_paid = type_data[
                type_data["Payer"].str.lower() == "ryan"
            ]["AllowedAmount"].sum()
            
            type_jordyn_paid = type_data[
                type_data["Payer"].str.lower() == "jordyn"
            ]["AllowedAmount"].sum()

            type_variance = type_ryan_paid - type_ryan_fair_share
            total_variance += type_variance

            category_details.append({
                "Category": trans_type,
                "TotalShared": round(type_total_shared, config.CURRENCY_PRECISION),
                "RyanPaidShared": round(type_ryan_paid, config.CURRENCY_PRECISION),
                "JordynPaidShared": round(type_jordyn_paid, config.CURRENCY_PRECISION),
                "RyanFairShare": round(type_ryan_fair_share, config.CURRENCY_PRECISION),
                "RyanVarianceForCategory": round(type_variance, config.CURRENCY_PRECISION),
            })

    return {
        "variance": float(total_variance),
        "category_details": category_details
    }


def triple_reconciliation(
    master_ledger: pd.DataFrame, 
    config: AnalysisConfig,
    logger_instance: logging.Logger = logger
) -> dict[str, Any]:
    """
    Perform triple reconciliation using helper functions.
    Orchestrates M1, M2, M3 calculations and validates reconciliation.
    """
    logger_instance.info("Starting triple reconciliation...")
    
    if master_ledger.empty or "BalanceImpact" not in master_ledger.columns:
        logger_instance.warning("Empty master ledger or missing BalanceImpact column")
        return {
            "m1": 0.0,
            "m2": 0.0, 
            "m3": 0.0,
            "all_reconciled": True,
            "method1_running_balance": 0.0,
            "method2_variance_ryan_vs_fair": 0.0,
            "method3_category_sum_ryan_vs_fair": 0.0,
            "reconciled": True,
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

    # Calculate M1, M2, M3 using helper functions
    m1 = calc_m1_running_balance(master_ledger)
    m2_result = calc_m2_fair_share(master_ledger, config)
    m3_result = calc_m3_category_sum(master_ledger, config)
    
    m2 = m2_result["variance"]
    m3 = m3_result["variance"]

    # Reconciliation check
    tolerance = 0.015  # 1.5 cents
    reconciled_1_2 = abs(m1 + m2) <= tolerance
    reconciled_2_3 = abs(m2 - m3) <= tolerance
    all_reconciled = reconciled_1_2 and reconciled_2_3

    # Determine who owes whom
    final_balance = m1
    who_owes = (
        "Ryan owes Jordyn" if final_balance > 0.005 else
        "Jordyn owes Ryan" if final_balance < -0.005 else
        "Settled"
    )
    amount_owed = abs(final_balance)

    # Structured logging with exact numbers
    logger_instance.info("Triple Reconciliation Results", extra={
        "m1": round(m1, config.CURRENCY_PRECISION),
        "m2": round(m2, config.CURRENCY_PRECISION), 
        "m3": round(m3, config.CURRENCY_PRECISION),
        "all_reconciled": all_reconciled
    })
    
    logger_instance.info(f"M1 (Running Balance): ${m1:,.2f}")
    logger_instance.info(f"M2 (Ryan's Net Payment vs Fair Share): ${m2:,.2f}")
    logger_instance.info(f"M3 (Category Sum): ${m3:,.2f}")
    logger_instance.info(f"All Reconciled: {all_reconciled}")
    
    if not all_reconciled:
        logger_instance.error(f"Reconciliation failed! M1+M2 diff: {m1 + m2:.4f}, M2-M3 diff: {m2 - m3:.4f}")

    # Calculate additional details for compatibility
    total_shared = m2_result["total_shared"]
    ryan_fair_share = m2_result["ryan_fair_share"]
    jordyn_fair_share = total_shared - ryan_fair_share if total_shared > 0 else 0.0
    ryan_actually_paid = m2_result["ryan_actually_paid"]
    jordyn_actually_paid = total_shared - ryan_actually_paid if total_shared > 0 else 0.0
    jordyn_variance = jordyn_actually_paid - jordyn_fair_share

    return {
        # New structured format
        "m1": round(m1, config.CURRENCY_PRECISION),
        "m2": round(m2, config.CURRENCY_PRECISION),
        "m3": round(m3, config.CURRENCY_PRECISION),
        "all_reconciled": all_reconciled,
        
        # Legacy format for backward compatibility
        "method1_running_balance": round(m1, config.CURRENCY_PRECISION),
        "method2_variance_ryan_vs_fair": round(m2, config.CURRENCY_PRECISION),
        "method3_category_sum_ryan_vs_fair": round(m3, config.CURRENCY_PRECISION),
        "reconciled": all_reconciled,
        "max_difference": round(max(abs(m1 + m2), abs(m2 - m3)), config.CURRENCY_PRECISION),
        "total_shared_amount": round(total_shared, config.CURRENCY_PRECISION),
        "ryan_total_fair_share": round(ryan_fair_share, config.CURRENCY_PRECISION),
        "jordyn_total_fair_share": round(jordyn_fair_share, config.CURRENCY_PRECISION),
        "ryan_actually_paid_for_shared": round(ryan_actually_paid, config.CURRENCY_PRECISION),
        "jordyn_actually_paid_for_shared": round(jordyn_actually_paid, config.CURRENCY_PRECISION),
        "ryan_net_variance_from_fair_share": round(m2, config.CURRENCY_PRECISION),
        "jordyn_net_variance_from_fair_share": round(jordyn_variance, config.CURRENCY_PRECISION),
        "category_details": m3_result["category_details"],
        "final_balance_reported": round(final_balance, config.CURRENCY_PRECISION),
        "who_owes_whom": who_owes,
        "amount_owed": round(amount_owed, config.CURRENCY_PRECISION),
    }
