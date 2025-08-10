#!/usr/bin/env python3
"""
INTEGRATE RENT CORRECTIONS
===========================

This script integrates the corrected rent allocation into the main audit trail,
replacing the incorrect rent transactions with the corrected ones.

Author: Financial Analysis System
Date: 2025-01-18
"""

import os
from datetime import datetime

import pandas as pd


def load_audit_trail():
    """Load the current integrated audit trail"""
    audit_file = 'integrated_audit_trail_with_zelle_20250702_103908.csv'
    
    if not os.path.exists(audit_file):
        print(f"❌ Error: Audit trail file not found: {audit_file}")
        return None
        
    df = pd.read_csv(audit_file)
    print(f"✅ Loaded audit trail: {len(df)} transactions")
    return df

def load_corrected_rent():
    """Load the corrected rent transactions"""
    rent_file = 'corrected_rent_transactions.csv'
    
    if not os.path.exists(rent_file):
        print(f"❌ Error: Corrected rent file not found: {rent_file}")
        return None
        
    df = pd.read_csv(rent_file)
    print(f"✅ Loaded corrected rent: {len(df)} transactions")
    return df

def remove_old_rent_transactions(audit_df):
    """Remove existing rent transactions from audit trail"""
    original_count = len(audit_df)
    
    # Remove all rent-related transactions
    rent_keywords = ['rent', 'Rent', 'RENT']
    
    # Create a mask for non-rent transactions
    mask = True
    for keyword in rent_keywords:
        mask = mask & (~audit_df['Description'].str.contains(keyword, na=False))
    
    cleaned_df = audit_df[mask].copy()
    removed_count = original_count - len(cleaned_df)
    
    print(f"🗑️  Removed {removed_count} old rent transactions")
    print(f"📊 Remaining transactions: {len(cleaned_df)}")
    
    return cleaned_df

def integrate_corrected_rent(audit_df, rent_df):
    """Integrate corrected rent transactions into audit trail"""
    
    # Ensure corrected rent has the same columns as audit trail
    required_columns = audit_df.columns.tolist()
    
    # Map corrected rent columns to audit trail format
    rent_mapped = pd.DataFrame()
    
    for _, row in rent_df.iterrows():
        mapped_row = {
            'Transaction_Number': row['Transaction_Number'],
            'Date': row['Date'],
            'Person': row['Person'],
            'Transaction_Type': row['Transaction_Type'],
            'Description': row['Description'],
            'Amount_Paid': row['Amount_Paid'],
            'Share_Owed': row['Share_Owed'],
            'Net_Effect': row['Net_Effect'],
            'Source_File': row['Source_File'],
            'Source': row['Source']
        }
        
        # Add any missing columns with default values
        for col in required_columns:
            if col not in mapped_row:
                mapped_row[col] = ''
        
        rent_mapped = pd.concat([rent_mapped, pd.DataFrame([mapped_row])], ignore_index=True)
    
    # Combine cleaned audit trail with corrected rent
    combined_df = pd.concat([audit_df, rent_mapped], ignore_index=True)
    
    # Sort by date and transaction number
    combined_df['Date'] = pd.to_datetime(combined_df['Date'])
    combined_df = combined_df.sort_values(['Date', 'Transaction_Number']).reset_index(drop=True)
    
    print(f"✅ Integrated {len(rent_mapped)} corrected rent transactions")
    print(f"📈 Total transactions in corrected audit trail: {len(combined_df)}")
    
    return combined_df

def calculate_corrected_balances(df):
    """Calculate running balances with corrected rent allocation"""
    
    # Ensure numeric columns
    df['Net_Effect'] = pd.to_numeric(df['Net_Effect'], errors='coerce')
    
    # Calculate running balances by person
    people = df['Person'].unique()
    
    print("\n💰 CORRECTED BALANCE SUMMARY:")
    print("=" * 50)
    
    total_balance = 0
    
    for person in people:
        person_df = df[df['Person'] == person].copy()
        person_balance = person_df['Net_Effect'].sum()
        total_balance += person_balance
        
        print(f"{person}: ${person_balance:,.2f}")
    
    print(f"\nTotal Balance Check: ${total_balance:,.2f} (should be ~0)")
    
    return df

def save_corrected_audit_trail(df):
    """Save the corrected audit trail"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"corrected_audit_trail_with_rent_fix_{timestamp}.csv"
    
    df.to_csv(filename, index=False)
    print(f"\n💾 Saved corrected audit trail: {filename}")
    
    return filename

def main():
    """Main integration process"""
    print("🔧 INTEGRATING RENT CORRECTIONS INTO AUDIT TRAIL")
    print("=" * 60)
    
    # Load data
    audit_df = load_audit_trail()
    if audit_df is None:
        return
        
    rent_df = load_corrected_rent()
    if rent_df is None:
        return
    
    # Remove old rent transactions
    cleaned_audit = remove_old_rent_transactions(audit_df)
    
    # Integrate corrected rent
    corrected_audit = integrate_corrected_rent(cleaned_audit, rent_df)
    
    # Calculate new balances
    corrected_audit = calculate_corrected_balances(corrected_audit)
    
    # Save corrected audit trail
    save_corrected_audit_trail(corrected_audit)
    
    print("\n🎉 RENT CORRECTION INTEGRATION COMPLETE!")
    print("=" * 60)
    print("Next steps:")
    print("1. Review the corrected audit trail")
    print("2. Update Power BI datasets")
    print("3. Regenerate all reports and dashboards")
    print("4. Validate that balances are now accurate")

if __name__ == "__main__":
    main()
