import pandas as pd
import pathlib

# Find latest audit file
audit_dir = pathlib.Path("audit_reports")
latest = max(audit_dir.glob("complete_audit_trail_*.csv"), key=lambda x: x.stat().st_mtime)

# Load and analyze
df = pd.read_csv(latest)
print(f"\nAnalyzing: {latest.name}")
print(f"Total rows: {len(df)}")

# Quick checks
print("\n=== QUICK SUMMARY ===")
print(f"\nUnique persons: {df['person'].nunique()}")
print("Person values:", df['person'].unique()[:5], "..." if df['person'].nunique() > 5 else "")

# Balance check
ryan_total = df[df['person'] == 'Ryan']['net_effect'].sum()
jordyn_total = df[df['person'] == 'Jordyn']['net_effect'].sum()
print(f"\nRyan net total: ${ryan_total:,.2f}")
print(f"Jordyn net total: ${jordyn_total:,.2f}")
print(f"System balance: ${ryan_total + jordyn_total:,.2f}")

# Duplicate check
dup_cols = ['date', 'person', 'merchant', 'actual_amount', 'allowed_amount']
duplicates = df[df.duplicated(subset=dup_cols, keep=False)]
print(f"\nDuplicate rows: {len(duplicates)}")

# Problem rows
invalid = df[~df['person'].isin(['Ryan', 'Jordyn'])]
print(f"Invalid person rows: {len(invalid)}")
