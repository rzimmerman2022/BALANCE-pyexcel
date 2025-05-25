import pandas as pd
from pathlib import Path

df = pd.read_parquet(r"C:\BALANCE\BALANCE-pyexcel\artifacts\balance_final.parquet")

print("INVESTIGATING PIPELINE PROCESSING INDICATORS")
print("=" * 60)

# Check 1: Look for columns that should have been created by the pipeline
expected_pipeline_columns = [
    'TxnID',           # Should always be created
    'CleanDesc',       # Cleaned description
    'CanonMerchant',   # Canonical merchant name
    'SharedFlag',      # Should be initialized to '?'
    'SplitPercent'     # Should be initialized to NA
]

print("\nCHECKING FOR EXPECTED PIPELINE-GENERATED COLUMNS:")
for col in expected_pipeline_columns:
    exists = col in df.columns
    status = "✓ Found" if exists else "✗ Missing"
    print(f"  {col}: {status}")

# Check 2: Look for evidence of date standardization
print("\n\nDATE COLUMN STANDARDIZATION CHECK:")
date_columns = [col for col in df.columns if 'date' in col.lower()]
print(f"Found {len(date_columns)} date-related columns:")
for col in date_columns:
    non_null = df[col].notna().sum()
    dtype = df[col].dtype
    print(f"  {col}: {non_null} values, dtype={dtype}")

# Check 3: Amount column - should be numeric after processing
print("\n\nAMOUNT COLUMN CHECK:")
if 'Amount' in df.columns:
    print(f"  Amount dtype: {df['Amount'].dtype}")
    non_numeric = df['Amount'].apply(lambda x: isinstance(x, str) if pd.notna(x) else False).sum()
    print(f"  String values in Amount: {non_numeric}")
    if non_numeric > 0:
        print("  Sample string amounts:")
        string_amounts = df[df['Amount'].apply(lambda x: isinstance(x, str) if pd.notna(x) else False)]
        for val in string_amounts['Amount'].head(5):
            print(f"    '{val}'")

# Check 4: Look for evidence of schema transformation
print("\n\nSCHEMA TRANSFORMATION EVIDENCE:")
print("Column name patterns by source:")

for source in df['DataSourceName'].unique():
    source_df = df[df['DataSourceName'] == source]
    # Get first non-null row to see column patterns
    first_row = source_df.dropna(axis=1, how='all').iloc[0] if not source_df.empty else None
    if first_row is not None:
        populated_cols = [col for col in source_df.columns if pd.notna(first_row[col])]
        print(f"\n  {source} uses these columns:")
        for col in populated_cols[:10]:  # Show first 10
            print(f"    - {col}")

# Check 5: Look at the actual values to see if any cleaning happened
print("\n\nMERCHANT CLEANING EVIDENCE:")
if 'Merchant' in df.columns:
    merchant_samples = df['Merchant'].dropna().head(10)
    print("Sample merchant values (looking for standardization):")
    for i, merchant in enumerate(merchant_samples):
        print(f"  {i+1}. '{merchant}'")
        # Check if it looks cleaned (title case, no extra spaces, etc.)
        is_cleaned = merchant == merchant.strip() and merchant == merchant.title()
        print(f"      Appears cleaned: {is_cleaned}")
