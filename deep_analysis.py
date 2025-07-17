"""
Deep dive analysis to find the exact source of the system imbalance
"""
import pandas as pd

def main():
    print("=== DEEP DIVE IMBALANCE ANALYSIS ===")
    
    # Load the latest enhanced results
    try:
        details = pd.read_csv("enhanced_audit_trail_20250624_004959.csv")
        print("Using enhanced audit trail data")
    except:
        try:
            details = pd.read_csv("reconciliation_details_20250624_003911.csv")
            print("Using standard reconciliation data")
        except:
            details = pd.read_csv("reconciliation_details_20250623_002813.csv")
            print("Using older reconciliation data")
    
    print(f"Total transactions in analysis: {len(details)}")
    print(f"Total system imbalance: ${details['Net_Effect'].sum():.2f}")
    
    # Let's also check the original source files to see what we're missing
    print(f"\n=== CHECKING ORIGINAL SOURCE FILES ===")
    
    # Check expense file
    expense_file = pd.read_csv("data/Consolidated_Expense_History_20250622.csv")
    print(f"Original expense file total rows: {len(expense_file)}")
    
    # Count valid expense rows (excluding headers)
    valid_expense = expense_file[expense_file['Name'].notna() & ~expense_file['Name'].str.contains('Name', na=False)]
    print(f"Valid expense rows (excluding headers): {len(valid_expense)}")
    
    # Count 2024+ expense rows
    expense_file['Date of Purchase'] = pd.to_datetime(expense_file['Date of Purchase'], errors='coerce')
    expense_2024_plus = expense_file[expense_file['Date of Purchase'] >= '2024-01-01']
    print(f"Expense rows from 2024+: {len(expense_2024_plus)}")
    
    # Count by person in 2024+ data
    if len(expense_2024_plus) > 0:
        person_counts = expense_2024_plus['Name'].value_counts()
        print(f"2024+ expense breakdown by person:")
        print(person_counts)
    
    print(f"\n*** POTENTIAL ISSUE ***")
    print(f"We should have ~{len(expense_2024_plus)} expense transactions from 2024+")
    print(f"But our audit trail only has {len(details[details['Source'] == 'Expense'])} expense transactions")
    print(f"We may be missing {len(expense_2024_plus) - len(details[details['Source'] == 'Expense'])} transactions!")
    
    # Separate rent and expense transactions
    rent_trans = details[details['Source'] == 'Rent']
    expense_trans = details[details['Source'] == 'Expense']
    
    print(f"\nRent net effect: ${rent_trans['Net_Effect'].sum():.2f}")
    print(f"Expense net effect: ${expense_trans['Net_Effect'].sum():.2f}")
    
    # The rent should balance to zero in a proper system
    # If it doesn't, that's part of our imbalance
    
    # Look at expense transactions in detail
    print(f"\n=== EXPENSE BREAKDOWN ===")
    
    # Categorize expenses
    expenses_allowed_zero = expense_trans[expense_trans['Share_Owed'] == 0]
    expenses_allowed_actual = expense_trans[expense_trans['Share_Owed'] == expense_trans['Amount_Paid']]
    expenses_partial_allowed = expense_trans[
        (expense_trans['Share_Owed'] > 0) & 
        (expense_trans['Share_Owed'] != expense_trans['Amount_Paid'])
    ]
    
    print(f"Expenses with $0 allowed: {len(expenses_allowed_zero)} (total: ${expenses_allowed_zero['Amount_Paid'].sum():.2f})")
    print(f"Expenses fully allowed: {len(expenses_allowed_actual)} (net effect: ${expenses_allowed_actual['Net_Effect'].sum():.2f})")
    print(f"Expenses partially allowed: {len(expenses_partial_allowed)} (net effect: ${expenses_partial_allowed['Net_Effect'].sum():.2f})")
    
    # The imbalance should come from:
    # 1. Expenses with $0 allowed (personal expenses)
    # 2. Expenses partially allowed (overspending)
    
    unallowed_total = expenses_allowed_zero['Amount_Paid'].sum()
    partial_overspend = expenses_partial_allowed['Net_Effect'].sum()
    
    print(f"\nUnallowed expenses: ${unallowed_total:.2f}")
    print(f"Partial overspending: ${partial_overspend:.2f}")
    print(f"Total expense imbalance: ${unallowed_total + partial_overspend:.2f}")
    
    # Check if this matches our system imbalance
    calculated_imbalance = unallowed_total + partial_overspend
    actual_imbalance = details['Net_Effect'].sum()
    
    print(f"\nCalculated imbalance: ${calculated_imbalance:.2f}")
    print(f"Actual system imbalance: ${actual_imbalance:.2f}")
    print(f"Difference: ${actual_imbalance - calculated_imbalance:.2f}")
    
    # Show some examples of partially allowed expenses
    if len(expenses_partial_allowed) > 0:
        print(f"\n=== PARTIAL ALLOWANCE EXAMPLES ===")
        print("Top 10 partially allowed expenses:")
        partial_sorted = expenses_partial_allowed.sort_values('Net_Effect', ascending=False)
        print(partial_sorted[['Person', 'Description', 'Amount_Paid', 'Share_Owed', 'Net_Effect']].head(10))
    
    # Final summary
    print(f"\n=== CORRECTED FINAL SUMMARY ===")
    
    # Calculate the true amounts owed
    ryan_data = details[details['Person'] == 'Ryan']
    jordyn_data = details[details['Person'] == 'Jordyn']
    
    ryan_net = ryan_data['Net_Effect'].sum()
    jordyn_net = jordyn_data['Net_Effect'].sum()
    
    print(f"Ryan's net effect: ${ryan_net:.2f}")
    print(f"Jordyn's net effect: ${jordyn_net:.2f}")
    print(f"System balance: ${ryan_net + jordyn_net:.2f}")
    
    # Interpretation
    if ryan_net < 0:
        print(f"\n✓ Ryan is owed ${abs(ryan_net):.2f}")
    else:
        print(f"\n✓ Ryan owes ${ryan_net:.2f}")
    
    if jordyn_net > 0:
        print(f"✓ Jordyn owes ${jordyn_net:.2f}")
    else:
        print(f"✓ Jordyn is owed ${abs(jordyn_net):.2f}")
    
    # The system imbalance represents unallowed spending
    # This should NOT be part of the reconciliation between Ryan and Jordyn
    print(f"\nNote: The ${abs(actual_imbalance):.2f} system imbalance represents")
    print("personal/unallowed expenses that should not be shared.")

if __name__ == "__main__":
    main()
