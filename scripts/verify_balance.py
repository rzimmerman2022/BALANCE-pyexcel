#!/usr/bin/env python3
"""
Manual Verification Script for Balance Reconciliation
This script helps you verify the calculations step-by-step
"""

import pathlib
from datetime import datetime

import pandas as pd


class BalanceVerifier:
    def __init__(self, audit_csv_path):
        """Initialize with the path to your audit CSV"""
        self.audit_df = pd.read_csv(audit_csv_path)
        self.issues = []
        
    def print_section(self, title):
        """Print a formatted section header"""
        print(f"\n{'='*60}")
        print(f" {title}")
        print(f"{'='*60}")
        
    def verify_person_column(self):
        """Check for invalid entries in person column"""
        self.print_section("PERSON COLUMN VERIFICATION")
        
        # Get unique person values
        unique_persons = self.audit_df['person'].unique()
        
        print(f"\nTotal unique person values: {len(unique_persons)}")
        print("\nExpected values: ['Ryan', 'Jordyn']")
        print("\nActual values found:")
        
        valid_persons = []
        invalid_persons = []
        
        for person in unique_persons:
            if pd.isna(person):
                invalid_persons.append("NaN/Missing")
            elif person in ['Ryan', 'Jordyn']:
                valid_persons.append(person)
            else:
                invalid_persons.append(person)
                
        print(f"\n✓ Valid: {valid_persons}")
        print(f"\n✗ Invalid ({len(invalid_persons)} found):")
        for inv in invalid_persons[:10]:  # Show first 10
            print(f"  - '{inv}'")
        
        if len(invalid_persons) > 10:
            print(f"  ... and {len(invalid_persons) - 10} more")
            
        # Count rows with invalid persons
        invalid_mask = ~self.audit_df['person'].isin(['Ryan', 'Jordyn'])
        invalid_count = invalid_mask.sum()
        
        print(f"\nRows with invalid person values: {invalid_count}")
        
        if invalid_count > 0:
            self.issues.append(f"Found {invalid_count} rows with invalid person values")
            
        return invalid_mask
        
    def verify_duplicates(self):
        """Check for duplicate transactions"""
        self.print_section("DUPLICATE TRANSACTION VERIFICATION")
        
        # Check for exact duplicates
        duplicate_cols = ['date', 'person', 'merchant', 'actual_amount', 'allowed_amount']
        duplicates = self.audit_df[self.audit_df.duplicated(subset=duplicate_cols, keep=False)]
        
        print(f"\nTotal duplicate rows: {len(duplicates)}")
        
        if len(duplicates) > 0:
            print("\nSample duplicate transactions:")
            # Group duplicates to show patterns
            dup_groups = duplicates.groupby(duplicate_cols).size().reset_index(name='count')
            dup_groups = dup_groups[dup_groups['count'] > 1].sort_values('count', ascending=False)
            
            for idx, row in dup_groups.head(5).iterrows():
                print(f"\n  Duplicated {row['count']} times:")
                print(f"    Date: {row['date']}, Person: {row['person']}")
                print(f"    Merchant: {row['merchant']}")
                print(f"    Actual: ${row['actual_amount']:.2f}, Allowed: ${row['allowed_amount']:.2f}")
                
            self.issues.append(f"Found {len(duplicates)} duplicate transactions")
            
        return duplicates
        
    def verify_balance_calculation(self):
        """Verify the balance calculations make sense"""
        self.print_section("BALANCE CALCULATION VERIFICATION")
        
        # Filter to only valid persons
        valid_df = self.audit_df[self.audit_df['person'].isin(['Ryan', 'Jordyn'])]
        
        print(f"\nProcessing {len(valid_df)} valid transactions")
        
        # Check basic accounting identity
        for person in ['Ryan', 'Jordyn']:
            person_df = valid_df[valid_df['person'] == person]
            
            total_actual = person_df['actual_amount'].sum()
            total_allowed = person_df['allowed_amount'].sum()
            total_net = person_df['net_effect'].sum()
            
            print(f"\n{person}:")
            print(f"  Total Actual Paid: ${total_actual:,.2f}")
            print(f"  Total Allowed: ${total_allowed:,.2f}")
            print(f"  Total Net Effect: ${total_net:,.2f}")
            
            # The accounting identity should be: net_effect = allowed - actual
            expected_net = total_allowed - total_actual
            discrepancy = abs(total_net - expected_net)
            
            print(f"  Expected Net: ${expected_net:,.2f}")
            print(f"  Discrepancy: ${discrepancy:,.2f}")
            
            if discrepancy > 0.01:
                self.issues.append(f"{person} has calculation discrepancy of ${discrepancy:,.2f}")
                
        # Check overall balance
        ryan_net = valid_df[valid_df['person'] == 'Ryan']['net_effect'].sum()
        jordyn_net = valid_df[valid_df['person'] == 'Jordyn']['net_effect'].sum()
        
        print("\nFinal Balance Check:")
        print(f"  Ryan Net: ${ryan_net:,.2f}")
        print(f"  Jordyn Net: ${jordyn_net:,.2f}")
        print(f"  Sum (should be ~0): ${ryan_net + jordyn_net:,.2f}")
        
        imbalance = abs(ryan_net + jordyn_net)
        if imbalance > 0.02:
            self.issues.append(f"System imbalance of ${imbalance:,.2f}")
            
    def verify_transaction_types(self):
        """Analyze transactions by type to find patterns"""
        self.print_section("TRANSACTION TYPE ANALYSIS")
        
        # Group by transaction type
        type_summary = self.audit_df.groupby('transaction_type').agg({
            'net_effect': ['count', 'sum'],
            'actual_amount': 'sum',
            'allowed_amount': 'sum'
        }).round(2)
        
        print("\nTransaction Type Summary:")
        print(type_summary)
        
        # Check for unusual patterns
        print("\n\nPattern Analysis:")
        
        # Check rent transactions
        rent_df = self.audit_df[self.audit_df['transaction_type'] == 'rent']
        if not rent_df.empty:
            print(f"\nRent Transactions: {len(rent_df)} rows")
            # Rent should typically have Ryan paying full amount
            ryan_rent = rent_df[rent_df['person'] == 'Ryan']
            print(f"  Ryan rent payments: {len(ryan_rent)}")
            print(f"  Average Ryan rent actual: ${ryan_rent['actual_amount'].mean():.2f}")
            print(f"  Average Ryan rent allowed: ${ryan_rent['allowed_amount'].mean():.2f}")
            
    def verify_source_files(self):
        """Check data from each source file"""
        self.print_section("SOURCE FILE VERIFICATION")
        
        source_summary = self.audit_df.groupby('source_file').agg({
            'net_effect': ['count', 'sum'],
            'person': lambda x: x.value_counts().to_dict()
        })
        
        print("\nSource File Summary:")
        for source in self.audit_df['source_file'].unique():
            source_df = self.audit_df[self.audit_df['source_file'] == source]
            print(f"\n{source}:")
            print(f"  Total rows: {len(source_df)}")
            print(f"  Date range: {source_df['date'].min()} to {source_df['date'].max()}")
            
            # Check for header rows (they typically have 0 amounts)
            zero_rows = source_df[(source_df['actual_amount'] == 0) & 
                                 (source_df['allowed_amount'] == 0)]
            if len(zero_rows) > 0:
                print(f"  ⚠️  Zero-amount rows: {len(zero_rows)}")
                
    def check_specific_examples(self):
        """Manually verify a few specific transactions"""
        self.print_section("SPECIFIC TRANSACTION VERIFICATION")
        
        print("\nLet's manually verify some transactions:")
        
        # Find a standard expense split 50/50
        standard_expense = self.audit_df[
            (self.audit_df['transaction_type'] == 'standard') & 
            (self.audit_df['actual_amount'] > 0) &
            (self.audit_df['person'] == 'Ryan')
        ].head(1)
        
        if not standard_expense.empty:
            row = standard_expense.iloc[0]
            print("\n1. Standard Expense Example:")
            print(f"   Description: {row['full_description']}")
            print(f"   Ryan paid: ${row['actual_amount']:.2f}")
            print(f"   Ryan's share: ${row['allowed_amount']:.2f}")
            print(f"   Net effect: ${row['net_effect']:.2f}")
            print(f"   ✓ Check: {row['allowed_amount']:.2f} - {row['actual_amount']:.2f} = {row['net_effect']:.2f}")
            
    def generate_summary_report(self):
        """Generate a summary of all findings"""
        self.print_section("VERIFICATION SUMMARY REPORT")
        
        print(f"\nTotal Issues Found: {len(self.issues)}")
        
        if self.issues:
            print("\nIssues requiring attention:")
            for i, issue in enumerate(self.issues, 1):
                print(f"  {i}. {issue}")
        else:
            print("\n✓ No major issues found!")
            
        print("\n\nRecommended Actions:")
        print("1. Filter out header rows (non-Ryan/Jordyn entries)")
        print("2. Remove duplicate transactions")
        print("3. Verify Transaction_Ledger allocation logic")
        print("4. Rerun calculations after data cleaning")
        
    def run_full_verification(self):
        """Run all verification checks"""
        print("\nBALANCE VERIFICATION REPORT")
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Analyzing: {len(self.audit_df)} transactions")
        
        # Run all checks
        self.verify_person_column()
        self.verify_duplicates()
        self.verify_balance_calculation()
        self.verify_transaction_types()
        self.verify_source_files()
        self.check_specific_examples()
        self.generate_summary_report()
        
        # Save problematic rows for manual review
        invalid_persons = ~self.audit_df['person'].isin(['Ryan', 'Jordyn'])
        if invalid_persons.any():
            problem_df = self.audit_df[invalid_persons]
            problem_file = "verification_invalid_persons.csv"
            problem_df.to_csv(problem_file, index=False)
            print(f"\n\n⚠️  Saved {len(problem_df)} invalid person rows to: {problem_file}")

if __name__ == "__main__":
    # Find the most recent audit file
    audit_dir = pathlib.Path("audit_reports")
    audit_files = list(audit_dir.glob("complete_audit_trail_*.csv"))
    
    if not audit_files:
        print("No audit files found in audit_reports/")
    else:
        latest_file = max(audit_files, key=lambda x: x.stat().st_mtime)
        print(f"Analyzing: {latest_file}")
        
        verifier = BalanceVerifier(latest_file)
        verifier.run_full_verification()
