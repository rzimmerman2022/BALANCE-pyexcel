from __future__ import annotations

import pandas as pd
import numpy as np
from scipy import stats
import logging
from typing import Dict, Any, Optional, List

# Assuming config.py is in the same directory or accessible via PYTHONPATH
from .config import AnalysisConfig, DataQualityFlag, DEFAULT_MERCHANT_CATEGORIES

logger = logging.getLogger(__name__)

def _categorize_merchant(merchant: Optional[str], categories_map: Optional[Dict[str, List[str]]] = None) -> str:
    """Categorize merchant based on keywords.
    P1: This should load categories_map from an external YAML via AnalysisConfig.
    For P0, it uses a default map.
    """
    if pd.isna(merchant) or not isinstance(merchant, str) or not merchant.strip():
        return "Other/Unspecified"

    merchant_lower = merchant.lower()
    
    # Use provided categories_map or default from config
    current_categories_map = categories_map if categories_map is not None else DEFAULT_MERCHANT_CATEGORIES

    for category, keywords in current_categories_map.items():
        if any(keyword in merchant_lower for keyword in keywords):
            return category
    return "Other Expenses" # Fallback if no category matched

def _analyze_rent_budget_variance(
    rent_df: pd.DataFrame, 
    config: AnalysisConfig, # Added config for consistency, though not directly used in this version
    logger_instance: logging.Logger = logger
) -> Dict[str, Any]:
    logger_instance.info("Analyzing rent budget variance...")
    analysis: Dict[str, Any] = {}

    if rent_df.empty or "Budget_Variance" not in rent_df.columns or rent_df["Budget_Variance"].isna().all():
        logger_instance.warning("No budget data available or all variances are NaN for rent budget analysis.")
        return {"message": "No budget data available or all variances are NaN"}

    variance_data = rent_df[rent_df["Budget_Variance"].notna()].copy()

    if not variance_data.empty:
        month_col = "Month_Display" if "Month_Display" in variance_data.columns else "Date"
        
        # Ensure month_col values are string for idxmax/idxmin if they are Timestamps or Periods
        if pd.api.types.is_datetime64_any_dtype(variance_data[month_col]) or \
           isinstance(variance_data[month_col].dtype, pd.PeriodDtype):
            variance_data[month_col] = variance_data[month_col].astype(str)


        analysis = {
            "total_budget_variance": round(variance_data["Budget_Variance"].sum(), config.CURRENCY_PRECISION),
            "avg_monthly_variance": round(variance_data["Budget_Variance"].mean(), config.CURRENCY_PRECISION),
            "months_over_budget": len(variance_data[variance_data["Budget_Variance"] > 0.005]),
            "months_under_budget": len(variance_data[variance_data["Budget_Variance"] < -0.005]),
            "largest_overrun": {},
            "largest_underrun": {},
        }
        if not variance_data[variance_data["Budget_Variance"] > 0.005].empty:
            overrun_idx = variance_data["Budget_Variance"].idxmax()
            analysis["largest_overrun"] = {
                "month": variance_data.loc[overrun_idx, month_col],
                "amount": round(variance_data.loc[overrun_idx, "Budget_Variance"], config.CURRENCY_PRECISION),
            }
        if not variance_data[variance_data["Budget_Variance"] < -0.005].empty:
            underrun_idx = variance_data["Budget_Variance"].idxmin()
            analysis["largest_underrun"] = {
                "month": variance_data.loc[underrun_idx, month_col],
                "amount": round(variance_data.loc[underrun_idx, "Budget_Variance"], config.CURRENCY_PRECISION),
            }
        logger_instance.info(f"Rent budget variance analysis: {analysis}")
    else:
        analysis = {"message": "No non-NaN budget variance data to analyze."}
        logger_instance.info(analysis["message"])
    return analysis

