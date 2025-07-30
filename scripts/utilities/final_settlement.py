#!/usr/bin/env python3
"""
Final Settlement Calculator
"""

import pandas as pd

def main():
    print("🎯 WHO OWES WHO WHAT? - FINAL ANSWER")
    print("=" * 60)
    
    # Load the final corrected audit trail
    df = pd.read_csv('FINAL_corrected_audit_trail_20250718_001910.csv')
    print(f"✅ Loaded {len(df)} transactions")
    
    # Ensure Net_Effect is numeric
    df['Net_Effect'] = pd.to_numeric(df['Net_Effect'], errors='coerce')
    
    # Calculate final balances by person
    final_balances = df.groupby('Person')['Net_Effect'].sum()
    
    print("\n📊 FINAL BALANCES:")
    for person, balance in final_balances.items():
        if balance > 0:
            print(f"  {person}: ${balance:,.2f} (owes money)")
        elif balance < 0:
            print(f"  {person}: ${abs(balance):,.2f} (is owed money)")
        else:
            print(f"  {person}: $0.00 (even)")
    
    # Get specific values
    jordyn_balance = final_balances.get('Jordyn', 0)
    ryan_balance = final_balances.get('Ryan', 0)
    
    print(f"\n🔍 DETAILED BREAKDOWN:")
    print(f"  Jordyn net effect: ${jordyn_balance:+,.2f}")
    print(f"  Ryan net effect: ${ryan_balance:+,.2f}")
    print(f"  Balance check: ${jordyn_balance + ryan_balance:+,.2f} (should be ~0)")
    
    # Determine settlement
    print(f"\n💰 SETTLEMENT NEEDED:")
    
    if jordyn_balance < 0 and ryan_balance > 0:
        # Jordyn is owed money (negative), Ryan owes money (positive)
        settlement = ryan_balance
        print(f"  Ryan owes Jordyn: ${settlement:,.2f}")
        print(f"\n🎯 FINAL ANSWER:")
        print(f"  Ryan should pay Jordyn ${settlement:,.2f} to settle all accounts")
        
    elif ryan_balance < 0 and jordyn_balance > 0:
        # Ryan is owed money (negative), Jordyn owes money (positive)
        settlement = jordyn_balance
        print(f"  Jordyn owes Ryan: ${settlement:,.2f}")
        print(f"\n🎯 FINAL ANSWER:")
        print(f"  Jordyn should pay Ryan ${settlement:,.2f} to settle all accounts")
        
    else:
        print("  Unusual balance situation - check data")
    
    print(f"\n📋 WHAT THIS INCLUDES:")
    print(f"  ✅ Rent payments (Jordyn pays full, Ryan owes 43%)")
    print(f"  ✅ All shared expenses split appropriately")
    print(f"  ✅ All Zelle transfers between you")
    print(f"  ✅ Personal expenses (each pays for their own)")

if __name__ == "__main__":
    main()
