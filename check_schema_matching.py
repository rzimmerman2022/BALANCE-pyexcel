# check_schema_matching.py
# This script checks which schemas your CSV files are matching to

import pandas as pd
from pathlib import Path
import sys
import yaml

# Add the project to Python path
sys.path.insert(0, 'src')

from balance_pipeline.schema_registry import find_matching_schema
# We might need access to the loaded schemas map or a getter if we need to "get_schema" later
# For now, let's assume find_matching_schema gives us enough.
# If direct access to _SCHEMAS_RULES_MAP or _GENERIC_SCHEMA_RULES is needed,
# schema_registry.py might need to expose them or provide getters.
# For now, we'll work with what find_matching_schema returns.
from balance_pipeline import config as app_config # Import the config module

print("Checking schema matching for your CSV files...")
print("=" * 80)

# Config variables are now accessed via app_config.VARIABLE_NAME

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
        
        # Try to match the schema using the imported function
        # find_matching_schema returns a MatchResult object or None
        match_info = find_matching_schema(headers) # Pass only headers as per new function signature
        
        if match_info and hasattr(match_info, 'rules') and match_info.rules:
            # The schema details are in match_info.rules (a dictionary)
            # The schema ID (name) is in match_info.rules['id']
            schema_name = match_info.rules.get('id', 'Unknown Schema ID')
            # Confidence is not directly available in the new MatchResult structure in the same way,
            # but we can infer a strong match if it's not generic.
            # The score attribute in MatchResult could be used: match_info.score
            confidence_score = match_info.score if hasattr(match_info, 'score') else "N/A"
            print(f"✓ Matched Schema: {schema_name} (score: {confidence_score})")
            
            # Check if this is generic_csv
            if schema_name == "generic_csv":
                print("  ⚠️  WARNING: This is matching to generic_csv!")
                print("     Generic CSV files might bypass comprehensive cleaning")
                
            # Check what transformations this schema applies
            # The schema rules are directly in match_info.rules
            schema_rules = match_info.rules
            if schema_rules: # Redundant check if we are inside the main if, but good practice
                # 'transformations' might not exist; 'column_map' is more standard from schema_registry.yml
                column_map = schema_rules.get('column_map', {})
                if 'Merchant' in column_map: # Check if 'Merchant' is a TARGET in column_map
                    # This logic was checking if 'Merchant' was a source.
                    # The original intent was likely to see how 'OriginalMerchant' or similar is derived.
                    # Let's check if 'OriginalMerchant' is mapped from 'Description'
                    # Or if 'Merchant' (as a canonical field) is mapped from 'Description'
                    merchant_source_column = None
                    for target_col, source_col in column_map.items():
                        if target_col == 'OriginalMerchant' or target_col == 'Merchant': # Check both common canonical names
                            merchant_source_column = source_col
                            break
                    
                    if merchant_source_column:
                        print(f"  Schema maps canonical Merchant field from: {merchant_source_column}")
                        if merchant_source_column == 'Description':
                             print("  🚨 PROBLEM: Schema is mapping Merchant from Description!")
                    elif 'Merchant' in headers and 'Merchant' not in column_map.values():
                        # If 'Merchant' exists in CSV but is not mapped from anywhere
                        print(f"  Schema has 'Merchant' in its column_map targetting {column_map.get('Merchant')}")


        else:
            print("✗ No schema match found!")
            print("  This file might be skipped or use fallback processing")
            
    except Exception as e:
        print(f"✗ Error reading file: {e}")

# Let's also check the schema registry to understand generic_csv
print("\n" + "=" * 80)
print("UNDERSTANDING GENERIC_CSV SCHEMA:")
print("-" * 80)

# To check generic_csv, we'd ideally need a way to get a specific schema by ID
# from schema_registry.py. The current find_matching_schema might return it if it matches.
# For now, we'll assume that if a file matches 'generic_csv', match_info.rules will be the generic_csv rules.
# A dedicated function like `get_schema_rules_by_id(schema_id)` in schema_registry.py would be cleaner.

# Let's try to get generic_csv rules by calling find_matching_schema with dummy headers
# that are unlikely to match anything else, or by checking if it was loaded.
# This is a bit of a hack for this script.
# A better way would be for schema_registry.py to expose its loaded _GENERIC_SCHEMA_RULES or a getter.
try:
    # Attempt to get generic_csv by matching it (if possible) or checking if it's loaded
    # This part is tricky without a direct getter.
    # We'll rely on the fact that _load_and_build_schema_maps in schema_registry.py
    # tries to load generic_csv.yaml and populates _GENERIC_SCHEMA_RULES.
    # We can't directly access it here without modifying schema_registry.py to expose it.
    # So, this check for generic_csv details might be limited.
    
    # We can, however, call find_matching_schema with headers that *should* only match generic_csv
    # e.g., very few, common headers not in other signatures.
    # For now, we'll just print a message that direct inspection of generic_csv's definition
    # from this script is harder with the new schema_registry structure.
    print("Note: Direct inspection of 'generic_csv' definition from this script is more complex.")
    print("      The matching logic will fall back to it if no other schema matches.")
    print("      If a file matches 'generic_csv', its rules will be shown above.")

except Exception as e:
    print(f"Error trying to inspect generic_csv: {e}")


# Check for schema_mode setting
print("\n" + "=" * 80)
print("CONFIGURATION SETTINGS:")
print("-" * 80)
print(f"Schema Mode: {app_config.SCHEMA_MODE}")
print(f"This affects how strictly schemas are matched and applied")

if app_config.SCHEMA_MODE == "flexible":
    print("✓ Flexible mode allows partial matches and should process most files")
elif app_config.SCHEMA_MODE == "strict":
    print("⚠️  Strict mode might skip files that don't match schemas perfectly")
