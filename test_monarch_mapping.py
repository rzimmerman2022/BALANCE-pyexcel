import pandas as pd
import yaml

# Read the Monarch CSV
df = pd.read_csv(r'C:\BALANCE\CSVs\Ryan\Ryan - Monarch Money - 20250524.csv')
print('CSV Columns:', df.columns.tolist())
print('\nFirst row of Original Statement:', df['Original Statement'].iloc[0] if 'Original Statement' in df.columns else 'COLUMN NOT FOUND')

# Load the schema
with open('rules/ryan_monarch_v1.yaml', 'r') as f:
    schema = yaml.safe_load(f)

print('\nSchema column_map:', schema.get('column_map', {}))

# Check if the mapping exists and would work
if 'Original Statement' in df.columns:
    print('\nOriginal Statement column exists in CSV')
    print('First 3 values:')
    for i in range(min(3, len(df))):
        print(f'  Row {i}: {df["Original Statement"].iloc[i]}')
