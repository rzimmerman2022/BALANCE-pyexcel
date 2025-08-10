"""
COMPREHENSIVE TRANSACTION AUDIT REPORT
Lists every single transaction with complete source details for manual review
"""

from datetime import datetime

import pandas as pd


def generate_comprehensive_audit():
    """Generate a detailed transaction-by-transaction audit report"""
    print("=" * 100)
    print("COMPREHENSIVE TRANSACTION AUDIT REPORT")
    print("Every transaction with complete source details for manual review")
    print("=" * 100)
    
    # Load the integrated audit trail (with Zelle)
    try:
        audit_df = pd.read_csv("integrated_audit_trail_with_zelle_20250701_015537.csv")
        print(f"✅ Loaded integrated audit trail: {len(audit_df)} transactions")
    except:
        # Fall back to enhanced audit trail (without Zelle)
        try:
            audit_df = pd.read_csv("enhanced_audit_trail_20250630_223446.csv")
            print(f"✅ Loaded enhanced audit trail: {len(audit_df)} transactions")
        except:
            print("❌ Could not load audit trail file")
            return None
    
    # Convert date for sorting
    audit_df['Date'] = pd.to_datetime(audit_df['Date'])
    audit_df = audit_df.sort_values(['Date', 'Transaction_Number']).reset_index(drop=True)
    
    # Create detailed audit report
    print("\n📊 AUDIT SUMMARY:")
    print(f"  • Total transactions: {len(audit_df)}")
    print(f"  • Date range: {audit_df['Date'].min().strftime('%Y-%m-%d')} to {audit_df['Date'].max().strftime('%Y-%m-%d')}")
    print(f"  • Sources: {', '.join(audit_df['Source'].unique())}")
    
    # Generate the detailed report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    detailed_report_file = f"detailed_transaction_audit_{timestamp}.csv"
    
    # Select and reorder columns for audit
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
    
    # Create the audit report
    audit_report = audit_df[audit_columns].copy()
    
    # Format dates and numbers for readability
    audit_report['Date'] = audit_report['Date'].dt.strftime('%Y-%m-%d')
    audit_report['Amount_Paid'] = audit_report['Amount_Paid'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "$0.00")
    audit_report['Share_Owed'] = audit_report['Share_Owed'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "$0.00")
    audit_report['Net_Effect'] = audit_report['Net_Effect'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "$0.00")
    audit_report['Running_Balance'] = audit_report['Running_Balance'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "$0.00")
    
    # Save the detailed report
    audit_report.to_csv(detailed_report_file, index=False)
    print(f"✅ Detailed audit report saved: {detailed_report_file}")
    
    # Generate summary by source
    print("\n📋 TRANSACTION BREAKDOWN BY SOURCE:")
    source_summary = audit_df.groupby(['Source', 'Source_File']).agg({
        'Transaction_Number': 'count',
        'Amount_Paid': 'sum'
    }).round(2)
    
    for (source, source_file), data in source_summary.iterrows():
        count = data['Transaction_Number']
        total = data['Amount_Paid']
        print(f"  {source} ({source_file}): {count} transactions, ${total:,.2f} total")
    
    # Show first 10 transactions as sample
    print("\n📄 SAMPLE TRANSACTIONS (first 10):")
    print("-" * 100)
    
    sample_cols = ['Transaction_Number', 'Date', 'Person', 'Description', 'Amount_Paid', 'Source_File', 'Original_Row']
    sample_df = audit_df[sample_cols].head(10)
    
    for _, row in sample_df.iterrows():
        desc = str(row['Description'])[:50] if pd.notna(row['Description']) else 'No description'
        print(f"#{row['Transaction_Number']:4d} | {row['Date'].strftime('%Y-%m-%d')} | {row['Person']:6s} | {row['Source_File']:35s} | Row {row['Original_Row']:3.0f} | ${row['Amount_Paid']:8.2f} | {desc}...")
    
    print("-" * 100)
    print("... (see full CSV file for all transactions)")
    
    # Generate verification checklist
    print("\n✅ VERIFICATION CHECKLIST:")
    print("For each transaction in the CSV file, verify:")
    print("  1. Date is correct")
    print("  2. Person is correct (Ryan or Jordyn)")
    print("  3. Amount matches the source file")
    print("  4. Description/explanation makes sense")
    print("  5. Source file and row number are accurate")
    print("  6. Transaction type is appropriate")
    
    # Check for any missing source references
    missing_source_file = audit_df[audit_df['Source_File'].isna() | (audit_df['Source_File'] == '')]
    missing_original_row = audit_df[audit_df['Original_Row'].isna()]
    
    if len(missing_source_file) > 0 or len(missing_original_row) > 0:
        print("\n⚠️  WARNING - MISSING SOURCE REFERENCES:")
        if len(missing_source_file) > 0:
            print(f"  • {len(missing_source_file)} transactions missing source file")
        if len(missing_original_row) > 0:
            print(f"  • {len(missing_original_row)} transactions missing original row number")
    else:
        print("\n✅ All transactions have complete source references!")
    
    return detailed_report_file

