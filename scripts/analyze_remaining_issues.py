#!/usr/bin/env python3
"""
Analyzes the comprehensive audit trail to identify any remaining inconsistent rows
and document edge cases or unusual transactions for future system improvement.
"""

import pathlib
from datetime import datetime

import pandas as pd


def analyze_issues():
    """Main function to run the issue analysis."""
    print("─" * 80)
    print("🔎 Phase 3: Identifying Remaining Issues & Edge Cases...")
    print("─" * 80)

    # 1. Load the audit trail
    timestamp = datetime.now().strftime("%Y-%m-%d")
    audit_file = pathlib.Path(f"artifacts/complete_audit_trail_{timestamp}.csv")

    if not audit_file.exists():
        print(f"❌ ERROR: Audit file not found at '{audit_file}'")
        # Fallback to a non-timestamped name if today's file isn't found
        audit_file = pathlib.Path("artifacts/enhanced_audit_trail.csv")
        if not audit_file.exists():
            print(f"❌ ERROR: Fallback audit file not found at '{audit_file}' either. Aborting.")
            return

    print(f"1. Loading audit trail from '{audit_file}'...")
    try:
        df = pd.read_csv(audit_file)
        print("✅ Audit trail loaded successfully.")
    except Exception as e:
        print(f"❌ Failed to load or parse CSV: {e}")
        return

    # 2. Pattern Analysis for Inconsistent Rows
    print("\n2. Analyzing for inconsistent rows...")
    inconsistent_rows = df[df['integrity_check'] == False]

    if inconsistent_rows.empty:
        print("✅ SUCCESS: No inconsistent rows found. All transactions are balanced.")
    else:
        print(f"🚨 FOUND {len(inconsistent_rows)} INCONSISTENT ROWS:")
        
        # Create frequency table
        print("\n   Frequency of inconsistent transactions by merchant:")
        freq_table = inconsistent_rows['merchant'].value_counts().reset_index()
        freq_table.columns = ['merchant', 'count']
        print(freq_table.to_markdown(index=False))

        print("\n   Full details of inconsistent rows:")
        print(inconsistent_rows.to_markdown(index=False))

    # 3. Edge Case Documentation
    print("\n3. Documenting edge cases and special handling...")
    
    # Identify edge cases by transaction type and calculation notes
    # Exclude standard 50/50 splits and pre-calculated rent
    edge_cases = df[
        ~df['calculation_notes'].str.contains("Standard 50/50", na=False) &
        ~df['calculation_notes'].str.contains("Rent: Pre-calculated", na=False)
    ]

    if edge_cases.empty:
        print("✅ No specific edge cases found beyond standard splits and rent.")
    else:
        print(f"✅ Found {len(edge_cases)} transactions with special handling rules:")
        
        # Provide a summary of the rules applied
        edge_case_summary = edge_cases.groupby('calculation_notes').agg(
            count=('transaction_id', 'size'),
            total_amount=('actual_amount', 'sum')
        ).reset_index()
        
        print("\n   Summary of special handling rules:")
        print(edge_case_summary.to_markdown(index=False))

        print("\n   Examples of each edge case:")
        for note, group in edge_cases.groupby('calculation_notes'):
            print(f"\n   - Rule: '{note}'")
            print(group[['person', 'merchant', 'actual_amount', 'allowed_amount', 'net_effect']].head(3).to_string())

    print("\n" + "─" * 80)
    print("🎉 Phase 3 Complete: Issue analysis finished.")
    print("─" * 80)


if __name__ == "__main__":
    analyze_issues()
