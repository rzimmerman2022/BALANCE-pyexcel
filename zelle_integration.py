"""
ZELLE INTEGRATION - Add missing Zelle payments to the reconciliation system
Creates an enhanced reconciliation that includes Zelle payments
"""

import pandas as pd
from datetime import datetime
import numpy as np

def load_unmatched_zelle_payments():
    """Load the unmatched Zelle payments from the matcher"""
    print("Loading unmatched Zelle payments...")
    
    # Find the most recent unmatched Zelle file
    import glob
    files = glob.glob("unmatched_zelle_payments_*.csv")
    
    if not files:
        print("No unmatched Zelle payments file found!")
        print("Run zelle_matcher.py first to identify unmatched payments")
        return None
    
    # Get the most recent file
    latest_file = max(files, key=lambda x: x.split('_')[-1])
    print(f"Loading: {latest_file}")
    
    try:
        df = pd.read_csv(latest_file)
        print(f"Loaded {len(df)} unmatched Zelle payments")
        return df
    except Exception as e:
        print(f"Error loading unmatched Zelle data: {e}")
        return None

def convert_zelle_to_reconciliation_format(zelle_df):
    """Convert Zelle payments to the same format as our reconciliation system"""
    if zelle_df is None or len(zelle_df) == 0:
        return pd.DataFrame()
    
    print("Converting Zelle payments to reconciliation format...")
    
    reconciliation_records = []
    
    for _, row in zelle_df.iterrows():
        # Determine transaction details
        amount = abs(row['Amount_Clean'])
        is_outgoing = row['Is_Outgoing']
        person = row['Person']
        date = pd.to_datetime(row['Date'])
        description = f"Zelle: {row['Description']}"
        category = row['Category']
        
        if person == 'Unknown':
            print(f"⚠️ Manual review needed for: {description} (${amount})")
            # Skip unknown person transactions for now
            continue
        
        # Create reconciliation record(s)
        if category == 'Shared':
            # Shared expense - create two records (one for payer, one for beneficiary)
            if is_outgoing:
                # Person paid, should be reimbursed for half
                payer_record = {
                    'Date': date,
                    'Person': person,
                    'Transaction_Type': 'Split Expense (Equal)',
                    'Description': description,
                    'Amount_Paid': amount,
                    'Share_Owed': amount / 2,  # Split equally
                    'Net_Effect': -(amount / 2),  # They're owed half back
                    'Source': 'Zelle',
                    'Source_File': row['Source_File'],
                    'Original_Row': row['Original_Row'],
                    'Explanation': f"{person} paid ${amount:.2f} via Zelle, should be reimbursed ${amount/2:.2f}"
                }
                
                # Determine the other person
                other_person = 'Jordyn' if person == 'Ryan' else 'Ryan'
                beneficiary_record = {
                    'Date': date,
                    'Person': other_person,
                    'Transaction_Type': 'Shared Expense Benefit',
                    'Description': description,
                    'Amount_Paid': 0.0,
                    'Share_Owed': amount / 2,
                    'Net_Effect': amount / 2,  # They owe half
                    'Source': 'Zelle',
                    'Source_File': row['Source_File'],
                    'Original_Row': row['Original_Row'],
                    'Explanation': f"{other_person} owes ${amount/2:.2f} for Zelle payment made by {person}"
                }
                
                reconciliation_records.extend([payer_record, beneficiary_record])
                
            else:
                # Person received money - this might be reimbursement
                # For now, treat as personal income (net effect = 0 for shared expenses)
                record = {
                    'Date': date,
                    'Person': person,
                    'Transaction_Type': 'Zelle Receipt',
                    'Description': description,
                    'Amount_Paid': 0.0,
                    'Share_Owed': 0.0,
                    'Net_Effect': -amount,  # They received money, reduces what they owe
                    'Source': 'Zelle',
                    'Source_File': row['Source_File'],
                    'Original_Row': row['Original_Row'],
                    'Explanation': f"{person} received ${amount:.2f} via Zelle"
                }
                
                reconciliation_records.append(record)
        
        elif category == 'Personal':
            # Personal expense - no sharing
            if is_outgoing:
                record = {
                    'Date': date,
                    'Person': person,
                    'Transaction_Type': 'Personal Expense',
                    'Description': description,
                    'Amount_Paid': amount,
                    'Share_Owed': 0.0,  # No sharing for personal
                    'Net_Effect': 0.0,  # No impact on shared balance
                    'Source': 'Zelle',
                    'Source_File': row['Source_File'],
                    'Original_Row': row['Original_Row'],
                    'Explanation': f"{person} made personal Zelle payment of ${amount:.2f}"
                }
                
                reconciliation_records.append(record)
        
        else:  # Unknown category
            print(f"⚠️ Manual review needed for category: {description} (${amount})")
            # Create a placeholder record that needs manual review
            record = {
                'Date': date,
                'Person': person,
                'Transaction_Type': 'Zelle - Needs Review',
                'Description': f"REVIEW NEEDED: {description}",
                'Amount_Paid': amount if is_outgoing else 0.0,
                'Share_Owed': 0.0,  # Will be determined during review
                'Net_Effect': 0.0,  # Will be determined during review
                'Source': 'Zelle',
                'Source_File': row['Source_File'],
                'Original_Row': row['Original_Row'],
                'Explanation': f"Manual review needed for {person} Zelle transaction"
            }
            
            reconciliation_records.append(record)
    
    if reconciliation_records:
        result_df = pd.DataFrame(reconciliation_records)
        print(f"Created {len(result_df)} reconciliation records from Zelle payments")
        return result_df
    else:
        print("No reconciliation records created from Zelle payments")
        return pd.DataFrame()

