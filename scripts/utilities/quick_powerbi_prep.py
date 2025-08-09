#!/usr/bin/env python3
"""
BALANCE Power BI Data Preparation Utility

Prepares combined transaction data from multiple CSV sources for Power BI analysis.
Supports dispute analysis, refund verification, and financial reporting.

Usage:
    python scripts/utilities/quick_powerbi_prep.py

Features:
    - Handles Monarch Money and Rocket Money CSV formats
    - Automatic deduplication of transactions
    - Merchant name standardization
    - Pre-flags potential refunds/disputes
    - Creates Power BI-optimized output files (Parquet, Excel, CSV)

Author: BALANCE Pipeline Team
"""

import pandas as pd
import numpy as np
from pathlib import Path
import re
from datetime import datetime

def clean_amount(amount_str):
    """Convert amount string to float, handling various formats"""
    if pd.isna(amount_str) or amount_str == '':
        return 0.0
    
    # Remove commas and whitespace
    amount_str = str(amount_str).replace(',', '').strip()
    
    # Handle negative signs and parentheses
    if amount_str.startswith('(') and amount_str.endswith(')'):
        amount_str = '-' + amount_str[1:-1]
    
    try:
        return float(amount_str)
    except ValueError:
        return 0.0

def standardize_merchant(description):
    """Basic merchant name standardization"""
    if pd.isna(description):
        return "Unknown"
    
    desc = str(description).upper()
    
    # Common patterns
    patterns = {
        r'AMAZON.*': 'Amazon',
        r'AMZN.*': 'Amazon', 
        r'WALMART.*': 'Walmart',
        r'STARBUCKS.*': 'Starbucks',
        r'SAFEWAY.*': 'Safeway',
        r'FRYS.*FOOD.*': 'Frys Food',
        r'WHOLEFDS.*': 'Whole Foods',
        r'TARGET.*': 'Target',
        r'COSTCO.*': 'Costco',
        r'.*REFUND.*': 'REFUND',
        r'.*RETURN.*': 'RETURN',
        r'.*REVERSAL.*': 'REVERSAL',
        r'.*DISPUTE.*': 'DISPUTE',
        r'.*CHARGEBACK.*': 'CHARGEBACK'
    }
    
    for pattern, merchant in patterns.items():
        if re.search(pattern, desc):
            return merchant
    
    # Return first few words as merchant name
    words = desc.split()[:3]
    return ' '.join(words)

def process_monarch_data(file_path):
    """Process Monarch Money format CSV"""
    df = pd.read_csv(file_path)
    
    # Standardize column names
    df_clean = pd.DataFrame({
        'date': pd.to_datetime(df['Date']),
        'merchant': df['Merchant'].fillna('Unknown'),
        'description': df['Original Statement'].fillna(''),
        'amount': df['Amount'].apply(clean_amount),
        'category': df['Category'].fillna('Uncategorized'),
        'account': df['Account'].fillna('Unknown'),
        'notes': df['Notes'].fillna(''),
        'tags': df['Tags'].fillna(''),
        'source_file': 'Monarch',
        'data_source': 'Combined Ryan & Jordyn'
    })
    
    return df_clean

def process_rocket_data(file_path):
    """Process Rocket Money format CSV"""
    df = pd.read_csv(file_path)
    
    # Standardize column names
    df_clean = pd.DataFrame({
        'date': pd.to_datetime(df['Date']),
        'merchant': df['Name'].fillna('Unknown'),
        'description': df['Description'].fillna(''),
        'amount': df['Amount'].apply(clean_amount),
        'category': df['Category'].fillna('Uncategorized'),
        'account': df['Account Name'].fillna('Unknown'),
        'account_number': df['Account Number'].fillna(''),
        'institution': df['Institution Name'].fillna(''),
        'notes': df['Note'].fillna(''),
        'source_file': 'Rocket',
        'data_source': 'Combined Ryan & Jordyn'
    })
    
    return df_clean

