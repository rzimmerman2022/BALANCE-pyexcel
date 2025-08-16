#!/usr/bin/env python3
"""
Balance Verification Script - Diagnose and understand balance calculation issues

This script analyzes your expense sharing data to identify why balances aren't
calculating correctly. It provides detailed insights into:
- How many expenses are shared vs personal
- The impact of including/excluding personal expenses
- Settlement transaction detection
- The true balance between Ryan and Jordyn

Run this to establish a baseline and understand your data better.
"""

import warnings
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

warnings.filterwarnings("ignore")


def load_and_analyze_data(data_dir="data"):
    """
    Load all data files and perform comprehensive analysis to understand
    why balance calculations might be incorrect.
    """
    print("=" * 80)
    print("BALANCE VERIFICATION SCRIPT - Understanding Your Data")
    print("=" * 80)
    print(f"\nAnalyzing data in: {Path(data_dir).absolute()}")

    # Initialize results dictionary
    results = {
        "files_found": {},
        "data_quality": {},
        "balance_analysis": {},
        "recommendations": [],
    }

    # Step 1: Load Expense History
    print("\n" + "=" * 60)
    print("STEP 1: Loading and Analyzing Expense History")
    print("=" * 60)

    expense_file = find_file(data_dir, "Expense_History*.csv", "expenses.csv")
    if expense_file:
        expenses_df = load_expense_history(expense_file)
        results["files_found"]["expenses"] = str(expense_file)

        # Analyze expense data structure
        expense_analysis = analyze_expense_structure(expenses_df)
        results["data_quality"]["expenses"] = expense_analysis

        # Show key findings
        print_expense_insights(expenses_df, expense_analysis)
    else:
        print("ERROR: No expense history file found!")
        return results

    # Step 2: Load Rent Allocation
    print("\n" + "=" * 60)
    print("STEP 2: Loading and Analyzing Rent Allocation")
    print("=" * 60)

    rent_file = find_file(data_dir, "Rent_Allocation*.csv", "rent.csv")
    if rent_file:
        rent_df = load_rent_allocation(rent_file)
        results["files_found"]["rent"] = str(rent_file)

        # Analyze rent data
        rent_analysis = analyze_rent_structure(rent_df)
        results["data_quality"]["rent"] = rent_analysis

        print_rent_insights(rent_df, rent_analysis)
    else:
        print("WARNING: No rent allocation file found!")
        rent_df = pd.DataFrame()

    # Step 3: The Critical Analysis - Shared vs Personal Expenses
    print("\n" + "=" * 60)
    print("STEP 3: THE CRITICAL ISSUE - Shared vs Personal Expenses")
    print("=" * 60)

    balance_comparison = analyze_shared_vs_all_expenses(expenses_df)
    results["balance_analysis"] = balance_comparison

    # Step 4: Settlement Detection
    print("\n" + "=" * 60)
    print("STEP 4: Settlement Transaction Detection")
    print("=" * 60)

    settlements = detect_settlements(expenses_df)
    results["balance_analysis"]["settlements"] = settlements

    # Step 5: Complete Balance Calculation
    print("\n" + "=" * 60)
    print("STEP 5: Complete Balance Calculation")
    print("=" * 60)

    final_balance = calculate_correct_balance(expenses_df, rent_df)
    results["balance_analysis"]["final"] = final_balance

    # Step 6: Visualizations
    print("\n" + "=" * 60)
    print("STEP 6: Creating Visualizations")
    print("=" * 60)

    create_analysis_visualizations(expenses_df, rent_df, balance_comparison)

    # Step 7: Generate Recommendations
    print("\n" + "=" * 60)
    print("STEP 7: Recommendations")
    print("=" * 60)

    recommendations = generate_recommendations(results)
    results["recommendations"] = recommendations

    for i, rec in enumerate(recommendations, 1):
        print(f"\n{i}. {rec}")

    # Save detailed report
    save_analysis_report(results)

    return results


