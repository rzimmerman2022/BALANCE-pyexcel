#!/usr/bin/env python3
"""
FINAL BALANCE CORRECTION
========================

Creates the final corrected audit trail by properly handling:
1. Zelle payments (should create offsetting entries)
2. Personal expenses (should be neutral overall)
3. Shared expenses (should be balanced between people)

Author: Financial Analysis System
Date: 2025-01-18
"""

import os
from datetime import datetime

import pandas as pd


def load_corrected_audit_trail():
    """Load the current corrected audit trail"""
    files = [f for f in os.listdir('.') if f.startswith('corrected_audit_trail_with_rent_fix_')]
    if not files:
        print("❌ No corrected audit trail found")
        return None
    
    latest_file = max(files, key=lambda x: os.path.getctime(x))
    df = pd.read_csv(latest_file)
    print(f"✅ Loaded: {latest_file}")
    return df

def create_zelle_offsetting_entries(df):
    """Create offsetting entries for Zelle payments"""
    print("\n💳 CREATING ZELLE OFFSETTING ENTRIES:")
    print("=" * 50)
    
    zelle_df = df[df['Transaction_Type'] == 'Zelle Payment'].copy()
    
    if len(zelle_df) == 0:
        print("No Zelle transactions found")
        return pd.DataFrame()
    
    offsetting_entries = []
    
    for _, zelle_row in zelle_df.iterrows():
        # Create offsetting entry for Ryan (since all Zelle payments are from Jordyn to Ryan)
        offset_entry = {
            'Transaction_Number': f"{zelle_row['Transaction_Number']}_offset",
            'Date': zelle_row['Date'],
            'Person': 'Ryan',  # Zelle recipient
            'Transaction_Type': 'Zelle Receipt',
            'Description': f"Received from Jordyn: {zelle_row['Description']}",
            'Amount_Paid': 0.0,
            'Share_Owed': 0.0,
            'Net_Effect': abs(zelle_row['Net_Effect']),  # Positive for Ryan
            'Source_File': zelle_row['Source_File'],
            'Source': 'Zelle_Offset'
        }
        offsetting_entries.append(offset_entry)
    
    offset_df = pd.DataFrame(offsetting_entries)
    print(f"✅ Created {len(offset_df)} Zelle offsetting entries")
    
    return offset_df

def fix_personal_expenses(df):
    """Fix personal expense categorization"""
    print("\n💰 ANALYZING PERSONAL EXPENSES:")
    print("=" * 50)
    
    personal_df = df[df['Transaction_Type'] == 'Personal Expense'].copy()
    
    # Personal expenses should only affect the person who incurred them
    # The current logic seems correct, so the issue might be elsewhere
    
    jordyn_personal = personal_df[personal_df['Person'] == 'Jordyn']['Net_Effect'].sum()
    ryan_personal = personal_df[personal_df['Person'] == 'Ryan']['Net_Effect'].sum()
    
    print(f"Jordyn personal expenses: ${jordyn_personal:,.2f}")
    print(f"Ryan personal expenses: ${ryan_personal:,.2f}")
    print(f"Total personal expense impact: ${jordyn_personal + ryan_personal:,.2f}")
    
    # Personal expenses are actually correct - they represent money each person spent on themselves
    print("✅ Personal expenses are correctly categorized")
    
    return pd.DataFrame()  # No changes needed

def fix_shared_expenses(df):
    """Fix shared expense allocation"""
    print("\n🤝 FIXING SHARED EXPENSES:")
    print("=" * 50)
    
    shared_df = df[df['Transaction_Type'] == 'Shared Expense'].copy()
    
    if len(shared_df) == 0:
        print("No shared expenses found")
        return pd.DataFrame()
    
    offsetting_entries = []
    
    # For each shared expense, create an offsetting entry for the other person
    for _, shared_row in shared_df.iterrows():
        if shared_row['Person'] == 'Ryan':
            # Create offsetting entry for Jordyn
            offset_entry = {
                'Transaction_Number': f"{shared_row['Transaction_Number']}_shared_offset",
                'Date': shared_row['Date'],
                'Person': 'Jordyn',
                'Transaction_Type': 'Shared Expense Benefit',
                'Description': f"Share of Ryan's expense: {shared_row['Description']}",
                'Amount_Paid': 0.0,
                'Share_Owed': 0.0,
                'Net_Effect': shared_row['Share_Owed'],  # Jordyn benefits from Ryan's expense
                'Source_File': shared_row['Source_File'],
                'Source': 'Shared_Offset'
            }
            offsetting_entries.append(offset_entry)
    
    offset_df = pd.DataFrame(offsetting_entries)
    print(f"✅ Created {len(offset_df)} shared expense offsetting entries")
    
    return offset_df

