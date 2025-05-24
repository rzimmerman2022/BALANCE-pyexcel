# comprehensive_data_audit.py
import pandas as pd
import numpy as np

def audit_data_quality(parquet_file='workbook/balance_final.parquet'):
    """
    Comprehensive audit of data quality issues in the balance file.
    This will reveal all the ways our data is broken.
    """
    
    # Read the data
    df = pd.read_parquet(parquet_file)
    
    print("=== COMPREHENSIVE DATA QUALITY AUDIT ===")
    print(f"Total records: {len(df)}")
    print(f"Date range attempted: {df['Date'].min()} to {df['Date'].max()}")
    
    # First, let's understand our data sources
    print("\n=== DATA SOURCE BREAKDOWN ===")
    source_counts = df['DataSourceName'].value_counts()
    for source, count in source_counts.items():
        percentage = (count / len(df)) * 100
        print(f"{source}: {count} records ({percentage:.1f}%)")
    
    # Now let's examine field completeness by source
    print("\n=== FIELD COMPLETENESS BY SOURCE ===")
    
    # Define which fields we expect to be important
    critical_fields = [
        'Date', 'Amount', 'Description', 'Account', 'Category',
        'PostDate', 'ReferenceNumber', 'Institution', 
        'StatementStart', 'StatementEnd', 'OriginalDate'
    ]
    
    # For each data source, check field completeness
    for source in df['DataSourceName'].unique():
        source_df = df[df['DataSourceName'] == source]
        print(f"\n{source} ({len(source_df)} records):")
        
        for field in critical_fields:
            if field in df.columns:
                # Count non-null, non-NaT, non-empty values
                if df[field].dtype == 'object':  # String field
                    valid_count = source_df[field].notna().sum()
                    valid_count -= (source_df[field] == '').sum()  # Remove empty strings
                    valid_count -= (source_df[field] == '<NA>').sum()  # Remove <NA> strings
                else:  # Numeric or date field
                    valid_count = source_df[field].notna().sum()
                
                percentage = (valid_count / len(source_df)) * 100
                
                # Only show fields that have data or should have data
                if percentage > 0 or field in ['Date', 'Amount', 'Description']:
                    status = "✓" if percentage > 90 else "⚠" if percentage > 50 else "✗"
                    print(f"  {status} {field}: {percentage:.1f}% complete ({valid_count}/{len(source_df)})")
    
    # Let's specifically examine the date problems
    print("\n=== DATE FIELD ANALYSIS ===")
    
    # Check Date field
    date_nat = df['Date'].isna().sum()
    print(f"Records with invalid Date: {date_nat} ({date_nat/len(df)*100:.1f}%)")
    
    # Check by source
    print("\nDate validity by source:")
    for source in df['DataSourceName'].unique():
        source_df = df[df['DataSourceName'] == source]
        source_nat = source_df['Date'].isna().sum()
        valid_pct = ((len(source_df) - source_nat) / len(source_df)) * 100
        print(f"  {source}: {valid_pct:.1f}% valid dates")
    
    # Check if we have date data in other columns
    if 'OriginalDate' in df.columns:
        # For records with NaT Date, do we have OriginalDate?
        nat_date_df = df[df['Date'].isna()]
        has_original = nat_date_df['OriginalDate'].notna().sum()
        print(f"\nRecords with invalid Date but valid OriginalDate: {has_original}")
        
        if has_original > 0:
            print("Sample of broken date records:")
            sample = nat_date_df[nat_date_df['OriginalDate'].notna()].head(3)
            for _, row in sample.iterrows():
                print(f"  Source: {row['DataSourceName']}, Date: {row['Date']}, OriginalDate: {row['OriginalDate']}")
    
    # Check for data type issues
    print("\n=== DATA TYPE ISSUES ===")
    
    # Amount should always be numeric
    if df['Amount'].dtype == 'object':
        print("WARNING: Amount is stored as text, not numeric!")
    else:
        zero_amounts = (df['Amount'] == 0).sum()
        null_amounts = df['Amount'].isna().sum()
        print(f"Zero amounts: {zero_amounts}")
        print(f"Null amounts: {null_amounts}")
    
    # Look for the most problematic records
    print("\n=== MOST PROBLEMATIC RECORDS ===")
    
    # Count issues per record
    issue_counts = pd.Series(0, index=df.index)
    
    # Check each critical field
    for field in ['Date', 'Amount', 'Description', 'Account', 'Category']:
        if field in df.columns:
            if df[field].dtype == 'object':
                is_invalid = df[field].isna() | (df[field] == '') | (df[field] == '<NA>')
            else:
                is_invalid = df[field].isna()
            issue_counts += is_invalid.astype(int)
    
    # Show records with the most issues
    worst_records = df[issue_counts > 3].head(5)
    if len(worst_records) > 0:
        print(f"\nShowing {len(worst_records)} records with 4+ missing critical fields:")
        for _, row in worst_records.iterrows():
            print(f"  {row['DataSourceName']}: Date={row['Date']}, Amount={row['Amount']}, "
                  f"Description={row.get('Description', 'N/A')[:30]}...")
    
    return df

# Run the audit
if __name__ == "__main__":
    df = audit_data_quality()