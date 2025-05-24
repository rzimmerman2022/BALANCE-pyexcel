import pandas as pd

# Load the parquet file
df = pd.read_parquet("output/balance_final.parquet")

# Check each column for null percentage
print("Column Analysis - Null Percentages:")
print("="*50)

null_counts = df.isnull().sum()
null_percentages = (null_counts / len(df) * 100).round(2)

for col in df.columns:
    null_pct = null_percentages[col]
    if null_pct > 90:
        print(f"❌ {col}: {null_pct}% null (PHANTOM COLUMN?)")
    elif null_pct > 50:
        print(f"⚠️  {col}: {null_pct}% null")
    else:
        print(f"✓  {col}: {null_pct}% null")

# Group by source to see which columns are populated per source
print("\n\nPer-Source Column Population:")
print("="*50)

if 'DataSourceName' in df.columns:
    for source in df['DataSourceName'].unique():
        source_df = df[df['DataSourceName'] == source]
        print(f"\n{source} ({len(source_df)} rows):")
        source_nulls = (source_df.isnull().sum() / len(source_df) * 100).round(2)
        populated_cols = [col for col in df.columns if source_nulls[col] < 50]
        print(f"  Populated columns: {', '.join(populated_cols[:10])}...")
        if len(populated_cols) > 10:
            print(f"  ... and {len(populated_cols) - 10} more") 