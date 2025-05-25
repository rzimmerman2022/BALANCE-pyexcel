# trace_cleaning_bypass.py
# This script investigates why your files bypass cleaning by examining the actual code flow

import re
from pathlib import Path

print("Investigating why comprehensive cleaning is bypassed...")
print("=" * 80)

# Read the csv_consolidator.py file
consolidator_path = Path('src/balance_pipeline/csv_consolidator.py')

with open(consolidator_path, 'r') as f:
    content = f.read()
    lines = content.split('\n')

# First, let's understand the structure around the cleaning call
print("\n1. CONTEXT AROUND COMPREHENSIVE CLEANING:")
print("-" * 80)

cleaning_line_num = None
for i, line in enumerate(lines):
    if 'apply_comprehensive_cleaning' in line and 'processed_df' in line:
        cleaning_line_num = i
        break

if cleaning_line_num:
    # Show 30 lines before the cleaning call to understand the flow
    start = max(0, cleaning_line_num - 30)
    
    print(f"Code leading up to cleaning (lines {start+1} to {cleaning_line_num+1}):\n")
    
    for i in range(start, cleaning_line_num + 5):
        marker = ">>>" if i == cleaning_line_num else "   "
        print(f"{marker} {i+1}: {lines[i]}")

# Look for early exits before cleaning
print("\n\n2. CHECKING FOR EARLY EXITS BEFORE CLEANING:")
print("-" * 80)

# Find the function containing cleaning
func_start = None
for i in range(cleaning_line_num, -1, -1):
    if 'def process_csv_files' in lines[i]:
        func_start = i
        break

if func_start and cleaning_line_num:
    # Look for continue/return statements between function start and cleaning
    early_exits = []
    
    for i in range(func_start, cleaning_line_num):
        line = lines[i].strip()
        if any(keyword in line for keyword in ['continue', 'return', 'break']):
            # Check if this is before cleaning by looking at indentation
            indent = len(lines[i]) - len(lines[i].lstrip())
            cleaning_indent = len(lines[cleaning_line_num]) - len(lines[cleaning_line_num].lstrip())
            
            # Only consider exits at same or lower indentation level
            if indent <= cleaning_indent:
                early_exits.append((i+1, line))
    
    if early_exits:
        print("Found potential early exits that could bypass cleaning:")
        for line_num, exit_statement in early_exits:
            print(f"\n  Line {line_num}: {exit_statement}")
            
            # Show context around each exit
            for j in range(max(0, line_num-6), min(len(lines), line_num+2)):
                marker = ">>>" if j == line_num-1 else "   "
                print(f"    {marker} {j+1}: {lines[j]}")

# Check for schema-specific processing
print("\n\n3. SCHEMA-SPECIFIC PROCESSING PATHS:")
print("-" * 80)

# Look for generic_csv handling
generic_csv_refs = []
for i, line in enumerate(lines):
    if 'generic_csv' in line.lower():
        generic_csv_refs.append((i+1, line.strip()))

if generic_csv_refs:
    print("Found references to generic_csv (which might bypass cleaning):")
    for line_num, line_content in generic_csv_refs[:5]:
        print(f"  Line {line_num}: {line_content}")

# Look for merchant column assignments
print("\n\n4. MERCHANT COLUMN ASSIGNMENTS:")
print("-" * 80)

merchant_assignments = []
for i, line in enumerate(lines):
    # Look for patterns where Merchant is assigned from Description
    if re.search(r'["\']Merchant["\'].*=.*["\']Description["\']', line) or \
       re.search(r'merchant.*=.*description', line, re.IGNORECASE):
        merchant_assignments.append((i+1, line.strip()))

if merchant_assignments:
    print("Found places where Merchant is assigned from Description:")
    for line_num, assignment in merchant_assignments:
        print(f"\n  Line {line_num}: {assignment}")
        
        # Show context
        for j in range(max(0, line_num-4), min(len(lines), line_num+3)):
            marker = ">>>" if j == line_num-1 else "   "
            print(f"    {marker} {j+1}: {lines[j]}")

# Check the schema application
print("\n\n5. SCHEMA TRANSFORMATION APPLICATION:")
print("-" * 80)

# Find where apply_schema_transformations is called
schema_transform_calls = []
for i, line in enumerate(lines):
    if 'apply_schema_transformations' in line:
        schema_transform_calls.append((i+1, line.strip()))

if schema_transform_calls:
    print("Schema transformations are applied at:")
    for line_num, call in schema_transform_calls:
        print(f"  Line {line_num}: {call}")
        
        # Check if this is before or after cleaning
        if cleaning_line_num and line_num < cleaning_line_num:
            print("    ^ This happens BEFORE comprehensive cleaning")
        elif cleaning_line_num and line_num > cleaning_line_num:
            print("    ^ This happens AFTER comprehensive cleaning")

# Final analysis
print("\n\n" + "=" * 80)
print("DIAGNOSIS SUMMARY:")
print("=" * 80)

if early_exits:
    print(f"\n⚠️  Found {len(early_exits)} potential early exits before cleaning")
    print("   These could cause files to skip comprehensive cleaning entirely")

if generic_csv_refs:
    print(f"\n⚠️  Found {len(generic_csv_refs)} references to generic_csv")
    print("   Files matching generic_csv might take a different processing path")

if merchant_assignments:
    print(f"\n⚠️  Found {len(merchant_assignments)} places where Merchant = Description")
    print("   This is the old logic that should be replaced by comprehensive cleaning")

print("\nRecommendation: Check the early exit conditions to see why your files")
print("might be skipping the comprehensive cleaning step.")