def generate_source_file_cross_reference():
    """Generate a cross-reference showing which source rows were used"""
    print("\n" + "=" * 100)
    print("SOURCE FILE CROSS-REFERENCE")
    print("Shows which rows from each source file were included in the reconciliation")
    print("=" * 100)
    
    try:
        audit_df = pd.read_csv("integrated_audit_trail_with_zelle_20250701_015537.csv")
    except:
        try:
            audit_df = pd.read_csv("enhanced_audit_trail_20250630_223446.csv")
        except:
            print("❌ Could not load audit trail file")
            return
    
    # Group by source file
    for source_file in audit_df['Source_File'].unique():
        if pd.isna(source_file) or source_file == '':
            continue
            
        file_transactions = audit_df[audit_df['Source_File'] == source_file]
        
        print(f"\n📁 {source_file}:")
        print(f"  • Transactions used: {len(file_transactions)}")
        
        # Show row number usage
        if 'Original_Row' in file_transactions.columns:
            used_rows = file_transactions['Original_Row'].dropna().astype(int).sort_values()
            if len(used_rows) > 0:
                print(f"  • Source rows used: {used_rows.min()} to {used_rows.max()}")
                
                # Show any gaps in row numbers (might indicate missing data)
                row_range = list(range(used_rows.min(), used_rows.max() + 1))
                missing_rows = [r for r in row_range if r not in used_rows.values]
                if missing_rows:
                    print(f"  • Missing rows in range: {missing_rows[:10]}{'...' if len(missing_rows) > 10 else ''}")
                else:
                    print("  • No gaps in row sequence")
        
        # Show sample transactions from this file
        sample = file_transactions[['Transaction_Number', 'Date', 'Person', 'Description', 'Original_Row']].head(3)
        print("  • Sample transactions:")
        for _, row in sample.iterrows():
            print(f"    #{row['Transaction_Number']} | Row {row['Original_Row']:.0f} | {row['Person']} | {row['Description'][:60]}...")

def main():
    """Generate comprehensive audit reports"""
    
    # Generate the main detailed audit report
    audit_file = generate_comprehensive_audit()
    
    # Generate source file cross-reference
    generate_source_file_cross_reference()
    
    print("\n" + "=" * 100)
    print("AUDIT REPORTS GENERATED")
    print("=" * 100)
    print(f"📁 Main audit file: {audit_file}")
    print("📋 This file contains every transaction with:")
    print("   • Transaction number and date")
    print("   • Person (Ryan/Jordyn)")
    print("   • Complete description")
    print("   • All amounts (paid, owed, net effect)")
    print("   • Source file name and original row number")
    print("   • Full explanation of each transaction")
    print("")
    print("🔍 Open the CSV file in Excel to review each transaction")
    print("📝 You can add a 'Verified' column to check off each one")
    print("⚠️  Pay special attention to transactions you don't recognize")
    print("")
    print("=" * 100)

if __name__ == "__main__":
    main()
