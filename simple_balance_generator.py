#!/usr/bin/env python3
"""
Simple version - just run it!
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

# CHANGE THIS TO YOUR FILE PATH IF NEEDED
INPUT_FILE = r"C:\BALANCE\New Master - New Joint Couple Finances (2024).xlsx - Expense History.csv"
OUTPUT_FILE = "detailed_balance_analysis.csv"

print("="*70)
print("EXPENSE BALANCE ANALYZER")
print("="*70)
print(f"\nLooking for file: {INPUT_FILE}")

if not Path(INPUT_FILE).exists():
    print("\n❌ File not found!")
    print("\nPlease update the INPUT_FILE path in this script to point to your expense CSV.")
    input("\nPress Enter to exit...")
    exit()

print("✅ File found! Processing...")

# Read the expense file
df = pd.read_csv(INPUT_FILE)

# Create detailed analysis
detailed_data = []
running_balance = 0.0

# Track totals
ryan_shared_total = 0
jordyn_shared_total = 0
transaction_count = 0

for _, row in df.iterrows():
    name = row.get('Name', '').strip()
    if not name:
        continue
        
    transaction_count += 1
    date = row.get('Date of Purchase', '')
    merchant = row.get('Merchant', '')
    actual = parse_amount(row.get('Actual Amount', row.get(' Actual Amount ', '0')))
    allowed = parse_amount(row.get('Allowed Amount', row.get(' Allowed Amount ', '0')))
    
    # Determine if shared
    is_shared = allowed > 0
    
    # Calculate shares
    ryan_share = 0
    jordyn_share = 0
    balance_change = 0
    
    if is_shared:
        ryan_share = allowed * 0.43
        jordyn_share = allowed * 0.57
        
        if name == 'Ryan':
            balance_change = jordyn_share
            ryan_shared_total += allowed
        elif name == 'Jordyn':
            balance_change = -ryan_share
            jordyn_shared_total += allowed
    
    # Update running balance
    running_balance += balance_change
    
    # Create row
    detailed_row = {
        'Date': date,
        'Who_Paid': name,
        'Merchant': merchant,
        'Actual_Amount': f"${actual:.2f}",
        'Allowed_Amount': f"${allowed:.2f}" if allowed > 0 else "$0.00",
        'Type': "SHARED" if is_shared else "PERSONAL",
        'Ryan_Share': f"${ryan_share:.2f}" if is_shared else "-",
        'Jordyn_Share': f"${jordyn_share:.2f}" if is_shared else "-",
        'Balance_Change': f"+${balance_change:.2f}" if balance_change > 0 else f"${balance_change:.2f}" if balance_change < 0 else "-",
        'Running_Balance': f"${abs(running_balance):.2f}",
        'Status': "J→R" if running_balance > 0 else "R→J" if running_balance < 0 else "Even"
    }
    
    detailed_data.append(detailed_row)

# Create DataFrame
detailed_df = pd.DataFrame(detailed_data)

# Save to CSV
detailed_df.to_csv(OUTPUT_FILE, index=False)

# Calculate summary
total_shared = ryan_shared_total + jordyn_shared_total
ryan_should_pay = total_shared * 0.43
jordyn_should_pay = total_shared * 0.57

# Print results
print(f"\n✅ Processed {transaction_count} transactions")
print(f"✅ Detailed CSV saved to: {OUTPUT_FILE}")

print("\n" + "="*50)
print("SUMMARY")
print("="*50)

print(f"\nSHARED EXPENSES:")
print(f"  Ryan paid: ${ryan_shared_total:,.2f}")
print(f"  Jordyn paid: ${jordyn_shared_total:,.2f}")
print(f"  Total shared: ${total_shared:,.2f}")

print(f"\nFAIR SHARE (43/57 split):")
print(f"  Ryan should pay: ${ryan_should_pay:,.2f}")
print(f"  Jordyn should pay: ${jordyn_should_pay:,.2f}")

print(f"\nOVER/UNDERPAYMENT:")
print(f"  Ryan overpaid: ${ryan_shared_total - ryan_should_pay:,.2f}")
print(f"  Jordyn underpaid: ${jordyn_should_pay - jordyn_shared_total:,.2f}")

print(f"\n" + "="*50)
print("FINAL BALANCE")
print("="*50)

if running_balance > 0:
    print(f"\n🎯 Jordyn owes Ryan: ${running_balance:,.2f}")
elif running_balance < 0:
    print(f"\n🎯 Ryan owes Jordyn: ${abs(running_balance):,.2f}")
else:
    print(f"\n🎯 You're even!")

input("\n\nPress Enter to exit...")
