import pandas as pd

# Read the parquet file
df = pd.read_parquet('workbook/balance_final.parquet')

# Show basic information
print("=== Balance Final Parquet Analysis ===")
print(f"\nTotal rows: {len(df)}")

# Show breakdown by data source
print("\nRows by Data Source:")
source_counts = df['DataSourceName'].value_counts()
for source, count in source_counts.items():
    print(f"  {source}: {count} rows")

# Show date range
print(f"\nDate range: {df['Date'].min()} to {df['Date'].max()}")

# Check for GenericCSV entries
generic_count = len(df[df['DataSourceName'] == 'GenericCSV'])
if generic_count > 0:
    print(f"\nWarning: Found {generic_count} GenericCSV entries (PDF extractions)")
else:
    print("\nGood: No GenericCSV entries found (no PDF extractions)")