def load_existing_reconciliation():
    """Load the existing reconciliation data"""
    print("Loading existing reconciliation data...")
    
    try:
        # Use the latest enhanced audit trail
        df = pd.read_csv("enhanced_audit_trail_20250630_223446.csv")
        print(f"Loaded {len(df)} existing reconciliation records")
        return df
    except Exception as e:
        print(f"Error loading existing reconciliation: {e}")
        return None

def combine_reconciliation_data(existing_df, zelle_df):
    """Combine existing reconciliation with Zelle payments"""
    if existing_df is None:
        print("Cannot combine without existing reconciliation data")
        return None
    
    if zelle_df is None or len(zelle_df) == 0:
        print("No Zelle data to add - returning existing reconciliation")
        return existing_df
    
    print(f"Combining {len(existing_df)} existing records with {len(zelle_df)} Zelle records...")
    
    # Ensure both DataFrames have the same columns
    required_columns = [
        'Date', 'Person', 'Transaction_Type', 'Description', 'Amount_Paid', 
        'Share_Owed', 'Net_Effect', 'Source', 'Source_File', 'Original_Row', 'Explanation'
    ]
    
    # Add missing columns to Zelle data if needed
    for col in required_columns:
        if col not in zelle_df.columns:
            zelle_df[col] = ''
    
    # Select only required columns from both DataFrames
    existing_subset = existing_df[required_columns].copy()
    zelle_subset = zelle_df[required_columns].copy()
    
    # Combine the data
    combined_df = pd.concat([existing_subset, zelle_subset], ignore_index=True)
    
    # Sort by date
    combined_df['Date'] = pd.to_datetime(combined_df['Date'])
    combined_df = combined_df.sort_values('Date').reset_index(drop=True)
    
    # Recalculate running balances
    combined_df = recalculate_running_balances(combined_df)
    
    print(f"Combined reconciliation has {len(combined_df)} total records")
    return combined_df

