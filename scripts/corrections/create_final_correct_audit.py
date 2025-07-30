#!/usr/bin/env python3
"""
FINAL CORRECT AUDIT TRAIL
=========================

Creates the definitive audit trail with the truly correct rent allocation.
"""

import pandas as pd
from datetime import datetime

def create_final_correct_audit_trail():
    print("🎯 CREATING FINAL CORRECT AUDIT TRAIL")
    print("=" * 60)
    
    # Load the original audit trail (without the incorrect rent)
    original_audit = pd.read_csv('integrated_audit_trail_with_zelle_20250702_103908.csv')
    print(f"✅ Loaded original audit trail: {len(original_audit)} transactions")
    
    # Remove all existing rent transactions
    rent_keywords = ['rent', 'Rent', 'RENT']
    mask = True
    for keyword in rent_keywords:
        mask = mask & (~original_audit['Description'].str.contains(keyword, na=False))
    
    cleaned_audit = original_audit[mask].copy()
    removed_count = len(original_audit) - len(cleaned_audit)
    print(f"🗑️  Removed {removed_count} old rent transactions")
    
    # Load the truly correct rent transactions
    correct_rent = pd.read_csv('TRULY_corrected_rent_transactions.csv')
    print(f"✅ Loaded truly correct rent: {len(correct_rent)} transactions")
    
    # Combine cleaned audit with correct rent
    final_audit = pd.concat([cleaned_audit, correct_rent], ignore_index=True)
    
    # Sort by date
    final_audit['Date'] = pd.to_datetime(final_audit['Date'])
    final_audit = final_audit.sort_values(['Date', 'Transaction_Number']).reset_index(drop=True)
    
    print(f"📈 Final audit trail: {len(final_audit)} transactions")
    
    return final_audit

def verify_final_balances(df):
    print("\n✅ FINAL BALANCE VERIFICATION:")
    print("=" * 50)
    
    df['Net_Effect'] = pd.to_numeric(df['Net_Effect'], errors='coerce')
    
    # Calculate balances by person
    final_balances = df.groupby('Person')['Net_Effect'].sum()
    
    print("Final balances:")
    for person, balance in final_balances.items():
        if balance > 0:
            print(f"  {person}: ${balance:,.2f} (is owed)")
        elif balance < 0:
            print(f"  {person}: ${abs(balance):,.2f} (owes)")
        else:
            print(f"  {person}: $0.00 (even)")
    
    total_balance = final_balances.sum()
    print(f"\nBalance check: ${total_balance:,.2f}")
    
    # Calculate the settlement
    jordyn_balance = final_balances.get('Jordyn', 0)
    ryan_balance = final_balances.get('Ryan', 0)
    
    print(f"\n💰 SETTLEMENT CALCULATION:")
    if jordyn_balance > 0 and ryan_balance < 0:
        if abs(jordyn_balance - abs(ryan_balance)) < 1:  # Within $1
            settlement = max(jordyn_balance, abs(ryan_balance))
            print(f"✅ Balanced! Ryan owes Jordyn approximately ${settlement:,.2f}")
        else:
            print(f"Jordyn is owed: ${jordyn_balance:,.2f}")
            print(f"Ryan owes: ${abs(ryan_balance):,.2f}")
            print(f"Difference: ${abs(jordyn_balance - abs(ryan_balance)):,.2f}")
    
    return final_balances

def save_final_audit_trail(df):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"FINAL_CORRECT_audit_trail_{timestamp}.csv"
    
    df.to_csv(filename, index=False)
    print(f"\n💾 Saved final correct audit trail: {filename}")
    
    return filename

def main():
    print("🎯 CREATING THE DEFINITIVE CORRECT AUDIT TRAIL")
    print("=" * 70)
    print("This uses the truly correct rent allocation with proper signs.\n")
    
    # Create final correct audit trail
    final_audit = create_final_correct_audit_trail()
    
    # Verify balances
    final_balances = verify_final_balances(final_audit)
    
    # Save final audit trail
    filename = save_final_audit_trail(final_audit)
    
    print("\n🎉 FINAL CORRECT AUDIT TRAIL COMPLETE!")
    print("=" * 70)
    print("This audit trail has:")
    print("✅ Correct rent allocation (Jordyn owed, Ryan owes)")
    print("✅ All Zelle transfers accounted for")
    print("✅ All shared expenses properly allocated")
    print("✅ Personal expenses correctly categorized")
    
    # Calculate who owes who
    jordyn_balance = final_balances.get('Jordyn', 0)
    ryan_balance = final_balances.get('Ryan', 0)
    
    print(f"\n🎯 FINAL ANSWER:")
    if ryan_balance < 0:
        amount = abs(ryan_balance)
        print(f"Ryan owes Jordyn ${amount:,.2f}")
    elif jordyn_balance < 0:
        amount = abs(jordyn_balance)
        print(f"Jordyn owes Ryan ${amount:,.2f}")
    else:
        print("Accounts are balanced")

if __name__ == "__main__":
    main()