def find_file(data_dir, pattern1, pattern2):
    """Find a file matching either pattern in the data directory."""
    data_path = Path(data_dir)

    # Try first pattern
    files = list(data_path.glob(pattern1))
    if files:
        return files[0]

    # Try second pattern
    files = list(data_path.glob(pattern2))
    if files:
        return files[0]

    return None


def load_expense_history(file_path):
    """Load and clean expense history data."""
    print(f"\nLoading: {file_path}")
    df = pd.read_csv(file_path)

    # Clean column names (remove extra spaces)
    df.columns = df.columns.str.strip()

    # Clean amount columns - convert to numeric
    for col in ["Actual Amount", "Allowed Amount"]:
        if col in df.columns:
            # Remove $ and commas, convert to float
            df[col] = (
                df[col]
                .astype(str)
                .str.replace("$", "")
                .str.replace(",", "")
                .str.strip()
            )
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Convert date column
    if "Date of Purchase" in df.columns:
        df["Date"] = pd.to_datetime(df["Date of Purchase"], errors="coerce")

    print(f"Loaded {len(df)} expense records")
    return df


def load_rent_allocation(file_path):
    """Load and clean rent allocation data."""
    print(f"\nLoading: {file_path}")
    df = pd.read_csv(file_path)

    # Clean column names
    df.columns = df.columns.str.strip()

    # Clean amount columns
    amount_cols = ["Gross Total", "Ryan's Rent (43%)", "Jordyn's Rent (57%)"]
    for col in amount_cols:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace("$", "")
                .str.replace(",", "")
                .str.strip()
            )
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    print(f"Loaded {len(df)} rent records")
    return df


def analyze_expense_structure(df):
    """Analyze the structure and quality of expense data."""
    analysis = {}

    # Basic counts
    analysis["total_records"] = len(df)
    analysis["date_range"] = (
        f"{df['Date'].min()} to {df['Date'].max()}"
        if "Date" in df.columns
        else "Unknown"
    )

    # Payer breakdown
    if "Name" in df.columns:
        payer_counts = df["Name"].value_counts()
        analysis["payers"] = payer_counts.to_dict()
        print("\nPayer breakdown:")
        for payer, count in payer_counts.items():
            print(f"  {payer}: {count} transactions")

    # Amount analysis
    if "Actual Amount" in df.columns and "Allowed Amount" in df.columns:
        analysis["total_actual"] = df["Actual Amount"].sum()
        analysis["total_allowed"] = df["Allowed Amount"].sum()

        # Key insight: Personal vs Shared
        shared_mask = df["Allowed Amount"] > 0
        analysis["shared_count"] = shared_mask.sum()
        analysis["personal_count"] = (~shared_mask).sum()
        analysis["shared_total"] = df.loc[shared_mask, "Allowed Amount"].sum()
        analysis["personal_total"] = df.loc[~shared_mask, "Actual Amount"].sum()

        print("\nExpense breakdown:")
        print(f"  Total transactions: {len(df)}")
        print(
            f"  Shared expenses: {analysis['shared_count']} (${analysis['shared_total']:,.2f})"
        )
        print(
            f"  Personal expenses: {analysis['personal_count']} (${analysis['personal_total']:,.2f})"
        )

    return analysis


def print_expense_insights(df, analysis):
    """Print key insights about expense data."""
    print("\n" + "-" * 40)
    print("KEY INSIGHTS - Expense History")
    print("-" * 40)

    # Insight 1: Personal expense impact
    if "personal_total" in analysis and "shared_total" in analysis:
        personal_pct = (
            analysis["personal_total"]
            / (analysis["personal_total"] + analysis["shared_total"])
            * 100
        )
        print("\n1. Personal Expense Impact:")
        print(f"   {personal_pct:.1f}% of total spending is personal (not shared)")
        print(
            f"   This represents ${analysis['personal_total']:,.2f} that should NOT affect balances"
        )

    # Insight 2: Payer imbalance
    if "Name" in df.columns and "Actual Amount" in df.columns:
        ryan_total = df[df["Name"] == "Ryan"]["Actual Amount"].sum()
        jordyn_total = df[df["Name"] == "Jordyn"]["Actual Amount"].sum()
        print("\n2. Who Pays More Often:")
        print(f"   Ryan has paid: ${ryan_total:,.2f}")
        print(f"   Jordyn has paid: ${jordyn_total:,.2f}")
        print(f"   Difference: ${abs(ryan_total - jordyn_total):,.2f}")


