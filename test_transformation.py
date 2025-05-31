import pandas as pd
import yaml
import sys
from pathlib import Path # Added import
sys.path.insert(0, 'src')

from balance_pipeline.csv_consolidator import apply_schema_transformations
from balance_pipeline.csv_consolidator import load_merchant_lookup_rules # Changed import

# Load the actual schema
with open('rules/ryan_monarch_v1.yaml', 'r') as f:
    schema = yaml.safe_load(f)

# Create a test dataframe that matches your CSV structure
test_df = pd.DataFrame({
    'Date': ['2024-01-01'],
    'Merchant': ['Test Merchant'],
    'Category': ['Test Category'],
    'Account': ['Test Account'],
    'Original Statement': ['TEST ORIGINAL STATEMENT DATA'],
    'Notes': ['Test Note'],
    'Amount': [-100],
    'Tags': ['test']
})

print("BEFORE transformation:")
print(f"Columns: {test_df.columns.tolist()}")
print(f"Has Original Statement: {'Original Statement' in test_df.columns}")
print(f"Has OriginalDescription: {'OriginalDescription' in test_df.columns}")

# Load merchant rules (required parameter)
# Path is relative to the project root, where test_transformation.py is located
merchant_rules_path = Path('rules/merchant_lookup.csv')
merchant_rules = load_merchant_lookup_rules(merchant_rules_path)

# Call the transformation exactly as the pipeline does
try:
    result_df = apply_schema_transformations(
        test_df, 
        schema, 
        merchant_rules, 
        'test_file.csv'
    )
    
    print("\nAFTER transformation:")
    print(f"Columns: {result_df.columns.tolist()}")
    print(f"Has Original Statement: {'Original Statement' in result_df.columns}")
    print(f"Has OriginalDescription: {'OriginalDescription' in result_df.columns}")
    
    if 'OriginalDescription' in result_df.columns:
        print(f"OriginalDescription content: {result_df['OriginalDescription'].iloc[0]}")
    else:
        print("PROBLEM: OriginalDescription was not created!")
        
except Exception as e:
    print(f"\nERROR during transformation: {e}")
    import traceback
    traceback.print_exc()
