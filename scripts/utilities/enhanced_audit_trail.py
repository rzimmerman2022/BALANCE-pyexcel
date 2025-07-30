"""
Enhanced Comprehensive Audit Trail with Source File References
Shows exactly where each transaction comes from and tracks all filtering
"""

import pandas as pd
from datetime import datetime
import numpy as np
import os

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

def load_and_process_expense_data_enhanced(file_path):
    """Load and process the expense history CSV file with detailed tracking"""
    print(f"Loading expense data from: {file_path}")
    
    try:
        # Load the CSV with index to track original row numbers
        df = pd.read_csv(file_path)
        df['Original_Row'] = df.index + 2  # +2 because CSV starts at row 1 and we have header
        df['Source_File'] = 'Consolidated_Expense_History_20250622.csv'
        
        print(f"Loaded {len(df)} rows from expense history")
        
        # Clean column names (remove extra spaces)
        df.columns = df.columns.str.strip()
        
        print(f"After column cleaning: {len(df)} rows")
        
        # Skip header rows that might be mixed in the data
        before_name_filter = len(df)
        df = df[df['Name'].notna() & ~df['Name'].str.contains('Name', na=False)]
        print(f"After removing header rows: {len(df)} rows (removed {before_name_filter - len(df)})")
        
        # Clean name variations
        df['Name'] = df['Name'].str.strip()
        df.loc[df['Name'].str.contains('Jordyn', case=False, na=False), 'Name'] = 'Jordyn'
        df.loc[df['Name'].str.contains('Ryan', case=False, na=False), 'Name'] = 'Ryan'
        
        # Filter to only Ryan and Jordyn
        before_person_filter = len(df)
        df = df[df['Name'].isin(['Ryan', 'Jordyn'])]
        print(f"After filtering to Ryan/Jordyn: {len(df)} rows (removed {before_person_filter - len(df)})")
        
        # Convert date column to datetime
        df['Date of Purchase'] = pd.to_datetime(df['Date of Purchase'], errors='coerce')
        
        # Check for invalid dates
        invalid_dates = df[df['Date of Purchase'].isna()]
        print(f"Found {len(invalid_dates)} rows with invalid dates")
        
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
        return None

def load_and_process_rent_data_enhanced(file_path):
    """Load and process the rent allocation CSV file with detailed tracking"""
    print(f"Loading rent data from: {file_path}")
    
    try:
        # Load the CSV
        df = pd.read_csv(file_path)
        df['Original_Row'] = df.index + 2  # +2 because CSV starts at row 1 and we have header
        df['Source_File'] = 'Consolidated_Rent_Allocation_20250527.csv'
        
        print(f"Loaded {len(df)} rows from rent allocation")
        
        # Convert Month to datetime (assuming format like 'Jan-24')
        df['Date'] = pd.to_datetime(df['Month'] + '-01', format='%b-%y-%d', errors='coerce')
        
        # Clean currency columns
        df['Gross Total'] = df['Gross Total'].apply(clean_currency_string)
        df["Ryan's Rent (43%)"] = df["Ryan's Rent (43%)"].apply(clean_currency_string)
        df["Jordyn's Rent (57%)"] = df["Jordyn's Rent (57%)"].apply(clean_currency_string)
        
        # Reshape data to reflect WHO ACTUALLY PAYS THE RENT
        rent_records = []
        
        for idx, row in df.iterrows():
            total_rent = row['Gross Total']
            ryan_share = row["Ryan's Rent (43%)"]
            jordyn_share = row["Jordyn's Rent (57%)"]
            original_row = row['Original_Row']
            
            # Ryan's record - he pays the FULL rent but only owes his share
            rent_records.append({
                'Name': 'Ryan',
                'Date of Purchase': row['Date'],
                'Description': f"Rent for {row['Month']} (paid full ${total_rent:.2f})",
                'Actual Amount': total_rent,
                'Allowed Amount': ryan_share,
                'Source': 'Rent',
                'Original_Row': original_row,
                'Source_File': 'Consolidated_Rent_Allocation_20250527.csv'
            })
            
            # Jordyn's record - she pays NOTHING but owes her share
            rent_records.append({
                'Name': 'Jordyn',
                'Date of Purchase': row['Date'],
                'Description': f"Rent for {row['Month']} (Ryan paid, Jordyn owes)",
                'Actual Amount': 0.0,
                'Allowed Amount': jordyn_share,
                'Source': 'Rent',
                'Original_Row': original_row,
                'Source_File': 'Consolidated_Rent_Allocation_20250527.csv'
            })
        
        rent_df = pd.DataFrame(rent_records)
        return rent_df
        
    except Exception as e:
        print(f"Error loading rent data: {e}")
        return None