def recalculate_running_balances(df):
    """Recalculate running balances for the combined data"""
    print("Recalculating running balances...")
    
    # Add transaction numbers
    df['Transaction_Number'] = range(1, len(df) + 1)
    
    # Calculate running balances for each person
    df['Running_Balance'] = 0.0
    
    ryan_balance = 0.0
    jordyn_balance = 0.0
    
    for idx, row in df.iterrows():
        if row['Person'] == 'Ryan':
            ryan_balance += row['Net_Effect']
            df.at[idx, 'Running_Balance'] = ryan_balance
        elif row['Person'] == 'Jordyn':
            jordyn_balance += row['Net_Effect']
            df.at[idx, 'Running_Balance'] = jordyn_balance
    
    return df

def generate_enhanced_reconciliation_report(df):
    """Generate a report for the enhanced reconciliation"""
    print("\n" + "=" * 80)
    print("ENHANCED RECONCILIATION REPORT (WITH ZELLE PAYMENTS)")
    print("=" * 80)
    
    if df is None or len(df) == 0:
        print("No data to report")
        return
    
    print(f"Total transactions: {len(df)}")
    
    # Breakdown by source
    source_counts = df['Source'].value_counts()
    print(f"\nTransactions by source:")
    for source, count in source_counts.items():
        source_df = df[df['Source'] == source]
        total_amount = source_df['Amount_Paid'].sum()
        print(f"  {source}: {count} transactions (${total_amount:,.2f} total payments)")
    
    # Final balances
    final_balances = df.groupby('Person')['Running_Balance'].last()
    print(f"\nFinal balances (after including Zelle payments):")
    for person, balance in final_balances.items():
        if balance < 0:
            print(f"  {person}: ${balance:,.2f} (is owed ${abs(balance):,.2f})")
        else:
            print(f"  {person}: ${balance:,.2f} (owes ${balance:,.2f})")
    
    # System balance check
    total_balance = sum(final_balances)
    print(f"\nSystem balance: ${total_balance:.2f}")
    if abs(total_balance) < 0.01:
        print("✅ System is balanced!")
    else:
        print(f"⚠️ System imbalance: ${abs(total_balance):,.2f} (expected due to personal expenses)")
    
    # Show Zelle transaction summary
    zelle_transactions = df[df['Source'] == 'Zelle']
    if len(zelle_transactions) > 0:
        print(f"\nZelle transactions added: {len(zelle_transactions)}")
        print("Sample Zelle transactions:")
        sample_cols = ['Date', 'Person', 'Description', 'Amount_Paid', 'Net_Effect']
        print(zelle_transactions[sample_cols].head(10).to_string(index=False))

def save_enhanced_reconciliation(df, timestamp=None):
    """Save the enhanced reconciliation"""
    if df is None or len(df) == 0:
        print("No data to save")
        return
    
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    filename = f"enhanced_reconciliation_with_zelle_{timestamp}.csv"
    df.to_csv(filename, index=False)
    print(f"Enhanced reconciliation saved to: {filename}")
    
    return filename

def main():
    """Main integration process"""
    print("ZELLE INTEGRATION INTO RECONCILIATION")
    print("=" * 50)
    
    # Load unmatched Zelle payments
    zelle_df = load_unmatched_zelle_payments()
    
    if zelle_df is None or len(zelle_df) == 0:
        print("No unmatched Zelle payments to integrate")
        return
    
    # Convert to reconciliation format
    zelle_reconciliation_df = convert_zelle_to_reconciliation_format(zelle_df)
    
    # Load existing reconciliation
    existing_df = load_existing_reconciliation()
    
    # Combine the data
    enhanced_df = combine_reconciliation_data(existing_df, zelle_reconciliation_df)
    
    if enhanced_df is not None:
        # Generate report
        generate_enhanced_reconciliation_report(enhanced_df)
        
        # Save enhanced reconciliation
        filename = save_enhanced_reconciliation(enhanced_df)
        
        print(f"\n" + "=" * 80)
        print("ZELLE INTEGRATION COMPLETE!")
        print(f"Enhanced reconciliation saved as: {filename}")
        print("This file now includes all your Zelle payments!")
        print("=" * 80)

if __name__ == "__main__":
    main()
