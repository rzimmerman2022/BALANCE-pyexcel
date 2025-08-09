#!/usr/bin/env python3
"""
BALANCE Dispute & Refund Analyzer

Interactive tool for analyzing disputes, refunds, and specific transaction questions.

Usage:
    python scripts/utilities/dispute_analyzer.py
"""

import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import re

def load_latest_data():
    """Load the most recent cleaned transaction file"""
    output_dir = Path("output")
    
    # Find latest cleaned file
    parquet_files = list(output_dir.glob("transactions_cleaned_*.parquet"))
    csv_files = list(output_dir.glob("transactions_cleaned_*.csv"))
    
    if parquet_files:
        latest_file = max(parquet_files, key=lambda x: x.stat().st_mtime)
        print(f"Loading: {latest_file}")
        return pd.read_parquet(latest_file)
    elif csv_files:
        latest_file = max(csv_files, key=lambda x: x.stat().st_mtime)
        print(f"Loading: {latest_file}")
        return pd.read_csv(latest_file, parse_dates=['date'])
    else:
        print("No cleaned data files found. Run quick_powerbi_prep.py first.")
        return None

def find_refunds_for_merchant(df, merchant_name, days_back=90):
    """Find potential refunds for a specific merchant"""
    merchant_pattern = merchant_name.upper()
    
    # Filter by merchant and potential refund flag
    merchant_mask = df['merchant_standardized'].str.contains(merchant_pattern, case=False, na=False)
    refund_mask = df['potential_refund'] == True
    date_mask = df['date'] >= (datetime.now() - timedelta(days=days_back))
    
    results = df[merchant_mask & (refund_mask | (df['amount'] > 0)) & date_mask]
    
    if len(results) > 0:
        print(f"\n=== Potential Refunds/Credits for '{merchant_name}' (last {days_back} days) ===")
        print(results[['date', 'merchant_standardized', 'amount', 'description']].to_string())
        print(f"\nTotal credits: ${results[results['amount'] > 0]['amount'].sum():,.2f}")
    else:
        print(f"No refunds found for '{merchant_name}' in last {days_back} days")
    
    return results

def find_duplicate_charges(df, days_window=3):
    """Find potential duplicate charges within a time window"""
    print(f"\n=== Checking for Duplicate Charges (within {days_window} days) ===")
    
    duplicates = []
    
    # Group by merchant and amount
    for (merchant, amount), group in df[df['amount'] < 0].groupby(['merchant_standardized', 'amount_abs']):
        if len(group) > 1:
            # Check if transactions are within days_window
            group_sorted = group.sort_values('date')
            for i in range(len(group_sorted) - 1):
                date_diff = (group_sorted.iloc[i+1]['date'] - group_sorted.iloc[i]['date']).days
                if date_diff <= days_window:
                    duplicates.append({
                        'merchant': merchant,
                        'amount': amount,
                        'date1': group_sorted.iloc[i]['date'],
                        'date2': group_sorted.iloc[i+1]['date'],
                        'days_apart': date_diff
                    })
    
    if duplicates:
        dup_df = pd.DataFrame(duplicates)
        print(dup_df.to_string())
        print(f"\nFound {len(duplicates)} potential duplicate charges")
        return dup_df
    else:
        print("No suspicious duplicate charges found")
        return None

def check_refund_status(df, merchant, charge_amount, charge_date_str):
    """Check if a specific charge was refunded"""
    charge_date = pd.to_datetime(charge_date_str)
    
    print(f"\n=== Checking Refund Status ===")
    print(f"Original charge: {merchant} ${charge_amount} on {charge_date_str}")
    
    # Look for matching positive amount within 60 days
    search_start = charge_date
    search_end = charge_date + timedelta(days=60)
    
    merchant_mask = df['merchant_standardized'].str.contains(merchant.upper(), case=False, na=False)
    date_mask = (df['date'] >= search_start) & (df['date'] <= search_end)
    amount_mask = abs(df['amount'] - abs(charge_amount)) < 0.01  # Allow penny difference
    refund_mask = df['amount'] > 0  # Looking for credits
    
    potential_refunds = df[merchant_mask & date_mask & amount_mask & refund_mask]
    
    if len(potential_refunds) > 0:
        print(f"✓ REFUND FOUND:")
        print(potential_refunds[['date', 'merchant_standardized', 'amount', 'description']].to_string())
    else:
        print(f"✗ No refund found within 60 days of charge")
        
        # Check if there are any credits from this merchant
        any_credits = df[merchant_mask & date_mask & refund_mask]
        if len(any_credits) > 0:
            print(f"\nOther credits from {merchant} in this period:")
            print(any_credits[['date', 'amount', 'description']].to_string())
    
    return potential_refunds

