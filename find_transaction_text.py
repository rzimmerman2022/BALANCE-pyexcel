import pandas as pd
df = pd.read_parquet(r"C:\BALANCE\BALANCE-pyexcel\artifacts\balance_final.parquet")

# Look at all columns and show sample data from any that might contain transaction text
print("SEARCHING FOR TRANSACTION DETAIL COLUMNS:")
print("=" * 60)

for col in df.columns:
    # Check if column has string data with reasonable length
    if df[col].dtype == 'object':
        non_empty = df[col].notna()
        if non_empty.any():
            sample = df.loc[non_empty, col].iloc[0]
            if isinstance(sample, str) and len(sample) > 20:
                print(f"\n{col}:")
                print(f"  Sample: {sample[:100]}...")
                print(f"  Non-empty: {non_empty.sum()}")
