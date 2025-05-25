import pandas as pd
from pathlib import Path

# Load the file
df = pd.read_parquet(r"C:\BALANCE\BALANCE-pyexcel\artifacts\balance_final.parquet")

# Check for metadata columns that might tell us about the processing
print("CHECKING FOR PROCESSING METADATA:")
print("=" * 60)

# Look for DataSourceName
if 'DataSourceName' in df.columns:
    print("\nDataSourceName values:")
    print(df['DataSourceName'].value_counts())

# Look for Owner
if 'Owner' in df.columns:
    print("\nOwner values:")
    print(df['Owner'].value_counts())

# Check date range
if 'Date' in df.columns:
    print(f"\nDate range: {df['Date'].min()} to {df['Date'].max()}")

# Sample a few rows to see what data we have
print("\nSAMPLE DATA (first 3 rows, selected columns):")
display_cols = [col for col in ['Date', 'Amount', 'Merchant', 'Description', 'Account'] if col in df.columns]
if display_cols:
    print(df[display_cols].head(3))
