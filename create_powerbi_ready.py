import pandas as pd
from pathlib import Path

# Load the current file
df = pd.read_parquet(r"C:\BALANCE\BALANCE-pyexcel\artifacts\balance_final.parquet")

print("CREATING POWER BI-READY FILE WITH UNIFIED DESCRIPTIONS")
print("=" * 60)

# Create a unified OriginalDescription column
# Prioritize Original Statement, then Description, then Merchant
df['OriginalDescription'] = df['Original Statement'].fillna(df['Description']).fillna(df['Merchant'])

print(f"\nOriginalDescription created:")
print(f"  Total non-empty: {df['OriginalDescription'].notna().sum()}")
print(f"  From Original Statement: {df['Original Statement'].notna().sum()}")
print(f"  From Description: {(df['Original Statement'].isna() & df['Description'].notna()).sum()}")
print(f"  From Merchant: {(df['Original Statement'].isna() & df['Description'].isna() & df['Merchant'].notna()).sum()}")

# Fix the Date column (mixed types issue)
print("\nFixing Date column...")
if 'Date' in df.columns:
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    print(f"  Valid dates after conversion: {df['Date'].notna().sum()}")

# Remove completely empty columns for Power BI
empty_cols = []
for col in df.columns:
    if df[col].isna().all() or (df[col] == '').all():
        empty_cols.append(col)

print(f"\nRemoving {len(empty_cols)} empty columns: {empty_cols}")
df_clean = df.drop(columns=empty_cols)

# Save the cleaned file
output_path = Path(r"C:\BALANCE\BALANCE-pyexcel\artifacts\powerbi_ready.parquet")
df_clean.to_parquet(output_path, index=False)

print(f"\nSaved Power BI-ready file to: {output_path}")
print(f"Final shape: {df_clean.shape}")
print(f"OriginalDescription has {df_clean['OriginalDescription'].notna().sum()} values for reconciliation")

# Show sample of the new OriginalDescription column
print("\nSample OriginalDescription values:")
for i, val in enumerate(df_clean['OriginalDescription'].dropna().head(5)):
    print(f"  {i+1}. {val[:100]}...")
