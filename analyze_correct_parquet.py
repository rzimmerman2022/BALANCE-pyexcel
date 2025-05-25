import pandas as pd
from pathlib import Path

# Specify the exact path to your artifacts parquet file
parquet_path = Path(r"C:\BALANCE\BALANCE-pyexcel\artifacts\balance_final.parquet")

if not parquet_path.exists():
    print(f"ERROR: File not found at {parquet_path}")
    print("Available parquet files in artifacts:")
    artifacts_dir = Path(r"C:\BALANCE\BALANCE-pyexcel\artifacts")
    for f in artifacts_dir.glob("*.parquet"):
        print(f"  - {f.name}")
else:
    print(f"Analyzing: {parquet_path}")
    print("=" * 60)
    
    # Read the parquet file
    df = pd.read_parquet(parquet_path)
    
    print(f"\nBASIC INFORMATION:")
    print(f"Total rows: {len(df):,}")
    print(f"Total columns: {len(df.columns)}")
    print(f"File size: {parquet_path.stat().st_size / 1024 / 1024:.2f} MB")
    
    # Continue with the problem detection...
    print("\nPOTENTIAL PROBLEM COLUMNS:")
    problems_found = False
    
    for col in df.columns:
        issues = []
        
        if df[col].isna().all() or (df[col] == '').all():
            issues.append("All values are empty/null")
            problems_found = True
        
        if df[col].dtype == 'object' and (df[col] == '').all():
            issues.append("All empty strings (ambiguous type)")
            problems_found = True
        
        if issues:
            print(f"\n{col}:")
            for issue in issues:
                print(f"  - {issue}")
    
    if not problems_found:
        print("No obvious problems found!")
    
    # Check OriginalDescription specifically
    print("\n" + "=" * 60)
    print("ORIGINALDESCRIPTION ANALYSIS:")
    if 'OriginalDescription' in df.columns:
        orig_desc = df['OriginalDescription']
        print(f"✓ Column exists")
        print(f"  Non-empty values: {orig_desc.notna().sum():,} ({orig_desc.notna().sum()/len(df)*100:.1f}%)")
        print(f"  Sample values:")
        samples = orig_desc[orig_desc.notna()].head(5)
        for i, desc in enumerate(samples):
            print(f"    {i+1}. {desc[:80]}{'...' if len(desc) > 80 else ''}")
    else:
        print(f"✗ OriginalDescription column NOT FOUND!")
