"""
ZELLE PAYMENT INTEGRATION SYSTEM
Integrates Zelle payments into the financial reconciliation system
"""

from datetime import datetime

import pandas as pd


def load_zelle_payments():
    """Load and process Zelle payment data"""
    print("=" * 80)
    print("LOADING ZELLE PAYMENTS")
    print("=" * 80)
    
    try:
        zelle_df = pd.read_csv("data/Zelle_From_Jordyn_Final.csv")
        print(f"✅ Loaded {len(zelle_df)} Zelle payments")
        
        # Convert date column
        zelle_df['Date'] = pd.to_datetime(zelle_df['Date'], errors='coerce')
        
        # Filter to 2024+ (our clean slate period)
        cutoff_date = datetime(2024, 1, 1)
        zelle_2024_plus = zelle_df[zelle_df['Date'] >= cutoff_date]
        
        print(f"✅ {len(zelle_2024_plus)} Zelle payments from 2024+ (filtered from {len(zelle_df)} total)")
        
        # Show summary
        total_amount = zelle_2024_plus['Amount'].sum()
        print(f"✅ Total Zelle payments (2024+): ${total_amount:,.2f}")
        
        # Show breakdown by year
        zelle_2024_plus['Year'] = zelle_2024_plus['Date'].dt.year
        yearly_summary = zelle_2024_plus.groupby('Year')['Amount'].agg(['count', 'sum'])
        print("\n📊 Zelle payments by year:")
        for year, data in yearly_summary.iterrows():
            print(f"  {year}: {data['count']} payments, ${data['sum']:,.2f}")
        
        return zelle_2024_plus
        
    except Exception as e:
        print(f"❌ Error loading Zelle data: {e}")
        return None

def analyze_zelle_impact():
    """Analyze how Zelle payments affect the current reconciliation"""
    print("\n" + "=" * 80)
    print("ANALYZING ZELLE IMPACT ON RECONCILIATION")
    print("=" * 80)
    
    # Load current reconciliation
    try:
        current_audit = pd.read_csv("enhanced_audit_trail_20250630_223446.csv")
        print(f"✅ Loaded current audit trail: {len(current_audit)} transactions")
        
        # Get current balances
        current_balances = current_audit.groupby('Person')['Running_Balance'].last()
        print("\n📊 CURRENT BALANCES (before Zelle):")
        for person, balance in current_balances.items():
            if balance < 0:
                print(f"  {person}: ${balance:,.2f} (is owed ${abs(balance):,.2f})")
            else:
                print(f"  {person}: ${balance:,.2f} (owes ${balance:,.2f})")
        
    except Exception as e:
        print(f"❌ Error loading current audit trail: {e}")
        return None
    
    # Load Zelle payments
    zelle_df = load_zelle_payments()
    if zelle_df is None:
        return None
    
    # Calculate Zelle impact
    total_zelle = zelle_df['Amount'].sum()
    
    print("\n💸 ZELLE PAYMENT IMPACT:")
    print(f"  • Jordyn paid Ryan via Zelle: ${total_zelle:,.2f}")
    print(f"  • This reduces Jordyn's debt by ${total_zelle:,.2f}")
    print(f"  • This reduces Ryan's credit by ${total_zelle:,.2f}")
    
    # Calculate adjusted balances
    print("\n📊 ADJUSTED BALANCES (after Zelle):")
    for person, balance in current_balances.items():
        if person == 'Ryan':
            adjusted_balance = balance + total_zelle  # Ryan received money, so less owed to him
            if adjusted_balance < 0:
                print(f"  Ryan: ${adjusted_balance:,.2f} (is owed ${abs(adjusted_balance):,.2f})")
            else:
                print(f"  Ryan: ${adjusted_balance:,.2f} (owes ${adjusted_balance:,.2f})")
        elif person == 'Jordyn':
            adjusted_balance = balance - total_zelle  # Jordyn paid money, so owes less
            if adjusted_balance < 0:
                print(f"  Jordyn: ${adjusted_balance:,.2f} (is owed ${abs(adjusted_balance):,.2f})")
            else:
                print(f"  Jordyn: ${adjusted_balance:,.2f} (owes ${adjusted_balance:,.2f})")
    
    # Net settlement after Zelle
    ryan_adjusted = current_balances['Ryan'] + total_zelle
    jordyn_adjusted = current_balances['Jordyn'] - total_zelle
    
    print("\n💰 FINAL SETTLEMENT (after Zelle):")
    if jordyn_adjusted > 0:
        print(f"  Jordyn still owes Ryan: ${jordyn_adjusted:,.2f}")
    elif jordyn_adjusted < 0:
        print(f"  Ryan now owes Jordyn: ${abs(jordyn_adjusted):,.2f}")
    else:
        print("  Perfect balance! No money owed either way.")
    
    return {
        'zelle_total': total_zelle,
        'ryan_before': current_balances['Ryan'],
        'jordyn_before': current_balances['Jordyn'],
        'ryan_after': ryan_adjusted,
        'jordyn_after': jordyn_adjusted,
        'zelle_payments': zelle_df
    }

