"""
Financial Reconciliation Script - Clean Slate from January 1, 2024

This script implements a complete financial reconciliation starting from January 1, 2024,
combining expense history and rent allocation data to calculate who owes whom.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os
import sys
from pathlib import Path

def clean_currency_string(value):
    """Convert currency strings like '$1,946.00 ' to float"""
    if pd.isna(value) or value == '':
        return 0.0
    
    # Convert to string and clean
    str_val = str(value).strip()
    
    # Skip header values
    if 'Amount' in str_val:
        return 0.0
    
    # Handle negative values in parentheses like '($9.23)'
    is_negative = False
    if str_val.startswith('(') and str_val.endswith(')'):
        is_negative = True
        str_val = str_val[1:-1]  # Remove parentheses
    
    # Remove dollar signs, commas, and spaces
    cleaned = str_val.replace('$', '').replace(',', '').replace(' ', '')
    
    # Handle special cases like '$ -   '
    if cleaned == '-' or cleaned == '':
        return 0.0
    
    try:
        result = float(cleaned)
        return -result if is_negative else result
    except ValueError:
        print(f"Warning: Could not convert '{value}' to float, using 0.0")
        return 0.0

def load_and_process_expense_data(file_path):
    """Load and process the expense history CSV file"""
    print(f"Loading expense data from: {file_path}")
    
    try:
        # Load the CSV
        df = pd.read_csv(file_path)
        print(f"Loaded {len(df)} rows from expense history")
        
        # Clean column names (remove extra spaces)
        df.columns = df.columns.str.strip()
        
        # Skip header rows that might be mixed in the data
        df = df[df['Name'].notna() & ~df['Name'].str.contains('Name', na=False)]
        
        # Clean name variations
        df['Name'] = df['Name'].str.strip()
        df.loc[df['Name'].str.contains('Jordyn', case=False, na=False), 'Name'] = 'Jordyn'
        df.loc[df['Name'].str.contains('Ryan', case=False, na=False), 'Name'] = 'Ryan'
        
        # Filter to only Ryan and Jordyn
        df = df[df['Name'].isin(['Ryan', 'Jordyn'])]
        
        # Convert date column to datetime
        df['Date of Purchase'] = pd.to_datetime(df['Date of Purchase'], errors='coerce')
        
        # Clean currency columns
        df['Actual Amount'] = df['Actual Amount'].apply(clean_currency_string)
        df['Allowed Amount'] = df['Allowed Amount'].apply(clean_currency_string)
        
        # Add source column for tracking
        df['Source'] = 'Expense'
        
        # Ensure Description column exists and is clean
        if 'Description' not in df.columns:
            df['Description'] = df.get('Merchant Description', '').fillna('')
        else:
            df['Description'] = df['Description'].fillna('')
        
        return df
        
    except Exception as e:
        print(f"Error loading expense data: {e}")
        sys.exit(1)

def load_and_process_rent_data(file_path):
    """Load and process the rent allocation CSV file"""
    print(f"Loading rent data from: {file_path}")
    
    try:
        # Load the CSV
        df = pd.read_csv(file_path)
        print(f"Loaded {len(df)} rows from rent allocation")
        
        # Convert Month to datetime (assuming format like 'Jan-24')
        df['Date'] = pd.to_datetime(df['Month'] + '-01', format='%b-%y-%d', errors='coerce')
        
        # Clean currency columns
        df['Gross Total'] = df['Gross Total'].apply(clean_currency_string)
        df["Ryan's Rent (43%)"] = df["Ryan's Rent (43%)"].apply(clean_currency_string)
        df["Jordyn's Rent (57%)"] = df["Jordyn's Rent (57%)"].apply(clean_currency_string)
        
        # Reshape data to reflect WHO ACTUALLY PAYS THE RENT
        # CORRECTED: Jordyn pays the full rent amount each month
        rent_records = []
        
        for _, row in df.iterrows():
            total_rent = row['Gross Total']
            ryan_share = row["Ryan's Rent (43%)"]
            jordyn_share = row["Jordyn's Rent (57%)"]
            
            # Ryan's record - he pays NOTHING but owes his share
            rent_records.append({
                'Name': 'Ryan',
                'Date of Purchase': row['Date'],
                'Description': f"Rent for {row['Month']} (Jordyn paid, Ryan owes)",
                'Actual Amount': 0.0,  # Ryan pays nothing
                'Allowed Amount': ryan_share,  # But owes his 43% share
                'Source': 'Rent'
            })
            
            # Jordyn's record - she pays the FULL rent but only owes her share
            rent_records.append({
                'Name': 'Jordyn',
                'Date of Purchase': row['Date'],
                'Description': f"Rent for {row['Month']} (paid full ${total_rent:.2f})",
                'Actual Amount': total_rent,  # Jordyn pays the full amount
                'Allowed Amount': jordyn_share,  # But only owes her 57% share
                'Source': 'Rent'
            })
        
        rent_df = pd.DataFrame(rent_records)
        return rent_df
        
    except Exception as e:
        print(f"Error loading rent data: {e}")
        sys.exit(1)

def filter_data_by_date(df, start_date, data_type):
    """Filter data to include only transactions from start_date onward"""
    print(f"\n--- Filtering {data_type} data ---")
    initial_count = len(df)
    print(f"Initial {data_type} records: {initial_count}")
    
    # Filter by date
    date_filtered = df[df['Date of Purchase'] >= start_date].copy()
    print(f"After date filter (>= {start_date.date()}): {len(date_filtered)}")
    
    # Filter out Master and Joint Finance transactions
    description_filtered = date_filtered[
        ~date_filtered['Description'].str.contains('Master|Joint Finance', case=False, na=False)
    ].copy()
    print(f"After excluding Master/Joint Finance: {len(description_filtered)}")
    
    # Check for invalid dates
    invalid_dates = df[df['Date of Purchase'].isna()]
    if len(invalid_dates) > 0:
        print(f"Warning: Found {len(invalid_dates)} records with invalid dates")
    
    return description_filtered

def calculate_reconciliation(combined_df):
    """Calculate the reconciliation amounts per person"""
    print("\n--- Calculating Reconciliation ---")
    
    # Calculate net effect for each transaction
    combined_df['Net Effect'] = combined_df['Allowed Amount'] - combined_df['Actual Amount']
    
    # Group by person and calculate totals
    summary = combined_df.groupby('Name').agg({
        'Actual Amount': 'sum',
        'Allowed Amount': 'sum',
        'Net Effect': 'sum'
    }).round(2)
    
    return summary, combined_df

def validate_data(combined_df, summary):
    """Perform data validation checks"""
    print("\n--- Data Validation ---")
    
    # Check for required people
    people_in_data = set(combined_df['Name'].unique())
    required_people = {'Ryan', 'Jordyn'}
    
    if not required_people.issubset(people_in_data):
        missing = required_people - people_in_data
        print(f"Warning: Missing required people in data: {missing}")
    else:
        print("✓ Both Ryan and Jordyn found in data")
    
    # Check system balance
    total_net_effect = summary['Net Effect'].sum()
    print(f"Total net effect (should be near zero): ${total_net_effect:.2f}")
    
    if abs(total_net_effect) < 0.01:
        print("✓ System balances correctly")
    else:
        print(f"⚠ System imbalance detected: ${total_net_effect:.2f}")
    
    return total_net_effect

def generate_balance_interpretation(summary):
    """Generate human-readable balance interpretation"""
    print("\n--- Balance Interpretation ---")
    
    # Sort by net effect to see who owes whom
    sorted_summary = summary.sort_values('Net Effect')
    
    interpretations = []
    
    for person, row in sorted_summary.iterrows():
        net = row['Net Effect']
        if net < 0:  # NEGATIVE means OVERPAID - they are OWED money
            interpretation = f"{person} is owed ${abs(net):.2f} (overpaid)"
        elif net > 0:  # POSITIVE means UNDERPAID - they OWE money
            interpretation = f"{person} owes ${net:.2f} (underpaid)"
        else:
            interpretation = f"{person} is even"
        
        interpretations.append(interpretation)
        print(f"  {interpretation}")
    
    return interpretations

def save_results(summary, combined_df, timestamp):
    """Save reconciliation results to CSV files"""
    print("\n--- Saving Results ---")
    
    # Save summary
    summary_file = f"reconciliation_results_{timestamp}.csv"
    summary.to_csv(summary_file)
    print(f"Summary saved to: {summary_file}")
    
    # Save detailed transactions
    detail_file = f"reconciliation_details_{timestamp}.csv"
    combined_df.to_csv(detail_file, index=False)
    print(f"Detailed transactions saved to: {detail_file}")
    
    return summary_file, detail_file

def main():
    """Main execution function"""
    print("="*60)
    print("FINANCIAL RECONCILIATION - CLEAN SLATE FROM JAN 1, 2024")
    print("="*60)
    
    # Set up paths
    data_dir = Path("data")
    expense_file = data_dir / "Consolidated_Expense_History_20250622.csv"
    rent_file = data_dir / "Consolidated_Rent_Allocation_20250527.csv"
    
    # Check if files exist
    if not expense_file.exists():
        print(f"Error: Expense file not found: {expense_file}")
        sys.exit(1)
    
    if not rent_file.exists():
        print(f"Error: Rent file not found: {rent_file}")
        sys.exit(1)
    
    # Load data
    expense_df = load_and_process_expense_data(expense_file)
    rent_df = load_and_process_rent_data(rent_file)
    
    # Set clean slate date
    clean_slate_date = datetime(2024, 1, 1)
    print(f"\nClean slate starting date: {clean_slate_date.date()}")
    
    # Filter data
    filtered_expense = filter_data_by_date(expense_df, clean_slate_date, "expense")
    filtered_rent = filter_data_by_date(rent_df, clean_slate_date, "rent")
    
    # Combine datasets
    print(f"\n--- Combining Datasets ---")
    combined_df = pd.concat([filtered_expense, filtered_rent], ignore_index=True)
    print(f"Total combined records: {len(combined_df)}")
      # Calculate reconciliation
    summary, detailed_df = calculate_reconciliation(combined_df)
    
    # Display results
    print("\n--- RECONCILIATION SUMMARY ---")
    print(summary.to_string())
    
    # Display transaction counts by person and source
    print("\n--- TRANSACTION BREAKDOWN ---")
    breakdown = detailed_df.groupby(['Name', 'Source']).size().reset_index(name='Count')
    print(breakdown.to_string(index=False))
    
    # Validate data
    validate_data(detailed_df, summary)
      # Generate interpretation
    interpretations = generate_balance_interpretation(summary)
    
    # Final summary
    print(f"\n--- FINAL RECONCILIATION SUMMARY ---")
    print(f"Clean slate period: January 1, 2024 to present")
    print(f"Total transactions processed: {len(detailed_df)}")
    print(f"System imbalance: ${summary['Net Effect'].sum():.2f}")
    
    if summary['Net Effect'].sum() < 0:
        total_owed = abs(summary['Net Effect'].sum())
        print(f"\nTotal amount in dispute: ${total_owed:.2f}")
        print("This represents the net amount of overspending beyond allowed amounts.")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_results(summary, detailed_df, timestamp)
    
    print("\n" + "="*60)
    print("RECONCILIATION COMPLETE")
    print("="*60)

if __name__ == "__main__":
    main()
