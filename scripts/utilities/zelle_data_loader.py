"""
ZELLE DATA LOADER AND PROCESSOR
Loads Wells Fargo Zelle payment data and prepares it for integration
"""

import pandas as pd
from datetime import datetime
import re

def clean_currency_string(value):
    """Convert currency strings to float, handling negative values"""
    if pd.isna(value) or value == '':
        return 0.0
    
    str_val = str(value).strip()
    
    # Handle negative values in parentheses like '($50.00)'
    is_negative = False
    if str_val.startswith('(') and str_val.endswith(')'):
        is_negative = True
        str_val = str_val[1:-1]
    elif str_val.startswith('-'):
        is_negative = True
        str_val = str_val[1:]
    
    # Remove dollar signs, commas, and spaces
    cleaned = str_val.replace('$', '').replace(',', '').replace(' ', '')
    
    try:
        result = float(cleaned)
        return -abs(result) if is_negative else result
    except ValueError:
        print(f"Warning: Could not convert '{value}' to float, using 0.0")
        return 0.0

def identify_zelle_person(description, amount):
    """
    Try to identify if a Zelle payment is related to Ryan or Jordyn
    This will need to be customized based on actual Zelle descriptions
    """
    desc_lower = description.lower()
    
    # Common patterns to look for
    # You'll need to customize these based on actual Zelle recipient names
    jordyn_patterns = [
        'jordyn', 'jord', 'girlfriend', 'roommate'
    ]
    
    ryan_patterns = [
        'ryan', 'ry', 'boyfriend', 'roommate'
    ]
    
    # Check for patterns
    for pattern in jordyn_patterns:
        if pattern in desc_lower:
            return 'Jordyn'
    
    for pattern in ryan_patterns:
        if pattern in desc_lower:
            return 'Ryan'
    
    # If we can't identify, mark as unknown for manual review
    return 'Unknown'

def categorize_zelle_payment(description, amount):
    """
    Categorize Zelle payments into shared vs personal expenses
    """
    desc_lower = description.lower()
    
    # Shared expense patterns
    shared_patterns = [
        'rent', 'utilities', 'groceries', 'dinner', 'restaurant',
        'uber', 'lyft', 'gas', 'parking', 'shared', 'split'
    ]
    
    # Personal expense patterns  
    personal_patterns = [
        'personal', 'loan', 'payback', 'owe', 'borrow'
    ]
    
    for pattern in shared_patterns:
        if pattern in desc_lower:
            return 'Shared'
    
    for pattern in personal_patterns:
        if pattern in desc_lower:
            return 'Personal'
    
    # Default to unknown for manual review
    return 'Unknown'

def load_zelle_data(file_path):
    """
    Load Wells Fargo Zelle data from CSV
    Expected columns: Date, Description, Amount, Account, Type
    """
    print(f"Loading Zelle data from: {file_path}")
    
    try:
        df = pd.read_csv(file_path)
        print(f"Loaded {len(df)} rows from Zelle file")
        print(f"Columns: {list(df.columns)}")
        
        # Clean column names
        df.columns = df.columns.str.strip()
        
        # Convert date column
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        elif 'Transaction Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Transaction Date'], errors='coerce')
        else:
            print("Warning: No Date column found, you may need to rename it")
        
        # Clean amount column
        if 'Amount' in df.columns:
            df['Amount_Clean'] = df['Amount'].apply(clean_currency_string)
        else:
            print("Warning: No Amount column found, you may need to rename it")
        
        # Filter to Zelle transactions only (in case file has other transactions)
        if 'Description' in df.columns:
            zelle_mask = df['Description'].str.contains('ZELLE|P2P|Zelle', case=False, na=False)
            df = df[zelle_mask]
            print(f"After filtering to Zelle transactions: {len(df)} rows")
        
        # Filter to 2024+ only
        cutoff_date = datetime(2024, 1, 1)
        df = df[df['Date'] >= cutoff_date]
        print(f"After filtering to 2024+: {len(df)} rows")
        
        # Add analysis columns
        df['Person'] = df['Description'].apply(lambda x: identify_zelle_person(x, 0))
        df['Category'] = df['Description'].apply(lambda x: categorize_zelle_payment(x, 0))
        df['Is_Outgoing'] = df['Amount_Clean'] < 0
        df['Abs_Amount'] = df['Amount_Clean'].abs()
        
        # Add source tracking
        df['Source'] = 'Zelle'
        df['Source_File'] = file_path.split('/')[-1]  # Just filename
        df['Original_Row'] = df.index + 2  # +2 for header and 1-based indexing
        
        return df
        
    except Exception as e:
        print(f"Error loading Zelle data: {e}")
        return None

