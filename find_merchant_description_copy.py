# find_merchant_description_copy.py
# This script hunts for where merchant = description logic is implemented

from pathlib import Path
import re
import yaml

print("Hunting for where Merchant = Description logic is implemented...")
print("=" * 80)

# First, let's examine apply_schema_transformations
consolidator_path = Path('src/balance_pipeline/csv_consolidator.py')

with open(consolidator_path, 'r') as f:
    content = f.read()
    lines = content.split('\n')

print("\n1. EXAMINING apply_schema_transformations FUNCTION:")
print("-" * 80)

# Find the function definition
func_start = None
func_end = None
for i, line in enumerate(lines):
    if 'def apply_schema_transformations(' in line:
        func_start = i
        # Find the end of the function by looking for the next def at the same indentation
        base_indent = len(line) - len(line.lstrip())
        for j in range(i+1, len(lines)):
            if lines[j].strip() and (len(lines[j]) - len(lines[j].lstrip())) <= base_indent:
                if 'def ' in lines[j]:
                    func_end = j
                    break
        break

if func_start:
    print(f"Found function from line {func_start+1} to {func_end+1 if func_end else 'end'}")
    
    # Look for merchant-related logic within this function
    print("\nSearching for merchant column logic in this function:")
    
    for i in range(func_start, func_end if func_end else len(lines)):
        line = lines[i]
        # Look for patterns involving merchant column
        if any(pattern in line.lower() for pattern in ['merchant', '"merchant"', "'merchant'"]):
            print(f"\n  Line {i+1}: {line.strip()}")
            # Show context
            for j in range(max(func_start, i-2), min(func_end if func_end else len(lines), i+3)):
                marker = ">>>" if j == i else "   "
                print(f"    {marker} {j+1}: {lines[j]}")

# Check schema registry files
print("\n\n2. CHECKING SCHEMA DEFINITIONS:")
print("-" * 80)

schema_registry_path = Path('rules/schema_registry.yml')
if schema_registry_path.exists():
    print(f"Found schema registry at: {schema_registry_path}")
    
    try:
        with open(schema_registry_path, 'r') as f:
            schema_content = yaml.safe_load(f)
        
        # Look for schemas that might set merchant = description
        print("\nChecking each schema for merchant transformations:")
        
        for schema_name, schema_def in schema_content.items():
            if isinstance(schema_def, dict):
                # Check if this schema has transformations
                transformations = schema_def.get('transformations', {})
                if transformations and 'Merchant' in transformations:
                    merchant_source = transformations['Merchant']
                    print(f"\n  Schema: {schema_name}")
                    print(f"    Merchant mapped from: {merchant_source}")
                    
                    if merchant_source == 'Description':
                        print("    🚨 FOUND IT! This schema sets Merchant = Description")
                
                # Also check for column_mapping
                column_mapping = schema_def.get('column_mapping', {})
                if column_mapping:
                    for target, source in column_mapping.items():
                        if target == 'Merchant' and source == 'Description':
                            print(f"\n  Schema: {schema_name}")
                            print(f"    🚨 FOUND IT! Column mapping sets Merchant = Description")
    
    except Exception as e:
        print(f"Error reading schema registry: {e}")
else:
    print("Schema registry not found at expected location")

# Check for any Python schema definition files
print("\n\n3. CHECKING PYTHON SCHEMA DEFINITIONS:")
print("-" * 80)

schema_dir = Path('src/balance_pipeline/schemas')
if schema_dir.exists():
    print(f"Found schemas directory: {schema_dir}")
    
    for schema_file in schema_dir.glob('*.py'):
        print(f"\nChecking {schema_file.name}:")
        
        with open(schema_file, 'r') as f:
            schema_content = f.read()
        
        # Look for merchant = description patterns
        if re.search(r'["\']Merchant["\'].*["\']Description["\']', schema_content):
            print("  🚨 Found Merchant = Description pattern!")
            
            # Show the specific lines
            for i, line in enumerate(schema_content.split('\n')):
                if 'Merchant' in line and 'Description' in line:
                    print(f"    Line {i+1}: {line.strip()}")

# Look for default column handling
print("\n\n4. CHECKING DEFAULT COLUMN HANDLING:")
print("-" * 80)

# Search for code that handles missing merchant columns
print("Looking for code that creates Merchant when it's missing:")

for i, line in enumerate(lines):
    # Look for patterns that suggest creating merchant from description
    if (('Merchant' in line and 'not in' in line) or 
        ('merchant' in line and 'missing' in line.lower()) or
        ('"Merchant"' not in line and 'Description' in line and 'Merchant' in line)):
        
        print(f"\n  Line {i+1}: {line.strip()}")
        # Show context
        for j in range(max(0, i-3), min(len(lines), i+4)):
            marker = ">>>" if j == i else "   "
            print(f"    {marker} {j+1}: {lines[j]}")

# Final summary
print("\n\n" + "=" * 80)
print("DIAGNOSIS:")
print("=" * 80)
print("\nThe old Merchant = Description logic is likely coming from:")
print("1. Schema transformation rules defined in schema_registry.yml")
print("2. Default column handling when Merchant is missing")
print("3. Schema-specific transformation logic")
print("\nCheck the findings above to locate the exact source.")