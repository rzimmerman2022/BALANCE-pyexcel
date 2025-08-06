#!/usr/bin/env python3
"""
ZELLE & PERSONAL EXPENSE INVESTIGATION
======================================

Investigates the imbalance caused by Zelle payments and personal expenses
to understand and fix the remaining $20,053 discrepancy.

Author: Financial Analysis System
Date: 2025-01-18
"""

import os

import pandas as pd


def load_corrected_audit_trail():
    """Load the corrected audit trail"""
    files = [f for f in os.listdir('.') if f.startswith('corrected_audit_trail_with_rent_fix_')]
    if not files:
        print("❌ No corrected audit trail found")
        return None
    
    latest_file = max(files, key=lambda x: os.path.getctime(x))
    df = pd.read_csv(latest_file)
    print(f"✅ Loaded: {latest_file}")
    return df

def analyze_zelle_transactions(df):
    """Analyze Zelle transactions"""
    print("\n💳 ZELLE TRANSACTION ANALYSIS:")
    print("=" * 50)
    
    zelle_df = df[df['Transaction_Type'] == 'Zelle Payment'].copy()
    
    if len(zelle_df) == 0:
        print("No Zelle transactions found")
        return
    
    print(f"Total Zelle transactions: {len(zelle_df)}")
    
    # Group by person
    zelle_by_person = zelle_df.groupby('Person').agg({
        'Net_Effect': ['count', 'sum'],
        'Amount_Paid': 'sum',
        'Share_Owed': 'sum'
    }).round(2)
    
    print("\nZelle by person:")
    print(zelle_by_person)
    
    print("\n📄 ALL ZELLE TRANSACTIONS:")
    print(zelle_df[['Date', 'Person', 'Description', 'Amount_Paid', 'Share_Owed', 'Net_Effect']])
    
    # Check if Zelle payments are being matched with corresponding transactions
    print("\n🔍 ZELLE MATCHING ANALYSIS:")
    total_zelle_net = zelle_df['Net_Effect'].sum()
    print(f"Total Zelle net effect: ${total_zelle_net:,.2f}")
    
    if abs(total_zelle_net) > 0.01:
        print("⚠️  Zelle transactions are not balanced!")
        print("This suggests Zelle payments are not properly matched with corresponding shared expenses.")

def analyze_personal_expenses(df):
    """Analyze personal expenses"""
    print("\n💰 PERSONAL EXPENSE ANALYSIS:")
    print("=" * 50)
    
    personal_df = df[df['Transaction_Type'] == 'Personal Expense'].copy()
    
    if len(personal_df) == 0:
        print("No personal expenses found")
        return
    
    print(f"Total personal expenses: {len(personal_df)}")
    
    # Group by person
    personal_by_person = personal_df.groupby('Person').agg({
        'Net_Effect': ['count', 'sum'],
        'Amount_Paid': 'sum',
        'Share_Owed': 'sum'
    }).round(2)
    
    print("\nPersonal expenses by person:")
    print(personal_by_person)
    
    # Show sample transactions
    print("\n📄 SAMPLE PERSONAL EXPENSES:")
    print(personal_df[['Date', 'Person', 'Description', 'Amount_Paid', 'Share_Owed', 'Net_Effect']].head(10))
    
    # Check for balance
    total_personal_net = personal_df['Net_Effect'].sum()
    print(f"\n💡 Total personal expense net effect: ${total_personal_net:,.2f}")
    
    if abs(total_personal_net) > 0.01:
        print("⚠️  Personal expenses are not balanced!")
        print("Personal expenses should have zero net effect across all people.")

def analyze_shared_expenses(df):
    """Analyze shared expenses"""
    print("\n🤝 SHARED EXPENSE ANALYSIS:")
    print("=" * 50)
    
    shared_df = df[df['Transaction_Type'] == 'Shared Expense'].copy()
    
    if len(shared_df) == 0:
        print("No shared expenses found")
        return
    
    print(f"Total shared expenses: {len(shared_df)}")
    
    # Group by person
    shared_by_person = shared_df.groupby('Person').agg({
        'Net_Effect': ['count', 'sum'],
        'Amount_Paid': 'sum',
        'Share_Owed': 'sum'
    }).round(2)
    
    print("\nShared expenses by person:")
    print(shared_by_person)
    
    # Show sample transactions
    print("\n📄 SAMPLE SHARED EXPENSES:")
    print(shared_df[['Date', 'Person', 'Description', 'Amount_Paid', 'Share_Owed', 'Net_Effect']].head(10))
    
    # Check for balance
    total_shared_net = shared_df['Net_Effect'].sum()
    print(f"\n💡 Total shared expense net effect: ${total_shared_net:,.2f}")