def analyze_zelle_data(df):
    """Analyze the loaded Zelle data"""
    if df is None or len(df) == 0:
        print("No Zelle data to analyze")
        return
    
    print("\n" + "=" * 60)
    print("ZELLE DATA ANALYSIS")
    print("=" * 60)
    
    print(f"Total Zelle transactions: {len(df)}")
    print(f"Date range: {df['Date'].min()} to {df['Date'].max()}")
    print(f"Total amount: ${df['Amount_Clean'].sum():.2f}")
    
    print(f"\nBy Direction:")
    print(f"Outgoing payments: {len(df[df['Is_Outgoing']])} (${df[df['Is_Outgoing']]['Amount_Clean'].sum():.2f})")
    print(f"Incoming payments: {len(df[~df['Is_Outgoing']])} (${df[~df['Is_Outgoing']]['Amount_Clean'].sum():.2f})")
    
    print(f"\nBy Person:")
    person_counts = df['Person'].value_counts()
    for person, count in person_counts.items():
        person_df = df[df['Person'] == person]
        total_amount = person_df['Amount_Clean'].sum()
        print(f"{person}: {count} transactions (${total_amount:.2f})")
    
    print(f"\nBy Category:")
    category_counts = df['Category'].value_counts()
    for category, count in category_counts.items():
        category_df = df[df['Category'] == category]
        total_amount = category_df['Amount_Clean'].sum()
        print(f"{category}: {count} transactions (${total_amount:.2f})")
    
    # Show some examples
    print(f"\nSample Zelle transactions:")
    sample_df = df[['Date', 'Description', 'Amount_Clean', 'Person', 'Category']].head(10)
    print(sample_df.to_string(index=False))
    
    # Flag items needing manual review
    unknown_person = df[df['Person'] == 'Unknown']
    unknown_category = df[df['Category'] == 'Unknown']
    
    if len(unknown_person) > 0:
        print(f"\n⚠️ MANUAL REVIEW NEEDED:")
        print(f"{len(unknown_person)} transactions with unknown person:")
        print(unknown_person[['Date', 'Description', 'Amount_Clean']].to_string(index=False))
    
    if len(unknown_category) > 0:
        print(f"\n⚠️ MANUAL REVIEW NEEDED:")
        print(f"{len(unknown_category)} transactions with unknown category:")
        print(unknown_category[['Date', 'Description', 'Amount_Clean']].to_string(index=False))

def save_processed_zelle_data(df, output_file):
    """Save the processed Zelle data"""
    if df is None or len(df) == 0:
        print("No data to save")
        return
    
    df.to_csv(output_file, index=False)
    print(f"Processed Zelle data saved to: {output_file}")

def main():
    """Main function - customize with your Zelle data file"""
    print("ZELLE DATA LOADER")
    print("=" * 50)
    
    # You'll need to update this path with your actual Zelle data file
    zelle_file = "data/wells_fargo_zelle_transactions.csv"  # Update this!
    
    print(f"Looking for Zelle data file: {zelle_file}")
    
    try:
        # Check if file exists
        import os
        if not os.path.exists(zelle_file):
            print(f"❌ File not found: {zelle_file}")
            print("\n📋 TO USE THIS SCRIPT:")
            print("1. Download your Wells Fargo Zelle transactions")
            print("2. Save as CSV in the data/ folder")
            print("3. Update the 'zelle_file' variable in this script")
            print("4. Run this script again")
            return
        
        # Load and process the data
        df = load_zelle_data(zelle_file)
        
        if df is not None:
            analyze_zelle_data(df)
            
            # Save processed data
            output_file = "data/processed_zelle_transactions.csv"
            save_processed_zelle_data(df, output_file)
            
            print(f"\n✅ Zelle data processing complete!")
            print(f"Next step: Run zelle_matcher.py to cross-reference with existing expense data")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
