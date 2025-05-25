# Create a detailed tracing script
@"
import pandas as pd
import yaml
import sys
sys.path.insert(0, 'src')

# Read the CSV
print('=== STEP 1: Reading CSV ===')
df = pd.read_csv(r'C:\BALANCE\CSVs\Ryan\Ryan - Monarch Money - 20250524.csv')
print(f'Columns in CSV: {df.columns.tolist()}')
print(f'Original Statement exists: {"Original Statement" in df.columns}')
if 'Original Statement' in df.columns:
    print(f'Sample Original Statement: {df["Original Statement"].iloc[0][:50]}...')

# Load and check schema
print('\n=== STEP 2: Loading Schema ===')
with open('rules/ryan_monarch_v1.yaml', 'r') as f:
    schema = yaml.safe_load(f)
    
column_map = schema.get('column_map', {})
print(f'Column map contains Original Statement: {"Original Statement" in column_map}')
print(f'Original Statement maps to: {column_map.get("Original Statement", "NOT MAPPED")}')

# Try to understand what the pipeline does
print('\n=== STEP 3: Checking Pipeline Behavior ===')
try:
    from balance_pipeline.csv_consolidator import apply_schema_transformations
    print('Successfully imported transformation function')
    
    # Check what happens to our data
    print('\nBefore transformation:')
    print(f'  OriginalDescription in df: {"OriginalDescription" in df.columns}')
    print(f'  Original Statement in df: {"Original Statement" in df.columns}')
    
except Exception as e:
    print(f'Could not import pipeline functions: {e}')
"@ | Set-Content -Path trace_monarch_data.py -Encoding UTF8

python trace_monarch_data.py