def analyze_rent_structure(df):
    """Analyze rent allocation data."""
    analysis = {}

    analysis["total_months"] = len(df)
    if "Gross Total" in df.columns:
        analysis["average_rent"] = df["Gross Total"].mean()
        analysis["total_rent"] = df["Gross Total"].sum()

        print("\nRent summary:")
        print(f"  Months tracked: {analysis['total_months']}")
        print(f"  Average monthly rent: ${analysis['average_rent']:,.2f}")
        print(f"  Total rent paid: ${analysis['total_rent']:,.2f}")

    if "Ryan's Rent (43%)" in df.columns:
        analysis["ryan_total_rent"] = df["Ryan's Rent (43%)"].sum()
        print(f"  Ryan's total rent obligation: ${analysis['ryan_total_rent']:,.2f}")

    return analysis


def print_rent_insights(df, analysis):
    """Print insights about rent data."""
    print("\n" + "-" * 40)
    print("KEY INSIGHTS - Rent Allocation")
    print("-" * 40)

    if "ryan_total_rent" in analysis:
        print(f"\n1. Rent adds ${analysis['ryan_total_rent']:,.2f} to what Ryan owes")
        print("   (Assuming Jordyn pays the landlord each month)")


def analyze_shared_vs_all_expenses(df):
    """
    This is the CRITICAL analysis that shows why your balance is wrong.
    Compare what happens when you count ALL expenses vs only SHARED expenses.
    """
    results = {}

    print("\nThis analysis shows the impact of counting ALL expenses vs only SHARED:")
    print("-" * 60)

    # Method 1: WRONG - Count everything
    print("\nMETHOD 1 (WRONG): Counting ALL transactions")

    if "Name" in df.columns and "Actual Amount" in df.columns:
        all_ryan = df[df["Name"] == "Ryan"]["Actual Amount"].sum()
        all_jordyn = df[df["Name"] == "Jordyn"]["Actual Amount"].sum()
        all_total = all_ryan + all_jordyn

        results["wrong_method"] = {
            "ryan_paid": all_ryan,
            "jordyn_paid": all_jordyn,
            "total": all_total,
        }

        print(f"  Ryan paid (all transactions): ${all_ryan:,.2f}")
        print(f"  Jordyn paid (all transactions): ${all_jordyn:,.2f}")
        print(f"  Total: ${all_total:,.2f}")

        # Calculate "balance" using wrong method
        ryan_share_wrong = all_total * 0.43
        jordyn_share_wrong = all_total * 0.57
        ryan_balance_wrong = ryan_share_wrong - all_ryan
        jordyn_balance_wrong = jordyn_share_wrong - all_jordyn

        print("\n  Using 43/57 split on TOTAL spending:")
        print(f"  Ryan should pay: ${ryan_share_wrong:,.2f}")
        print(f"  Ryan balance: ${ryan_balance_wrong:,.2f}")
        print(f"  Jordyn should pay: ${jordyn_share_wrong:,.2f}")
        print(f"  Jordyn balance: ${jordyn_balance_wrong:,.2f}")
        print(
            f"  Sum of balances: ${ryan_balance_wrong + jordyn_balance_wrong:,.2f} (SHOULD BE ZERO!)"
        )

    # Method 2: CORRECT - Count only shared
    print("\n\nMETHOD 2 (CORRECT): Counting only SHARED expenses")

    if "Allowed Amount" in df.columns:
        shared_only = df[df["Allowed Amount"] > 0]

        shared_ryan = shared_only[shared_only["Name"] == "Ryan"]["Allowed Amount"].sum()
        shared_jordyn = shared_only[shared_only["Name"] == "Jordyn"][
            "Allowed Amount"
        ].sum()
        shared_total = shared_ryan + shared_jordyn

        results["correct_method"] = {
            "ryan_paid": shared_ryan,
            "jordyn_paid": shared_jordyn,
            "total": shared_total,
        }

        print(f"  Ryan paid (shared only): ${shared_ryan:,.2f}")
        print(f"  Jordyn paid (shared only): ${shared_jordyn:,.2f}")
        print(f"  Total shared: ${shared_total:,.2f}")

        # Calculate balance using correct method
        ryan_share_correct = shared_total * 0.43
        jordyn_share_correct = shared_total * 0.57
        ryan_balance_correct = ryan_share_correct - shared_ryan
        jordyn_balance_correct = jordyn_share_correct - shared_jordyn

        print("\n  Using 43/57 split on SHARED expenses only:")
        print(f"  Ryan should pay: ${ryan_share_correct:,.2f}")
        print(f"  Ryan balance: ${ryan_balance_correct:,.2f}")
        print(f"  Jordyn should pay: ${jordyn_share_correct:,.2f}")
        print(f"  Jordyn balance: ${jordyn_balance_correct:,.2f}")
        print(
            f"  Sum of balances: ${ryan_balance_correct + jordyn_balance_correct:,.2f} (PROPERLY ZERO!)"
        )

        # Show the difference
        print("\n\nTHE CRITICAL DIFFERENCE:")
        print(f"  Wrong method total: ${all_total:,.2f}")
        print(f"  Correct method total: ${shared_total:,.2f}")
        print(f"  Difference (personal expenses): ${all_total - shared_total:,.2f}")
        print(
            f"\n  This ${all_total - shared_total:,.2f} of personal expenses is why your balance is wrong!"
        )

        results["difference"] = all_total - shared_total
        results["correct_balance"] = {
            "ryan": ryan_balance_correct,
            "jordyn": jordyn_balance_correct,
        }

    return results


