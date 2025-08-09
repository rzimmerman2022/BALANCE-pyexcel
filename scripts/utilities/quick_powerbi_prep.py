#!/usr/bin/env python3
"""
BALANCE Power BI Data Preparation Utility - Improved Version

Enhanced deduplication and data cleaning for dispute analysis.
Handles the complex duplicate patterns between Monarch and Rocket data.

Usage:
    python scripts/utilities/improved_powerbi_prep.py

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

def normalize_description(desc):
    """Normalize description for better duplicate detection"""
    if pd.isna(desc):
        return ""
    
    desc = str(desc).strip()
    
    # Remove extra whitespace
    desc = re.sub(r'\s+', ' ', desc)
    
    # Remove common prefixes/suffixes that vary
    desc = re.sub(r'^(WT\s+)?SEQ#?\d*\s*', '', desc, flags=re.IGNORECASE)
    desc = re.sub(r'\s*/?ORG=.*$', '', desc, flags=re.IGNORECASE)  
    desc = re.sub(r'\s*SRF#.*$', '', desc, flags=re.IGNORECASE)
    desc = re.sub(r'\s*TRN#.*$', '', desc, flags=re.IGNORECASE)
    desc = re.sub(r'\s*RFB#.*$', '', desc, flags=re.IGNORECASE)
    desc = re.sub(r'\s*REF#.*$', '', desc, flags=re.IGNORECASE)
    
    # Remove trailing numbers and codes
    desc = re.sub(r'\s+\d{6,}$', '', desc)
    
    return desc.strip().upper()

def standardize_merchant(description, merchant=""):
    """Enhanced merchant name standardization"""
    if pd.isna(description) and pd.isna(merchant):
        return "Unknown"
    
    # Combine description and merchant for analysis
    combined = f"{str(merchant)} {str(description)}".upper()
    
    # Specific patterns for your data
    patterns = {
        r'JOAN\s*M\s*ZIMMERMAN': 'Internal Transfer - Joan Zimmerman',
        r'RYAN\s*ZIMMERMAN': 'Internal Transfer - Ryan Zimmerman', 
        r'SALLIE\s*MAE': 'Sallie Mae',
        r'DISBURSEMENT': 'Student Loan Disbursement',
        r'PAYMENT.*THANK\s*YOU': 'Credit Card Payment',
        r'ARIZ\s*STATE\s*UNIV': 'Arizona State University',
        r'WELLS\s*FARGO.*VISA': 'Wells Fargo Credit Card',
        r'AMAZON.*': 'Amazon',
        r'AMZN.*': 'Amazon', 
        r'WALMART.*': 'Walmart',
        r'STARBUCKS.*': 'Starbucks',
        r'SAFEWAY.*': 'Safeway',
        r'FRYS.*FOOD.*': 'Frys Food',
        r'WHOLEFDS.*|WHOLE\s*FOODS': 'Whole Foods',
        r'TARGET.*': 'Target',
        r'COSTCO.*': 'Costco',
        r'UBER.*': 'Uber',
        r'ZELLE.*': 'Zelle Transfer',
        r'.*REFUND.*': 'REFUND',
        r'.*RETURN.*': 'RETURN',
        r'.*REVERSAL.*': 'REVERSAL',
        r'.*DISPUTE.*': 'DISPUTE',
        r'.*CHARGEBACK.*': 'CHARGEBACK'
    }
    
    for pattern, merchant_name in patterns.items():
        if re.search(pattern, combined):
            return merchant_name
    
    # Clean up merchant field if available
    if not pd.isna(merchant) and str(merchant).strip() != '':
        clean_merchant = str(merchant).strip()
        if clean_merchant.upper() not in ['UNKNOWN', 'NAN', '']:
            return clean_merchant
    
    # Extract meaningful parts from description
    desc = str(description) if not pd.isna(description) else ""
    desc_clean = normalize_description(desc)
    
    if desc_clean:
        # Return first few words as merchant name
        words = desc_clean.split()[:3]
        return ' '.join(words)
    
    return "Unknown"

def create_dedup_key(row):
    """Create a key for duplicate detection"""
    date_key = row['date'].strftime('%Y-%m-%d') if pd.notnull(row['date']) else 'unknown'
    amount_key = f"{abs(row['amount']):.2f}"
    
    # Normalize description for key
    desc_key = normalize_description(row.get('description', ''))
    
    # Use first few words of normalized description
    desc_words = desc_key.split()[:5]  # First 5 words
    desc_key_short = '_'.join(desc_words)
    
    return f"{date_key}_{amount_key}_{desc_key_short}"

def process_monarch_data(file_path):
    """Process Monarch Money format CSV"""
    df = pd.read_csv(file_path)
    
    # Standardize column names
    df_clean = pd.DataFrame({
        'date': pd.to_datetime(df['Date']),
        'merchant': df['Merchant'].fillna(''),
        'description': df['Original Statement'].fillna(''),
        'amount': df['Amount'].apply(clean_amount),
        'category': df['Category'].fillna('Uncategorized'),
        'account': df['Account'].fillna('Unknown'),
        'notes': df['Notes'].fillna(''),
        'tags': df['Tags'].fillna(''),
        'source_file': 'Monarch',
        'data_source': 'Combined Ryan & Jordyn',
        'account_number': '',
        'institution': ''
    })
    
    return df_clean

def process_rocket_data(file_path):
    """Process Rocket Money format CSV"""
    df = pd.read_csv(file_path)
    
    # Standardize column names
    df_clean = pd.DataFrame({
        'date': pd.to_datetime(df['Date']),
        'merchant': df['Name'].fillna(''),
        'description': df['Description'].fillna(''),
        'amount': df['Amount'].apply(clean_amount),
        'category': df['Category'].fillna('Uncategorized'),
        'account': df['Account Name'].fillna('Unknown'),
        'account_number': df['Account Number'].fillna(''),
        'institution': df['Institution Name'].fillna(''),
        'notes': df['Note'].fillna(''),
        'source_file': 'Rocket',
        'data_source': 'Combined Ryan & Jordyn',
        'tags': ''
    })
    
    return df_clean

def smart_deduplication(df):
    """Enhanced deduplication logic"""
    print("Starting smart deduplication...")
    
    # Create deduplication key
    df['dedup_key'] = df.apply(create_dedup_key, axis=1)
    
    print(f"Before deduplication: {len(df)} transactions")
    
    # Group by dedup key and handle duplicates
    deduplicated_rows = []
    
    for key, group in df.groupby('dedup_key'):
        if len(group) == 1:
            # No duplicates
            deduplicated_rows.append(group.iloc[0])
        else:
            # Handle duplicates - prefer more detailed record
            best_record = None
            max_info_score = -1
            
            for _, row in group.iterrows():
                # Score based on amount of information
                info_score = 0
                if row['merchant'] and str(row['merchant']).strip() not in ['', 'Unknown']:
                    info_score += 2
                if row['description'] and len(str(row['description'])) > 10:
                    info_score += 3
                if row['account_number'] and str(row['account_number']).strip():
                    info_score += 1
                if row['institution'] and str(row['institution']).strip():
                    info_score += 1
                if row['category'] and str(row['category']).strip() not in ['', 'Uncategorized']:
                    info_score += 1
                    
                if info_score > max_info_score:
                    max_info_score = info_score
                    best_record = row
            
            if best_record is not None:
                deduplicated_rows.append(best_record)
    
    # Create final dataframe
    df_dedup = pd.DataFrame(deduplicated_rows).reset_index(drop=True)
    
    # Remove dedup_key column
    df_dedup = df_dedup.drop('dedup_key', axis=1)
    
    print(f"After deduplication: {len(df_dedup)} transactions")
    print(f"Removed {len(df) - len(df_dedup)} duplicates")
    
    return df_dedup

def main():
    """Main processing function"""
    print("Processing CSV files for Power BI (Improved Version)...")
    
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
    print("Combining data...")
    combined_df = pd.concat(dataframes, ignore_index=True, sort=False)
    print(f"Combined total: {len(combined_df)} transactions")
    
    # Smart deduplication
    combined_df = smart_deduplication(combined_df)
    
    # Add standardized merchant names
    print("Standardizing merchant names...")
    combined_df['merchant_standardized'] = combined_df.apply(
        lambda x: standardize_merchant(x['description'], x['merchant']), 
        axis=1
    )
    
    # Add useful analysis columns
    print("Adding analysis columns...")
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
    
    # Sort by date
    combined_df = combined_df.sort_values('date').reset_index(drop=True)
    
    # Create output directory
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Save as multiple formats for Power BI
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Excel format (good for manual review)
    excel_file = output_dir / f"transactions_cleaned_{timestamp}.xlsx"
    combined_df.to_excel(excel_file, index=False, sheet_name="Transactions")
    print(f"Saved Excel file: {excel_file}")
    
    # CSV format (fastest for Power BI import)
    csv_file = output_dir / f"transactions_cleaned_{timestamp}.csv"
    combined_df.to_csv(csv_file, index=False)
    print(f"Saved CSV file: {csv_file}")
    
    # Parquet format (most efficient for large datasets) - fix data types first
    parquet_file = output_dir / f"transactions_cleaned_{timestamp}.parquet"
    try:
        # Convert problematic columns to string to avoid type conflicts
        parquet_df = combined_df.copy()
        parquet_df['account_number'] = parquet_df['account_number'].astype(str)
        parquet_df.to_parquet(parquet_file, index=False)
        print(f"Saved Parquet file: {parquet_file}")
    except Exception as e:
        print(f"Note: Parquet export failed ({e}), but CSV and Excel files are available")
    
    # Summary statistics
    print("\n=== IMPROVED DATA SUMMARY ===")
    print(f"Total transactions: {len(combined_df)}")
    print(f"Date range: {combined_df['date'].min()} to {combined_df['date'].max()}")
    print(f"Total amount: ${combined_df['amount'].sum():,.2f}")
    print(f"Expenses: ${combined_df[combined_df['amount'] < 0]['amount'].sum():,.2f}")
    print(f"Income: ${combined_df[combined_df['amount'] > 0]['amount'].sum():,.2f}")
    print(f"Potential refunds/disputes: {combined_df['potential_refund'].sum()}")
    
    print(f"\nTop merchants by transaction count:")
    print(combined_df['merchant_standardized'].value_counts().head(10))
    
    # Check for remaining potential duplicates
    print(f"\n=== DUPLICATE CHECK ===")
    potential_dups = combined_df.groupby(['date', 'amount_abs']).size()
    potential_dups = potential_dups[potential_dups > 1]
    print(f"Potential remaining duplicates (same date + amount): {len(potential_dups)}")
    
    print(f"\nFiles ready for Power BI import!")
    print(f"Recommend using: {parquet_file}")

if __name__ == "__main__":
    main()