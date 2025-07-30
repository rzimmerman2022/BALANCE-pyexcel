"""
Comprehensive Line-by-Line Audit Trail Generator
This creates the detailed audit trail showing every transaction and its impact on the balance
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
        return 0.0

def create_comprehensive_audit_trail():
    """
    Creates a complete line-by-line audit trail showing:
    1. Every transaction (both expenses and rent)
    2. Who paid what
    3. What each person's share should be
    4. The running balance after each transaction
    5. Clear explanations for each line
    6. Source file and row number for each transaction
    """
    
    print("="*80)
    print("GENERATING COMPREHENSIVE LINE-BY-LINE AUDIT TRAIL")
    print("="*80)
      # Load the most recent reconciliation details
    try:
        details = pd.read_csv("reconciliation_details_20250624_003911.csv")
    except:
        try:
            details = pd.read_csv("reconciliation_details_20250623_002813.csv")
        except:
            print("Error: Could not find reconciliation details. Please run the main script first.")
            return
    
    # Also load the original source files to get row references
    expense_file = "data/Consolidated_Expense_History_20250622.csv"
    rent_file = "data/Consolidated_Rent_Allocation_20250527.csv"
    
    try:
        # Load original files with row indices
        original_expenses = pd.read_csv(expense_file)
        original_rent = pd.read_csv(rent_file)
        
        print(f"Original expense file has {len(original_expenses)} rows")
        print(f"Original rent file has {len(original_rent)} rows")
        
        # Clean and prepare original expense data for matching
        original_expenses.columns = original_expenses.columns.str.strip()
        original_expenses = original_expenses[original_expenses['Name'].notna() & ~original_expenses['Name'].str.contains('Name', na=False)]
        original_expenses['Name'] = original_expenses['Name'].str.strip()
        original_expenses.loc[original_expenses['Name'].str.contains('Jordyn', case=False, na=False), 'Name'] = 'Jordyn'
        original_expenses.loc[original_expenses['Name'].str.contains('Ryan', case=False, na=False), 'Name'] = 'Ryan'
        original_expenses = original_expenses[original_expenses['Name'].isin(['Ryan', 'Jordyn'])]
        original_expenses['Date of Purchase'] = pd.to_datetime(original_expenses['Date of Purchase'], errors='coerce')
        
        print(f"Cleaned expense file has {len(original_expenses)} valid rows")
        
    except Exception as e:
        print(f"Warning: Could not load original files for row references: {e}")
        original_expenses = None
        original_rent = None
    
    # Sort by date to show chronological flow
    details['Date of Purchase'] = pd.to_datetime(details['Date of Purchase'])
    details = details.sort_values(['Date of Purchase', 'Name'])
    details = details.reset_index(drop=True)
    
    # Create the comprehensive audit trail
    audit_trail = []
    running_balance_ryan = 0
    running_balance_jordyn = 0
    
    print(f"\nProcessing {len(details)} transactions...")
    
    for idx, row in details.iterrows():
        # Extract transaction details
        trans_date = row['Date of Purchase']
        person = row['Name']
        description = row['Description']
        actual_paid = row['Actual Amount']
        allowed_share = row['Allowed Amount']
        net_effect = row['Net Effect']
        source = row['Source']
        
        # Find source file and row number
        source_file = ""
        source_row = ""
        
        if original_expenses is not None and source == 'Expense':
            # Try to match this transaction to the original expense file
            # Match by person, date, and amount
            matches = original_expenses[
                (original_expenses['Name'] == person) &
                (original_expenses['Date of Purchase'] == trans_date) &
                (abs(original_expenses['Actual Amount'].apply(lambda x: clean_currency_string(x)) - actual_paid) < 0.01)
            ]
            
            if len(matches) > 0:
                source_file = "Consolidated_Expense_History_20250622.csv"
                source_row = f"Row {matches.index[0] + 2}"  # +2 because Excel starts at 1 and has header
            else:
                source_file = "Consolidated_Expense_History_20250622.csv"
                source_row = "Match not found"
                
        elif source == 'Rent':
            source_file = "Consolidated_Rent_Allocation_20250527.csv"
            # For rent, try to match by month
            month_str = trans_date.strftime('%b-%y')
            if original_rent is not None:
                rent_matches = original_rent[original_rent['Month'].str.contains(month_str, na=False)]
                if len(rent_matches) > 0:
                    source_row = f"Row {rent_matches.index[0] + 2}"
                else:
                    source_row = "Match not found"
            else:
                source_row = "Unknown"
        
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
        # Negative net effect = overpaid (owed money)
        # Positive net effect = underpaid (owes money)
        if person == 'Ryan':
            running_balance_ryan += net_effect
            current_balance_display = running_balance_ryan
        else:
            running_balance_jordyn += net_effect
            current_balance_display = running_balance_jordyn
        
        # Create audit trail entry
        audit_entry = {
            'Transaction_Number': idx + 1,
            'Date': trans_date.strftime('%Y-%m-%d'),
            'Person': person,
            'Transaction_Type': trans_type,
            'Description': description[:50] + '...' if len(str(description)) > 50 else description,
            'Amount_Paid': actual_paid,
            'Share_Owed': allowed_share,
            'Net_Effect': net_effect,
            'Running_Balance': current_balance_display,
            'Source_File': source_file,
            'Source_Row': source_row,
            'Explanation': explanation,
            'Source': source
        }
        
        audit_trail.append(audit_entry)
    
    # Convert to DataFrame
    audit_df = pd.DataFrame(audit_trail)
    
    # Add summary section at the end
    print("\n" + "="*80)
    print("AUDIT TRAIL SUMMARY")
    print("="*80)
    
    # Calculate final positions
    final_ryan = running_balance_ryan
    final_jordyn = running_balance_jordyn
    
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
    
    # Save the detailed audit trail
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audit_filename = f"complete_audit_trail_{timestamp}.csv"
    audit_df.to_csv(audit_filename, index=False)
    print(f"\nDetailed audit trail saved to: {audit_filename}")
    
    # Create a verification summary
    create_verification_summary(audit_df, final_ryan, final_jordyn)
    
    return audit_df

def create_verification_summary(audit_df, final_ryan, final_jordyn):
    """Create a summary that allows for easy verification of the calculations"""
    
    print("\n" + "="*80)
    print("VERIFICATION SUMMARY")
    print("="*80)
    
    # Group by person and transaction type
    print("\nTransaction counts by type and person:")
    type_summary = audit_df.groupby(['Person', 'Transaction_Type']).size().reset_index(name='Count')
    print(type_summary.to_string(index=False))
    
    # Sum amounts by category
    print("\n\nAmount totals by person:")
    amount_summary = audit_df.groupby('Person').agg({
        'Amount_Paid': 'sum',
        'Share_Owed': 'sum',
        'Net_Effect': 'sum'
    }).round(2)
    print(amount_summary.to_string())
    
    # Verify the math
    print("\n\nMathematical Verification:")
    for person in ['Ryan', 'Jordyn']:
        person_data = audit_df[audit_df['Person'] == person]
        total_paid = person_data['Amount_Paid'].sum()
        total_owed = person_data['Share_Owed'].sum()
        total_net = person_data['Net_Effect'].sum()
        calculated_net = total_owed - total_paid
        
        print(f"\n{person}:")
        print(f"  Total Paid: ${total_paid:,.2f}")
        print(f"  Total Share Owed: ${total_owed:,.2f}")
        print(f"  Calculated Net (Owed - Paid): ${calculated_net:,.2f}")
        print(f"  Actual Net Effect Sum: ${total_net:,.2f}")
        print(f"  Verification: {'✓ MATCHES' if abs(calculated_net - total_net) < 0.01 else '✗ MISMATCH'}")
    
    # Cross-verification
    print(f"\n\nCross-Verification:")
    print(f"Ryan's final balance from running total: ${final_ryan:,.2f}")
    print(f"Jordyn's final balance from running total: ${final_jordyn:,.2f}")
    print(f"System balance check: ${final_ryan + final_jordyn:,.2f} (should be the system imbalance)")
    
    # Show some sample transactions for manual verification
    print("\n\nSample transactions for manual verification:")
    print("\nFirst 10 transactions:")
    first_10 = audit_df.head(10)[['Transaction_Number', 'Date', 'Person', 'Transaction_Type', 'Amount_Paid', 'Share_Owed', 'Net_Effect', 'Running_Balance']]
    print(first_10.to_string(index=False))
    
    print("\n\nLast 10 transactions:")
    last_10 = audit_df.tail(10)[['Transaction_Number', 'Date', 'Person', 'Transaction_Type', 'Amount_Paid', 'Share_Owed', 'Net_Effect', 'Running_Balance']]
    print(last_10.to_string(index=False))
    
    # Create a pivoted view for easier reading
    create_monthly_summary(audit_df)

def create_monthly_summary(audit_df):
    """Create a monthly summary for easier pattern recognition"""
    
    print("\n" + "="*80)
    print("MONTHLY SUMMARY VIEW")
    print("="*80)
    
    # Extract month from date
    audit_df['Month'] = pd.to_datetime(audit_df['Date']).dt.to_period('M')
    
    # Summarize by month and person
    monthly_summary = audit_df.groupby(['Month', 'Person']).agg({
        'Amount_Paid': 'sum',
        'Share_Owed': 'sum',
        'Net_Effect': 'sum'
    }).round(2)
    
    print("\nMonthly breakdown (first 12 months):")
    print(monthly_summary.head(24).to_string())  # Show first 12 months (24 rows for 2 people)
    
    # Save monthly summary
    monthly_summary.to_csv('monthly_summary_audit.csv')
    print(f"\nMonthly summary saved to: monthly_summary_audit.csv")

def create_transaction_lookup():
    """Create a lookup table for finding specific transactions"""
    
    print("\n" + "="*80)
    print("CREATING TRANSACTION LOOKUP TOOLS")
    print("="*80)
    
    try:
        # Find the most recent audit trail file
        audit_files = [f for f in os.listdir('.') if f.startswith('complete_audit_trail_') and f.endswith('.csv')]
        if not audit_files:
            print("No audit trail files found")
            return
            
        latest_file = sorted(audit_files)[-1]
        audit_df = pd.read_csv(latest_file)
        
        # Create lookup by largest amounts
        print("\nLargest payments made:")
        largest_payments = audit_df.nlargest(10, 'Amount_Paid')[['Transaction_Number', 'Date', 'Person', 'Description', 'Amount_Paid', 'Transaction_Type']]
        print(largest_payments.to_string(index=False))
        
        # Transactions with biggest impact on balance
        print("\n\nTransactions with biggest impact on balance:")
        audit_df['Abs_Net_Effect'] = audit_df['Net_Effect'].abs()
        largest_impacts = audit_df.nlargest(10, 'Abs_Net_Effect')[['Transaction_Number', 'Date', 'Person', 'Description', 'Net_Effect', 'Transaction_Type']]
        print(largest_impacts.to_string(index=False))
        
        # Rent payments summary
        print("\n\nAll rent payments:")
        rent_transactions = audit_df[audit_df['Source'] == 'Rent'].sort_values('Date')
        rent_summary = rent_transactions[['Date', 'Person', 'Amount_Paid', 'Share_Owed', 'Net_Effect']]
        print(rent_summary.to_string(index=False))
        
    except Exception as e:
        print(f"Could not create lookup tools: {e}")

if __name__ == "__main__":
    # Generate the comprehensive audit trail
    audit_df = create_comprehensive_audit_trail()
    
    # Additional analysis - find largest transactions
    if audit_df is not None:
        create_transaction_lookup()
        
        print("\n" + "="*80)
        print("AUDIT TRAIL COMPLETE")
        print("="*80)
        print("\nYou now have:")
        print("1. Complete line-by-line audit trail CSV")
        print("2. Mathematical verification of all calculations")
        print("3. Monthly summary breakdown")
        print("4. Transaction lookup tools")
        print("\nEvery transaction is accounted for and can be verified.")
        print("The running balance shows exactly how we arrive at the final numbers.")
        print("\nThe CSV file can be opened in Excel for detailed line-by-line review.")
