from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go

# Assuming analytics.py for _categorize_merchant if it's not passed in
# For P0, let's assume _categorize_merchant is available or passed if needed by a viz function.
# Best practice would be to pass any needed categorization logic or pre-categorized data.
from .analytics import _categorize_merchant

# import plotly.io as pio # Not directly used in these functions, but good for theme setting if done here
# Assuming config.py is accessible for TABLEAU_COLORBLIND_10 and AnalysisConfig
from .config import TABLEAU_COLORBLIND_10, AnalysisConfig

logger = logging.getLogger(__name__)

def build_design_theme(logger_instance: logging.Logger = logger):
    """
    Configure consistent design theme for all visualizations.
    Sets Matplotlib rcParams and returns Plotly template.
    """
    logger_instance.info("Building design theme for visualizations...")
    # Matplotlib configuration - use sans-serif fallback to prevent font warnings
    import matplotlib
    matplotlib.rcParams["font.family"] = "sans-serif"
    
    plt.rcParams.update({
        "font.family": "sans-serif", "font.size": 10,
        "font.sans-serif": ["DejaVu Sans", "Arial", "Liberation Sans"],
        "axes.titlesize": 12, "axes.labelsize": 10,
        "axes.prop_cycle": plt.cycler("color", TABLEAU_COLORBLIND_10),
        "axes.grid": True, "grid.linestyle": "--", "grid.alpha": 0.25,
        "axes.spines.top": False, "axes.spines.right": False,
        "figure.dpi": 100, "savefig.dpi": 300,
        "figure.facecolor": "white", "axes.facecolor": "white",
    })

    # Plotly template
    plotly_template = go.layout.Template()
    plotly_template.layout = go.Layout(
        font=dict(family="Inter, Arial, sans-serif", size=12, color="#333333"),
        title_font=dict(family="Montserrat, Arial Black, sans-serif", size=16),
        colorway=TABLEAU_COLORBLIND_10,
        plot_bgcolor="white", paper_bgcolor="white",
        hovermode="x unified",
        hoverlabel=dict(bgcolor="white", font_size=12, font_family="Inter"),
    )
    return plotly_template

# Visualization Builder Methods
# Each function will take necessary data (e.g., a DataFrame), config, output_dir, and optionally a theme.

def build_running_balance_timeline(
    ledger_df: pd.DataFrame, 
    config: AnalysisConfig, 
    output_dir: Path,
    logger_instance: logging.Logger = logger
) -> tuple[Path, str]:
    logger_instance.info("Building running balance timeline visualization...")
    ledger_df = ledger_df.dropna(subset=["Date", "RunningBalance"])
    if ledger_df.empty:
        logger_instance.warning("No data for running balance timeline.")
        # Consider creating a placeholder "no data" image if required by downstream processes
        return output_dir / "placeholder_no_data.png", "No data for running balance timeline."

    fig, ax = plt.subplots(figsize=(12, 6))
    ledger_df.plot(x="Date", y="RunningBalance", ax=ax, legend=None, color=TABLEAU_COLORBLIND_10[0])

    min_bal, max_bal = ledger_df["RunningBalance"].min(), ledger_df["RunningBalance"].max()
    if pd.notna(min_bal) and pd.notna(max_bal):
        ax.axhspan(-config.LIQUIDITY_STRAIN_THRESHOLD, config.LIQUIDITY_STRAIN_THRESHOLD, alpha=0.05, color="green", label="Normal Range")
        ax.axhspan(config.LIQUIDITY_STRAIN_THRESHOLD, max_bal + 1000, alpha=0.15, color="red", label="Ryan Liquidity Strain Potential")
        ax.axhspan(min_bal - 1000, -config.LIQUIDITY_STRAIN_THRESHOLD, alpha=0.15, color="orange", label="Jordyn Liquidity Strain Potential")
    
    ax.axhline(0, color="grey", linestyle="--", linewidth=0.8, alpha=0.5)

    if "BalanceImpact" in ledger_df.columns:
        top5 = ledger_df.iloc[ledger_df["BalanceImpact"].abs().nlargest(5).index]
        for _, row in top5.iterrows():
            if pd.notna(row["Date"]) and pd.notna(row["RunningBalance"]):
                desc_short = (str(row.get("Description", ""))[:20] + "..." if len(str(row.get("Description", ""))) > 20 else str(row.get("Description", "")))
                ax.annotate(
                    f"{desc_short}\n${row['BalanceImpact']:,.0f}",
                    xy=(row["Date"], row["RunningBalance"]),
                    xytext=(0, 20 if row["BalanceImpact"] > 0 else -30), textcoords="offset points",
                    ha="center", fontsize=8, arrowprops=dict(arrowstyle="->", lw=0.5, color="black", alpha=0.5)
                )
    
    ax.set_title("Running Balance Over Time (Ryan owes Jordyn when > 0)", fontsize=14, fontweight="bold")
    ax.set_ylabel("Balance ($)")
    ax.set_xlabel("Date")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"${x:,.0f}"))
    ax.legend(loc="best", framealpha=0.9)
    plt.tight_layout()
    path = output_dir / "running_balance_timeline.png"
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    alt_text = f"Running balance timeline. Liquidity strain zones at ±${config.LIQUIDITY_STRAIN_THRESHOLD:,.0f}."
    logger_instance.info(f"Saved: {path}")
    return path, alt_text

