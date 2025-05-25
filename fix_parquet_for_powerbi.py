import pandas as pd
import numpy as np
from pathlib import Path

# Find your parquet file
parquet_files = list(Path(".").glob("*.parquet"))
if not parquet_files:
    print("No parquet files found!")
    exit()

latest_parquet = max(parquet_files, key=lambda p: p.stat().st_mtime)
print(f"Analyzing: {latest_parquet.name}")
print("=" * 60)

# Read the parquet file
df = pd.read_parquet(latest_parquet)

# Identify problematic columns
print("\nPOTENTIAL PROBLEM COLUMNS:")
problems_found = False

for col in df.columns:
    issues = []
    
    # Check if column is entirely null/empty
    if df[col].isna().all() or (df[col] == '').all():
        issues.append("All values are empty/null")
        problems_found = True
    
    # Check for mixed types
    if df[col].notna().any():
        unique_types = df[col].dropna().apply(type).unique()
        if len(unique_types) > 1:
            issues.append(f"Mixed types: {[t.__name__ for t in unique_types]}")
            problems_found = True
    
    # Check for object dtype with all empty strings
    if df[col].dtype == 'object' and (df[col] == '').all():
        issues.append("All empty strings (ambiguous type)")
        problems_found = True
    
    if issues:
        print(f"\n{col}:")
        for issue in issues:
            print(f"  - {issue}")

if not problems_found:
    print("No obvious problems found!")

# Create a Power BI-friendly version
print("\n" + "=" * 60)
print("Creating Power BI-friendly version...")

# Make a copy for cleaning
df_powerbi = df.copy()

# Fix problematic columns
for col in df_powerbi.columns:
    # Replace all-empty-string columns with proper nulls
    if (df_powerbi[col] == '').all():
        df_powerbi[col] = pd.NA
    
    # Ensure date columns are properly typed
    if 'date' in col.lower() and df_powerbi[col].dtype == 'object':
        try:
            df_powerbi[col] = pd.to_datetime(df_powerbi[col], errors='coerce')
        except:
            pass
    
    # Ensure numeric columns are properly typed
    if col in ['Amount', 'SplitPercent'] and df_powerbi[col].dtype == 'object':
        df_powerbi[col] = pd.to_numeric(df_powerbi[col], errors='coerce')
    
    # Convert boolean columns
    if col in ['SharedFlag', 'TaxDeductible']:
        if df_powerbi[col].dtype == 'object':
            df_powerbi[col] = df_powerbi[col].map({'True': True, 'False': False, '': None})

# Drop the Extras column if it exists (JSON not directly supported in Power BI)
if 'Extras' in df_powerbi.columns:
    print("Removing 'Extras' column (contains JSON data)")
    df_powerbi = df_powerbi.drop(columns=['Extras'])

# Save the cleaned version
output_name = "powerbi_ready.parquet"
df_powerbi.to_parquet(output_name, index=False, engine='pyarrow')

print(f"\nCreated cleaned file: {output_name}")
print(f"Rows: {len(df_powerbi):,}")
print(f"Columns: {len(df_powerbi.columns)}")

# Verify OriginalDescription is preserved
if 'OriginalDescription' in df_powerbi.columns:
    print(f"\n✓ OriginalDescription preserved!")
    print(f"  Non-empty values: {df_powerbi['OriginalDescription'].notna().sum():,}")
else:
    print(f"\n✗ WARNING: OriginalDescription not found!")
