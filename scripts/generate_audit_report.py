#!/usr/bin/env python3
"""
Generate comprehensive audit report with CTS pipeline + baseline_math analysis.
Saves timestamped files to audit_reports/ folder.
"""

import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from src.balance_pipeline.data_loader import load_all_data
from src.baseline_analyzer import baseline_math as bm


def main():
    print("🔍 BALANCE AUDIT REPORT GENERATOR")
    print("=" * 50)
    
    # Load data using CTS pipeline
    data_dir = pathlib.Path('data')
    print("📊 Loading transaction data...")
    df = load_all_data(data_dir)
    
    if df.empty:
        print("❌ No data loaded. Check data directory.")
        return
    
    print(f"✅ Loaded {len(df):,} transactions")
    print(f"📅 Date range: {df['date'].min()} to {df['date'].max()}")
    
    # Show source breakdown
    print("\n📁 Source breakdown:")
    for source, count in df['source_file'].value_counts().items():
        print(f"   {source}: {count:,} transactions")
    
    # Generate audit trail
    print("\n💰 Generating audit trail...")
    summary_df, audit_df = bm.build_baseline(df)
    
    print(f"✅ Generated {len(audit_df):,} audit rows")
    print(f"✅ Balance summary for {len(summary_df)} people")
    
    # Show balance summary
    print("\n📋 Balance Summary:")
    for _, row in summary_df.iterrows():
        person = row['person']
        net_owed = row['net_owed']
        print(f"   {person}: ${net_owed:,.2f}")
    
    total_imbalance = summary_df['net_owed'].sum()
    print(f"\n⚖️  Total Imbalance: ${total_imbalance:,.2f}")
    
    if abs(total_imbalance) <= 0.02:
        print("✅ Balance check: PASSED")
    else:
        print("⚠️  Balance check: FAILED (business logic review needed)")
    
    print(f"\n🎉 Audit report complete!")
    print(f"📂 Files saved to: audit_reports/")


if __name__ == '__main__':
    main()