def build_waterfall_category_impact(
    ledger_df: pd.DataFrame, 
    config: AnalysisConfig, # For _categorize_merchant if used
    output_dir: Path, 
    theme: go.layout.Template, # Pass plotly theme
    logger_instance: logging.Logger = logger
) -> tuple[Path, str]:
    logger_instance.info("Building waterfall category impact visualization...")
    if ledger_df.empty or "BalanceImpact" not in ledger_df.columns:
        logger_instance.warning("No data for waterfall chart.")
        return output_dir / "placeholder_no_data.html", "No data for waterfall chart."

    ledger_df_c = ledger_df.copy()
    ledger_df_c["MerchantCategory"] = ledger_df_c.apply(
        lambda row: str(row.get("TransactionType", "Other")) if str(row.get("TransactionType", "Other")) == "RENT" 
        else _categorize_merchant(row.get("Merchant", "Other"), config.DEFAULT_MERCHANT_CATEGORIES if hasattr(config, 'DEFAULT_MERCHANT_CATEGORIES') else None),
        axis=1
    )
    category_impacts = ledger_df_c.groupby("MerchantCategory")["BalanceImpact"].sum().sort_values(ascending=False)
    if category_impacts.empty:
        logger_instance.warning("No category impacts for waterfall.")
        return output_dir / "placeholder_no_data.html", "No category impacts for waterfall."

    x_labels = list(category_impacts.index)
    y_values = list(category_impacts.values)
    if x_labels:
        x_labels.append("Final Balance")
        y_values.append(ledger_df_c["BalanceImpact"].sum())

    fig = go.Figure(go.Waterfall(
        name="Balance Impact", orientation="v",
        measure=["relative"] * (len(x_labels) - 1) + ["total"] if x_labels else [],
        x=x_labels, textposition="outside", text=[f"${val:,.0f}" for val in y_values], y=y_values,
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        increasing={"marker": {"color": TABLEAU_COLORBLIND_10[1]}},
        decreasing={"marker": {"color": TABLEAU_COLORBLIND_10[0]}},
        totals={"marker": {"color": "#2E2E2E"}},
    ))
    fig.update_layout(title="Cumulative Balance Impact by Category", yaxis_title="Balance Impact ($)", template=theme, height=600, showlegend=False)
    path = output_dir / "waterfall_category_impact.html"
    fig.write_html(str(path))
    alt_text = f"Waterfall chart of balance impact by category. Final balance ${ledger_df_c['BalanceImpact'].sum():,.0f}."
    logger_instance.info(f"Saved: {path}")
    return path, alt_text

