import pandas as pd

# Read the new parquet file
df = pd.read_parquet('output/cleaned_transactions_fixed.parquet')

# Filter for just Monarch Money transactions
monarch_df = df[df['DataSourceName'].str.contains('Monarch', na=False)]

# Show columns
print("Columns in Monarch transactions:")
print(monarch_df.columns.tolist())

# Show a sample transaction
if len(monarch_df) > 0:
    print("\nSample Monarch transaction:")
    sample = monarch_df.iloc[0]
    print(f"OriginalDescription: {sample.get('OriginalDescription', 'MISSING')}")
    print(f"Description: {sample.get('Description', 'MISSING')}")
    print(f"OriginalMerchant: {sample.get('OriginalMerchant', 'MISSING')}")
    print(f"Merchant: {sample.get('Merchant', 'MISSING')}")