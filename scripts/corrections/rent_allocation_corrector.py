"""
Rent Allocation Correction Tool
Creates corrected rent allocation CSV with proper logic:
- Jordyn pays full rent
- Ryan owes 43% back to Jordyn
- Jordyn is owed 43% from Ryan
"""

import pandas as pd
import numpy as np

def create_corrected_rent_allocation():
    """Create corrected rent allocation CSV"""
    
    print("🔧 CREATING CORRECTED RENT ALLOCATION")
    print("=" * 50)
    
    # Load the current (incorrect) rent data
    try:
        current_rent = pd.read_csv("data/Consolidated_Rent_Allocation_20250527.csv")
        print(f"✅ Loaded current rent data: {len(current_rent)} months")
    except Exception as e:
        print(f"❌ Error loading current rent data: {e}")
        return None
    
    # Helper function to clean currency strings
    def clean_currency(value):
        if pd.isna(value) or value == '':
            return 0.0
        str_val = str(value).strip()
        cleaned = str_val.replace('$', '').replace(',', '').replace(' ', '')
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
    
    # Clean the current data
    current_rent['Gross Total Clean'] = current_rent['Gross Total'].apply(clean_currency)
    current_rent['Ryan Share Clean'] = current_rent["Ryan's Rent (43%)"].apply(clean_currency)
    current_rent['Jordyn Share Clean'] = current_rent["Jordyn's Rent (57%)"].apply(clean_currency)
    
    print("\n📊 CURRENT (INCORRECT) ALLOCATION:")
    print("-" * 40)
    print("Shows Ryan paying full rent, owing his 43% share")
    recent_total = current_rent['Gross Total Clean'].iloc[-1]
    recent_ryan = current_rent['Ryan Share Clean'].iloc[-1]
    recent_jordyn = current_rent['Jordyn Share Clean'].iloc[-1]
    print(f"Recent example: ${recent_total:.2f} total")
    print(f"  Ryan shown as: pays ${recent_total:.2f}, owes ${recent_ryan:.2f}")
    print(f"  Jordyn shown as: pays $0, owes ${recent_jordyn:.2f}")
    
    # Create corrected allocation
    corrected_data = []
    
    for _, row in current_rent.iterrows():
        month = row['Month']
        gross_total = row['Gross Total Clean']
        
        # CORRECTED LOGIC:
        # - Jordyn pays the FULL rent
        # - Ryan owes 43% of the total back to Jordyn
        # - Jordyn is owed 43% from Ryan (so her net is negative)
        
        ryan_owes = gross_total * 0.43  # Ryan's 43% share
        jordyn_overpaid = gross_total * 0.43  # Jordyn overpaid by Ryan's share
        
        corrected_data.append({
            'Month': month,
            'Gross_Total': gross_total,
            'Ryan_Pays': 0.0,  # Ryan pays nothing
            'Ryan_Owes': ryan_owes,  # Ryan owes 43%
            'Ryan_Net_Effect': ryan_owes,  # Positive = owes money
            'Jordyn_Pays': gross_total,  # Jordyn pays full rent
            'Jordyn_Owed': ryan_owes,  # Jordyn is owed 43% from Ryan
            'Jordyn_Net_Effect': -jordyn_overpaid,  # Negative = overpaid/owed money
            'Transaction_Type_Ryan': 'Rent Share Owed',
            'Transaction_Type_Jordyn': 'Rent Payment (Full)',
            'Description_Ryan': f"Rent for {month} (Jordyn paid, Ryan owes 43%)",
            'Description_Jordyn': f"Rent for {month} (paid full ${gross_total:.2f})"
        })
    
    # Convert to DataFrame
    corrected_df = pd.DataFrame(corrected_data)
    
    print(f"\n✅ CORRECTED ALLOCATION:")
    print("-" * 40)
    print("Jordyn pays full rent, Ryan owes 43% back to her")
    print(f"Recent example: ${recent_total:.2f} total")
    print(f"  Jordyn: pays ${recent_total:.2f}, owed ${ryan_owes:.2f}, net = ${-jordyn_overpaid:.2f}")
    print(f"  Ryan: pays $0, owes ${ryan_owes:.2f}, net = ${ryan_owes:.2f}")
    
    # Save corrected allocation
    corrected_df.to_csv("data/Consolidated_Rent_Allocation_CORRECTED_20250718.csv", index=False)
    print(f"\n💾 Saved corrected allocation: data/Consolidated_Rent_Allocation_CORRECTED_20250718.csv")
    
    # Calculate total impact
    total_months = len(corrected_df)
    total_ryan_correct = corrected_df['Ryan_Net_Effect'].sum()
    total_jordyn_correct = corrected_df['Jordyn_Net_Effect'].sum()
    
    print(f"\n📈 TOTAL IMPACT ACROSS {total_months} MONTHS:")
    print("-" * 40)
    print(f"Ryan total owed: ${total_ryan_correct:,.2f}")
    print(f"Jordyn total overpaid: ${abs(total_jordyn_correct):,.2f}")
    print(f"Balance check: ${total_ryan_correct + total_jordyn_correct:.2f} (should be 0)")
    
    return corrected_df

