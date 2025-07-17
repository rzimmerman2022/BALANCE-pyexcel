"""
Diagnostic script to understand the reconciliation imbalance
"""
import pandas as pd
from pathlib import Path

def main():
    print("=== DIAGNOSING RECONCILIATION ISSUES ===")
    
    # Load the most recent detailed results
    try:
        details = pd.read_csv("reconciliation_details_20250623_002813.csv")
    except:
        try:
            details = pd.read_csv("reconciliation_details_20250623_000922.csv")
        except:
            print("Error: Could not find recent reconciliation results. Running main script first...")
            return
    
    print(f"Total transactions loaded: {len(details)}")
    
    # Check rent transactions specifically
    print("\n=== RENT ANALYSIS ===")
    rent_trans = details[details['Source'] == 'Rent']
    print(f"Total rent transactions: {len(rent_trans)}")
    print("\nRent by person:")
    rent_summary = rent_trans.groupby('Name')[['Actual Amount', 'Allowed Amount', 'Net Effect']].sum()
    print(rent_summary)
    
    # Check if actual equals allowed for rent (which shouldn't be the case)
    rent_discrepancy = rent_trans[rent_trans['Actual Amount'] != rent_trans['Allowed Amount']]
    print(f"\nRent transactions where actual != allowed: {len(rent_discrepancy)}")
    
    # Look for the imbalance source
    print("\n=== SYSTEM BALANCE ANALYSIS ===")
    total_allowed = details['Allowed Amount'].sum()
    total_actual = details['Actual Amount'].sum()
    print(f"Sum of all Allowed Amounts: ${total_allowed:,.2f}")
    print(f"Sum of all Actual Amounts: ${total_actual:,.2f}")
    print(f"Difference: ${total_allowed - total_actual:,.2f}")
    
    # This difference should equal the system imbalance
    net_effects_sum = details['Net Effect'].sum()
    print(f"Sum of Net Effects: ${net_effects_sum:,.2f}")
    
    # Check expense transactions
    print("\n=== EXPENSE ANALYSIS ===")
    expense_trans = details[details['Source'] == 'Expense']
    expense_summary = expense_trans.groupby('Name')[['Actual Amount', 'Allowed Amount', 'Net Effect']].sum()
    print("Expenses by person:")
    print(expense_summary)
    
    # Look at rent data structure
    print("\n=== RENT DATA INVESTIGATION ===")
    print("Sample rent transactions:")
    print(rent_trans[['Name', 'Date of Purchase', 'Description', 'Actual Amount', 'Allowed Amount', 'Net Effect']].head(6))
    
    # Check if the issue is that rent is double-counted or incorrectly allocated
    print(f"\nTotal rent actual payments: ${rent_trans['Actual Amount'].sum():,.2f}")
    print(f"Total rent allowed amounts: ${rent_trans['Allowed Amount'].sum():,.2f}")
    
    # Look at the original rent file
    print("\n=== ORIGINAL RENT FILE ANALYSIS ===")
    try:
        rent_df = pd.read_csv("data/Consolidated_Rent_Allocation_20250527.csv")
        print(f"Original rent file has {len(rent_df)} rows")
        
        # Clean currency function
        def clean_currency_string(value):
            if pd.isna(value) or value == '':
                return 0.0
            str_val = str(value).strip()
            if str_val.startswith('(') and str_val.endswith(')'):
                str_val = str_val[1:-1]
                is_negative = True
            else:
                is_negative = False
            cleaned = str_val.replace('$', '').replace(',', '').replace(' ', '')
            if cleaned == '-' or cleaned == '':
                return 0.0
            try:
                result = float(cleaned)
                return -result if is_negative else result
            except ValueError:
                return 0.0
        
        # Check 2024 data
        rent_2024 = rent_df[rent_df['Month'].str.contains('24', na=False)]
        print(f"2024 rent records: {len(rent_2024)}")
        
        if len(rent_2024) > 0:
            sample_row = rent_2024.iloc[0]
            gross_total = clean_currency_string(sample_row["Gross Total"])
            ryan_share = clean_currency_string(sample_row["Ryan's Rent (43%)"])
            jordyn_share = clean_currency_string(sample_row["Jordyn's Rent (57%)"])
            
            print(f"\nSample month: {sample_row['Month']}")
            print(f"Gross Total: ${gross_total:,.2f}")
            print(f"Ryan's Share (43%): ${ryan_share:,.2f}")
            print(f"Jordyn's Share (57%): ${jordyn_share:,.2f}")
            print(f"Shares sum: ${ryan_share + jordyn_share:,.2f}")
            
            # This reveals the core issue - we need to know WHO ACTUALLY PAYS the rent
            print(f"\n*** CRITICAL QUESTION ***")
            print(f"Does Ryan pay the full ${gross_total:,.2f} rent each month?")
            print(f"Or do they each pay their individual shares?")
    
    except Exception as e:
        print(f"Error reading rent file: {e}")
    
    # NEW ANALYSIS - Find the source of the $9,603 imbalance
    print("\n=== IMBALANCE SOURCE INVESTIGATION ===")
    
    # Look for transactions where allowed amount seems incorrect
    print("Looking for potential data issues...")
    
    # Check for zero allowed amounts
    zero_allowed = details[details['Allowed Amount'] == 0]
    print(f"Transactions with $0 allowed amount: {len(zero_allowed)}")
    if len(zero_allowed) > 0:
        print("Sample zero-allowed transactions:")
        print(zero_allowed[['Name', 'Description', 'Actual Amount', 'Allowed Amount']].head())
    
    # Check for very large discrepancies between actual and allowed
    details['Abs_Discrepancy'] = abs(details['Net Effect'])
    large_discrepancies = details[details['Abs_Discrepancy'] > 100].sort_values('Abs_Discrepancy', ascending=False)
    
    print(f"\nTransactions with large discrepancies (>$100):")
    print(f"Count: {len(large_discrepancies)}")
    if len(large_discrepancies) > 0:
        print("Top 10 largest discrepancies:")
        print(large_discrepancies[['Name', 'Description', 'Actual Amount', 'Allowed Amount', 'Net Effect']].head(10))
    
    # Analyze the expense data for patterns
    print(f"\n=== EXPENSE PATTERN ANALYSIS ===")
    expense_only = details[details['Source'] == 'Expense']
    
    # Look at the distribution of allowed vs actual amounts
    print("Expense summary statistics:")
    print("Actual Amount stats:")
    print(expense_only['Actual Amount'].describe())
    print("\nAllowed Amount stats:")
    print(expense_only['Allowed Amount'].describe())
    
    # Check if there's a systematic issue with allowed amounts
    expenses_where_allowed_zero = expense_only[expense_only['Allowed Amount'] == 0]
    expenses_where_allowed_equals_actual = expense_only[expense_only['Allowed Amount'] == expense_only['Actual Amount']]
    
    print(f"\nExpenses where allowed = $0: {len(expenses_where_allowed_zero)}")
    print(f"Expenses where allowed = actual: {len(expenses_where_allowed_equals_actual)}")
    
    # The key insight: if most expenses have allowed=actual, then the imbalance
    # comes from expenses where someone spent money but it wasn't "allowed"
    total_unallowed_spending = expense_only[expense_only['Allowed Amount'] == 0]['Actual Amount'].sum()
    print(f"Total spending on unallowed expenses: ${total_unallowed_spending:,.2f}")
    
    # Break down unallowed spending by person
    if len(expenses_where_allowed_zero) > 0:
        unallowed_by_person = expenses_where_allowed_zero.groupby('Name')['Actual Amount'].sum()
        print("Unallowed spending by person:")
        for person, amount in unallowed_by_person.items():
            print(f"  {person}: ${amount:,.2f}")
    
    print(f"\n=== FINAL DIAGNOSIS ===")
    print(f"System imbalance: ${details['Net Effect'].sum():,.2f}")
    print(f"This likely represents spending on items that were deemed 'unallowed'")
    print(f"or personal expenses that shouldn't be shared.")
    
    # Check if the imbalance matches the unallowed spending
    if abs(abs(details['Net Effect'].sum()) - total_unallowed_spending) < 1:
        print("✓ The system imbalance exactly matches unallowed spending!")
        print("This suggests the reconciliation is working correctly.")
    else:
        print("⚠ The imbalance doesn't match unallowed spending - need further investigation.")

if __name__ == "__main__":
    main()
