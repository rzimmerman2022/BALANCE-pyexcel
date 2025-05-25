import pandas as pd

# Load the parquet file
df = pd.read_parquet(r"C:\BALANCE\BALANCE-pyexcel\artifacts\balance_final.parquet")

print("INVESTIGATING DESCRIPTION vs MERCHANT RELATIONSHIP")
print("=" * 60)

# First, let's see how many rows have both Description and Merchant
both_present = df['Description'].notna() & df['Merchant'].notna()
print(f"\nRows with both Description and Merchant: {both_present.sum()}")

# Check if they're actually identical
if both_present.any():
    df_both = df[both_present]
    identical = (df_both['Description'] == df_both['Merchant']).sum()
    print(f"Rows where Description equals Merchant: {identical}")
    print(f"Rows where they differ: {both_present.sum() - identical}")
    
    # Show some examples where they differ (if any)
    if identical < both_present.sum():
        print("\nExamples where Description and Merchant differ:")
        diff_rows = df_both[df_both['Description'] != df_both['Merchant']].head(5)
        for idx, row in diff_rows.iterrows():
            print(f"\n  Row {idx}:")
            print(f"    Description: {row['Description'][:60]}...")
            print(f"    Merchant: {row['Merchant'][:60]}...")

# Now let's check Original Statement vs Description
print("\n\nORIGINAL STATEMENT vs DESCRIPTION ANALYSIS:")
print("-" * 50)

# How many rows have Original Statement?
orig_present = df['Original Statement'].notna()
desc_present = df['Description'].notna()

print(f"Rows with Original Statement: {orig_present.sum()}")
print(f"Rows with Description: {desc_present.sum()}")

# For rows that have both, let's see the relationship
both_orig_desc = orig_present & desc_present
if both_orig_desc.any():
    print(f"\nRows with both Original Statement and Description: {both_orig_desc.sum()}")
    
    # Show some examples
    print("\nSample comparisons:")
    sample_both = df[both_orig_desc].head(3)
    for idx, row in sample_both.iterrows():
        print(f"\n  Row {idx}:")
        print(f"    Original: {row['Original Statement'][:80]}...")
        print(f"    Descript: {row['Description'][:80]}...")
        
# Check data sources
print("\n\nDATA SOURCE ANALYSIS:")
print("-" * 50)
print("\nWhich sources have Original Statement?")
for source in df['DataSourceName'].unique():
    source_df = df[df['DataSourceName'] == source]
    has_orig = source_df['Original Statement'].notna().sum()
    total = len(source_df)
    print(f"  {source}: {has_orig}/{total} rows ({has_orig/total*100:.1f}%)")

print("\nWhich sources have Description?")
for source in df['DataSourceName'].unique():
    source_df = df[df['DataSourceName'] == source]
    has_desc = source_df['Description'].notna().sum()
    total = len(source_df)
    print(f"  {source}: {has_desc}/{total} rows ({has_desc/total*100:.1f}%)")