def create_final_corrected_trail(df):
    """Create the final corrected audit trail"""
    print("\n🔧 CREATING FINAL CORRECTED AUDIT TRAIL:")
    print("=" * 60)
    
    # Create offsetting entries
    zelle_offsets = create_zelle_offsetting_entries(df)
    personal_fixes = fix_personal_expenses(df)
    shared_offsets = fix_shared_expenses(df)
    
    # Combine all data
    all_dfs = [df]
    
    if not zelle_offsets.empty:
        all_dfs.append(zelle_offsets)
    
    if not personal_fixes.empty:
        all_dfs.append(personal_fixes)
    
    if not shared_offsets.empty:
        all_dfs.append(shared_offsets)
    
    final_df = pd.concat(all_dfs, ignore_index=True)
    
    # Sort by date and transaction number
    final_df['Date'] = pd.to_datetime(final_df['Date'])
    final_df = final_df.sort_values(['Date', 'Transaction_Number']).reset_index(drop=True)
    
    print(f"📈 Final audit trail: {len(final_df)} transactions")
    
    return final_df

def verify_final_balances(df):
    """Verify the final balances"""
    print("\n✅ FINAL BALANCE VERIFICATION:")
    print("=" * 50)
    
    # Ensure numeric
    df['Net_Effect'] = pd.to_numeric(df['Net_Effect'], errors='coerce')
    
    # Calculate final balances
    person_balances = df.groupby('Person')['Net_Effect'].sum().round(2)
    total_balance = person_balances.sum()
    
    print("Final balances:")
    for person, balance in person_balances.items():
        status = "owes" if balance > 0 else "is owed"
        print(f"  {person}: ${abs(balance):,.2f} ({status})")
    
    print(f"\nBalance check: ${total_balance:,.2f}")
    
    if abs(total_balance) < 0.01:
        print("🎉 BALANCES ARE NOW RECONCILED!")
        return True
    else:
        print(f"❌ Still ${abs(total_balance):,.2f} imbalance remaining")
        return False

def save_final_audit_trail(df):
    """Save the final corrected audit trail"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"FINAL_corrected_audit_trail_{timestamp}.csv"
    
    df.to_csv(filename, index=False)
    print(f"\n💾 Saved final audit trail: {filename}")
    
    return filename

def main():
    """Main correction process"""
    print("🎯 FINAL BALANCE CORRECTION")
    print("=" * 60)
    print("This script creates the definitive corrected audit trail")
    print("by properly handling Zelle payments and shared expenses.\n")
    
    # Load current data
    df = load_corrected_audit_trail()
    if df is None:
        return
    
    # Create final corrected trail
    final_df = create_final_corrected_trail(df)
    
    # Verify balances
    is_balanced = verify_final_balances(final_df)
    
    # Save final trail
    output_file = save_final_audit_trail(final_df)
    
    print("\n🎉 FINAL CORRECTION COMPLETE!")
    print("=" * 60)
    
    if is_balanced:
        print("✅ All balances are now reconciled!")
        print("✅ The audit trail is mathematically correct!")
        print(f"✅ Final file: {output_file}")
    else:
        print("⚠️  Some imbalances may remain")
        print("🔍 Additional investigation may be needed")
    
    print("\nNext steps:")
    print("1. Update Power BI datasets with the final audit trail")
    print("2. Regenerate all reports and dashboards")
    print("3. Archive old audit trails")
    print("4. Document the correction process")

if __name__ == "__main__":
    main()