def create_corrected_audit_transactions():
    """Create corrected rent transactions for the audit trail"""
    
    print("\n🔄 CREATING CORRECTED AUDIT TRANSACTIONS")
    print("=" * 50)
    
    try:
        corrected_rent = pd.read_csv("data/Consolidated_Rent_Allocation_CORRECTED_20250718.csv")
    except Exception as e:
        print(f"❌ Error loading corrected rent data: {e}")
        return None
    
    # Create transactions for audit trail
    transactions = []
    transaction_number = 1
    
    for _, row in corrected_rent.iterrows():
        month = row['Month']
        
        # Convert month to date (first of month)
        if '-' in month:
            year_part = month.split('-')[0]   # e.g., "24", "25"  
            month_part = month.split('-')[1]  # e.g., "Jan", "Feb"
            
            # Convert 2-digit year to 4-digit
            year = int('20' + year_part) if len(year_part) == 2 else int(year_part)
            
            month_map = {
                'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
            }
            month_num = month_map.get(month_part, 1)
            date_str = f"{year}-{month_num:02d}-01"
        else:
            date_str = "2024-01-01"  # fallback
        
        # Jordyn's transaction - pays full rent
        transactions.append({
            'Transaction_Number': transaction_number,
            'Date': date_str,
            'Person': 'Jordyn',
            'Transaction_Type': row['Transaction_Type_Jordyn'],
            'Description': row['Description_Jordyn'],
            'Amount_Paid': row['Jordyn_Pays'],
            'Share_Owed': row['Jordyn_Owed'],  # She's owed Ryan's share
            'Net_Effect': row['Jordyn_Net_Effect'],
            'Source_File': 'Consolidated_Rent_Allocation_CORRECTED_20250718.csv',
            'Source': 'Rent'
        })
        transaction_number += 1
        
        # Ryan's transaction - owes his share
        transactions.append({
            'Transaction_Number': transaction_number,
            'Date': date_str,
            'Person': 'Ryan',
            'Transaction_Type': row['Transaction_Type_Ryan'],
            'Description': row['Description_Ryan'],
            'Amount_Paid': row['Ryan_Pays'],  # Pays nothing
            'Share_Owed': row['Ryan_Owes'],   # Owes his share
            'Net_Effect': row['Ryan_Net_Effect'],
            'Source_File': 'Consolidated_Rent_Allocation_CORRECTED_20250718.csv',
            'Source': 'Rent'
        })
        transaction_number += 1
    
    # Convert to DataFrame and save
    transactions_df = pd.DataFrame(transactions)
    transactions_df.to_csv("corrected_rent_transactions.csv", index=False)
    
    print(f"✅ Created {len(transactions_df)} corrected rent transactions")
    print("💾 Saved: corrected_rent_transactions.csv")
    
    return transactions_df

if __name__ == "__main__":
    # Create corrected rent allocation
    corrected_allocation = create_corrected_rent_allocation()
    
    if corrected_allocation is not None:
        # Create corrected transactions
        corrected_transactions = create_corrected_audit_transactions()
        
        print("\n🎉 RENT ALLOCATION CORRECTION COMPLETE!")
        print("=" * 50)
        print("Next steps:")
        print("1. Review corrected files")
        print("2. Replace original rent data with corrected version")
        print("3. Regenerate comprehensive audit trail")
        print("4. Recalculate all balances")
        print("5. Update Power BI datasets")