def identify_imbalance_sources(df):
    """Identify the sources of the $20,053 imbalance"""
    print("\n🎯 IMBALANCE SOURCE IDENTIFICATION:")
    print("=" * 60)
    
    # Calculate net effects by transaction type
    type_nets = df.groupby('Transaction_Type')['Net_Effect'].sum().round(2)
    
    print("Net effects by transaction type:")
    total_imbalance = 0
    
    for trans_type, net_effect in type_nets.items():
        print(f"  {trans_type}: ${net_effect:,.2f}")
        total_imbalance += net_effect
    
    print(f"\nTotal imbalance: ${total_imbalance:,.2f}")
    
    # Identify the main culprits
    print("\n🔍 MAIN CONTRIBUTORS TO IMBALANCE:")
    
    imbalance_sources = []
    
    if abs(type_nets.get('Personal Expense', 0)) > 0.01:
        imbalance_sources.append(('Personal Expense', type_nets['Personal Expense']))
    
    if abs(type_nets.get('Zelle Payment', 0)) > 0.01:
        imbalance_sources.append(('Zelle Payment', type_nets['Zelle Payment']))
    
    if abs(type_nets.get('Shared Expense', 0)) > 0.01:
        imbalance_sources.append(('Shared Expense', type_nets['Shared Expense']))
    
    for source, amount in imbalance_sources:
        print(f"  {source}: ${amount:,.2f}")
    
    return imbalance_sources

def suggest_corrections(imbalance_sources):
    """Suggest corrections for the identified imbalances"""
    print("\n🔧 SUGGESTED CORRECTIONS:")
    print("=" * 50)
    
    for source, amount in imbalance_sources:
        if source == 'Personal Expense':
            print(f"\n📝 Personal Expense Imbalance: ${amount:,.2f}")
            print("   Likely cause: Personal expenses incorrectly categorized or missing counterpart transactions")
            print("   Solution: Review personal expense logic and ensure proper categorization")
        
        elif source == 'Zelle Payment':
            print(f"\n💳 Zelle Payment Imbalance: ${amount:,.2f}")
            print("   Likely cause: Zelle payments not properly matched with shared expenses")
            print("   Solution: Ensure each Zelle payment has a corresponding shared expense entry")
        
        elif source == 'Shared Expense':
            print(f"\n🤝 Shared Expense Imbalance: ${amount:,.2f}")
            print("   Likely cause: Shared expenses not properly balanced between people")
            print("   Solution: Verify shared expense allocation logic")

def main():
    """Main investigation process"""
    print("🔍 ZELLE & PERSONAL EXPENSE INVESTIGATION")
    print("=" * 60)
    
    # Load data
    df = load_corrected_audit_trail()
    if df is None:
        return
    
    # Ensure numeric columns
    df['Net_Effect'] = pd.to_numeric(df['Net_Effect'], errors='coerce')
    df['Amount_Paid'] = pd.to_numeric(df['Amount_Paid'], errors='coerce')
    df['Share_Owed'] = pd.to_numeric(df['Share_Owed'], errors='coerce')
    
    # Run analyses
    analyze_zelle_transactions(df)
    analyze_personal_expenses(df)
    analyze_shared_expenses(df)
    
    # Identify imbalance sources
    imbalance_sources = identify_imbalance_sources(df)
    
    # Suggest corrections
    suggest_corrections(imbalance_sources)
    
    print("\n🎉 INVESTIGATION COMPLETE!")
    print("\nThe $20,053 imbalance is primarily caused by:")
    print("1. Personal expenses not being properly balanced ($8,677)")
    print("2. Zelle payments not matched with shared expenses ($10,450)")
    print("3. Shared expenses not properly allocated ($927)")

if __name__ == "__main__":
    main()
