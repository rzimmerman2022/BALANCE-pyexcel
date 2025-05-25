import pandas as pd
import yaml
import sys
import logging
from pathlib import Path

# Set up detailed logging
logging.basicConfig(level=logging.DEBUG, format='%(message)s')
log = logging.getLogger()

sys.path.insert(0, 'src')

from balance_pipeline.csv_consolidator import (
    process_csv_files, 
    apply_schema_transformations,
    _normalize_csv_header
)

# Test 1: Verify the normalization function
print("=" * 60)
print("TEST 1: Column Name Normalization")
print("=" * 60)
test_names = ['Original Statement', 'original statement', 'ORIGINAL STATEMENT', 'Original  Statement']
for name in test_names:
    normalized = _normalize_csv_header(name)
    print(f"'{name}' -> '{normalized}'")

# Test 2: Check your actual CSV file
print("\n" + "=" * 60)
print("TEST 2: Actual CSV File Analysis")
print("=" * 60)
csv_path = Path(r'C:\BALANCE\CSVs\Ryan\Ryan - Monarch Money - 20250524.csv')
if csv_path.exists():
    df = pd.read_csv(csv_path, nrows=5)
    print(f"CSV columns: {list(df.columns)}")
    print(f"'Original Statement' in columns: {'Original Statement' in df.columns}")
    if 'Original Statement' in df.columns:
        print(f"First value: {df['Original Statement'].iloc[0]}")

# Test 3: Process a single file through the full pipeline
print("\n" + "=" * 60)
print("TEST 3: Full Pipeline Processing")
print("=" * 60)

# Add a custom logging handler to capture transformation steps
class ColumnTracker:
    def __init__(self):
        self.stages = []
    
    def track(self, stage, df):
        cols = list(df.columns) if hasattr(df, 'columns') else []
        has_original = 'Original Statement' in cols
        has_description = 'OriginalDescription' in cols
        self.stages.append({
            'stage': stage,
            'columns': cols,
            'has_original': has_original,
            'has_description': has_description,
            'shape': df.shape if hasattr(df, 'shape') else None
        })
        print(f"\n[{stage}]")
        print(f"  Shape: {df.shape if hasattr(df, 'shape') else 'N/A'}")
        print(f"  Has 'Original Statement': {has_original}")
        print(f"  Has 'OriginalDescription': {has_description}")
        if has_description and hasattr(df, 'iloc') and len(df) > 0:
            print(f"  OriginalDescription sample: {df['OriginalDescription'].iloc[0][:50]}...")

tracker = ColumnTracker()

# Monkey-patch to track transformations
original_apply = apply_schema_transformations
def tracked_apply(df, schema_rules, merchant_rules, filename):
    tracker.track("Before apply_schema_transformations", df)
    result = original_apply(df, schema_rules, merchant_rules, filename)
    tracker.track("After apply_schema_transformations", result)
    return result

# Temporarily replace the function
import balance_pipeline.csv_consolidator
balance_pipeline.csv_consolidator.apply_schema_transformations = tracked_apply

try:
    # Process just the Monarch file
    result_df = process_csv_files(
        [str(csv_path)],
        schema_registry_override_path=None,
        merchant_lookup_override_path=None
    )
    
    tracker.track("Final result from process_csv_files", result_df)
    
    # Check final columns
    print("\n" + "=" * 60)
    print("FINAL ANALYSIS")
    print("=" * 60)
    print(f"Final columns: {list(result_df.columns)}")
    print(f"Columns containing 'original': {[c for c in result_df.columns if 'original' in c.lower()]}")
    print(f"Columns containing 'description': {[c for c in result_df.columns if 'description' in c.lower()]}")
    
    # Check if data ended up in Extras
    if 'Extras' in result_df.columns and not result_df['Extras'].isna().all():
        import json
        first_extras = result_df['Extras'].iloc[0]
        if first_extras:
            try:
                extras_dict = json.loads(first_extras)
                print(f"\nExtras column contains: {list(extras_dict.keys())}")
                if 'Original Statement' in extras_dict:
                    print(f"  Found 'Original Statement' in Extras: {extras_dict['Original Statement']}")
            except:
                print(f"\nCouldn't parse Extras: {first_extras}")
                
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    # Restore original function
    balance_pipeline.csv_consolidator.apply_schema_transformations = original_apply

print("\n" + "=" * 60)
print("DEBUGGING COMPLETE")
print("=" * 60)