def build_monthly_shared_trend(
    analytics_results: dict[str, Any], # Expects pre-calculated trend data
    output_dir: Path,
    logger_instance: logging.Logger = logger
) -> tuple[Path, str]:
    logger_instance.info("Building monthly shared trend visualization...")
    trend_data = analytics_results.get("monthly_shared_spending_trend", {})
    monthly_values_dict = trend_data.get("monthly_values", {})
    if not monthly_values_dict:
        logger_instance.warning("No monthly trend data available for plot.")
        return output_dir / "placeholder_no_data.png", "No monthly trend data available."

    monthly_shared_series = pd.Series(monthly_values_dict).sort_index()
    if len(monthly_shared_series) < 3:
        logger_instance.warning("Insufficient data for trend plot (need at least 3 months).")
        return output_dir / "placeholder_no_data.png", "Insufficient data for trend plot."

    fig, ax = plt.subplots(figsize=(12, 7))
    x_labels = [d for d in monthly_shared_series.index]
    x_pos = np.arange(len(x_labels))
    ax.bar(x_pos, monthly_shared_series.values, color=TABLEAU_COLORBLIND_10[2], alpha=0.8)
    for i, val in enumerate(monthly_shared_series.values):
        ax.text(x_pos[i], val + 50, f"${val:,.0f}", ha="center", va="bottom", fontsize=9)

    slope = trend_data.get("slope_per_month", 0)
    p_value = trend_data.get("p_value", 1.0)
    if len(x_pos) >= 2 and pd.notna(slope): # Check if slope is valid
        # Recalculate intercept for plotting based on the series and given slope
        # intercept = y_mean - slope * x_mean
        y_mean = monthly_shared_series.values.mean()
        x_mean = x_pos.mean()
        intercept = y_mean - slope * x_mean # Use the slope from analytics
        regression_line = slope * x_pos + intercept
        ax.plot(x_pos, regression_line, color=TABLEAU_COLORBLIND_10[0], linewidth=2, label=f"Trend: ${slope:+.0f}/month (p={p_value:.3f})")

    ax.set_xticks(x_pos)
    ax.set_xticklabels(x_labels, rotation=45, ha="right")
    ax.set_xlabel("Month")
    ax.set_ylabel("Total Shared Spending ($)")
    ax.set_title(f'Monthly Shared Spending Trend (${slope:+.0f}/month, {"sig." if p_value < 0.05 else "not sig."})', fontsize=14, fontweight="bold")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"${x:,.0f}"))
    ax.legend()
    plt.tight_layout()
    path = output_dir / "monthly_shared_trend.png"
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    alt_text = f"Monthly shared spending trend: ${slope:+.0f}/month change."
    logger_instance.info(f"Saved: {path}")
    return path, alt_text

def build_payer_type_heatmap(
    ledger_df: pd.DataFrame, 
    output_dir: Path, 
    theme: go.layout.Template,
    logger_instance: logging.Logger = logger
) -> tuple[Path, str]:
    logger_instance.info("Building payer type heatmap visualization...")
    if ledger_df.empty or "AllowedAmount" not in ledger_df.columns or "Payer" not in ledger_df.columns or "TransactionType" not in ledger_df.columns:
        logger_instance.warning("No data for payer-type heatmap.")
        return output_dir / "placeholder_no_data.html", "No data for payer-type heatmap."

    shared_df = ledger_df[ledger_df["IsShared"] == True]
    if shared_df.empty:
        logger_instance.warning("No shared transactions for payer-type heatmap.")
        return output_dir / "placeholder_no_data.html", "No shared transactions for payer-type heatmap."

    pivot_data = shared_df.pivot_table(values="AllowedAmount", index="Payer", columns="TransactionType", aggfunc="sum", fill_value=0)
    if pivot_data.empty:
        logger_instance.warning("Pivot data empty for heatmap.")
        return output_dir / "placeholder_no_data.html", "Pivot data empty for heatmap."

    fig = go.Figure(data=go.Heatmap(
        z=pivot_data.values, x=pivot_data.columns, y=pivot_data.index, colorscale="Blues",
        text=[[f"${val:,.0f}" for val in row] for row in pivot_data.values], texttemplate="%{text}",
        textfont={"size":12}, hovertemplate="Payer: %{y}<br>Type: %{x}<br>Shared Amount: $%{z:,.0f}<extra></extra>"
    ))
    fig.update_layout(title="Shared Spending by Payer and Transaction Type", template=theme, height=400)
    path = output_dir / "payer_type_heatmap.html"
    fig.write_html(str(path))
    alt_text = f"Heatmap of shared spending by payer and transaction type. Total ${pivot_data.values.sum():,.0f}."
    logger_instance.info(f"Saved: {path}")
    return path, alt_text

