# debug_cleaning_execution.py
# This script helps us understand why the cleaning code isn't running

import pandas as pd
from pathlib import Path
import sys
import logging

# Set up detailed logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
log = logging.getLogger(__name__)

# Add the project to Python path
sys.path.insert(0, 'src')

# First, let's verify the integration exists in csv_consolidator
log.info("Checking if cleaning integration exists in csv_consolidator.py...")
consolidator_path = Path('src/balance_pipeline/csv_consolidator.py')

if consolidator_path.exists():
    with open(consolidator_path, 'r') as f:
        content = f.read()
        
    # Check for the cleaning integration
    if 'apply_comprehensive_cleaning' in content:
        log.info("✓ Found apply_comprehensive_cleaning in csv_consolidator.py")
        
        # Find the line number
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'apply_comprehensive_cleaning' in line and 'processed_df' in line:
                log.info(f"  - Found at line {i+1}: {line.strip()}")
                
                # Check the surrounding context
                start = max(0, i-5)
                end = min(len(lines), i+5)
                log.info("  - Context around the cleaning call:")
                for j in range(start, end):
                    marker = ">>>" if j == i else "   "
                    log.info(f"    {marker} {j+1}: {lines[j]}")
    else:
        log.error("✗ apply_comprehensive_cleaning NOT found in csv_consolidator.py")
else:
    log.error("✗ csv_consolidator.py not found at expected path")

# Now let's check if there might be conditions preventing execution
log.info("\nChecking for conditions that might skip cleaning...")
if 'apply_comprehensive_cleaning' in content:
    # Look for the function that contains our cleaning call
    in_process_csv_files = False
    indent_level = 0
    cleaning_indent = 0
    
    for i, line in enumerate(lines):
        if 'def process_csv_files' in line:
            in_process_csv_files = True
            log.info(f"Found process_csv_files function at line {i+1}")
        
        if in_process_csv_files and 'apply_comprehensive_cleaning' in line:
            # Count the indentation
            cleaning_indent = len(line) - len(line.lstrip())
            log.info(f"Cleaning call has indent level: {cleaning_indent}")
            
            # Look backwards for any conditions
            for j in range(i-1, max(0, i-20), -1):
                check_line = lines[j]
                check_indent = len(check_line) - len(check_line.lstrip())
                
                if check_indent < cleaning_indent and ('if ' in check_line or 'else' in check_line):
                    log.warning(f"  ! Found condition at line {j+1}: {check_line.strip()}")
                    log.warning("    This condition might prevent cleaning from running!")

# Let's also verify the transaction_cleaner module can be imported
log.info("\nTesting if transaction_cleaner can be imported...")
try:
    from balance_pipeline.transaction_cleaner import apply_comprehensive_cleaning
    log.info("✓ Successfully imported apply_comprehensive_cleaning")
    
    # Check if the function works with a minimal test
    test_df = pd.DataFrame({'test': [1, 2, 3]})
    analysis_path = Path('transaction_analysis_results')
    
    if analysis_path.exists():
        log.info(f"✓ Analysis path exists: {analysis_path}")
        try:
            # Try to call the function
            result = apply_comprehensive_cleaning(test_df, analysis_path)
            log.info("✓ apply_comprehensive_cleaning can be called successfully")
        except Exception as e:
            log.error(f"✗ Error calling apply_comprehensive_cleaning: {e}")
    else:
        log.error(f"✗ Analysis path does not exist: {analysis_path}")
        
except ImportError as e:
    log.error(f"✗ Failed to import transaction_cleaner: {e}")
    
# Finally, let's check if there are any try/except blocks that might be swallowing errors
log.info("\nChecking for try/except blocks that might hide errors...")
if 'apply_comprehensive_cleaning' in content:
    for i, line in enumerate(lines):
        if 'apply_comprehensive_cleaning' in line:
            # Check surrounding lines for try/except
            for j in range(max(0, i-10), min(len(lines), i+10)):
                if 'try:' in lines[j] or 'except' in lines[j]:
                    log.warning(f"  ! Found error handling at line {j+1}: {lines[j].strip()}")
                    log.warning("    This might be hiding errors from the cleaning process!")

log.info("\nDiagnosis complete. Check the output above for clues about why cleaning isn't running.")