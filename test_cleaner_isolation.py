# test_cleaner_isolation.py
# This script tests if the ComprehensiveTransactionCleaner works correctly

import pandas as pd
from pathlib import Path
import sys

# Add the project to Python path
sys.path.insert(0, 'src')

try:
    from balance_pipeline.transaction_cleaner import ComprehensiveTransactionCleaner
    print("✓ Successfully imported ComprehensiveTransactionCleaner")
except ImportError as e:
    print(f"✗ Failed to import ComprehensiveTransactionCleaner: {e}")
    sys.exit(1)

# Create test data that matches your actual data
test_data = pd.DataFrame({
    'OriginalDescription': [
        'FRYS-FOOD-DRG #051',
        'PURCHASE AUTHORIZED ON 04/19 APPLE CASH 1INFINITELOOP CA S303109599173355 CARD 0968',
        'TARGET 00001825 TEMPE AZ',
        'WHOLEFDS MKT 10456 CHANDLER AZ'
    ],
    'Description': [
        'FRYS-FOOD-DRG #051',
        'PURCHASE AUTHORIZED ON 04/19 APPLE CASH 1INFINITELOOP CA S303109599173355 CARD 0968',
        'TARGET 00001825 TEMPE AZ',
        'WHOLEFDS MKT 10456 CHANDLER AZ'
    ],
    'Merchant': [
        'FRYS-FOOD-DRG #051',
        'PURCHASE AUTHORIZED ON 04/19 APPLE CASH 1INFINITELOOP CA S303109599173355 CARD 0968',
        'TARGET 00001825 TEMPE AZ',
        'WHOLEFDS MKT 10456 CHANDLER AZ'
    ]
})

print("\nOriginal data:")
print(test_data[['OriginalDescription', 'Merchant']].to_string())

# Try to initialize and run the cleaner
try:
    analysis_path = Path('transaction_analysis_results')
    cleaner = ComprehensiveTransactionCleaner(analysis_path)
    print(f"\n✓ Initialized cleaner with analysis path: {analysis_path}")
    
    # Process the data
    cleaned_data = cleaner.process_dataframe(test_data)
    
    print("\nCleaned data:")
    print(cleaned_data[['Description', 'OriginalMerchant', 'Merchant']].to_string())
    
    # Check if cleaning actually happened
    if 'OriginalMerchant' in cleaned_data.columns:
        print("\n✓ OriginalMerchant column was created")
    else:
        print("\n✗ OriginalMerchant column is missing")
        
    if cleaned_data['Merchant'].iloc[0] != test_data['Merchant'].iloc[0]:
        print("✓ Merchant column was cleaned")
    else:
        print("✗ Merchant column was NOT cleaned")
        
except Exception as e:
    print(f"\n✗ Error running cleaner: {e}")
    import traceback
    traceback.print_exc()