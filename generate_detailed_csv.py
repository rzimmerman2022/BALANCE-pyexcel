#!/usr/bin/env python3
"""
Generate a detailed CSV with crystal clear balance calculations
Shows exactly how each transaction affects the balance
"""

import pandas as pd
import re
from pathlib import Path
from datetime import datetime

def parse_amount(amount_str):
    """Parse amount string, handling $ and commas"""
    if not amount_str:
        return 0.0
    cleaned = re.sub(r'[$,]', '', str(amount_str).strip())
    try:
        return float(cleaned)
    except:
        return 0.0

def generate_detailed_balance_csv(input_file, output_file=None):
    """
    Generate a detailed CSV showing every calculation
    """
    print("="*70)
    print("GENERATING DETAILED BALANCE CSV")
    print("="*70)
    
    # Read the expense file
    df = pd.read_csv(input_file)
    
    # Create a new detailed dataframe
    detailed_data = []
    running_balance = 0.0
    
    # Track totals for summary
    ryan_shared_total = 0
    jordyn_shared_total = 0
    ryan_personal_total = 0
    jordyn_personal_total = 0
    
    for _, row in df.iterrows():
        # Parse the data
        name = row.get('Name', '').strip()
        if not name:
            continue
            
        date = row.get('Date of Purchase', '')
        merchant = row.get('Merchant', '')
        description = row.get('Description', row.get(' Description ', ''))
        actual = parse_amount(row.get('Actual Amount', row.get(' Actual Amount ', '0')))
        allowed = parse_amount(row.get('Allowed Amount', row.get(' Allowed Amount ', '0')))
        
        # Determine if shared
        is_shared = allowed > 0
        
        # Calculate shares
        ryan_share = 0
        jordyn_share = 0
        balance_change = 0
        calculation_notes = ""
        
        if is_shared:
            ryan_share = allowed * 0.43
            jordyn_share = allowed * 0.57
            
            if name == 'Ryan':
                balance_change = jordyn_share
                calculation_notes = f"Ryan paid ${actual:.2f}, Jordyn owes her 57% share (${jordyn_share:.2f})"
                ryan_shared_total += allowed
            elif name == 'Jordyn':
                balance_change = -ryan_share
                calculation_notes = f"Jordyn paid ${actual:.2f}, reduces Ryan's debt by his 43% share (${ryan_share:.2f})"
                jordyn_shared_total += allowed
        else:
            calculation_notes = "Personal expense - no sharing"
            if name == 'Ryan':
                ryan_personal_total += actual
            else:
                jordyn_personal_total += actual
        
        # Update running balance
        running_balance += balance_change
        
        # Determine who owes whom
        if running_balance > 0:
            balance_status = f"Jordyn owes Ryan ${running_balance:.2f}"
        elif running_balance < 0:
            balance_status = f"Ryan owes Jordyn ${abs(running_balance):.2f}"
        else:
            balance_status = "Even"
        
        # Create detailed row
        detailed_row = {
            'Date': date,
            'Who_Paid': name,
            'Merchant': merchant,
            'Description': description,
            'Actual_Amount': f"${actual:.2f}",
            'Allowed_Amount': f"${allowed:.2f}" if allowed > 0 else "$0.00",
            'Is_Shared': "SHARED" if is_shared else "PERSONAL",
            'Ryan_43%_Share': f"${ryan_share:.2f}" if is_shared else "N/A",
            'Jordyn_57%_Share': f"${jordyn_share:.2f}" if is_shared else "N/A",
            'Balance_Change': f"+${balance_change:.2f}" if balance_change > 0 else f"${balance_change:.2f}" if balance_change < 0 else "$0.00",
            'Running_Balance': f"${running_balance:.2f}",
            'Who_Owes_Whom': balance_status,
            'Calculation_Notes': calculation_notes
        }
        
        detailed_data.append(detailed_row)
    
    # Create DataFrame
    detailed_df = pd.DataFrame(detailed_data)
    
    # Add summary at the end
    total_shared = ryan_shared_total + jordyn_shared_total
    ryan_should_pay = total_shared * 0.43
    jordyn_should_pay = total_shared * 0.57
    
    # Add blank row
    detailed_data.append({col: '' for col in detailed_df.columns})
    
    # Add summary rows
    summary_rows = [
        {
            'Date': 'SUMMARY',
            'Who_Paid': '',
            'Merchant': 'Total Shared Expenses',
            'Description': '',
            'Actual_Amount': f"${total_shared:.2f}",
            'Allowed_Amount': '',
            'Is_Shared': '',
            'Ryan_43%_Share': f"Should: ${ryan_should_pay:.2f}",
            'Jordyn_57%_Share': f"Should: ${jordyn_should_pay:.2f}",
            'Balance_Change': '',
            'Running_Balance': '',
            'Who_Owes_Whom': '',
            'Calculation_Notes': 'Total of all shared expenses (AllowedAmount > 0)'
        },
        {
            'Date': '',
            'Who_Paid': 'Ryan',
            'Merchant': 'Ryan Paid (Shared)',
            'Description': '',
            'Actual_Amount': f"${ryan_shared_total:.2f}",
            'Allowed_Amount': '',
            'Is_Shared': '',
            'Ryan_43%_Share': '',
            'Jordyn_57%_Share': '',
            'Balance_Change': '',
            'Running_Balance': '',
            'Who_Owes_Whom': '',
            'Calculation_Notes': f"Overpaid by ${ryan_shared_total - ryan_should_pay:.2f}"
        },
        {
            'Date': '',
            'Who_Paid': 'Jordyn',
            'Merchant': 'Jordyn Paid (Shared)',
            'Description': '',
            'Actual_Amount': f"${jordyn_shared_total:.2f}",
            'Allowed_Amount': '',
            'Is_Shared': '',
            'Ryan_43%_Share': '',
            'Jordyn_57%_Share': '',
            'Balance_Change': '',
            'Running_Balance': '',
            'Who_Owes_Whom': '',
            'Calculation_Notes': f"Underpaid by ${jordyn_should_pay - jordyn_shared_total:.2f}"
        },
        {
            'Date': '',
            'Who_Paid': '',
            'Merchant': '',
            'Description': '',
            'Actual_Amount': '',
            'Allowed_Amount': '',
            'Is_Shared': '',
            'Ryan_43%_Share': '',
            'Jordyn_57%_Share': '',
            'Balance_Change': '',
            'Running_Balance': '',
            'Who_Owes_Whom': '',
            'Calculation_Notes': ''
        },
        {
            'Date': 'FINAL',
            'Who_Paid': '',
            'Merchant': 'BALANCE',
            'Description': '',
            'Actual_Amount': '',
            'Allowed_Amount': '',
            'Is_Shared': '',
            'Ryan_43%_Share': '',
            'Jordyn_57%_Share': '',
            'Balance_Change': '',
            'Running_Balance': f"${abs(running_balance):.2f}",
            'Who_Owes_Whom': balance_status,
            'Calculation_Notes': 'Based on all shared expenses where AllowedAmount > 0'
        }
    ]
    
    for row in summary_rows:
        detailed_data.append(row)
    
    # Create final DataFrame
    final_df = pd.DataFrame(detailed_data)
    
    # Save to CSV
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"detailed_balance_{timestamp}.csv"
    
    final_df.to_csv(output_file, index=False)
    
    # Print summary
    print(f"\n✅ Detailed CSV saved to: {output_file}")
    print(f"\nSUMMARY:")
    print(f"  Total Shared Expenses: ${total_shared:,.2f}")
    print(f"  Ryan Paid (Shared): ${ryan_shared_total:,.2f}")
    print(f"  Jordyn Paid (Shared): ${jordyn_shared_total:,.2f}")
    print(f"\n  Ryan Should Pay (43%): ${ryan_should_pay:,.2f}")
    print(f"  Jordyn Should Pay (57%): ${jordyn_should_pay:,.2f}")
    print(f"\n  FINAL BALANCE: {balance_status}")
    
    return final_df

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate detailed balance CSV')
    parser.add_argument('input_file', help='Path to expense history CSV')
    parser.add_argument('-o', '--output', help='Output file name (optional)')
    
    args = parser.parse_args()
    
    # For testing without command line
    if not hasattr(args, 'input_file'):
        input_file = r"C:\BALANCE\New Master - New Joint Couple Finances (2024).xlsx - Expense History.csv"
        output_file = "detailed_balance_analysis.csv"
    else:
        input_file = args.input_file
        output_file = args.output
    
    if Path(input_file).exists():
        generate_detailed_balance_csv(input_file, output_file)
    else:
        print(f"Error: File not found: {input_file}")
