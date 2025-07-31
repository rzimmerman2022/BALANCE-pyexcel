#!/usr/bin/env python3
"""
Test script to process all sample data through the pipeline
"""
import sys
import glob
from pathlib import Path

# Add src to path
sys.path.insert(0, 'src')

from balance_pipeline.main import main

def test_all_sample_data():
    """Process all sample data files"""
    
    # Find all CSV files
    files = glob.glob('sample_data_multi/*/*.csv')
    print(f"Found {len(files)} CSV files:")
    for file in files:
        print(f"  - {file}")
    
    # Set up sys.argv for the main function
    sys.argv = [
        'test_pipeline',
        'process'
    ] + files + [
        '--debug',
        '--format', 'excel',
        '--output', 'output/sample_test_results.xlsx'
    ]
    
    print("\nProcessing files through pipeline...")
    main()
    print("\nProcessing complete!")

if __name__ == "__main__":
    test_all_sample_data()