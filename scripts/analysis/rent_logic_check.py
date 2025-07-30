#!/usr/bin/env python3
"""
RENT LOGIC VERIFICATION
=======================

Let's verify what the correct rent allocation should be.
"""

def verify_rent_logic():
    print("🏠 RENT LOGIC VERIFICATION")
    print("=" * 50)
    
    # Example month: January 2024
    total_rent = 2119.72
    ryan_share_percent = 0.43
    
    print(f"Total rent: ${total_rent:,.2f}")
    print(f"Ryan's share: {ryan_share_percent:.0%}")
    
    # Correct logic:
    ryan_share_amount = total_rent * ryan_share_percent
    jordyn_share_amount = total_rent - ryan_share_amount
    
    print(f"\nCORRECT ALLOCATION:")
    print(f"Ryan should pay: ${ryan_share_amount:,.2f}")
    print(f"Jordyn should pay: ${jordyn_share_amount:,.2f}")
    
    # Current situation: Jordyn pays full rent
    print(f"\nCURRENT SITUATION:")
    print(f"Jordyn actually pays: ${total_rent:,.2f}")
    print(f"Ryan actually pays: $0.00")
    
    # Net effects (what should be recorded):
    print(f"\nNET EFFECTS (what should be in audit trail):")
    
    # Jordyn: Paid more than her share, so she's OWED money (positive balance)
    jordyn_net = ryan_share_amount  # She's owed Ryan's share
    print(f"Jordyn net effect: +${jordyn_net:,.2f} (she's owed money)")
    
    # Ryan: Paid less than his share, so he OWES money (negative balance)  
    ryan_net = -ryan_share_amount  # He owes his share
    print(f"Ryan net effect: -${abs(ryan_net):,.2f} (he owes money)")
    
    balance_check = jordyn_net + ryan_net
    print(f"Balance check: ${balance_check:,.2f} (should be 0)")
    
    return jordyn_net, ryan_net

def check_current_rent_data():
    print(f"\n🔍 CHECKING CURRENT RENT DATA:")
    print("=" * 50)
    
    import pandas as pd
    
    # Load current rent allocation
    df = pd.read_csv('data/Consolidated_Rent_Allocation_CORRECTED_20250718.csv')
    
    # Check first month
    first_month = df.iloc[0]
    
    print(f"Current data for {first_month['Month']}:")
    print(f"Total rent: ${first_month['Gross_Total']:,.2f}")
    print(f"Jordyn pays: ${first_month['Jordyn_Pays']:,.2f}")
    print(f"Jordyn net effect: ${first_month['Jordyn_Net_Effect']:,.2f}")
    print(f"Ryan pays: ${first_month['Ryan_Pays']:,.2f}")  
    print(f"Ryan net effect: ${first_month['Ryan_Net_Effect']:,.2f}")
    
    print(f"\n⚠️  PROBLEM IDENTIFIED:")
    if first_month['Jordyn_Net_Effect'] < 0:
        print(f"Jordyn's net effect is NEGATIVE (${first_month['Jordyn_Net_Effect']:,.2f})")
        print(f"This means she OWES money, but she paid the full rent!")
        print(f"This is backwards - she should have a POSITIVE net effect.")
    
    if first_month['Ryan_Net_Effect'] > 0:
        print(f"Ryan's net effect is POSITIVE (${first_month['Ryan_Net_Effect']:,.2f})")
        print(f"This means he's OWED money, but he paid nothing!")
        print(f"This is backwards - he should have a NEGATIVE net effect.")

if __name__ == "__main__":
    verify_rent_logic()
    check_current_rent_data()
