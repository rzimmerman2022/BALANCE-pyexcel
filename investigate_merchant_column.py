# pyth
# This script investigates where the Merchant column gets populated with Description

import yaml
import json
from pathlib import Path
import pandas as pd

print("Investigating where Merchant column gets populated...")
print("=" * 80)

# First, let's properly read the schema registry
print("\n1. READING SCHEMA REGISTRY (handling list structure):")
print("-" * 80)

schema_registry_path = Path('rules/schema_registry.yml')
if schema_registry_path.exists():
    try:
        with open(schema_registry_path, 'r') as f:
            schema_content = yaml.safe_load(f)
        
        print(f"Schema registry type: {type(schema_content)}")
        
        if isinstance(schema_content, list):
            print(f"Found {len(schema_content)} schemas in the list")
            
            # Check each schema in the list
            for i, schema in enumerate(schema_content):
                if isinstance(schema, dict):
                    schema_name = schema.get('name', schema.get('id', f'Schema_{i}'))
                    print(f"\n  Checking schema: {schema_name}")
                    
                    # Look for column_mapping
                    if 'column_mapping' in schema:
                        mappings = schema['column_mapping']
                        if isinstance(mappings, dict) and 'Merchant' in mappings:
                            print(f"    Merchant mapped from: {mappings['Merchant']}")
                            if mappings['Merchant'] == 'Description':
                                print("    🚨 FOUND IT! This schema maps Merchant from Description")
                    
                    # Look for transformations
                    if 'transformations' in schema:
                        trans = schema['transformations']
                        if isinstance(trans, dict) and 'Merchant' in trans:
                            print(f"    Merchant transformation: {trans['Merchant']}")
                            if trans['Merchant'] == 'Description':
                                print("    🚨 FOUND IT! This schema transforms Merchant from Description")
                    
                    # Look for rules
                    if 'rules' in schema:
                        rules = schema['rules']
                        if isinstance(rules, dict):
                            for col, rule in rules.items():
                                if col == 'Merchant' and rule == 'Description':
                                    print(f"    🚨 FOUND IT! Rule sets Merchant = Description")
                                elif col == 'Merchant':
                                    print(f"    Merchant rule: {rule}")
        
        elif isinstance(schema_content, dict):
            print("Schema registry is a dictionary")
            # Handle dictionary structure (original approach)
            for schema_name, schema_def in schema_content.items():
                if isinstance(schema_def, dict) and 'Merchant' in str(schema_def):
                    print(f"\n  Schema {schema_name} mentions Merchant")
                    
    except Exception as e:
        print(f"Error reading schema registry: {e}")
        import traceback
        traceback.print_exc()

# Check master schema constants
print("\n\n2. CHECKING MASTER SCHEMA DEFINITION:")
print("-" * 80)

constants_path = Path('src/balance_pipeline/constants.py')
if constants_path.exists():
    with open(constants_path, 'r') as f:
        constants_content = f.read()
    
    # Look for MASTER_SCHEMA_COLUMNS
    if 'MASTER_SCHEMA_COLUMNS' in constants_content:
        print("Found MASTER_SCHEMA_COLUMNS definition")
        
        # Check if both OriginalMerchant and Merchant are defined
        if 'OriginalMerchant' in constants_content:
            print("✓ OriginalMerchant is in MASTER_SCHEMA_COLUMNS")
        else:
            print("✗ OriginalMerchant is NOT in MASTER_SCHEMA_COLUMNS")
            
        if '"Merchant"' in constants_content or "'Merchant'" in constants_content:
            print("✓ Merchant is in MASTER_SCHEMA_COLUMNS")
        else:
            print("✗ Merchant is NOT in MASTER_SCHEMA_COLUMNS")

# Let's trace through a sample transformation
print("\n\n3. SIMULATING A TRANSFORMATION:")
print("-" * 80)

print("Creating a test DataFrame similar to your data...")
test_df = pd.DataFrame({
    'Date': ['2024-01-01'],
    'Description': ['FRYS-FOOD-DRG #051'],
    'Amount': [-50.00]
})

print("\nOriginal DataFrame:")
print(test_df)

# Check what columns exist after reading
print("\nColumns in test data:", list(test_df.columns))
print("Does Merchant column exist initially?", 'Merchant' in test_df.columns)

# Look for default column creation
print("\n\n4. CHECKING FOR DEFAULT COLUMN CREATION:")
print("-" * 80)

csv_consolidator_path = Path('src/balance_pipeline/csv_consolidator.py')
if csv_consolidator_path.exists():
    with open(csv_consolidator_path, 'r') as f:
        lines = f.readlines()
    
    # Look for places where Merchant column might be created
    for i, line in enumerate(lines):
        if '"Merchant"' in line or "'Merchant'" in line:
            # Check if this is about creating/assigning to Merchant
            if '=' in line and 'Merchant' in line.split('=')[0]:
                print(f"\nLine {i+1}: {line.strip()}")
                # Show context
                for j in range(max(0, i-2), min(len(lines), i+3)):
                    print(f"  {j+1}: {lines[j].rstrip()}")

# Check the comprehensive cleaner's expected input
print("\n\n5. COMPREHENSIVE CLEANER EXPECTATIONS:")
print("-" * 80)

cleaner_path = Path('src/balance_pipeline/transaction_cleaner.py')
if cleaner_path.exists():
    with open(cleaner_path, 'r') as f:
        cleaner_content = f.read()
    
    # Look for what columns the cleaner expects
    if 'def process_dataframe' in cleaner_content:
        print("Found process_dataframe method")
        
        # Check what columns it works with
        expected_cols = []
        if 'OriginalDescription' in cleaner_content:
            expected_cols.append('OriginalDescription')
        if 'Description' in cleaner_content:
            expected_cols.append('Description')
        if 'Merchant' in cleaner_content:
            expected_cols.append('Merchant')
        
        print(f"Cleaner works with columns: {expected_cols}")

print("\n\n" + "=" * 80)
print("SUMMARY:")
print("=" * 80)
print("\nThe Merchant = Description behavior is likely happening because:")
print("1. Schema rules are setting Merchant = Description during transformation")
print("2. The old merchant cleaning is commented out")
print("3. The comprehensive cleaner might not be creating the Merchant column properly")
print("\nCheck the findings above for the specific source.")