def generate_integrated_audit_trail():
    """Generate a new audit trail that includes Zelle payments"""
    print("\n" + "=" * 80)
    print("GENERATING INTEGRATED AUDIT TRAIL WITH ZELLE")
    print("=" * 80)
    
    # Load current audit trail
    try:
        current_audit = pd.read_csv("enhanced_audit_trail_20250630_223446.csv")
        print(f"✅ Loaded current audit trail: {len(current_audit)} transactions")
    except Exception as e:
        print(f"❌ Error loading current audit trail: {e}")
        return None
    
    # Load Zelle payments
    zelle_df = load_zelle_payments()
    if zelle_df is None:
        return None
    
    # Convert Zelle payments to audit trail format
    zelle_transactions = []
    
    for idx, zelle in zelle_df.iterrows():
        # Create Zelle payment transaction
        zelle_trans = {
            'Transaction_Number': len(current_audit) + len(zelle_transactions) + 1,
            'Date': zelle['Date'],
            'Person': 'Jordyn',  # Jordyn sent the money
            'Transaction_Type': 'Zelle Payment',
            'Description': f"Zelle payment to Ryan: {zelle['Notes'] if pd.notna(zelle['Notes']) and zelle['Notes'].strip() else 'Payment'}",
            'Amount_Paid': zelle['Amount'],
            'Share_Owed': 0,  # This is a payment, not a shared expense
            'Net_Effect': -zelle['Amount'],  # Negative because Jordyn is reducing her debt
            'Running_Balance': 0,  # Will be calculated later
            'Source_File': 'Zelle_From_Jordyn_Final.csv',
            'Original_Row': idx + 2,  # +2 for header and 0-indexing
            'Explanation': f"Zelle payment from Jordyn to Ryan: ${zelle['Amount']:.2f}",
            'Source': 'Zelle'
        }
        zelle_transactions.append(zelle_trans)
    
    # Combine with current audit trail
    zelle_df_audit = pd.DataFrame(zelle_transactions)
    combined_audit = pd.concat([current_audit, zelle_df_audit], ignore_index=True)
    
    # Sort by date to maintain chronological order
    combined_audit['Date'] = pd.to_datetime(combined_audit['Date'])
    combined_audit = combined_audit.sort_values('Date').reset_index(drop=True)
    
    # Recalculate transaction numbers and running balances
    combined_audit['Transaction_Number'] = range(1, len(combined_audit) + 1)
    
    # Recalculate running balances by person
    ryan_balance = 0
    jordyn_balance = 0
    
    for idx, row in combined_audit.iterrows():
        if row['Person'] == 'Ryan':
            ryan_balance += row['Net_Effect']
            combined_audit.at[idx, 'Running_Balance'] = ryan_balance
        elif row['Person'] == 'Jordyn':
            jordyn_balance += row['Net_Effect']
            combined_audit.at[idx, 'Running_Balance'] = jordyn_balance
    
    # Save the integrated audit trail
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"integrated_audit_trail_with_zelle_{timestamp}.csv"
    combined_audit.to_csv(output_file, index=False)
    
    print(f"✅ Integrated audit trail saved: {output_file}")
    print(f"✅ Total transactions: {len(combined_audit)} (added {len(zelle_transactions)} Zelle payments)")
    
    # Show final balances
    final_ryan = combined_audit[combined_audit['Person'] == 'Ryan']['Running_Balance'].iloc[-1] if len(combined_audit[combined_audit['Person'] == 'Ryan']) > 0 else 0
    final_jordyn = combined_audit[combined_audit['Person'] == 'Jordyn']['Running_Balance'].iloc[-1] if len(combined_audit[combined_audit['Person'] == 'Jordyn']) > 0 else 0
    
    print("\n💰 FINAL BALANCES (with Zelle integrated):")
    if final_ryan < 0:
        print(f"  Ryan: ${final_ryan:,.2f} (is owed ${abs(final_ryan):,.2f})")
    else:
        print(f"  Ryan: ${final_ryan:,.2f} (owes ${final_ryan:,.2f})")
    
    if final_jordyn < 0:
        print(f"  Jordyn: ${final_jordyn:,.2f} (is owed ${abs(final_jordyn):,.2f})")
    else:
        print(f"  Jordyn: ${final_jordyn:,.2f} (owes ${final_jordyn:,.2f})")
    
    # Net settlement
    if final_jordyn > 0:
        print(f"\n🎯 FINAL SETTLEMENT: Jordyn owes Ryan ${final_jordyn:,.2f}")
    elif final_jordyn < 0:
        print(f"\n🎯 FINAL SETTLEMENT: Ryan owes Jordyn ${abs(final_jordyn):,.2f}")
    else:
        print("\n🎯 FINAL SETTLEMENT: Perfect balance! No money owed.")
    
    return output_file

def main():
    """Run the complete Zelle integration analysis"""
    print("🔄 ZELLE PAYMENT INTEGRATION SYSTEM")
    print("This will analyze and integrate Zelle payments into your reconciliation")
    
    # Step 1: Analyze impact
    impact_data = analyze_zelle_impact()
    
    # Step 2: Generate integrated audit trail
    integrated_file = generate_integrated_audit_trail()
    
    print("\n" + "=" * 80)
    print("ZELLE INTEGRATION COMPLETE!")
    print("=" * 80)
    print("✅ Zelle payments have been integrated into your reconciliation")
    print("✅ New integrated audit trail generated")
    print("✅ All balances updated to reflect Zelle payments")
    print("\n📁 Files generated:")
    print(f"  • {integrated_file}")

if __name__ == "__main__":
    main()
