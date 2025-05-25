# trace_pipeline_execution.py
# This script helps us understand which code path your data takes through the pipeline

import sys
import ast
from pathlib import Path

# Add the project to Python path
sys.path.insert(0, 'src')

print("Analyzing the execution flow in csv_consolidator.py...")
print("=" * 60)

# Read the csv_consolidator.py file
consolidator_path = Path('src/balance_pipeline/csv_consolidator.py')

with open(consolidator_path, 'r') as f:
    content = f.read()
    lines = content.split('\n')

# Find all the different processing functions and entry points
print("\n1. FINDING ENTRY POINTS AND PROCESSING FUNCTIONS:")
print("-" * 50)

functions_with_processing = []
for i, line in enumerate(lines):
    if 'def ' in line and ('process' in line.lower() or 'transform' in line.lower()):
        func_name = line.split('def ')[1].split('(')[0]
        functions_with_processing.append((i+1, func_name, line.strip()))
        print(f"Line {i+1}: {func_name}")

# Look for where apply_comprehensive_cleaning is called
print("\n2. LOCATION OF COMPREHENSIVE CLEANING:")
print("-" * 50)

cleaning_line = None
for i, line in enumerate(lines):
    if 'apply_comprehensive_cleaning' in line and 'processed_df' in line:
        cleaning_line = i
        print(f"Cleaning is called at line {i+1}")
        
        # Find which function contains this
        for line_num, func_name, _ in reversed(functions_with_processing):
            if line_num < i+1:
                print(f"Inside function: {func_name}")
                break

# Trace back to see what conditions might affect execution
if cleaning_line:
    print("\n3. EXECUTION PATH TO CLEANING:")
    print("-" * 50)
    print("Tracing conditions and function calls that lead to cleaning...\n")
    
    # Start from cleaning line and work backwards
    current_indent = len(lines[cleaning_line]) - len(lines[cleaning_line].lstrip())
    
    # Look for the containing function
    for i in range(cleaning_line, -1, -1):
        line = lines[i]
        if line.strip().startswith('def ') and 'process_csv_files' in line:
            print(f"Found containing function at line {i+1}: {line.strip()}")
            
            # Now trace forward looking for branches
            print("\nLooking for execution branches between function start and cleaning...")
            
            branch_depth = 0
            for j in range(i, cleaning_line):
                line = lines[j]
                stripped = line.strip()
                
                # Skip empty lines
                if not stripped:
                    continue
                    
                # Check for conditions or branches
                if stripped.startswith('if '):
                    branch_depth += 1
                    print(f"  Line {j+1}: CONDITION - {stripped[:60]}...")
                elif stripped.startswith('for '):
                    print(f"  Line {j+1}: LOOP - {stripped[:60]}...")
                elif stripped.startswith('try:'):
                    print(f"  Line {j+1}: TRY BLOCK")
                elif stripped.startswith('except'):
                    print(f"  Line {j+1}: EXCEPT - {stripped[:60]}...")
                elif 'return' in stripped and j < cleaning_line:
                    print(f"  Line {j+1}: EARLY RETURN - {stripped[:60]}...")
                elif 'continue' in stripped:
                    print(f"  Line {j+1}: CONTINUE - {stripped[:60]}...")
                    
            break

# Look for multiple code paths
print("\n4. CHECKING FOR ALTERNATIVE PROCESSING PATHS:")
print("-" * 50)

# Search for different processing modes or configurations
config_patterns = ['schema_mode', 'processing_mode', 'clean', 'transform', 'skip']
for pattern in config_patterns:
    occurrences = []
    for i, line in enumerate(lines):
        if pattern in line.lower() and ('if' in line or '=' in line):
            occurrences.append((i+1, line.strip()))
    
    if occurrences:
        print(f"\nFound '{pattern}' related logic:")
        for line_num, line_content in occurrences[:5]:  # Show first 5
            print(f"  Line {line_num}: {line_content[:80]}...")

# Check for function calls that might bypass cleaning
print("\n5. ALTERNATIVE PROCESSING FUNCTIONS:")
print("-" * 50)

# Look for calls to process_dataframe or similar without cleaning
for i, line in enumerate(lines):
    if 'process_dataframe' in line and 'apply_comprehensive_cleaning' not in lines[max(0,i-10):min(len(lines),i+10)]:
        print(f"Line {i+1}: Direct processing without cleaning - {line.strip()[:60]}...")

# Check the main entry point
print("\n6. MAIN ENTRY POINT ANALYSIS:")
print("-" * 50)

# Find the balance-pipe process command handler
for i, line in enumerate(lines):
    if '@click.command' in line or 'def process(' in line:
        print(f"Found command handler at line {i+1}")
        # Look at the next 20 lines to see what it calls
        for j in range(i, min(i+20, len(lines))):
            if 'process_csv_files' in lines[j]:
                print(f"  Line {j+1}: Calls process_csv_files")
                break
            elif any(func in lines[j] for _, func, _ in functions_with_processing):
                print(f"  Line {j+1}: Calls {lines[j].strip()}")

print("\n" + "=" * 60)
print("DIAGNOSIS COMPLETE")
print("=" * 60)