#!/usr/bin/env python3
"""
TRULY CORRECT RENT ALLOCATION
=============================

Fixes the sign error in the rent allocation logic.
"""

import pandas as pd


def create_truly_correct_rent_allocation():
    print("🔧 CREATING TRULY CORRECT RENT ALLOCATION")
    print("=" * 60)
    
    # Load the current (incorrect) rent data
    df = pd.read_csv('data/Consolidated_Rent_Allocation_CORRECTED_20250718.csv')
    print(f"✅ Loaded current rent data: {len(df)} months")
    
    # Fix the logic by flipping the signs
    print("\n🔄 FLIPPING THE SIGNS:")
    print("=" * 40)
    
    corrected_data = []
    
    for _, row in df.iterrows():
        # Current (wrong) logic has signs backwards
        # Jordyn should have POSITIVE net effect (she's owed money)
        # Ryan should have NEGATIVE net effect (he owes money)
        
        corrected_row = {
            'Month': row['Month'],
            'Gross_Total': row['Gross_Total'],
            'Ryan_Pays': 0.0,  # Ryan pays nothing
            'Ryan_Owes': row['Ryan_Owes'],  # Amount Ryan owes (same)
            'Ryan_Net_Effect': -row['Ryan_Owes'],  # NEGATIVE (he owes money)
            'Jordyn_Pays': row['Gross_Total'],  # Jordyn pays full rent
            'Jordyn_Owed': row['Ryan_Owes'],  # Jordyn is owed Ryan's share
            'Jordyn_Net_Effect': row['Ryan_Owes'],  # POSITIVE (she's owed money)
            'Transaction_Type_Ryan': 'Rent Share Owed',
            'Transaction_Type_Jordyn': 'Rent Payment (Full)',
            'Description_Ryan': f"Rent for {row['Month']} (owes Jordyn 43%)",
            'Description_Jordyn': f"Rent for {row['Month']} (paid full ${row['Gross_Total']:.2f})"
        }
        
        corrected_data.append(corrected_row)
    
    corrected_df = pd.DataFrame(corrected_data)
    
    # Verify the correction
    print("\n✅ VERIFICATION:")
    print("=" * 30)
    
    sample_month = corrected_df.iloc[0]
    print(f"Sample month: {sample_month['Month']}")
    print(f"Total rent: ${sample_month['Gross_Total']:,.2f}")
    print(f"Jordyn net effect: ${sample_month['Jordyn_Net_Effect']:+,.2f} (should be positive)")
    print(f"Ryan net effect: ${sample_month['Ryan_Net_Effect']:+,.2f} (should be negative)")
    print(f"Balance check: ${sample_month['Jordyn_Net_Effect'] + sample_month['Ryan_Net_Effect']:,.2f} (should be 0)")
    
    # Save the truly corrected allocation
    filename = 'data/TRULY_CORRECTED_Rent_Allocation_20250718.csv'
    corrected_df.to_csv(filename, index=False)
    print(f"\n💾 Saved truly corrected rent allocation: {filename}")
    
    # Calculate total impact
    total_jordyn_net = corrected_df['Jordyn_Net_Effect'].sum()
    total_ryan_net = corrected_df['Ryan_Net_Effect'].sum()
    
    print("\n📊 TOTAL IMPACT ACROSS ALL MONTHS:")
    print(f"Jordyn total owed: ${total_jordyn_net:,.2f}")
    print(f"Ryan total owes: ${abs(total_ryan_net):,.2f}")
    print(f"Balance check: ${total_jordyn_net + total_ryan_net:,.2f}")
    
    return corrected_df

def create_truly_correct_audit_transactions():
    print("\n🔄 CREATING TRULY CORRECT AUDIT TRANSACTIONS")
    print("=" * 60)
    
    # Load the truly corrected rent allocation
    df = pd.read_csv('data/TRULY_CORRECTED_Rent_Allocation_20250718.csv')
    
    transactions = []
    transaction_number = 1
    
    for _, row in df.iterrows():
        # Parse month to create date
        month_year = row['Month']
        if '-' in month_year:
            year_part = month_year.split('-')[0]
            month_part = month_year.split('-')[1]
            
            # Convert to full year
            year = int('20' + year_part) if len(year_part) == 2 else int(year_part)
            
            month_map = {
                'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
            }
            month_num = month_map.get(month_part, 1)
            date_str = f"{year}-{month_num:02d}-01"
        else:
            date_str = "2024-01-01"
        
        # Jordyn transaction (she paid full rent, is owed money)
        jordyn_transaction = {
            'Transaction_Number': transaction_number,
            'Date': date_str,
            'Person': 'Jordyn',
            'Transaction_Type': row['Transaction_Type_Jordyn'],
            'Description': row['Description_Jordyn'],
            'Amount_Paid': row['Jordyn_Pays'],
            'Share_Owed': row['Jordyn_Owed'],
            'Net_Effect': row['Jordyn_Net_Effect'],  # Positive (she's owed)
            'Source_File': 'TRULY_CORRECTED_Rent_Allocation_20250718.csv',
            'Source': 'Rent'
        }
        transactions.append(jordyn_transaction)
        transaction_number += 1
        
        # Ryan transaction (he owes money)
        ryan_transaction = {
            'Transaction_Number': transaction_number,
            'Date': date_str,
            'Person': 'Ryan',
            'Transaction_Type': row['Transaction_Type_Ryan'],
            'Description': row['Description_Ryan'],
            'Amount_Paid': row['Ryan_Pays'],
            'Share_Owed': row['Ryan_Owes'],
            'Net_Effect': row['Ryan_Net_Effect'],  # Negative (he owes)
            'Source_File': 'TRULY_CORRECTED_Rent_Allocation_20250718.csv',
            'Source': 'Rent'
        }
        transactions.append(ryan_transaction)
        transaction_number += 1
    
    transactions_df = pd.DataFrame(transactions)
    
    # Save transactions
    transactions_df.to_csv('TRULY_corrected_rent_transactions.csv', index=False)
    print(f"✅ Created {len(transactions_df)} truly corrected rent transactions")
    print("💾 Saved: TRULY_corrected_rent_transactions.csv")
    
    return transactions_df

def main():
    print("🎯 CREATING THE TRULY CORRECT RENT ALLOCATION")
    print("=" * 70)
    print("This fixes the fundamental sign error in the rent logic.\n")
    
    # Create truly corrected rent allocation
    rent_df = create_truly_correct_rent_allocation()
    
    # Create truly corrected audit transactions
    transactions_df = create_truly_correct_audit_transactions()
    
    print("\n🎉 TRULY CORRECT RENT ALLOCATION COMPLETE!")
    print("=" * 70)
    print("The signs are now correct:")
    print("✅ Jordyn has POSITIVE net effects (she's owed money)")
    print("✅ Ryan has NEGATIVE net effects (he owes money)")
    print("\nNext step: Integrate these into the audit trail")

if __name__ == "__main__":
    main()