def detect_settlements(df):
    """Detect potential settlement transactions."""
    settlements = []

    settlement_keywords = [
        "venmo",
        "zelle",
        "paypal",
        "cash app",
        "settlement",
        "payment to",
        "payment from",
    ]

    for col in ["Merchant", "Description"]:
        if col in df.columns:
            for keyword in settlement_keywords:
                mask = df[col].str.contains(keyword, case=False, na=False)
                if mask.any():
                    settlement_rows = df[mask]
                    for _, row in settlement_rows.iterrows():
                        settlements.append(
                            {
                                "date": row.get("Date", "Unknown"),
                                "payer": row.get("Name", "Unknown"),
                                "amount": row.get("Actual Amount", 0),
                                "description": row.get(
                                    "Description", row.get("Merchant", "Unknown")
                                ),
                                "allowed": row.get("Allowed Amount", 0),
                            }
                        )

    # Also check for transactions where description mentions the other person
    if "Description" in df.columns:
        for name in ["Ryan", "Jordyn"]:
            mask = df["Description"].str.contains(name, case=False, na=False)
            if mask.any():
                potential_settlements = df[mask]
                for _, row in potential_settlements.iterrows():
                    # Only add if not already in settlements
                    if not any(
                        s["date"] == row.get("Date")
                        and s["amount"] == row.get("Actual Amount", 0)
                        for s in settlements
                    ):
                        settlements.append(
                            {
                                "date": row.get("Date", "Unknown"),
                                "payer": row.get("Name", "Unknown"),
                                "amount": row.get("Actual Amount", 0),
                                "description": row.get("Description", "Unknown"),
                                "allowed": row.get("Allowed Amount", 0),
                            }
                        )

    print(f"\nFound {len(settlements)} potential settlement transactions:")
    for s in settlements[:5]:  # Show first 5
        print(
            f"  {s['date']}: {s['payer']} - ${s['amount']:.2f} - {s['description'][:50]}"
        )

    if len(settlements) > 5:
        print(f"  ... and {len(settlements) - 5} more")

    return settlements


