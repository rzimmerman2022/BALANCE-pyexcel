# trace_data_flow.py
import pandas as pd
from pathlib import Path
import logging

# Set up detailed logging
logging.basicConfig(level=logging.DEBUG, format='%(message)s')

def trace_single_file_processing(csv_path):
    """
    This traces the data transformation for a single file
    to see exactly where things go wrong
    """
    print(f"\n=== TRACING: {csv_path} ===\n")
    
    # Step 1: Raw CSV
    df_raw = pd.read_csv(csv_path, nrows=5)
    print("1. RAW CSV DATA:")
    print(f"   Columns: {list(df_raw.columns)}")
    print(f"   First row data:")
    for col in df_raw.columns[:5]:  # Just first 5 columns
        print(f"     {col}: '{df_raw[col].iloc[0]}'")
    
    # Step 2: Check what schema would be matched
    from balance_pipeline.schema_registry import find_matching_schema
    
    match_result = find_matching_schema(list(df_raw.columns))
    if match_result:
        print(f"\n2. MATCHED SCHEMA: {match_result.schema.name}")
        print(f"   Rules: {match_result.rules.get('id', 'unknown')}")
    
    # Step 3: Check the column mappings
    if match_result and match_result.rules:
        column_map = match_result.rules.get('column_map', {})
        print(f"\n3. COLUMN MAPPINGS:")
        for source, target in column_map.items():
            if source in df_raw.columns:
                print(f"   '{source}' -> '{target}'")
                print(f"   Sample value: '{df_raw[source].iloc[0]}'")
    
    return match_result

# Test with one file from each source
test_files = [
    '../CSVs/Ryan/Ryan - Monarch Money - 20250524.csv',
    '../CSVs/Jordyn/Jordyn - Chase Bank - Total Checking x6173 - All.csv'
]

for filepath in test_files:
    if Path(filepath).exists():
        trace_single_file_processing(filepath)