def perform_advanced_analytics(
    master_ledger: pd.DataFrame, 
    processed_rent_df: pd.DataFrame, # Pass processed_rent_df for its budget info
    config: AnalysisConfig,
    logger_instance: logging.Logger = logger
) -> Dict[str, Any]:
    logger_instance.info("Running advanced analytics...")
    analytics: Dict[str, Any] = {}
    if master_ledger.empty or master_ledger["Date"].isna().all():
        logger_instance.warning("Master ledger is empty or has no valid dates for advanced analytics.")
        return {"error": "No data for advanced analytics"}

    master_ledger["Date"] = pd.to_datetime(master_ledger["Date"], errors="coerce")
    valid_dates_ledger = master_ledger.dropna(subset=["Date"]).copy() # Use .copy()
    if valid_dates_ledger.empty:
        logger_instance.warning("Master ledger has no valid dates after coercion for advanced analytics.")
        return {"error": "No valid dates for advanced analytics"}

    shared_ledger = valid_dates_ledger[valid_dates_ledger["IsShared"] == True].copy() # Use .copy()
    if not shared_ledger.empty:
        if "Payer" not in shared_ledger.columns: shared_ledger["Payer"] = "Unknown"
        monthly_cash_flow = (
            shared_ledger.groupby([pd.Grouper(key="Date", freq="ME"), "Payer"])
            ["AllowedAmount"].sum().unstack(fill_value=0).round(config.CURRENCY_PRECISION)
        )
        analytics["monthly_payments_by_payer_for_shared_items"] = monthly_cash_flow.to_dict("index")
    else:
        analytics["monthly_payments_by_payer_for_shared_items"] = {}

    liquidity_issues = []
    if "RunningBalance" in valid_dates_ledger.columns and "TransactionID" in valid_dates_ledger.columns:
        high_balance_transactions = valid_dates_ledger[
            valid_dates_ledger["RunningBalance"].abs() > config.LIQUIDITY_STRAIN_THRESHOLD
        ]
        for idx, row in high_balance_transactions.iterrows():
            liquidity_issues.append({
                "date": row["Date"].strftime("%Y-%m-%d") if pd.notna(row["Date"]) else "N/A",
                "running_balance": round(row["RunningBalance"], config.CURRENCY_PRECISION),
                "transaction_id": row["TransactionID"],
                "description": row.get("Description", "N/A"),
            })
    analytics["potential_liquidity_strain_points"] = liquidity_issues

    expense_only_df = valid_dates_ledger[
        (valid_dates_ledger["TransactionType"] == "EXPENSE") & (valid_dates_ledger["IsShared"] == True)
    ].copy()
    if not expense_only_df.empty and "Merchant" in expense_only_df.columns:
        expense_only_df["Category"] = expense_only_df["Merchant"].apply(
            lambda m: _categorize_merchant(m, config.DEFAULT_MERCHANT_CATEGORIES if hasattr(config, 'DEFAULT_MERCHANT_CATEGORIES') else None)
        )
        category_summary = (
            expense_only_df.groupby("Category")["AllowedAmount"]
            .agg(["sum", "count", "mean"]).round(config.CURRENCY_PRECISION)
        )
        if not category_summary.empty:
            category_totals = category_summary["sum"].sort_values(ascending=False)
            pareto_cumsum_pct = ((category_totals.cumsum() / category_totals.sum() * 100) if category_totals.sum() != 0 else pd.Series(dtype=float))
            pareto_80_categories = pareto_cumsum_pct[pareto_cumsum_pct <= 80].index.tolist() if not pareto_cumsum_pct.empty else []
            analytics["expense_category_analysis"] = {
                "summary_table": category_summary.reset_index().to_dict("records"),
                "pareto_80_categories_list": pareto_80_categories,
                "pareto_80_amount_sum": round(category_totals.loc[pareto_80_categories].sum(), config.CURRENCY_PRECISION) if pareto_80_categories else 0.0,
            }
    else:
        analytics["expense_category_analysis"] = {"message": "No shared expenses with merchant data for category analysis."}

    if not shared_ledger.empty and "AllowedAmount" in shared_ledger.columns:
        monthly_shared_spending = shared_ledger.resample("ME", on="Date")["AllowedAmount"].sum()
        if len(monthly_shared_spending) >= 3:
            x = np.arange(len(monthly_shared_spending))
            y = monthly_shared_spending.values
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
            analytics["monthly_shared_spending_trend"] = {
                "slope_per_month": round(slope, config.CURRENCY_PRECISION),
                "r_squared": round(r_value**2, 4) if pd.notna(r_value) else 0.0,
                "p_value": round(p_value, 4) if pd.notna(p_value) else 1.0,
                "trend_significant": (p_value < 0.05) if pd.notna(p_value) else False,
                "monthly_values": {d.strftime("%Y-%m"): round(val, config.CURRENCY_PRECISION) for d, val in monthly_shared_spending.items()},
            }
            if not monthly_shared_spending.index.empty and pd.notna(slope) and pd.notna(intercept): # Ensure slope/intercept are valid
                future_x = np.arange(len(monthly_shared_spending), len(monthly_shared_spending) + 3)
                forecast_values = slope * future_x + intercept
                forecast_start_date = monthly_shared_spending.index.max() + pd.DateOffset(months=1)
                forecast_dates = pd.date_range(start=forecast_start_date, periods=3, freq="ME")
                analytics["monthly_shared_spending_forecast"] = dict(zip([d.strftime("%Y-%m") for d in forecast_dates], np.round(forecast_values, config.CURRENCY_PRECISION)))
            else:
                analytics["monthly_shared_spending_forecast"] = {"message": "Not enough data or invalid trend for forecast."}
        else:
            analytics["monthly_shared_spending_trend"] = {"message": "Not enough monthly data points (need at least 3) for trend."}
            analytics["monthly_shared_spending_forecast"] = {"message": "Not enough data for forecast."}
    else:
        analytics["monthly_shared_spending_trend"] = {"message": "No shared spending data for trend."}
        analytics["monthly_shared_spending_forecast"] = {"message": "No data for forecast."}


    if "RunningBalance" in valid_dates_ledger.columns:
        month_end_balances = valid_dates_ledger.resample("ME", on="Date")["RunningBalance"].last()
        if not month_end_balances.empty:
            analytics["month_end_running_balance_stats"] = {
                "mean": round(month_end_balances.mean(), config.CURRENCY_PRECISION),
                "std_dev": round(month_end_balances.std(), config.CURRENCY_PRECISION),
                "min": round(month_end_balances.min(), config.CURRENCY_PRECISION),
                "max": round(month_end_balances.max(), config.CURRENCY_PRECISION),
                "median": round(month_end_balances.median(), config.CURRENCY_PRECISION),
            }
        else: analytics["month_end_running_balance_stats"] = {"message": "No data for running balance stats."}
    else: analytics["month_end_running_balance_stats"] = {"message": "RunningBalance column not available."}

    # Rent Budget Analysis (using processed_rent_df which has budget columns)
    if not processed_rent_df.empty:
         analytics["rent_budget_analysis"] = _analyze_rent_budget_variance(processed_rent_df, config, logger_instance)
    else:
        analytics["rent_budget_analysis"] = {"message": "Processed rent data is empty, skipping budget variance analysis."}


    # Calculate and store data quality score
    data_quality_score = _calculate_data_quality_score(master_ledger, logger_instance)
    analytics["data_quality_score"] = data_quality_score
    
    logger_instance.info("Advanced analytics completed.")
    return analytics