def calculate_correct_balance(expenses_df, rent_df):
    """Calculate the correct balance using only shared expenses."""
    balance = {
        "expense_balance": {"ryan": 0, "jordyn": 0},
        "rent_balance": {"ryan": 0, "jordyn": 0},
        "final_balance": {"ryan": 0, "jordyn": 0},
    }

    # Calculate expense balance (shared only)
    if not expenses_df.empty and "Allowed Amount" in expenses_df.columns:
        shared = expenses_df[expenses_df["Allowed Amount"] > 0]
        total_shared = shared["Allowed Amount"].sum()

        ryan_paid = shared[shared["Name"] == "Ryan"]["Allowed Amount"].sum()
        jordyn_paid = shared[shared["Name"] == "Jordyn"]["Allowed Amount"].sum()

        ryan_should_pay = total_shared * 0.43
        jordyn_should_pay = total_shared * 0.57

        balance["expense_balance"]["ryan"] = ryan_should_pay - ryan_paid
        balance["expense_balance"]["jordyn"] = jordyn_should_pay - jordyn_paid

    # Add rent balance
    if not rent_df.empty and "Ryan's Rent (43%)" in rent_df.columns:
        ryan_rent_total = rent_df["Ryan's Rent (43%)"].sum()
        balance["rent_balance"]["ryan"] = ryan_rent_total  # Ryan owes this
        balance["rent_balance"]["jordyn"] = -ryan_rent_total  # Jordyn is owed this

    # Calculate final balance
    balance["final_balance"]["ryan"] = (
        balance["expense_balance"]["ryan"] + balance["rent_balance"]["ryan"]
    )
    balance["final_balance"]["jordyn"] = (
        balance["expense_balance"]["jordyn"] + balance["rent_balance"]["jordyn"]
    )

    print("\nFINAL CORRECT BALANCE CALCULATION:")
    print("-" * 40)
    print(
        f"From expenses: Ryan {'owes' if balance['expense_balance']['ryan'] > 0 else 'is owed'} ${abs(balance['expense_balance']['ryan']):,.2f}"
    )
    print(f"From rent: Ryan owes ${balance['rent_balance']['ryan']:,.2f}")
    print(
        f"\nFINAL BALANCE: Ryan {'owes' if balance['final_balance']['ryan'] > 0 else 'is owed'} ${abs(balance['final_balance']['ryan']):,.2f}"
    )
    print(
        f"              Jordyn {'owes' if balance['final_balance']['jordyn'] > 0 else 'is owed'} ${abs(balance['final_balance']['jordyn']):,.2f}"
    )
    print(
        f"\nBalance check (should be ~0): ${balance['final_balance']['ryan'] + balance['final_balance']['jordyn']:,.2f}"
    )

    return balance


