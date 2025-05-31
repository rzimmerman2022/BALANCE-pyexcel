# diagnostic_dates.py
import pandas as pd
from pathlib import Path
import yaml

def diagnose_date_formats():
    """
    This script will help us understand why date parsing is failing
    by examining the actual date values in your CSV files
    """
    
    # First, let's look at the raw CSV data before any processing
    csv_files = {
        'Jordyn Chase': Path('../CSVs/Jordyn/Jordyn - Chase Bank - Total Checking x6173 - All.csv'),
        'Ryan Monarch': Path('../CSVs/Ryan/Ryan - Monarch Money - 20250524.csv'),
        'Ryan Rocket': Path('../CSVs/Ryan/Ryan - Rocket Money - 20250524.csv')
    }
    
    print("=== RAW DATE FORMATS IN CSV FILES ===\n")
    
    for name, filepath in csv_files.items():
        if filepath.exists():
            # Read just first 5 rows to see date format
            df = pd.read_csv(filepath, nrows=5)
            
            print(f"\n{name} ({filepath.name}):")
            print(f"Columns: {list(df.columns)}")
            
            # Look for any column that might contain dates
            date_columns = [col for col in df.columns if 'date' in col.lower() or 'trans' in col.lower()]
            
            for col in date_columns:
                print(f"\n  {col} samples:")
                for idx, val in enumerate(df[col].head()):
                    print(f"    Row {idx}: '{val}' (type: {type(val).__name__})")
    
    # Now let's check what the schemas are expecting
    print("\n\n=== SCHEMA DATE FORMAT EXPECTATIONS ===\n")
    
    schema_files = list(Path('rules').glob('*.yaml'))
    for schema_file in schema_files:
        if schema_file.name == 'schema_registry.yml':
            continue
            
        try:
            with open(schema_file, 'r') as f:
                schema = yaml.safe_load(f)
                
            if schema and isinstance(schema, dict) and 'id' in schema:
                print(f"\nSchema: {schema['id']}")
                print(f"  Date format specified: {schema.get('date_format', 'NOT SPECIFIED')}")
                
                # Check column mappings for date columns
                column_map = schema.get('column_map', {})
                date_mappings = {k: v for k, v in column_map.items() 
                               if 'Date' in v or 'date' in k.lower()}
                if date_mappings:
                    print(f"  Date column mappings: {date_mappings}")
                    
        except Exception as e:
            print(f"  Error reading {schema_file.name}: {e}")

if __name__ == "__main__":
    diagnose_date_formats()