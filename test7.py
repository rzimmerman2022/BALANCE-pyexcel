import pandas as pd
from pathlib import Path

# Read the Excel file
output_path = Path("output.xlsx")
if output_path.exists():
    df = pd.read_excel(output_path)
    
    print("=== ANALYSIS OF output.xlsx ===\n")
    
    # 1. Basic info
    print(f"Total rows: {len(df)}")
    print(f"Total columns: {len(df.columns)}")
    print(f"\nColumn names:\n{list(df.columns)}")
    
    # 2. Check for foundational columns
    foundational_columns = ['TxnID', 'Owner', 'Date', 'Amount', 'Merchant', 
                           'Description', 'Category', 'Account', 'sharing_status']
    
    print(f"\n=== FOUNDATIONAL COLUMNS CHECK ===")
    for col in foundational_columns:
        if col in df.columns:
            print(f"✓ {col}: Present")
        else:
            print(f"✗ {col}: MISSING!")
    
    # 3. Analyze sharing_status column
    if 'sharing_status' in df.columns:
        print(f"\n=== SHARING_STATUS ANALYSIS ===")
        print("Value counts:")
        print(df['sharing_status'].value_counts(dropna=False))
        print(f"\nUnique values: {df['sharing_status'].unique()}")
    
    # 4. Analyze Merchant column
    if 'Merchant' in df.columns:
        print(f"\n=== MERCHANT ANALYSIS ===")
        total_merchants = len(df)
        missing_merchants = df['Merchant'].isna().sum()
        print(f"Total rows: {total_merchants}")
        print(f"Missing merchants: {missing_merchants} ({missing_merchants/total_merchants*100:.1f}%)")
        print(f"Populated merchants: {total_merchants - missing_merchants} ({(total_merchants - missing_merchants)/total_merchants*100:.1f}%)")
        
        # Show sample of merchant names
        print("\nSample merchant names (first 10 unique):")
        print(df['Merchant'].dropna().unique()[:10])
    
    # 5. Check for other important columns
    print(f"\n=== OTHER COLUMNS ANALYSIS ===")
    for col in df.columns:
        if col not in foundational_columns:
            null_count = df[col].isna().sum()
            print(f"{col}: {len(df) - null_count} populated, {null_count} missing")
    
    # 6. Sample data
    print(f"\n=== SAMPLE DATA (first 5 rows) ===")
    print(df[foundational_columns].head() if all(col in df.columns for col in foundational_columns) else df.head())
    
else:
    print("Error: output.xlsx file not found!")