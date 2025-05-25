# check_schema_matching.py
# This script checks which schemas your CSV files are matching to

import pandas as pd
from pathlib import Path
import sys
import yaml

# Add the project to Python path
sys.path.insert(0, 'src')

from balance_pipeline.schema_registry import SchemaRegistry
from balance_pipeline.config import Config

print("Checking schema matching for your CSV files...")
print("=" * 80)

# Initialize the schema registry
config = Config()
registry = SchemaRegistry(config.SCHEMA_REGISTRY_PATH)

# Find all CSV files in your CSVs directory
csv_dir = Path(r"C:\BALANCE\CSVs")
csv_files = list(csv_dir.rglob("*.csv"))

print(f"\nFound {len(csv_files)} CSV files")
print("-" * 80)

# Check each file
for csv_file in csv_files:
    print(f"\nFile: {csv_file.name}")
    print(f"Path: {csv_file}")
    
    try:
        # Read the first few rows to get headers
        df = pd.read_csv(csv_file, nrows=5)
        headers = list(df.columns)
        
        print(f"Headers: {headers[:5]}{'...' if len(headers) > 5 else ''}")
        
        # Try to match the schema
        match_result = registry.match_schema(headers)
        
        if match_result:
            schema_name = match_result['name']
            confidence = match_result.get('confidence', 'N/A')
            print(f"✓ Matched Schema: {schema_name} (confidence: {confidence})")
            
            # Check if this is generic_csv
            if schema_name == "generic_csv":
                print("  ⚠️  WARNING: This is matching to generic_csv!")
                print("     Generic CSV files might bypass comprehensive cleaning")
                
            # Check what transformations this schema applies
            schema_obj = registry.get_schema(schema_name)
            if schema_obj and hasattr(schema_obj, 'transformations'):
                trans = schema_obj.transformations
                if trans and 'Merchant' in trans:
                    merchant_mapping = trans['Merchant']
                    print(f"  Schema maps Merchant from: {merchant_mapping}")
                    if merchant_mapping == 'Description':
                        print("  🚨 PROBLEM: Schema is mapping Merchant = Description!")
        else:
            print("✗ No schema match found!")
            print("  This file might be skipped or use fallback processing")
            
    except Exception as e:
        print(f"✗ Error reading file: {e}")

# Let's also check the schema registry to understand generic_csv
print("\n" + "=" * 80)
print("UNDERSTANDING GENERIC_CSV SCHEMA:")
print("-" * 80)

try:
    generic_schema = registry.get_schema("generic_csv")
    if generic_schema:
        print("Generic CSV schema exists")
        if hasattr(generic_schema, 'transformations'):
            print("Transformations:", generic_schema.transformations)
        if hasattr(generic_schema, 'description'):
            print("Description:", generic_schema.description)
    else:
        print("No generic_csv schema found")
except Exception as e:
    print(f"Error checking generic_csv: {e}")

# Check for schema_mode setting
print("\n" + "=" * 80)
print("CONFIGURATION SETTINGS:")
print("-" * 80)
print(f"Schema Mode: {config.SCHEMA_MODE}")
print(f"This affects how strictly schemas are matched and applied")

if config.SCHEMA_MODE == "flexible":
    print("✓ Flexible mode allows partial matches and should process most files")
elif config.SCHEMA_MODE == "strict":
    print("⚠️  Strict mode might skip files that don't match schemas perfectly")