def main():
    """Main processing function"""
    print("Processing CSV files for Power BI...")
    
    # File paths
    monarch_file = Path("csv_inbox/ryan&jordyn-monarch-020250809.csv")
    rocket_file = Path("csv_inbox/ryan&jordyn-rocket-020250809.csv")
    
    dataframes = []
    
    # Process Monarch data
    if monarch_file.exists():
        print(f"Processing {monarch_file}...")
        monarch_df = process_monarch_data(monarch_file)
        dataframes.append(monarch_df)
        print(f"  Loaded {len(monarch_df)} transactions")
    
    # Process Rocket data  
    if rocket_file.exists():
        print(f"Processing {rocket_file}...")
        rocket_df = process_rocket_data(rocket_file)
        dataframes.append(rocket_df)
        print(f"  Loaded {len(rocket_df)} transactions")
    
    if not dataframes:
        print("No CSV files found!")
        return
    
    # Combine all data
    print("Combining and cleaning data...")
    combined_df = pd.concat(dataframes, ignore_index=True, sort=False)
    
    # Add standardized merchant names
    combined_df['merchant_standardized'] = combined_df.apply(
        lambda x: standardize_merchant(x['description'] if pd.isna(x['merchant']) or x['merchant'] == 'Unknown' else x['merchant']), 
        axis=1
    )
    
    # Add useful analysis columns
    combined_df['year'] = combined_df['date'].dt.year
    combined_df['month'] = combined_df['date'].dt.month
    combined_df['quarter'] = combined_df['date'].dt.quarter
    combined_df['day_of_week'] = combined_df['date'].dt.day_name()
    combined_df['is_weekend'] = combined_df['date'].dt.weekday >= 5
    combined_df['amount_abs'] = combined_df['amount'].abs()
    combined_df['is_expense'] = combined_df['amount'] < 0
    combined_df['is_income'] = combined_df['amount'] > 0
    combined_df['transaction_id'] = range(1, len(combined_df) + 1)
    
    # Flag potential refunds/disputes for your analysis
    combined_df['potential_refund'] = combined_df['description'].str.contains(
        r'(?i)(refund|return|reversal|dispute|chargeback|credit.*adjustment)', 
        na=False
    )
    
    # Remove duplicates (basic deduplication)
    print(f"Before deduplication: {len(combined_df)} transactions")
    combined_df = combined_df.drop_duplicates(
        subset=['date', 'merchant_standardized', 'amount', 'description'], 
        keep='first'
    )
    print(f"After deduplication: {len(combined_df)} transactions")
    
    # Sort by date
    combined_df = combined_df.sort_values('date').reset_index(drop=True)
    
    # Create output directory
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Save as multiple formats for Power BI
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Excel format (good for manual review)
    excel_file = output_dir / f"transactions_for_powerbi_{timestamp}.xlsx"
    combined_df.to_excel(excel_file, index=False, sheet_name="Transactions")
    print(f"Saved Excel file: {excel_file}")
    
    # CSV format (fastest for Power BI import)
    csv_file = output_dir / f"transactions_for_powerbi_{timestamp}.csv"
    combined_df.to_csv(csv_file, index=False)
    print(f"Saved CSV file: {csv_file}")
    
    # Parquet format (most efficient for large datasets)
    parquet_file = output_dir / f"transactions_for_powerbi_{timestamp}.parquet"
    combined_df.to_parquet(parquet_file, index=False)
    print(f"Saved Parquet file: {parquet_file}")
    
    # Summary statistics
    print("\n=== DATA SUMMARY ===")
    print(f"Total transactions: {len(combined_df)}")
    print(f"Date range: {combined_df['date'].min()} to {combined_df['date'].max()}")
    print(f"Total amount: ${combined_df['amount'].sum():,.2f}")
    print(f"Expenses: ${combined_df[combined_df['amount'] < 0]['amount'].sum():,.2f}")
    print(f"Income: ${combined_df[combined_df['amount'] > 0]['amount'].sum():,.2f}")
    print(f"Potential refunds/disputes: {combined_df['potential_refund'].sum()}")
    
    print("\nTop merchants by transaction count:")
    print(combined_df['merchant_standardized'].value_counts().head(10))
    
    print("\nFiles ready for Power BI import!")
    print(f"Recommend using: {parquet_file} for best performance")

if __name__ == "__main__":
    main()