def create_analysis_visualizations(expenses_df, rent_df, balance_comparison):
    """Create helpful visualizations to understand the data."""
    try:
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle("Balance Analysis Visualization", fontsize=16)

        # 1. Shared vs Personal Expenses
        if "Allowed Amount" in expenses_df.columns:
            ax = axes[0, 0]
            shared = expenses_df[expenses_df["Allowed Amount"] > 0][
                "Allowed Amount"
            ].sum()
            personal = expenses_df[expenses_df["Allowed Amount"] == 0][
                "Actual Amount"
            ].sum()

            ax.pie(
                [shared, personal],
                labels=["Shared", "Personal"],
                autopct="%1.1f%%",
                startangle=90,
            )
            ax.set_title("Shared vs Personal Expenses")

        # 2. Who Pays More
        if "Name" in expenses_df.columns:
            ax = axes[0, 1]
            payer_totals = expenses_df.groupby("Name")["Actual Amount"].sum()
            ax.bar(payer_totals.index, payer_totals.values)
            ax.set_title("Total Payments by Person")
            ax.set_ylabel("Amount ($)")

        # 3. Monthly Spending Trend
        if "Date" in expenses_df.columns:
            ax = axes[1, 0]
            expenses_df["Month"] = expenses_df["Date"].dt.to_period("M")
            monthly = expenses_df.groupby("Month")["Actual Amount"].sum()
            ax.plot(monthly.index.astype(str), monthly.values, marker="o")
            ax.set_title("Monthly Spending Trend")
            ax.set_xlabel("Month")
            ax.set_ylabel("Amount ($)")
            ax.tick_params(axis="x", rotation=45)

        # 4. Balance Impact Comparison
        if (
            "wrong_method" in balance_comparison
            and "correct_method" in balance_comparison
        ):
            ax = axes[1, 1]
            methods = ["Wrong\n(All Expenses)", "Correct\n(Shared Only)"]
            totals = [
                balance_comparison["wrong_method"]["total"],
                balance_comparison["correct_method"]["total"],
            ]

            bars = ax.bar(methods, totals, color=["red", "green"])
            ax.set_title("Impact of Calculation Method")
            ax.set_ylabel("Total Amount ($)")

            # Add value labels on bars
            for bar, total in zip(bars, totals, strict=False):
                height = bar.get_height()
                ax.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    height,
                    f"${total:,.0f}",
                    ha="center",
                    va="bottom",
                )

        plt.tight_layout()
        plt.savefig("balance_analysis.png")
        print("\nSaved visualization to: balance_analysis.png")
        plt.close()

    except Exception as e:
        print(f"\nCould not create visualizations: {e}")


def generate_recommendations(results):
    """Generate specific recommendations based on the analysis."""
    recommendations = []

    # Check if wrong calculation method is being used
    if "balance_analysis" in results and "difference" in results["balance_analysis"]:
        diff = results["balance_analysis"]["difference"]
        if diff > 1000:
            recommendations.append(
                f"CRITICAL: Your code is including ${diff:,.2f} of personal expenses in balance calculations. "
                "Fix the _reconcile() function to only count expenses where AllowedAmount > 0."
            )

    # Check for settlements
    if (
        "settlements" in results["balance_analysis"]
        and results["balance_analysis"]["settlements"]
    ):
        recommendations.append(
            f"Found {len(results['balance_analysis']['settlements'])} potential settlement transactions. "
            "Ensure these are properly marked with AllowedAmount = 0 and not counted as shared expenses."
        )

    # Check data quality
    if "data_quality" in results and "expenses" in results["data_quality"]:
        expense_quality = results["data_quality"]["expenses"]
        if expense_quality.get("personal_count", 0) > expense_quality.get(
            "shared_count", 0
        ):
            recommendations.append(
                "You have more personal expenses than shared expenses. "
                "Consider reviewing if expenses are correctly marked as shared/personal."
            )

    # Balance check
    if "final" in results["balance_analysis"]:
        final = results["balance_analysis"]["final"]["final_balance"]
        check_sum = final["ryan"] + final["jordyn"]
        if abs(check_sum) > 0.01:
            recommendations.append(
                f"WARNING: Final balances don't sum to zero (sum = ${check_sum:.2f}). "
                "This indicates a calculation error that needs to be fixed."
            )

    return recommendations


def save_analysis_report(results):
    """Save a detailed analysis report."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"balance_analysis_report_{timestamp}.txt"

    with open(report_file, "w") as f:
        f.write("BALANCE VERIFICATION REPORT\n")
        f.write("=" * 60 + "\n")
        f.write(f"Generated: {datetime.now()}\n\n")

        # Write all results
        import json

        f.write(json.dumps(results, indent=2, default=str))

    print(f"\nDetailed report saved to: {report_file}")


# Main execution
if __name__ == "__main__":
    import sys

    data_dir = sys.argv[1] if len(sys.argv) > 1 else "data"
    results = load_and_analyze_data(data_dir)

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print(
        "\nThe verification script has identified the key issues with your balance calculation."
    )
    print("Review the recommendations above and the saved report for details.")
    print("\nNext steps:")
    print("1. Fix the _reconcile() function to only count AllowedAmount > 0")
    print("2. Ensure settlements are properly marked")
    print("3. Re-run this script to verify the fix worked")
