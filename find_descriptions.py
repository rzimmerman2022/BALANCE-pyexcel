import pandas as pd
import json

df = pd.read_parquet(r"C:\BALANCE\BALANCE-pyexcel\artifacts\balance_final.parquet")

print("INVESTIGATING POSSIBLE DESCRIPTION LOCATIONS")
print("=" * 60)

# Method 1: Check if Extras column contains the original data
if 'Extras' in df.columns:
    print("\nChecking Extras column for hidden description data...")
    non_empty_extras = df[df['Extras'].notna()].head(5)
    
    for idx, row in non_empty_extras.iterrows():
        try:
            # Try to parse as JSON
            extras_data = json.loads(row['Extras'])
            print(f"\nRow {idx} Extras content:")
            for key, value in extras_data.items():
                if isinstance(value, str) and len(value) > 20:
                    print(f"  {key}: {value[:60]}...")
        except:
            print(f"\nRow {idx} Extras (not JSON): {str(row['Extras'])[:100]}...")
            
# Method 2: Look for any column with transaction-like text
print("\n\nColumns with substantial text data:")
print("-" * 40)

text_columns = {}
for col in df.columns:
    if df[col].dtype == 'object':
        # Calculate average length of non-empty values
        non_empty = df[df[col].notna()][col]
        if len(non_empty) > 0:
            avg_length = non_empty.astype(str).str.len().mean()
            if avg_length > 20:  # Likely to contain descriptions
                text_columns[col] = avg_length

# Sort by average length
for col, avg_len in sorted(text_columns.items(), key=lambda x: x[1], reverse=True):
    print(f"{col}: avg length = {avg_len:.1f} chars")
    
# Method 3: Check specific columns that might contain the data
possible_desc_columns = ['Merchant', 'Payee', 'Name', 'Transaction', 'Details', 'Memo']
print("\n\nChecking common description column names:")
for col in possible_desc_columns:
    if col in df.columns:
        non_empty = df[col].notna().sum()
        if non_empty > 0:
            print(f"\n{col} column found with {non_empty} values!")
            print("Samples:")
            for i, val in enumerate(df[col].dropna().head(3)):
                print(f"  {i+1}. {val}")
