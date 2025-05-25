import pandas as pd
from pathlib import Path

# Look for recent output files
output_dir = Path(".")  # Adjust to your output directory
parquet_files = list(output_dir.glob("*.parquet"))
csv_files = list(output_dir.glob("*.csv"))
excel_files = list(output_dir.glob("*.xlsx"))

print("Found output files:")
for f in parquet_files + csv_files + excel_files:
    print(f"  - {f.name}")

# Check the most recent parquet file
if parquet_files:
    latest_parquet = max(parquet_files, key=lambda p: p.stat().st_mtime)
    print(f"\nChecking {latest_parquet.name}:")
    
    df = pd.read_parquet(latest_parquet)
    
    if 'OriginalDescription' in df.columns:
        print("✓ OriginalDescription column found!")
        print(f"  Total rows: {len(df)}")
        print(f"  Non-empty values: {df['OriginalDescription'].notna().sum()}")
        print(f"\nSample OriginalDescription values:")
        
        # Show some examples
        samples = df[df['OriginalDescription'].notna()]['OriginalDescription'].head(5)
        for i, desc in enumerate(samples):
            print(f"  {i+1}. {desc[:80]}...")
            
        # Search for specific transactions
        search_terms = ['BEST BUY', 'ZELLE', 'ROCKET']
        print(f"\nSearching for specific transactions:")
        for term in search_terms:
            matches = df[df['OriginalDescription'].str.contains(term, na=False)]
            print(f"  '{term}': {len(matches)} matches")
            if len(matches) > 0:
                print(f"    Example: {matches.iloc[0]['OriginalDescription'][:60]}...")
    else:
        print("✗ OriginalDescription column NOT found")
        print(f"  Available columns: {list(df.columns)}")
