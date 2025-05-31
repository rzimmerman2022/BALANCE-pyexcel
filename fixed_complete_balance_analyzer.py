#!/usr/bin/env python3
"""
Complete Balance Analyzer - Processes BOTH rent and expense files
Shows the FULL financial picture
FIXED VERSION - Handles empty rows properly
"""

import pandas as pd
import re
from pathlib import Path
from datetime import datetime

def parse_amount(amount_str):
    """Parse amount string, handling $ and commas"""
    if not amount_str or pd.isna(amount_str):
        return 0.0
    cleaned = re.sub(r'[$,]', '', str(amount_str).strip())
    try:
        return float(cleaned)
    except:
        return 0.0

# File paths
RENT_FILE = r"C:\BALANCE\New Master - New Joint Couple Finances (2024).xlsx - Rent Allocation.csv"
EXPENSE_FILE = r"C:\BALANCE\New Master - New Joint Couple Finances (2024).xlsx - Expense History.csv"

print("="*80)
print("COMPLETE BALANCE ANALYZER - RENT + EXPENSES")
print("="*80)

# Initialize totals
ryan_owes_from_rent = 0
jordyn_paid_rent_total = 0
running_balance = 0
all_transactions = []

# PART 1: PROCESS RENT FILE
print(f"\n📊 ANALYZING RENT...")
if Path(RENT_FILE).exists():
    print(f"✅ Found rent file")
    rent_df = pd.read_csv(RENT_FILE)
    
    for _, row in rent_df.iterrows():
        month = row.get('Month', '')
        if pd.isna(month):
            continue
        month = str(month).strip()
        if not month:
            continue
            
        # Find the gross total and rent amounts
        gross_total = 0
        ryan_rent = 0
        jordyn_rent = 0
        
        for col, val in row.items():
            if pd.isna(val):
                continue
            if 'gross total' in str(col).lower():
                gross_total = parse_amount(val)
            elif 'ryan' in str(col).lower() and 'rent' in str(col).lower():
                ryan_rent = parse_amount(val)
            elif 'jordyn' in str(col).lower() and 'rent' in str(col).lower():
                jordyn_rent = parse_amount(val)
        
        if gross_total > 0:
            # Jordyn pays the full rent, Ryan owes his share
            jordyn_paid_rent_total += gross_total
            ryan_owes_from_rent += ryan_rent
            running_balance += ryan_rent  # Ryan owes this
            
            all_transactions.append({
                'Date': month,
                'Category': 'RENT',
                'Who_Paid': 'Jordyn',
                'Description': f'Rent for {month}',
                'Amount': f'${gross_total:.2f}',
                'Ryan_Owes': f'${ryan_rent:.2f}',
                'Jordyn_Owes': '$0.00',
                'Balance_Change': f'+${ryan_rent:.2f}',
                'Running_Balance': f'${running_balance:.2f}',
                'Notes': f'Jordyn pays full rent, Ryan owes 43%'
            })
            
            print(f"  {month}: Jordyn paid ${gross_total:.2f}, Ryan owes ${ryan_rent:.2f}")
    
    print(f"\n  RENT SUMMARY:")
    print(f"  Total rent paid by Jordyn: ${jordyn_paid_rent_total:,.2f}")
    print(f"  Ryan owes for rent: ${ryan_owes_from_rent:,.2f}")
else:
    print(f"❌ Rent file not found: {RENT_FILE}")

# PART 2: PROCESS EXPENSE FILE
print(f"\n💳 ANALYZING OTHER EXPENSES...")
ryan_shared_expenses = 0
jordyn_shared_expenses = 0
expense_count = 0

if Path(EXPENSE_FILE).exists():
    print(f"✅ Found expense file")
    expense_df = pd.read_csv(EXPENSE_FILE)
    
    for _, row in expense_df.iterrows():
        # Handle Name field safely
        name = row.get('Name', '')
        if pd.isna(name):
            continue
        name = str(name).strip()
        if not name:
            continue
            
        # Handle other fields safely
        date = row.get('Date of Purchase', '')
        if pd.isna(date):
            date = ''
        else:
            date = str(date)
            
        merchant = row.get('Merchant', '')
        if pd.isna(merchant):
            merchant = ''
        else:
            merchant = str(merchant)
            
        actual = parse_amount(row.get('Actual Amount', row.get(' Actual Amount ', '0')))
        allowed = parse_amount(row.get('Allowed Amount', row.get(' Allowed Amount ', '0')))
        
        # Only process shared expenses
        if allowed > 0:
            expense_count += 1
            ryan_share = allowed * 0.43
            jordyn_share = allowed * 0.57
            
            if name == 'Ryan':
                ryan_shared_expenses += allowed
                balance_change = jordyn_share  # Jordyn owes her share
                running_balance += balance_change
                
                all_transactions.append({
                    'Date': date,
                    'Category': 'EXPENSE',
                    'Who_Paid': 'Ryan',
                    'Description': f'{merchant}',
                    'Amount': f'${allowed:.2f}',
                    'Ryan_Owes': '$0.00',
                    'Jordyn_Owes': f'${jordyn_share:.2f}',
                    'Balance_Change': f'+${balance_change:.2f}',
                    'Running_Balance': f'${running_balance:.2f}',
                    'Notes': f'Ryan paid, Jordyn owes 57%'
                })
            
            elif name == 'Jordyn':
                jordyn_shared_expenses += allowed
                balance_change = -ryan_share  # Reduces Ryan's debt
                running_balance += balance_change
                
                all_transactions.append({
                    'Date': date,
                    'Category': 'EXPENSE',
                    'Who_Paid': 'Jordyn',
                    'Description': f'{merchant}',
                    'Amount': f'${allowed:.2f}',
                    'Ryan_Owes': f'${ryan_share:.2f}',
                    'Jordyn_Owes': '$0.00',
                    'Balance_Change': f'${balance_change:.2f}',
                    'Running_Balance': f'${running_balance:.2f}',
                    'Notes': f'Jordyn paid, reduces Ryan\'s debt by 43%'
                })
    
    print(f"\n  EXPENSE SUMMARY:")
    print(f"  Shared expenses Ryan paid: ${ryan_shared_expenses:,.2f}")
    print(f"  Shared expenses Jordyn paid: ${jordyn_shared_expenses:,.2f}")
    print(f"  Total shared expenses: ${ryan_shared_expenses + jordyn_shared_expenses:,.2f}")
    print(f"  Number of shared expense transactions: {expense_count}")