def build_calendar_heatmaps(
    ledger_df: pd.DataFrame, 
    output_dir: Path,
    logger_instance: logging.Logger = logger
) -> dict[str, tuple[Path, str]]:
    logger_instance.info("Building calendar heatmaps...")
    calendar_paths = {}
    if ledger_df.empty or "Date" not in ledger_df.columns or "AllowedAmount" not in ledger_df.columns:
        logger_instance.warning("No data for calendar heatmaps.")
        return calendar_paths

    shared_only = ledger_df[(ledger_df["IsShared"] == True) & ledger_df["Date"].notna()].copy()
    if shared_only.empty:
        logger_instance.warning("No shared transactions with valid dates for calendar heatmaps.")
        return calendar_paths

    shared_only["YearMonth"] = shared_only["Date"].dt.to_period("M")
    for year_month_period in shared_only["YearMonth"].unique():
        year_month_str = str(year_month_period)
        month_data = shared_only[shared_only["YearMonth"] == year_month_period].copy()
        if month_data.empty: continue

        daily_spending = month_data.groupby(month_data["Date"].dt.date)["AllowedAmount"].sum()
        if daily_spending.empty: continue
        
        start_date = year_month_period.start_time
        end_date = year_month_period.end_time
        all_days_in_month = pd.Series(index=pd.date_range(start=start_date, end=end_date, freq="D"), dtype=float).fillna(0)
        daily_spending.index = pd.to_datetime(daily_spending.index)
        all_days_in_month = all_days_in_month.add(daily_spending, fill_value=0)

        fig, ax = plt.subplots(figsize=(12, 6))
        all_days_in_month.plot(kind="bar", ax=ax, color=TABLEAU_COLORBLIND_10[4])
        ax.set_title(f"Daily Shared Spending - {year_month_str}", fontsize=14, fontweight="bold")
        ax.set_ylabel("Shared Spending ($)")
        ax.set_xlabel("Day of Month")
        ax.xaxis.set_major_formatter(plt.FixedFormatter(all_days_in_month.index.strftime("%d")))
        plt.tight_layout()
        path = output_dir / f"calendar_heatmap_{year_month_str}.png"
        plt.savefig(path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        alt_text = f"Daily shared spending for {year_month_str}. Total ${all_days_in_month.sum():,.0f}."
        calendar_paths[year_month_str] = (path, alt_text)
        logger_instance.info(f"Saved calendar heatmap: {path}")
    return calendar_paths

def build_treemap_shared_spending(
    ledger_df: pd.DataFrame, 
    config: AnalysisConfig, # For _categorize_merchant
    output_dir: Path, 
    theme: go.layout.Template,
    logger_instance: logging.Logger = logger
) -> tuple[Path, str]:
    logger_instance.info("Building treemap of shared spending...")
    if ledger_df.empty or "AllowedAmount" not in ledger_df.columns:
        logger_instance.warning("No data for treemap.")
        return output_dir / "placeholder_no_data.html", "No data for treemap."

    shared_df = ledger_df[ledger_df["IsShared"] == True].copy()
    if shared_df.empty:
        logger_instance.warning("No shared transactions for treemap.")
        return output_dir / "placeholder_no_data.html", "No shared transactions for treemap."

    category_data = []
    rent_total = shared_df[shared_df["TransactionType"] == "RENT"]["AllowedAmount"].sum()
    if rent_total > 0: category_data.append({"Category": "RENT", "Amount": rent_total, "Parent": ""})

    expense_df = shared_df[shared_df["TransactionType"] == "EXPENSE"].copy()
    if not expense_df.empty and "Merchant" in expense_df.columns:
        expense_df["Category"] = expense_df["Merchant"].apply(
             lambda m: _categorize_merchant(m, config.DEFAULT_MERCHANT_CATEGORIES if hasattr(config, 'DEFAULT_MERCHANT_CATEGORIES') else None)
        )
        category_totals = expense_df.groupby("Category")["AllowedAmount"].sum()
        for cat, amount in category_totals.items():
            if amount > 0: category_data.append({"Category": cat, "Amount": amount, "Parent": "EXPENSES"})
        total_expenses = category_totals.sum()
        if total_expenses > 0: category_data.append({"Category": "EXPENSES", "Amount": total_expenses, "Parent": ""})

    if not category_data:
        logger_instance.warning("No categories for treemap after processing.")
        return output_dir / "placeholder_no_data.html", "No categories for treemap."

    labels = [item["Category"] for item in category_data]
    parents = [item["Parent"] for item in category_data]
    values = [item["Amount"] for item in category_data]
    total_overall_amount = sum(d["Amount"] for d in category_data if d["Parent"] == "")
    text = [f"${item['Amount']:,.0f}<br>{(item['Amount']/total_overall_amount*100 if total_overall_amount else 0):.1f}%" for item in category_data]

    fig = go.Figure(go.Treemap(
        labels=labels, parents=parents, values=values, text=text, textinfo="label+text",
        marker_colorscale="Blues", line=dict(width=1)
    ))
    fig.update_layout(title="Distribution of Shared Spending", template=theme, height=600, margin=dict(t=50, l=0, r=0, b=0))
    path = output_dir / "treemap_shared_spending.html"
    fig.write_html(str(path))
    alt_text = f"Treemap of shared spending. Total ${total_overall_amount:,.0f}."
    logger_instance.info(f"Saved: {path}")
    return path, alt_text

def build_anomaly_scatter(
    ledger_df: pd.DataFrame, 
    output_dir: Path,
    logger_instance: logging.Logger = logger
) -> tuple[Path, str]:
    logger_instance.info("Building anomaly scatter plot...")
    if ledger_df.empty or "AllowedAmount" not in ledger_df.columns or "BalanceImpact" not in ledger_df.columns:
        logger_instance.warning("No data for anomaly scatter plot.")
        return output_dir / "placeholder_no_data.png", "No data for anomaly scatter plot."

    plot_df = ledger_df.dropna(subset=["AllowedAmount", "BalanceImpact", "DataQualityFlag"])
    if plot_df.empty:
        logger_instance.warning("No valid data points for anomaly scatter plot.")
        return output_dir / "placeholder_no_data.png", "No valid data points for anomaly scatter plot."

    fig, ax = plt.subplots(figsize=(12, 8))
    unique_flags = plot_df["DataQualityFlag"].unique()
    flag_colors = {flag: TABLEAU_COLORBLIND_10[i % len(TABLEAU_COLORBLIND_10)] for i, flag in enumerate(unique_flags)}

    for flag_val in unique_flags:
        subset = plot_df[plot_df["DataQualityFlag"] == flag_val]
        ax.scatter(subset["AllowedAmount"], subset["BalanceImpact"], label=flag_val, alpha=0.6, s=50, color=flag_colors[flag_val])

    if not plot_df.empty and "BalanceImpact" in plot_df.columns:
        valid_impacts = plot_df["BalanceImpact"].abs().dropna()
        if len(valid_impacts) > 0: # Check if there are any non-NaN absolute impacts
            threshold_pct = 99
            # Ensure enough points for percentile calculation if valid_impacts is not empty
            if len(valid_impacts) > (100 / (100-threshold_pct)): # e.g. for 99th percentile, need > 100 points. Simplified: need some points.
                 threshold_value = np.percentile(valid_impacts, threshold_pct)
                 outliers = plot_df[plot_df["BalanceImpact"].abs() > threshold_value]
                 for _, row in outliers.iterrows():
                    desc_short = (str(row.get("Description", ""))[:15] + "..." if len(str(row.get("Description", ""))) > 15 else str(row.get("Description", "")))
                    ax.annotate(desc_short, xy=(row["AllowedAmount"], row["BalanceImpact"]), xytext=(5, 5), textcoords="offset points", fontsize=8, alpha=0.7)

    ax.axhline(0, color="grey", linestyle="--", alpha=0.5)
    ax.axvline(0, color="grey", linestyle="--", alpha=0.5)
    ax.set_xlabel("Allowed Amount ($)")
    ax.set_ylabel("Balance Impact ($)")
    ax.set_title("Transaction Anomaly Detection (colored by data quality flag)", fontsize=14, fontweight="bold")
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"${x:,.0f}"))
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"${x:,.0f}"))
    ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left", framealpha=0.9)
    plt.tight_layout()
    path = output_dir / "anomaly_scatter.png"
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    alt_text = "Anomaly scatter plot of transactions by Allowed Amount vs Balance Impact, colored by DataQualityFlag."
    logger_instance.info(f"Saved: {path}")
    return path, alt_text