def _calculate_data_quality_score(master_ledger: pd.DataFrame, logger_instance: logging.Logger = logger) -> float:
    if master_ledger.empty or "DataQualityFlag" not in master_ledger.columns:
        return 0.0
    clean_rows = (master_ledger["DataQualityFlag"] == DataQualityFlag.CLEAN.value).sum()
    total_rows = len(master_ledger)
    score = (clean_rows / total_rows * 100) if total_rows > 0 else 0.0
    logger_instance.info(f"Data Quality Score: {score:.2f}% ({clean_rows} clean rows out of {total_rows})")
    return score

def _summarize_data_quality_issues(master_ledger: pd.DataFrame) -> Dict[str, int]:
    if master_ledger.empty or "DataQualityFlag" not in master_ledger.columns:
        return {"No data quality flags to summarize.": 0}
    flag_counts: Dict[str, int] = {}
    for flags_str_per_row in master_ledger["DataQualityFlag"].dropna():
        if flags_str_per_row != DataQualityFlag.CLEAN.value:
            individual_flags_in_row = flags_str_per_row.split(",")
            for flag in individual_flags_in_row:
                if flag and flag != DataQualityFlag.CLEAN.value:
                    flag_counts[flag] = flag_counts.get(flag, 0) + 1
    return flag_counts if flag_counts else {"All Clear": len(master_ledger)}