def analyze_disputes(df):
    """Comprehensive dispute analysis"""
    print("\n" + "="*60)
    print("COMPREHENSIVE DISPUTE & REFUND ANALYSIS")
    print("="*60)
    
    # Overall statistics
    total_disputes = df['potential_refund'].sum()
    dispute_df = df[df['potential_refund'] == True]
    
    print(f"\nTotal potential disputes/refunds: {total_disputes}")
    
    if total_disputes > 0:
        print(f"Total dispute amount: ${dispute_df['amount'].sum():,.2f}")
        print(f"Date range: {dispute_df['date'].min().date()} to {dispute_df['date'].max().date()}")
        
        print("\n=== Top Merchants with Disputes ===")
        merchant_disputes = dispute_df.groupby('merchant_standardized').agg({
            'amount': ['count', 'sum']
        }).round(2)
        merchant_disputes.columns = ['Count', 'Total Amount']
        print(merchant_disputes.sort_values('Count', ascending=False).head(10).to_string())
        
        print("\n=== Recent Disputes (Last 30 Days) ===")
        recent_mask = dispute_df['date'] >= (datetime.now() - timedelta(days=30))
        recent_disputes = dispute_df[recent_mask]
        
        if len(recent_disputes) > 0:
            print(recent_disputes[['date', 'merchant_standardized', 'amount', 'description']].tail(10).to_string())
        else:
            print("No disputes in last 30 days")

def interactive_menu():
    """Interactive menu for dispute analysis"""
    df = load_latest_data()
    if df is None:
        return
    
    print(f"\nLoaded {len(df)} transactions")
    print(f"Date range: {df['date'].min().date()} to {df['date'].max().date()}")
    
    while True:
        print("\n" + "="*60)
        print("DISPUTE & REFUND ANALYZER")
        print("="*60)
        print("1. Search refunds for specific merchant")
        print("2. Find potential duplicate charges")
        print("3. Check if specific charge was refunded")
        print("4. Show comprehensive dispute analysis")
        print("5. Export disputes to Excel")
        print("6. Custom search (advanced)")
        print("0. Exit")
        
        choice = input("\nSelect option: ").strip()
        
        if choice == '1':
            merchant = input("Enter merchant name (partial match OK): ").strip()
            days = int(input("Days to look back (default 90): ").strip() or "90")
            find_refunds_for_merchant(df, merchant, days)
            
        elif choice == '2':
            days = int(input("Day window for duplicates (default 3): ").strip() or "3")
            find_duplicate_charges(df, days)
            
        elif choice == '3':
            merchant = input("Merchant name: ").strip()
            amount = float(input("Charge amount (without $ sign): ").strip())
            date_str = input("Charge date (YYYY-MM-DD): ").strip()
            check_refund_status(df, merchant, amount, date_str)
            
        elif choice == '4':
            analyze_disputes(df)
            
        elif choice == '5':
            disputes = df[df['potential_refund'] == True]
            filename = f"disputes_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            disputes.to_excel(f"output/{filename}", index=False)
            print(f"Exported {len(disputes)} disputes to output/{filename}")
            
        elif choice == '6':
            print("\nEnter pandas query (e.g., 'amount > 100 & merchant_standardized.str.contains(\"Amazon\")'):")
            query = input("> ").strip()
            try:
                results = df.query(query)
                print(f"\nFound {len(results)} matching transactions:")
                print(results[['date', 'merchant_standardized', 'amount', 'description']].head(20).to_string())
                
                export = input("\nExport results to Excel? (y/n): ").strip().lower()
                if export == 'y':
                    filename = f"custom_search_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                    results.to_excel(f"output/{filename}", index=False)
                    print(f"Exported to output/{filename}")
            except Exception as e:
                print(f"Query error: {e}")
                
        elif choice == '0':
            break
        else:
            print("Invalid option")
    
    print("\nGoodbye!")

if __name__ == "__main__":
    # Run interactive menu
    interactive_menu()