def build_pareto_concentration(
    ledger_df: pd.DataFrame, 
    config: AnalysisConfig, # For _categorize_merchant
    output_dir: Path,
    logger_instance: logging.Logger = logger
) -> tuple[Path, str]:
    logger_instance.info("Building Pareto concentration chart...")
    if ledger_df.empty or "AllowedAmount" not in ledger_df.columns:
        logger_instance.warning("No data for Pareto chart.")
        return output_dir / "placeholder_no_data.png", "No data for Pareto chart."

    shared_only = ledger_df[ledger_df["IsShared"] == True].copy()
    if shared_only.empty:
        logger_instance.warning("No shared transactions for Pareto chart.")
        return output_dir / "placeholder_no_data.png", "No shared transactions for Pareto chart."

    shared_only["Category"] = shared_only.apply(
        lambda row: str(row.get("TransactionType", "Other")) if str(row.get("TransactionType", "Other")) == "RENT" 
        else _categorize_merchant(row.get("Merchant", "Other"), config.DEFAULT_MERCHANT_CATEGORIES if hasattr(config, 'DEFAULT_MERCHANT_CATEGORIES') else None),
        axis=1
    )
    category_totals = shared_only.groupby("Category")["AllowedAmount"].sum().sort_values(ascending=False)
    if category_totals.empty or category_totals.sum() == 0:
        logger_instance.warning("No category totals for Pareto chart.")
        return output_dir / "placeholder_no_data.png", "No category totals for Pareto."

    fig, ax1 = plt.subplots(figsize=(12, 7))
    x_pos = np.arange(len(category_totals))
    ax1.bar(x_pos, category_totals.values, color=TABLEAU_COLORBLIND_10[3], alpha=0.8)
    for i, val in enumerate(category_totals.values):
        ax1.text(x_pos[i], val + (category_totals.values.max()*0.02), f"${val:,.0f}", ha="center", va="bottom", fontsize=9, rotation=30)

    ax1.set_xlabel("Category")
    ax1.set_ylabel("Total Shared Amount ($)", color=TABLEAU_COLORBLIND_10[3])
    ax1.tick_params(axis="y", labelcolor=TABLEAU_COLORBLIND_10[3])
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(category_totals.index, rotation=45, ha="right")
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x,p: f"${x:,.0f}"))

    ax2 = ax1.twinx()
    cumulative_pct = category_totals.cumsum() / category_totals.sum() * 100
    ax2.plot(x_pos, cumulative_pct.values, color=TABLEAU_COLORBLIND_10[1], marker="o", lw=2, ms=6, label="Cumulative %")
    ax2.axhline(80, color="red", linestyle="--", alpha=0.7, label="80% Threshold")
    
    idx_80 = np.where(cumulative_pct.values >= 80)[0]
    if len(idx_80) > 0:
        x_80, y_80 = idx_80[0], cumulative_pct.values[idx_80[0]]
        ax2.plot(x_80, y_80, "ro", markersize=10)
        ax2.annotate(f"{x_80+1} cat.\nreach 80%", xy=(x_80,y_80), xytext=(x_80+0.5, y_80-10), arrowprops=dict(arrowstyle="->",color="red",lw=1))

    ax2.set_ylabel("Cumulative Percentage (%)", color=TABLEAU_COLORBLIND_10[1])
    ax2.tick_params(axis="y", labelcolor=TABLEAU_COLORBLIND_10[1])
    ax2.set_ylim(0, 105)
    ax1.set_title("Pareto Analysis of Shared Spending by Category", fontsize=14, fontweight="bold")
    ax2.legend(loc="center right")
    plt.tight_layout()
    path = output_dir / "pareto_concentration.png"
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    alt_text = f"Pareto chart of shared spending concentration by category. {idx_80[0]+1 if len(idx_80)>0 else 'N/A'} categories make up 80% of spending."
    logger_instance.info(f"Saved: {path}")
    return path, alt_text