def comprehensive_risk_assessment(
    master_ledger: pd.DataFrame, 
    analytics_results: Dict[str, Any],
    validation_summary: Dict[str, Any], # Pass validation_summary from main orchestrator
    config: AnalysisConfig,
    logger_instance: logging.Logger = logger
) -> Dict[str, Any]:
    logger_instance.info("Performing comprehensive risk assessment...")
    risks: Dict[str, Any] = {"overall_risk_level": "LOW", "details": []}
    if master_ledger.empty:
        risks["details"].append({"risk_type": "Data Availability", "assessment": "No data to assess risks.", "level": "HIGH"})
        risks["overall_risk_level"] = "HIGH"
        return risks

    dq_score = _calculate_data_quality_score(master_ledger, logger_instance) # Use helper
    if dq_score < config.DATA_QUALITY_THRESHOLD * 100:
        level = "HIGH" if dq_score < 70 else "MEDIUM"
        risks["details"].append({
            "risk_type": "Data Quality",
            "assessment": f"Data quality score ({dq_score:.1f}%) is below threshold ({config.DATA_QUALITY_THRESHOLD*100:.1f}%). Review issues.",
            "level": level,
        })

    if "potential_liquidity_strain_points" in analytics_results and analytics_results["potential_liquidity_strain_points"]:
        strain_count = len(analytics_results["potential_liquidity_strain_points"])
        risks["details"].append({
            "risk_type": "Liquidity Strain",
            "assessment": f"{strain_count} instance(s) where running balance exceeded ${config.LIQUIDITY_STRAIN_THRESHOLD:,.0f}. Regular settlements advised.",
            "level": "HIGH" if strain_count > 3 else "MEDIUM" if strain_count > 0 else "LOW", # Adjusted severity
        })

    trend_info = analytics_results.get("monthly_shared_spending_trend", {})
    if trend_info.get("slope_per_month", 0) > 100 and trend_info.get("trend_significant", False):
        risks["details"].append({
            "risk_type": "Spending Trend",
            "assessment": f"Shared spending shows a significant increasing trend of ${trend_info['slope_per_month']:.2f}/month. Monitor habits.",
            "level": "MEDIUM",
        })

    rent_budget_analysis = analytics_results.get("rent_budget_analysis", {})
    if "avg_monthly_variance" in rent_budget_analysis and abs(rent_budget_analysis.get("avg_monthly_variance", 0)) > config.RENT_BASELINE * 0.05: # e.g. 5% of baseline
        risks["details"].append({
            "risk_type": "Rent Budget Adherence",
            "assessment": f"Average monthly rent variance is ${rent_budget_analysis['avg_monthly_variance']:,.2f}. Largest overrun: ${rent_budget_analysis.get('largest_overrun',{}).get('amount',0):,.2f} in {rent_budget_analysis.get('largest_overrun',{}).get('month','N/A')}.",
            "level": "MEDIUM",
        })

    if validation_summary.get("ledger_balance_match") not in ["Matched", "Skipped - No Ledger Data", None, True]: # True if matched
        risks["details"].append({
            "risk_type": "Ledger Balance Mismatch",
            "assessment": f"Calculated running balance does not match transaction ledger's. Details: {validation_summary['ledger_balance_match']}",
            "level": "HIGH",
        })
    
    if not validation_summary.get("reconciliation_match_strict", True):
         risks["details"].append({
            "risk_type": "Triple Reconciliation Failure",
            "assessment": "Triple reconciliation methods show discrepancies. Review calculations and data immediately.",
            "level": "HIGH",
        })


    high_risk_count = sum(1 for r in risks["details"] if r.get("level") == "HIGH")
    medium_risk_count = sum(1 for r in risks["details"] if r.get("level") == "MEDIUM")

    if high_risk_count > 0: risks["overall_risk_level"] = "HIGH"
    elif medium_risk_count > 0: risks["overall_risk_level"] = "MEDIUM"

    if not risks["details"]:
        risks["details"].append({"risk_type": "General", "assessment": "No major specific risks identified.", "level": "LOW"})

    logger_instance.info(f"Risk assessment completed. Overall level: {risks['overall_risk_level']}")
    return risks
