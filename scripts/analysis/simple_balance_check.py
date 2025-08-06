#!/usr/bin/env python3
"""
SIMPLE BALANCE CALCULATOR
=========================

Let's calculate the true balance using just the corrected rent data
and see what the real settlement should be.
"""

import pandas as pd


def calculate_simple_balance():
    print("🎯 SIMPLE BALANCE CALCULATION")
    print("=" * 50)
    print("Using only the corrected rent allocation to see the true balance.\n")
    
    # Load the truly corrected rent transactions
    rent_df = pd.read_csv('TRULY_corrected_rent_transactions.csv')
    print(f"✅ Loaded {len(rent_df)} rent transactions")
    
    # Calculate rent balances
    rent_df['Net_Effect'] = pd.to_numeric(rent_df['Net_Effect'], errors='coerce')
    rent_balances = rent_df.groupby('Person')['Net_Effect'].sum()
    
    print("\n🏠 RENT-ONLY BALANCES:")
    for person, balance in rent_balances.items():
        if balance > 0:
            print(f"  {person}: ${balance:,.2f} (is owed)")
        elif balance < 0:
            print(f"  {person}: ${abs(balance):,.2f} (owes)")
        else:
            print(f"  {person}: $0.00 (even)")
    
    rent_balance_check = rent_balances.sum()
    print(f"\nRent balance check: ${rent_balance_check:,.2f} (should be 0)")
    
    if abs(rent_balance_check) < 0.01:
        print("✅ Rent transactions are perfectly balanced!")
        
        # This is the core settlement
        jordyn_rent = rent_balances.get('Jordyn', 0)
        ryan_rent = rent_balances.get('Ryan', 0)
        
        if jordyn_rent > 0 and ryan_rent < 0:
            settlement = jordyn_rent
            print("\n💰 CORE RENT SETTLEMENT:")
            print(f"Based purely on rent, Ryan owes Jordyn ${settlement:,.2f}")
            
            # Now let's see what other transactions add to this
            print("\n📊 OTHER CONSIDERATIONS:")
            print(f"This ${settlement:,.2f} is just for rent.")
            print("Additional amounts may be owed for:")
            print("  • Shared expenses")
            print("  • Zelle transfers")
            print("  • Other shared costs")
            
            return settlement
    else:
        print("❌ Rent transactions are not balanced - there's still an error")
        return None

def main():
    settlement = calculate_simple_balance()
    
    if settlement:
        print("\n🎯 MINIMUM SETTLEMENT AMOUNT:")
        print(f"Ryan owes Jordyn at least ${settlement:,.2f} for rent alone.")
        print("\nTo get the complete picture including all shared expenses,")
        print("we'd need to carefully review all non-rent transactions.")

if __name__ == "__main__":
    main()
