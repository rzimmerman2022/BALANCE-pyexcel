import pandas as pd
import json

df = pd.read_parquet(r"C:\BALANCE\BALANCE-pyexcel\artifacts\balance_final.parquet")

print("PIPELINE PROCESSING CLUES")
print("=" * 60)

# Check if there's an Extras column with processing metadata
if 'Extras' in df.columns:
    extras_non_null = df['Extras'].notna().sum()
    print(f"\nExtras column has {extras_non_null} non-null values")
    
    if extras_non_null > 0:
        # Sample some Extras to see what's in there
        print("\nChecking first few Extras entries:")
        for i, (idx, val) in enumerate(df[df['Extras'].notna()].head(3).iterrows()):
            print(f"\n  Row {idx}:")
            try:
                extras_dict = json.loads(val['Extras'])
                print(f"    Contains keys: {list(extras_dict.keys())}")
                # Show any interesting values
                for k, v in extras_dict.items():
                    if isinstance(v, str) and len(str(v)) > 10:
                        print(f"    {k}: {str(v)[:50]}...")
            except:
                print(f"    Raw value: {str(val['Extras'])[:100]}...")

# Check column patterns by data source
print("\n\nCOLUMN AVAILABILITY BY DATA SOURCE:")
print("-" * 50)

important_cols = ['Original Statement', 'Description', 'Merchant', 'Name', 'Account', 'Amount']

for source in df['DataSourceName'].unique():
    print(f"\n{source}:")
    source_df = df[df['DataSourceName'] == source]
    for col in important_cols:
        if col in df.columns:
            non_empty = source_df[col].notna().sum()
            pct = non_empty / len(source_df) * 100
            print(f"  {col}: {non_empty}/{len(source_df)} ({pct:.1f}%)")

# Look for TxnID to see if deduplication happened
if 'TxnID' in df.columns:
    print("\n\nTxnID ANALYSIS:")
    print(f"TxnID column exists: {'TxnID' in df.columns}")
    if 'TxnID' in df.columns:
        txn_non_null = df['TxnID'].notna().sum()
        print(f"Non-null TxnIDs: {txn_non_null}/{len(df)}")
else:
    print("\n\nNO TxnID column found - this suggests incomplete processing")
