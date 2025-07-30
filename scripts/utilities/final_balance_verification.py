#!/usr/bin/env python3
"""
FINAL BALANCE VERIFICATION
==========================

Analyzes the corrected audit trail to understand remaining balance discrepancies
and provides a comprehensive breakdown of all transactions.

Author: Financial Analysis System
Date: 2025-01-18
"""

import os

import pandas as pd

def load_corrected_audit_trail():
    """Load the most recent corrected audit trail"""
    # Find the most recent corrected audit trail
    files = [f for f in os.listdir('.') if f.startswith('corrected_audit_trail_with_rent_fix_')]
    if not files:
        print("❌ No corrected audit trail found")
        return None
    
    latest_file = max(files, key=lambda x: os.path.getctime(x))
    
    df = pd.read_csv(latest_file)
    print(f"✅ Loaded corrected audit trail: {latest_file}")
    print(f"📊 Total transactions: {len(df)}")
    
    return df

def analyze_transaction_types(df):
    """Analyze transaction types and their impact"""
    print("\n📋 TRANSACTION TYPE ANALYSIS:")
    print("=" * 50)
    
    type_summary = df.groupby('Transaction_Type').agg({
        'Net_Effect': ['count', 'sum'],
        'Amount_Paid': 'sum',
        'Share_Owed': 'sum'
    }).round(2)
    
    print(type_summary)
    
    print("\n📈 TRANSACTION TYPE BREAKDOWN BY PERSON:")
    print("=" * 50)
    
    person_type_summary = df.groupby(['Person', 'Transaction_Type']).agg({
        'Net_Effect': ['count', 'sum']
    }).round(2)
    
    print(person_type_summary)

def analyze_rent_transactions(df):
    """Specifically analyze rent transactions"""
    print("\n🏠 RENT TRANSACTION ANALYSIS:")
    print("=" * 50)
    
    rent_df = df[df['Description'].str.contains('Rent|rent', na=False)].copy()
    
    if len(rent_df) == 0:
        print("❌ No rent transactions found")
        return
    
    print(f"Total rent transactions: {len(rent_df)}")
    
    # Group by person
    rent_by_person = rent_df.groupby('Person').agg({
        'Net_Effect': ['count', 'sum'],
        'Amount_Paid': 'sum',
        'Share_Owed': 'sum'
    }).round(2)
    
    print("\nRent impact by person:")
    print(rent_by_person)
    
    # Show sample rent transactions
    print("\n📄 SAMPLE RENT TRANSACTIONS:")
    print(rent_df[['Date', 'Person', 'Transaction_Type', 'Amount_Paid', 'Share_Owed', 'Net_Effect']].head(10))

def analyze_balance_discrepancy(df):
    """Analyze what's causing the balance discrepancy"""
    print("\n🔍 BALANCE DISCREPANCY ANALYSIS:")
    print("=" * 50)
    
    # Calculate balances by person
    person_balances = df.groupby('Person')['Net_Effect'].sum().round(2)
    total_balance = person_balances.sum()
    
    print("Individual balances:")
    for person, balance in person_balances.items():
        print(f"  {person}: ${balance:,.2f}")
    
    print(f"\nTotal balance: ${total_balance:,.2f}")
    print("Expected balance: $0.00")
    print(f"Discrepancy: ${total_balance:,.2f}")
    
    if abs(total_balance) > 0.01:
        print("\n⚠️  BALANCE ISSUES DETECTED:")
        print("This suggests there are still unresolved transaction imbalances.")
        
        # Look for transaction types that might be causing issues
        print("\n🔎 POTENTIAL CAUSES:")
        
        # Check for transactions without pairs
        type_net_effects = df.groupby('Transaction_Type')['Net_Effect'].sum().round(2)
        
        for trans_type, net_effect in type_net_effects.items():
            if abs(net_effect) > 0.01:
                print(f"  {trans_type}: Net effect ${net_effect:,.2f}")

def analyze_monthly_trends(df):
    """Analyze monthly balance trends"""
    print("\n📅 MONTHLY BALANCE TRENDS:")
    print("=" * 50)
    
    df['Date'] = pd.to_datetime(df['Date'])
    df['Month'] = df['Date'].dt.to_period('M')
    
    monthly_summary = df.groupby(['Month', 'Person'])['Net_Effect'].sum().unstack(fill_value=0).round(2)
    
    print("Monthly net effects by person:")
    print(monthly_summary)
    
    # Calculate running balances
    print("\n📈 RUNNING BALANCE BY MONTH:")
    running_balances = monthly_summary.cumsum()
    print(running_balances)

def generate_final_summary(df):
    """Generate final summary and recommendations"""
    print("\n🎯 FINAL SUMMARY & RECOMMENDATIONS:")
    print("=" * 60)
    
    total_transactions = len(df)
    total_amount_paid = df['Amount_Paid'].sum()
    total_share_owed = df['Share_Owed'].sum()
    
    print(f"Total transactions processed: {total_transactions:,}")
    print(f"Total amount paid: ${total_amount_paid:,.2f}")
    print(f"Total share owed: ${total_share_owed:,.2f}")
    
    # Final balance check
    person_balances = df.groupby('Person')['Net_Effect'].sum().round(2)
    total_balance = person_balances.sum()
    
    print("\nFinal balances:")
    for person, balance in person_balances.items():
        status = "owes" if balance > 0 else "is owed"
        print(f"  {person}: ${abs(balance):,.2f} ({status})")
    
    print(f"\nBalance verification: ${total_balance:,.2f}")
    
    if abs(total_balance) < 0.01:
        print("✅ BALANCES ARE RECONCILED!")
    else:
        print("❌ BALANCES STILL HAVE DISCREPANCIES")
        print("\n🔧 RECOMMENDED ACTIONS:")
        print("1. Check for missing or duplicate transactions")
        print("2. Verify Zelle transaction matching")
        print("3. Review expense sharing calculations")
        print("4. Check for data entry errors")

def main():
    """Main analysis process"""
    print("🔍 FINAL BALANCE VERIFICATION ANALYSIS")
    print("=" * 60)
    
    # Load corrected audit trail
    df = load_corrected_audit_trail()
    if df is None:
        return
    
    # Ensure numeric columns
    df['Net_Effect'] = pd.to_numeric(df['Net_Effect'], errors='coerce')
    df['Amount_Paid'] = pd.to_numeric(df['Amount_Paid'], errors='coerce')
    df['Share_Owed'] = pd.to_numeric(df['Share_Owed'], errors='coerce')
    
    # Run analyses
    analyze_transaction_types(df)
    analyze_rent_transactions(df)
    analyze_balance_discrepancy(df)
    analyze_monthly_trends(df)
    generate_final_summary(df)
    
    print("\n🎉 ANALYSIS COMPLETE!")

if __name__ == "__main__":
    main()
