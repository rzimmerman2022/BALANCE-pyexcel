"""
COMPREHENSIVE TRANSACTION AUDIT TOOL
Lists every single transaction with source file, row number, and all details
"""

import pandas as pd
from datetime import datetime

def generate_comprehensive_audit():
    print("=" * 80)
    print("COMPREHENSIVE TRANSACTION AUDIT")
    print("Every transaction with source file and row references")
    print("=" * 80)
    
    try:
        # Load the integrated audit trail (with Zelle)
        audit_df = pd.read_csv("integrated_audit_trail_with_zelle_20250701_015537.csv")
        print(f"✅ Loaded {len(audit_df)} transactions from integrated audit trail")
    except:
        try:
            # Fallback to regular audit trail
            audit_df = pd.read_csv("enhanced_audit_trail_20250630_223446.csv")
            print(f"✅ Loaded {len(audit_df)} transactions from enhanced audit trail")
        except Exception as e:
            print(f"❌ Error loading audit trail: {e}")
            return
    
    # Create detailed audit report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"detailed_transaction_audit_{timestamp}.csv"
    
    # Select all relevant columns for audit
    audit_columns = [
        'Transaction_Number',
        'Date', 
        'Person',
        'Transaction_Type',
        'Description',
        'Amount_Paid',
        'Share_Owed', 
        'Net_Effect',
        'Running_Balance',
        'Source',
        'Source_File',
        'Original_Row',
        'Explanation'
    ]
    
    # Ensure all columns exist
    for col in audit_columns:
        if col not in audit_df.columns:
            audit_df[col] = ''
    
    # Create the detailed audit
    detailed_audit = audit_df[audit_columns].copy()
    
    # Sort by transaction number
    detailed_audit = detailed_audit.sort_values('Transaction_Number')
    
    # Save to CSV
    detailed_audit.to_csv(output_file, index=False)
    
    print(f"✅ Comprehensive audit saved to: {output_file}")
    
    # Generate summary statistics
    print(f"\n📊 AUDIT SUMMARY:")
    print(f"Total transactions: {len(detailed_audit)}")
    
    # By source
    source_counts = detailed_audit['Source'].value_counts()
    print(f"\nBy source:")
    for source, count in source_counts.items():
        source_total = detailed_audit[detailed_audit['Source'] == source]['Amount_Paid'].sum()
        print(f"  {source}: {count} transactions, ${source_total:,.2f} total")
    
    # By person
    person_counts = detailed_audit['Person'].value_counts()
    print(f"\nBy person:")
    for person, count in person_counts.items():
        person_total = detailed_audit[detailed_audit['Person'] == person]['Amount_Paid'].sum()
        print(f"  {person}: {count} transactions, ${person_total:,.2f} total")
    
    # Show sample transactions
    print(f"\n📋 SAMPLE TRANSACTIONS (first 10):")
    print("─" * 120)
    sample_cols = ['Transaction_Number', 'Date', 'Person', 'Description', 'Amount_Paid', 'Source_File', 'Original_Row']
    print(detailed_audit[sample_cols].head(10).to_string(index=False, max_colwidth=30))
    
    print(f"\n📋 SAMPLE TRANSACTIONS (last 10):")
    print("─" * 120)
    print(detailed_audit[sample_cols].tail(10).to_string(index=False, max_colwidth=30))
    
    # Final balances
    final_balances = detailed_audit.groupby('Person')['Running_Balance'].last()
    print(f"\n💰 FINAL BALANCES:")
    for person, balance in final_balances.items():
        if balance < 0:
            print(f"  {person}: ${balance:,.2f} (is owed ${abs(balance):,.2f})")
        else:
            print(f"  {person}: ${balance:,.2f} (owes ${balance:,.2f})")
    
    # Source file breakdown
    print(f"\n📁 SOURCE FILE BREAKDOWN:")
    source_file_counts = detailed_audit['Source_File'].value_counts()
    for file, count in source_file_counts.items():
        print(f"  {file}: {count} transactions")
    
    print(f"\n" + "=" * 80)
    print(f"COMPREHENSIVE AUDIT COMPLETE!")
    print(f"Review file: {output_file}")
    print(f"This file contains every transaction with full source traceability.")
    print("=" * 80)
    
    return output_file

def generate_excel_audit():
    """Generate an Excel version with multiple sheets for easier review"""
    print("\n🔄 Generating Excel version for easier review...")
    
    try:
        # Load the audit data
        audit_df = pd.read_csv("integrated_audit_trail_with_zelle_20250701_015537.csv")
    except:
        audit_df = pd.read_csv("enhanced_audit_trail_20250630_223446.csv")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    excel_file = f"detailed_transaction_audit_{timestamp}.xlsx"
    
    with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
        # Sheet 1: All transactions
        audit_df.to_excel(writer, sheet_name='All_Transactions', index=False)
        
        # Sheet 2: Expense transactions only
        expense_df = audit_df[audit_df['Source'] == 'Expense']
        expense_df.to_excel(writer, sheet_name='Expenses_Only', index=False)
        
        # Sheet 3: Rent transactions only
        rent_df = audit_df[audit_df['Source'] == 'Rent']
        rent_df.to_excel(writer, sheet_name='Rent_Only', index=False)
        
        # Sheet 4: Zelle transactions only
        zelle_df = audit_df[audit_df['Source'] == 'Zelle']
        if len(zelle_df) > 0:
            zelle_df.to_excel(writer, sheet_name='Zelle_Only', index=False)
        
        # Sheet 5: Summary
        summary_data = []
        summary_data.append(['Total Transactions', len(audit_df)])
        summary_data.append(['Expense Transactions', len(expense_df)])
        summary_data.append(['Rent Transactions', len(rent_df)])
        summary_data.append(['Zelle Transactions', len(zelle_df)])
        summary_data.append([''])
        summary_data.append(['Final Ryan Balance', audit_df[audit_df['Person'] == 'Ryan']['Running_Balance'].iloc[-1] if len(audit_df[audit_df['Person'] == 'Ryan']) > 0 else 0])
        summary_data.append(['Final Jordyn Balance', audit_df[audit_df['Person'] == 'Jordyn']['Running_Balance'].iloc[-1] if len(audit_df[audit_df['Person'] == 'Jordyn']) > 0 else 0])
        
        summary_df = pd.DataFrame(summary_data, columns=['Metric', 'Value'])
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
    
    print(f"✅ Excel audit saved to: {excel_file}")
    return excel_file

def main():
    """Generate comprehensive transaction audit"""
    csv_file = generate_comprehensive_audit()
    excel_file = generate_excel_audit()
    
    print(f"\n🎯 FILES GENERATED:")
    print(f"• CSV: {csv_file}")
    print(f"• Excel: {excel_file}")
    print(f"\nBoth files contain every transaction with:")
    print(f"• Source file name and row number")
    print(f"• Complete transaction details")
    print(f"• Running balance calculations")
    print(f"• Full audit trail")

if __name__ == "__main__":
    main()
