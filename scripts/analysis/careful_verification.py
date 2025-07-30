#!/usr/bin/env python3
"""
CAREFUL BALANCE VERIFICATION
============================

Let's carefully trace through the numbers to make sure everything is correct.
"""

import pandas as pd

def main():
    print("🔍 CAREFUL BALANCE VERIFICATION")
    print("=" * 60)
    
    # Load the final corrected audit trail
    df = pd.read_csv('FINAL_corrected_audit_trail_20250718_001910.csv')
    print(f"✅ Loaded {len(df)} transactions")
    
    # Ensure Net_Effect is numeric
    df['Net_Effect'] = pd.to_numeric(df['Net_Effect'], errors='coerce')
    
    # First, let's check the rent allocation specifically
    print("\n🏠 RENT TRANSACTION VERIFICATION:")
    print("=" * 50)
    
    rent_df = df[df['Description'].str.contains('Rent|rent', na=False)].copy()
    print(f"Total rent transactions: {len(rent_df)}")
    
    rent_summary = rent_df.groupby('Person').agg({
        'Net_Effect': ['count', 'sum'],
        'Amount_Paid': 'sum',
        'Share_Owed': 'sum'
    })
    
    print("\nRent summary by person:")
    print(rent_summary)
    
    # Check if rent balances out
    rent_total = rent_df['Net_Effect'].sum()
    print(f"\nRent balance check: ${rent_total:,.2f} (should be 0)")
    
    # Now let's look at the major transaction types
    print("\n📊 TRANSACTION TYPE BREAKDOWN:")
    print("=" * 50)
    
    type_summary = df.groupby('Transaction_Type').agg({
        'Net_Effect': ['count', 'sum']
    }).round(2)
    
    print(type_summary)
    
    # Let's specifically check if we have duplicate or incorrect entries
    print("\n🔍 POTENTIAL ISSUES:")
    print("=" * 50)
    
    # Check for any transaction types that shouldn't have net effects
    problematic_types = []
    
    for trans_type in df['Transaction_Type'].unique():
        type_df = df[df['Transaction_Type'] == trans_type]
        net_effect = type_df['Net_Effect'].sum()
        
        if trans_type in ['Split Expense (Equal)', 'Rent Payment (Full)', 'Rent Share Owed']:
            if abs(net_effect) > 0.01:
                problematic_types.append((trans_type, net_effect))
    
    if problematic_types:
        print("⚠️  Transaction types that should balance but don't:")
        for trans_type, net_effect in problematic_types:
            print(f"  {trans_type}: ${net_effect:,.2f}")
    else:
        print("✅ Core transaction types are balanced")
    
    # Let's check the monthly rent amounts to see if they're reasonable
    print("\n💰 MONTHLY RENT VERIFICATION:")
    print("=" * 50)
    
    rent_payments = df[df['Transaction_Type'] == 'Rent Payment (Full)'].copy()
    if len(rent_payments) > 0:
        rent_payments['Month'] = pd.to_datetime(rent_payments['Date']).dt.to_period('M')
        monthly_rent = rent_payments.groupby('Month')['Amount_Paid'].sum()
        
        print("Monthly rent amounts:")
        for month, amount in monthly_rent.items():
            print(f"  {month}: ${amount:,.2f}")
        
        avg_rent = monthly_rent.mean()
        print(f"\nAverage monthly rent: ${avg_rent:,.2f}")
        
        if avg_rent > 3000:
            print("⚠️  This seems high for monthly rent - please verify")
        elif avg_rent < 1000:
            print("⚠️  This seems low for monthly rent - please verify")
        else:
            print("✅ Rent amounts seem reasonable")
    
    # Final balance calculation with detailed breakdown
    print("\n📊 DETAILED FINAL BALANCE CALCULATION:")
    print("=" * 60)
    
    final_balances = df.groupby('Person')['Net_Effect'].sum()
    
    for person in final_balances.index:
        person_df = df[df['Person'] == person]
        print(f"\n{person.upper()}:")
        
        # Break down by transaction type
        type_breakdown = person_df.groupby('Transaction_Type')['Net_Effect'].sum()
        for trans_type, amount in type_breakdown.items():
            if abs(amount) > 0.01:
                print(f"  {trans_type}: ${amount:+,.2f}")
        
        total = final_balances[person]
        print(f"  TOTAL: ${total:+,.2f}")
    
    print(f"\nOverall balance check: ${final_balances.sum():,.2f}")
    
    # Check if we're double-counting anything
    print("\n🔍 DOUBLE-COUNTING CHECK:")
    print("=" * 50)
    
    # Look for potential duplicates in rent
    rent_by_date = rent_df.groupby(['Date', 'Person']).size()
    duplicates = rent_by_date[rent_by_date > 1]
    
    if len(duplicates) > 0:
        print("⚠️  Potential duplicate rent entries:")
        print(duplicates)
    else:
        print("✅ No obvious rent duplicates")

if __name__ == "__main__":
    main()