else:
    print(f"❌ Expense file not found: {EXPENSE_FILE}")

# PART 3: COMPLETE PICTURE
print("\n" + "="*80)
print("COMPLETE FINANCIAL PICTURE")
print("="*80)

# Total amounts paid
total_jordyn_paid = jordyn_paid_rent_total + jordyn_shared_expenses
total_ryan_paid = ryan_shared_expenses

print(f"\n💰 TOTAL AMOUNTS PAID:")
print(f"  Jordyn paid: ${total_jordyn_paid:,.2f}")
print(f"    - Rent: ${jordyn_paid_rent_total:,.2f}")
print(f"    - Other: ${jordyn_shared_expenses:,.2f}")
print(f"  Ryan paid: ${total_ryan_paid:,.2f}")
print(f"    - All expenses: ${ryan_shared_expenses:,.2f}")

# What each should have paid
total_shared = jordyn_paid_rent_total + ryan_shared_expenses + jordyn_shared_expenses
ryan_fair_share = total_shared * 0.43
jordyn_fair_share = total_shared * 0.57

print(f"\n📊 FAIR SHARE (43/57 split of ${total_shared:,.2f}):")
print(f"  Ryan should pay: ${ryan_fair_share:,.2f}")
print(f"  Jordyn should pay: ${jordyn_fair_share:,.2f}")

print(f"\n💸 OVER/UNDERPAYMENT:")
print(f"  Ryan paid ${total_ryan_paid:,.2f} but should pay ${ryan_fair_share:,.2f}")
print(f"    → {'Overpaid' if total_ryan_paid > ryan_fair_share else 'Underpaid'} by ${abs(total_ryan_paid - ryan_fair_share):,.2f}")
print(f"  Jordyn paid ${total_jordyn_paid:,.2f} but should pay ${jordyn_fair_share:,.2f}")
print(f"    → {'Overpaid' if total_jordyn_paid > jordyn_fair_share else 'Underpaid'} by ${abs(total_jordyn_paid - jordyn_fair_share):,.2f}")

# Save detailed transaction log
if all_transactions:
    transaction_df = pd.DataFrame(all_transactions)
    output_file = f"complete_balance_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    transaction_df.to_csv(output_file, index=False)
    print(f"\n✅ Detailed transaction log saved to: {output_file}")

# FINAL BALANCE
print("\n" + "="*80)
print("FINAL BALANCE")
print("="*80)

print(f"\n🎯 TRANSACTION-BY-TRANSACTION METHOD:")
if running_balance > 0:
    print(f"   Jordyn owes Ryan: ${running_balance:,.2f}")
elif running_balance < 0:
    print(f"   Ryan owes Jordyn: ${abs(running_balance):,.2f}")
else:
    print(f"   Even!")

print(f"\n🎯 TOTAL OVERPAYMENT METHOD:")
balance_by_overpayment = (total_ryan_paid - ryan_fair_share)
if balance_by_overpayment > 0:
    print(f"   Jordyn owes Ryan: ${balance_by_overpayment:,.2f}")
elif balance_by_overpayment < 0:
    print(f"   Ryan owes Jordyn: ${abs(balance_by_overpayment):,.2f}")
else:
    print(f"   Even!")

print(f"\n📝 Note: Both methods should give the same result!")
print(f"   Any difference is due to transactions not included or rounding.")

# Show the key insight
print("\n" + "="*80)
print("💡 KEY INSIGHT")
print("="*80)
if balance_by_overpayment > 0:
    print(f"\nDespite Jordyn paying all the rent (${jordyn_paid_rent_total:,.2f}),")
    print(f"Ryan has paid so much in other shared expenses (${ryan_shared_expenses:,.2f})")
    print(f"that Jordyn actually owes Ryan ${balance_by_overpayment:,.2f}!")
    print(f"\nThe rent is significant, but it's only part of the total shared expenses.")

input("\n\nPress Enter to exit...")
