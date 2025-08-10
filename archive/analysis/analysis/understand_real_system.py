#!/usr/bin/env python3
"""
UNDERSTAND THE REAL SYSTEM
==========================

Ryan is explaining that Jordyn always owed him money, and his rent 
was "paid" by subtracting from what she owed him. This means:

1. There was an existing balance where Jordyn owed Ryan money
2. Each month, Ryan's rent share was subtracted from that balance
3. The rent was considered "paid" via this offset system

Let's figure out what the real balances should be.
"""

import pandas as pd


def analyze_non_rent_transactions():
    print("🔍 ANALYZING NON-RENT TRANSACTIONS")
    print("=" * 60)
    print("Let's see what Jordyn owed Ryan BEFORE considering rent.\n")
    
    # Load the original audit trail (without rent)
    df = pd.read_csv('integrated_audit_trail_with_zelle_20250702_103908.csv')
    
    # Remove all rent transactions to see the base balance
    rent_keywords = ['rent', 'Rent', 'RENT']
    mask = True
    for keyword in rent_keywords:
        mask = mask & (~df['Description'].str.contains(keyword, na=False))
    
    non_rent_df = df[mask].copy()
    print(f"✅ Non-rent transactions: {len(non_rent_df)}")
    
    # Calculate balances without rent
    non_rent_df['Net_Effect'] = pd.to_numeric(non_rent_df['Net_Effect'], errors='coerce')
    non_rent_balances = non_rent_df.groupby('Person')['Net_Effect'].sum()
    
    print("📊 BALANCES WITHOUT RENT:")
    for person, balance in non_rent_balances.items():
        if balance > 0:
            print(f"  {person}: ${balance:,.2f} (is owed)")
        elif balance < 0:
            print(f"  {person}: ${abs(balance):,.2f} (owes)")
        else:
            print(f"  {person}: $0.00 (even)")
    
    jordyn_non_rent = non_rent_balances.get('Jordyn', 0)
    ryan_non_rent = non_rent_balances.get('Ryan', 0)
    
    print("\n💡 INTERPRETATION:")
    if jordyn_non_rent < 0:
        jordyn_owes_ryan = abs(jordyn_non_rent)
        print(f"Before considering rent, Jordyn owed Ryan ${jordyn_owes_ryan:,.2f}")
        
        # Now let's see how rent was handled
        total_rent_ryan_should_pay = 17701.17  # From our earlier calculation
        
        print("\n🏠 RENT OFFSET SYSTEM:")
        print(f"Ryan's total rent obligation: ${total_rent_ryan_should_pay:,.2f}")
        print(f"Jordyn owed Ryan (pre-rent): ${jordyn_owes_ryan:,.2f}")
        
        if jordyn_owes_ryan >= total_rent_ryan_should_pay:
            # Jordyn owed more than Ryan's rent, so rent was fully "paid" by offset
            remaining_jordyn_owes = jordyn_owes_ryan - total_rent_ryan_should_pay
            print("\n✅ RENT FULLY PAID VIA OFFSET")
            print(f"After rent offset, Jordyn still owes Ryan: ${remaining_jordyn_owes:,.2f}")
            print("\n🎯 FINAL ANSWER:")
            print(f"Jordyn owes Ryan ${remaining_jordyn_owes:,.2f}")
            
        else:
            # Jordyn owed less than Ryan's rent, so there's still a rent balance
            remaining_rent_owed = total_rent_ryan_should_pay - jordyn_owes_ryan
            print("\n⚠️  RENT PARTIALLY PAID VIA OFFSET")
            print(f"Jordyn's debt (${jordyn_owes_ryan:,.2f}) < Ryan's rent (${total_rent_ryan_should_pay:,.2f})")
            print(f"Remaining rent Ryan owes: ${remaining_rent_owed:,.2f}")
            print("\n🎯 FINAL ANSWER:")
            print(f"Ryan owes Jordyn ${remaining_rent_owed:,.2f}")
    
    else:
        print(f"Unexpected: Jordyn is owed ${jordyn_non_rent:,.2f} before rent")
    
    return non_rent_balances

def show_transaction_breakdown(df):
    print("\n📋 TRANSACTION TYPE BREAKDOWN (NON-RENT):")
    print("=" * 60)
    
    df['Net_Effect'] = pd.to_numeric(df['Net_Effect'], errors='coerce')
    
    # Show what types of transactions created the pre-rent balance
    type_summary = df.groupby(['Person', 'Transaction_Type'])['Net_Effect'].sum().round(2)
    
    for (person, trans_type), amount in type_summary.items():
        if abs(amount) > 0.01:
            print(f"  {person} - {trans_type}: ${amount:+,.2f}")

def main():
    print("🎯 UNDERSTANDING THE REAL BALANCE SYSTEM")
    print("=" * 70)
    print("Ryan explains: Jordyn always owed him money, and his rent")
    print("was 'paid' by subtracting from what she owed him.\n")
    
    # Load non-rent data
    df = pd.read_csv('integrated_audit_trail_with_zelle_20250702_103908.csv')
    
    # Remove rent
    rent_keywords = ['rent', 'Rent', 'RENT']
    mask = True
    for keyword in rent_keywords:
        mask = mask & (~df['Description'].str.contains(keyword, na=False))
    
    non_rent_df = df[mask].copy()
    
    # Analyze the true balance
    balances = analyze_non_rent_transactions()
    
    # Show breakdown
    show_transaction_breakdown(non_rent_df)

if __name__ == "__main__":
    main()