def filter_data_by_date_enhanced(df, start_date, data_type):
    """Filter data to include only transactions from start_date onward with detailed tracking"""
    print(f"\n--- Filtering {data_type} data ---")
    initial_count = len(df)
    print(f"Initial {data_type} records: {initial_count}")
    
    # Filter by date
    date_filtered = df[df['Date of Purchase'] >= start_date].copy()
    print(f"After date filter (>= {start_date.date()}): {len(date_filtered)} (removed {initial_count - len(date_filtered)})")
    
    # Filter out Master and Joint Finance transactions
    before_desc_filter = len(date_filtered)
    description_filtered = date_filtered[
        ~date_filtered['Description'].str.contains('Master|Joint Finance', case=False, na=False)
    ].copy()
    print(f"After excluding Master/Joint Finance: {len(description_filtered)} (removed {before_desc_filter - len(description_filtered)})")
    
    # Show what we filtered out if significant
    if initial_count - len(description_filtered) > 10:
        print(f"Total filtered out: {initial_count - len(description_filtered)} transactions")
    
    return description_filtered

def create_enhanced_audit_trail():
    """Creates comprehensive audit trail with source file references"""
    
    print("="*80)
    print("ENHANCED COMPREHENSIVE AUDIT TRAIL WITH SOURCE REFERENCES")
    print("="*80)
    
    # Load data with enhanced tracking
    expense_df = load_and_process_expense_data_enhanced("data/Consolidated_Expense_History_20250622.csv")
    rent_df = load_and_process_rent_data_enhanced("data/Consolidated_Rent_Allocation_20250527.csv")
    
    if expense_df is None or rent_df is None:
        print("Error loading data files")
        return
    
    # Set clean slate date
    clean_slate_date = datetime(2024, 1, 1)
    print(f"\nClean slate starting date: {clean_slate_date.date()}")
    
    # Filter data with enhanced tracking
    filtered_expense = filter_data_by_date_enhanced(expense_df, clean_slate_date, "expense")
    filtered_rent = filter_data_by_date_enhanced(rent_df, clean_slate_date, "rent")
    
    # Combine datasets
    print(f"\n--- Combining Datasets ---")
    combined_df = pd.concat([filtered_expense, filtered_rent], ignore_index=True)
    print(f"Total combined records: {len(combined_df)}")
    
    # Calculate net effects
    combined_df['Net Effect'] = combined_df['Allowed Amount'] - combined_df['Actual Amount']
    
    # Sort by date for chronological audit trail
    combined_df['Date of Purchase'] = pd.to_datetime(combined_df['Date of Purchase'])
    combined_df = combined_df.sort_values(['Date of Purchase', 'Name'])
    combined_df = combined_df.reset_index(drop=True)
    
    # Create the enhanced audit trail
    audit_trail = []
    running_balance_ryan = 0
    running_balance_jordyn = 0
    
    print(f"\nProcessing {len(combined_df)} transactions for audit trail...")
    
    for idx, row in combined_df.iterrows():
        # Extract transaction details
        trans_date = row['Date of Purchase']
        person = row['Name']
        description = row['Description']
        actual_paid = row['Actual Amount']
        allowed_share = row['Allowed Amount']
        net_effect = row['Net Effect']
        source = row['Source']
        original_row = row['Original_Row']
        source_file = row['Source_File']
        
        # Determine transaction type and explanation
        if source == 'Rent':
            if person == 'Ryan' and actual_paid > 0:
                trans_type = "Rent Payment (Full)"
                explanation = f"Ryan paid full rent ${actual_paid:,.2f}, his share is ${allowed_share:,.2f}"
            elif person == 'Jordyn' and actual_paid == 0:
                trans_type = "Rent Share Owed"
                explanation = f"Jordyn owes her rent share ${allowed_share:,.2f}"
            else:
                trans_type = "Rent"
                explanation = f"Rent transaction"
        else:  # Expense
            if allowed_share == 0:
                trans_type = "Personal Expense"
                explanation = f"{person} personal expense - not shared"
            elif actual_paid > 0 and allowed_share > 0:
                if actual_paid == allowed_share:
                    trans_type = "Split Expense (Equal)"
                    explanation = f"{person} paid ${actual_paid:,.2f} for their exact share"
                else:
                    trans_type = "Shared Expense"
                    explanation = f"{person} paid ${actual_paid:,.2f}, their share is ${allowed_share:,.2f}"
            elif actual_paid == 0 and allowed_share > 0:
                trans_type = "Expense Share"
                explanation = f"{person} owes ${allowed_share:,.2f} for shared expense"
            else:
                trans_type = "Other"
                explanation = "See amounts"
        
        # Update running balances
        if person == 'Ryan':
            running_balance_ryan += net_effect
            current_balance_display = running_balance_ryan
        else:
            running_balance_jordyn += net_effect
            current_balance_display = running_balance_jordyn
        
        # Create enhanced audit trail entry
        audit_entry = {
            'Transaction_Number': idx + 1,
            'Date': trans_date.strftime('%Y-%m-%d'),
            'Person': person,
            'Transaction_Type': trans_type,
            'Description': description[:60] + '...' if len(str(description)) > 60 else description,
            'Amount_Paid': actual_paid,
            'Share_Owed': allowed_share,
            'Net_Effect': net_effect,
            'Running_Balance': current_balance_display,
            'Source_File': source_file,
            'Original_Row': original_row,
            'Explanation': explanation,
            'Source': source
        }
        
        audit_trail.append(audit_entry)
    
    # Convert to DataFrame
    audit_df = pd.DataFrame(audit_trail)
    
    # Calculate final positions
    final_ryan = running_balance_ryan
    final_jordyn = running_balance_jordyn
    
    print("\n" + "="*80)
    print("ENHANCED AUDIT TRAIL SUMMARY")
    print("="*80)
    
    print(f"\nFinal Balances:")
    print(f"Ryan: ${final_ryan:,.2f}")
    print(f"Jordyn: ${final_jordyn:,.2f}")
    
    # Interpret the results
    print("\nInterpretation:")
    if final_ryan < 0:
        print(f"Ryan is owed ${abs(final_ryan):,.2f}")
    else:
        print(f"Ryan owes ${final_ryan:,.2f}")
        
    if final_jordyn < 0:
        print(f"Jordyn is owed ${abs(final_jordyn):,.2f}")
    else:
        print(f"Jordyn owes ${final_jordyn:,.2f}")
    
    # The key reconciliation
    print("\n" + "="*40)
    print("FINAL RECONCILIATION:")
    print("="*40)
    if final_ryan < 0 and final_jordyn > 0:
        print(f"Jordyn owes Ryan: ${final_jordyn:,.2f}")
    elif final_jordyn < 0 and final_ryan > 0:
        print(f"Ryan owes Jordyn: ${final_ryan:,.2f}")
    else:
        print("Complex situation - see individual balances above")
    
    # Save the enhanced audit trail
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audit_filename = f"enhanced_audit_trail_{timestamp}.csv"
    audit_df.to_csv(audit_filename, index=False)
    print(f"\nEnhanced audit trail saved to: {audit_filename}")
    
    # Show sample with source references
    print(f"\nSample transactions with source file references:")
    print(audit_df[['Transaction_Number', 'Date', 'Person', 'Source_File', 'Original_Row', 'Amount_Paid', 'Running_Balance']].head(10).to_string(index=False))
    
    return audit_df

if __name__ == "__main__":
    # Generate the enhanced audit trail
    audit_df = create_enhanced_audit_trail()
    
    if audit_df is not None:
        print("\n" + "="*80)
        print("ENHANCED AUDIT TRAIL COMPLETE")
        print("="*80)
        print("\nYou now have:")
        print("1. Complete audit trail with source file references")
        print("2. Original row numbers for easy verification")
        print("3. Detailed filtering tracking")
        print("4. All transactions accounted for")
        print("\nEach transaction shows exactly which file and row it came from.")
