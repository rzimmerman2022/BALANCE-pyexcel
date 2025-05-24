# inspect_parquet_columns.py
"""
Reveals exactly what columns exist in your Parquet file and what Power BI sees.
This will help us understand why you're seeing more than 27 columns.
"""

import pandas as pd
import pyarrow.parquet as pq
import json

def inspect_parquet_structure(parquet_file='workbook/balance_final.parquet'):
    """
    Deep inspection of Parquet file structure to understand what Power BI sees
    """
    print("=== PARQUET FILE COLUMN INSPECTION ===\n")
    
    # Method 1: Load with pandas and check
    print("1. PANDAS PERSPECTIVE (Basic Load):")
    df = pd.read_parquet(parquet_file)
    print(f"   Total columns seen by pandas: {len(df.columns)}")
    print(f"   Total rows: {len(df)}")
    
    # List all columns
    print("\n2. COMPLETE COLUMN LIST:")
    for i, col in enumerate(df.columns, 1):
        dtype = str(df[col].dtype)
        print(f"   {i:2d}. {col} (type: {dtype})")
    
    # Method 2: Check PyArrow schema (what's actually in the file)
    print("\n3. PARQUET FILE SCHEMA (PyArrow):")
    parquet_file_obj = pq.ParquetFile(parquet_file)
    schema = parquet_file_obj.schema
    print(f"   Schema fields: {len(schema)}")
    
    # Check for nested types that Power BI might expand
    print("\n4. NESTED/COMPLEX COLUMNS:")
    nested_found = False
    
    for field in schema:
        if 'struct' in str(field.type) or 'list' in str(field.type) or 'map' in str(field.type):
            print(f"   ⚠️  {field.name}: {field.type}")
            print(f"      Power BI will likely expand this into multiple columns!")
            nested_found = True
    
    # Check the Extras column specifically
    if 'Extras' in df.columns:
        print("\n5. EXTRAS COLUMN ANALYSIS:")
        print(f"   Data type: {df['Extras'].dtype}")
        
        # Sample some Extras values to see what's in them
        non_empty_extras = df[df['Extras'].notna() & (df['Extras'] != '{}')]
        
        if len(non_empty_extras) > 0:
            print(f"   Found {len(non_empty_extras)} rows with non-empty Extras")
            print("   Sample Extras contents:")
            
            # Collect all unique keys across all Extras
            all_keys = set()
            for idx, value in non_empty_extras['Extras'].head(10).items():
                try:
                    if isinstance(value, str):
                        extras_dict = json.loads(value) if value.startswith('{') else {}
                    elif isinstance(value, dict):
                        extras_dict = value
                    else:
                        continue
                    
                    all_keys.update(extras_dict.keys())
                    print(f"      Row {idx}: {list(extras_dict.keys())}")
                except:
                    print(f"      Row {idx}: Could not parse - {type(value)}")
            
            if all_keys:
                print(f"\n   All unique keys found in Extras: {sorted(all_keys)}")
                print(f"   ⚠️  Power BI will create {len(all_keys)} additional columns from Extras!")
        else:
            print("   All Extras values are empty or {}")
    
    # Check for columns that might be all null/empty
    print("\n6. EMPTY/PLACEHOLDER COLUMNS:")
    empty_columns = []
    placeholder_columns = []
    
    for col in df.columns:
        if df[col].isna().all():
            empty_columns.append(col)
        elif df[col].dtype == 'object':
            # Check for columns that are all '<NA>', 'nan', 'None', etc
            unique_values = df[col].dropna().unique()
            if len(unique_values) == 1 and str(unique_values[0]).upper() in ['<NA>', 'NAN', 'NONE', '']:
                placeholder_columns.append(col)
    
    if empty_columns:
        print(f"   Found {len(empty_columns)} completely empty columns:")
        for col in empty_columns:
            print(f"      - {col}")
    
    if placeholder_columns:
        print(f"   Found {len(placeholder_columns)} columns with only placeholder values:")
        for col in placeholder_columns:
            print(f"      - {col}")
    
    # Method 3: Check what Power BI specific issues might exist
    print("\n7. POWER BI SPECIFIC CONCERNS:")
    
    # Check for duplicate column names (case variations)
    lowercase_cols = [col.lower() for col in df.columns]
    if len(lowercase_cols) != len(set(lowercase_cols)):
        print("   ⚠️  Found columns that differ only in case!")
        print("      Power BI might merge or rename these")
    
    # Check for columns with special characters
    special_char_cols = [col for col in df.columns if any(c in col for c in ['/', '\\', '[', ']', '(', ')'])]
    if special_char_cols:
        print(f"   ⚠️  Found {len(special_char_cols)} columns with special characters:")
        for col in special_char_cols:
            print(f"      - {col}")
    
    # Final summary
    print("\n8. SUMMARY:")
    expected_columns = 27
    actual_columns = len(df.columns)
    
    if actual_columns > expected_columns:
        print(f"   ❌ Expected {expected_columns} columns but found {actual_columns}")
        print(f"      Extra columns: {actual_columns - expected_columns}")
    elif actual_columns < expected_columns:
        print(f"   ❌ Expected {expected_columns} columns but only found {actual_columns}")
        print(f"      Missing columns: {expected_columns - actual_columns}")
    else:
        print(f"   ✓ Found exactly {expected_columns} columns as expected")
    
    # If we found nested data that Power BI will expand
    if nested_found or (all_keys if 'all_keys' in locals() else False):
        estimated_total = actual_columns
        if 'all_keys' in locals() and all_keys:
            estimated_total += len(all_keys) - 1  # -1 because Extras column gets replaced
        
        print(f"\n   ⚠️  Power BI will likely show ~{estimated_total} columns after expansion")
    
    return df

if __name__ == "__main__":
    df = inspect_parquet_structure()