def build_sankey_settlements(
    ledger_df: pd.DataFrame, 
    config: AnalysisConfig, 
    output_dir: Path, 
    theme: go.layout.Template,
    logger_instance: logging.Logger = logger
) -> tuple[Path, str]:
    logger_instance.info("Building Sankey diagram for settlements...")
    if ledger_df.empty:
        logger_instance.warning("No data for Sankey diagram.")
        return output_dir / "placeholder_no_data.html", "No data for Sankey diagram."

    shared_expenses = ledger_df[ledger_df["IsShared"] == True].copy()
    settlements = ledger_df[ledger_df["TransactionType"] == "SETTLEMENT"].copy()

    ryan_paid_shared = shared_expenses[shared_expenses["Payer"].str.lower() == "ryan"]["AllowedAmount"].sum()
    jordyn_paid_shared = shared_expenses[shared_expenses["Payer"].str.lower() == "jordyn"]["AllowedAmount"].sum()
    total_shared = ryan_paid_shared + jordyn_paid_shared
    
    # Using DEFAULT_SETTLEMENT_KEYWORDS from config module
    settlement_keywords = config.DEFAULT_SETTLEMENT_KEYWORDS if hasattr(config, 'DEFAULT_SETTLEMENT_KEYWORDS') else ["venmo", "zelle", "cash app", "paypal"]


    ryan_paid_jordyn_settle = settlements[
        (settlements["Payer"].str.lower() == "ryan") & 
        (settlements["Description"].str.contains(r"to\s+jordyn", case=False, regex=True, na=False) |
         settlements["Merchant"].str.lower().isin([f"{k} to jordyn" for k in settlement_keywords]))
    ]["ActualAmount"].sum()

    jordyn_paid_ryan_settle = settlements[
        (settlements["Payer"].str.lower() == "jordyn") & 
        (settlements["Description"].str.contains(r"to\s+ryan", case=False, regex=True, na=False) |
         settlements["Merchant"].str.lower().isin([f"{k} to ryan" for k in settlement_keywords]))
    ]["ActualAmount"].sum()

    simple_labels = ["Ryan", "Jordyn", "Shared Expenses Bucket"]
    simple_source, simple_target, simple_values, simple_link_labels = [], [], [], []
    node_colors = [TABLEAU_COLORBLIND_10[0], TABLEAU_COLORBLIND_10[1], TABLEAU_COLORBLIND_10[2]]
    link_colors_list = []

    if ryan_paid_shared > 0:
        simple_source.append(0); simple_target.append(2); simple_values.append(ryan_paid_shared)
        simple_link_labels.append(f"Ryan paid to Shared: ${ryan_paid_shared:,.0f}")
        link_colors_list.append("rgba(0,122,204,0.4)")
    if jordyn_paid_shared > 0:
        simple_source.append(1); simple_target.append(2); simple_values.append(jordyn_paid_shared)
        simple_link_labels.append(f"Jordyn paid to Shared: ${jordyn_paid_shared:,.0f}")
        link_colors_list.append("rgba(255,176,0,0.4)")
    if ryan_paid_jordyn_settle > 0:
        simple_source.append(0); simple_target.append(1); simple_values.append(ryan_paid_jordyn_settle)
        simple_link_labels.append(f"Ryan settled Jordyn: ${ryan_paid_jordyn_settle:,.0f}")
        link_colors_list.append("rgba(0,122,204,0.6)")
    if jordyn_paid_ryan_settle > 0:
        simple_source.append(1); simple_target.append(0); simple_values.append(jordyn_paid_ryan_settle)
        simple_link_labels.append(f"Jordyn settled Ryan: ${jordyn_paid_ryan_settle:,.0f}")
        link_colors_list.append("rgba(255,176,0,0.6)")

    if not simple_values:
        logger_instance.warning("No flow data for Sankey diagram.")
        return output_dir / "placeholder_no_data.html", "No flow data for Sankey diagram."

    fig = go.Figure(data=[go.Sankey(
        node=dict(pad=15, thickness=20, line=dict(color="black", width=0.5), label=simple_labels, color=node_colors),
        link=dict(source=simple_source, target=simple_target, value=simple_values, label=simple_link_labels, color=link_colors_list)
    )])
    fig.update_layout(title_text="Flow of Shared Expenses and Settlements", font_size=12, template=theme, height=500)
    path = output_dir / "sankey_settlements.html"
    fig.write_html(str(path))
    alt_text = f"Sankey diagram of expense and settlement flows. Total shared paid: ${total_shared:,.0f}."
    logger_instance.info(f"Saved: {path}")
    return path, alt_text

