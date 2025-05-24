#!/usr/bin/env python3
"""
Test script to validate the flexible schema implementation.
This script creates sample data and tests both strict and flexible modes.
"""

import pandas as pd
import os
import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Import the necessary modules
from balance_pipeline import config
from balance_pipeline.csv_consolidator import process_csv_files
from balance_pipeline.constants import MASTER_SCHEMA_COLUMNS

def create_test_data():
    """Create test CSV files that simulate different data sources"""
    
    # Create test directory
    test_dir = Path("test_flexible_schema")
    test_dir.mkdir(exist_ok=True)
    
    # 1. Bank statement data (has banking-specific columns)
    bank_data = pd.DataFrame({
        'Date': ['2024-01-15', '2024-01-16', '2024-01-17'],
        'Description': ['GROCERY STORE', 'GAS STATION', 'RESTAURANT'],
        'Amount': [-50.00, -30.00, -25.00],
        'Account': ['Checking', 'Checking', 'Checking'],
        'AccountLast4': ['1234', '1234', '1234'],
        'AccountType': ['Checking', 'Checking', 'Checking'],
        'Institution': ['Chase', 'Chase', 'Chase'],
        'ReferenceNumber': ['CHK001', 'CHK002', 'CHK003']
    })
    bank_data.to_csv(test_dir / 'chase_checking.csv', index=False)
    
    # 2. Aggregator data (has aggregator-specific columns)
    aggregator_data = pd.DataFrame({
        'Date': ['2024-01-15', '2024-01-18', '2024-01-20'],
        'Merchant': ['Amazon', 'Netflix', 'Spotify'],
        'Amount': [-99.99, -15.99, -9.99],
        'Account': ['Chase Checking', 'Chase Checking', 'Chase Checking'],
        'Category': ['Shopping', 'Entertainment', 'Entertainment'],
        'Tags': ['online,subscription', 'streaming', 'music'],
        'OriginalDate': ['2024-01-14', '2024-01-18', '2024-01-20']
    })
    aggregator_data.to_csv(test_dir / 'rocket_money_export.csv', index=False)
    
    # 3. Minimal data (only has core columns)
    minimal_data = pd.DataFrame({
        'Date': ['2024-01-21', '2024-01-22'],
        'Description': ['PAYCHECK', 'REFUND'],
        'Amount': [2000.00, 50.00],
        'Account': ['Checking', 'Checking']
    })
    minimal_data.to_csv(test_dir / 'manual_entries.csv', index=False)
    
    return test_dir


def test_schema_mode(mode):
    """Test the pipeline in a specific schema mode"""
    
    print(f"\n{'='*60}")
    print(f"Testing {mode.upper()} mode")
    print(f"{'='*60}")
    
    # Set the schema mode
    os.environ['SCHEMA_MODE'] = mode
    # Force reload of config to pick up new environment variable
    import importlib
    importlib.reload(config)
    
    # Create test data
    test_dir = create_test_data()
    
    # Get all CSV files
    csv_files = list(test_dir.glob('*.csv'))
    
    # Process the files
    try:
        result_df = process_csv_files(csv_files)
        
        print(f"\nProcessed {len(result_df)} total rows")
        print(f"Columns in output ({len(result_df.columns)} total):")
        
        # Group columns by type
        core_cols = [col for col in result_df.columns if col in config.CORE_REQUIRED_COLUMNS]
        optional_cols = [col for col in result_df.columns if col not in config.CORE_REQUIRED_COLUMNS]
        
        print(f"\nCore columns present: {core_cols}")
        print(f"Optional columns present: {optional_cols}")
        
        # Check for phantom columns (all empty)
        phantom_cols = []
        for col in result_df.columns:
            if result_df[col].isna().all() or (result_df[col] == '').all():
                phantom_cols.append(col)
        
        if phantom_cols:
            print(f"\nPhantom columns (all empty): {phantom_cols}")
        else:
            print(f"\nNo phantom columns found!")
            
        # Compare to full schema
        if mode == 'strict':
            missing_from_master = set(MASTER_SCHEMA_COLUMNS) - set(result_df.columns)
            if missing_from_master:
                print(f"\nWARNING: Missing expected columns in strict mode: {missing_from_master}")
        else:
            print(f"\nColumns reduced from {len(MASTER_SCHEMA_COLUMNS)} to {len(result_df.columns)}")
            
        # Show sample of data
        print(f"\nSample data (first 3 rows):")
        print(result_df.head(3))
        
    except Exception as e:
        print(f"ERROR during processing: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        import shutil
        if test_dir.exists():
            shutil.rmtree(test_dir)


def main():
    """Run tests in both modes"""
    
    print("Testing Flexible Schema Implementation")
    print("This will test both STRICT and FLEXIBLE modes")
    
    # Test strict mode (current behavior)
    test_schema_mode('strict')
    
    # Test flexible mode (new behavior)
    test_schema_mode('flexible')
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print("""
In STRICT mode:
- All 25 columns from MASTER_SCHEMA_COLUMNS are present
- Many columns may be empty (phantom columns)
- Backward compatible with existing processes

In FLEXIBLE mode:
- Only columns with actual data are retained
- Core required columns are always present
- Reduces clutter in Power BI and Excel
- More efficient storage and processing
""")


if __name__ == "__main__":
    main()