def build_data_quality_table_viz(
    ledger_df: pd.DataFrame, 
    output_dir: Path, 
    theme: go.layout.Template,
    logger_instance: logging.Logger = logger
) -> tuple[Path, str]:
    logger_instance.info("Building data quality table visualization...")
    if ledger_df.empty or "DataQualityFlag" not in ledger_df.columns:
        logger_instance.warning("No data for data quality table visualization.")
        return output_dir / "placeholder_no_data.html", "No data for data quality table visualization."

    flagged_rows = ledger_df[ledger_df["DataQualityFlag"] != DataQualityFlag.CLEAN.value].copy()
    high_impact_rows = pd.DataFrame()
    if "BalanceImpact" in ledger_df.columns and not ledger_df.empty:
        valid_impacts = ledger_df["BalanceImpact"].dropna()
        if not valid_impacts.empty and len(valid_impacts) > 10:
            threshold_98 = np.percentile(valid_impacts.abs(), 98)
            high_impact_rows = ledger_df[ledger_df["BalanceImpact"].abs() > threshold_98].copy()

    combined = pd.concat([flagged_rows, high_impact_rows]).drop_duplicates().reset_index(drop=True)
    if combined.empty:
        logger_instance.info("No data quality issues or high impact transactions found for table visualization.")
        return output_dir / "placeholder_no_data.html", "No data quality issues or high impact transactions found for table."

    display_cols = ["Date", "TransactionType", "Payer", "Description", "ActualAmount", "AllowedAmount", "BalanceImpact", "DataQualityFlag"]
    final_display_cols = [col for col in display_cols if col in combined.columns]
    display_df = combined[final_display_cols].copy()

    if "Date" in display_df.columns: display_df["Date"] = pd.to_datetime(display_df["Date"]).dt.strftime("%Y-%m-%d")
    for col in ["ActualAmount", "AllowedAmount", "BalanceImpact"]:
        if col in display_df.columns: display_df[col] = display_df[col].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "$0.00")

    fig = go.Figure(data=[go.Table(
        header=dict(values=list(display_df.columns), fill_color="#007ACC", font=dict(color="white",size=12), align="left"),
        cells=dict(values=[display_df[col] for col in display_df.columns], 
                   fill_color=[['#f0f0f0' if i%2==0 else 'white' for i in range(len(display_df))]], 
                   align="left", font_size=11)
    )])
    fig.update_layout(title=f"Data Quality Issues & High-Impact Transactions ({len(display_df)} rows)", template=theme, height=max(400, 30 * len(display_df) + 100)) # Dynamic height
    path = output_dir / "data_quality_table_viz.html"
    fig.write_html(str(path))
    alt_text = f"Table of {len(display_df)} transactions with data quality issues or high balance impact."
    logger_instance.info(f"Saved: {path}")
    return path, alt_text
