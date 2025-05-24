# true_data_quality_audit.py
"""
A comprehensive data quality audit that reveals the TRUE state of your financial data.
This tool checks not just if fields exist, but if they contain USABLE data.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from collections import defaultdict

def analyze_date_quality(df, date_column='Date'):
    """Check if dates are actually valid, not just non-null"""
    total = len(df)
    
    # Check for various date issues
    if date_column not in df.columns:
        return {"exists": False}
    
    # For datetime columns, check for NaT explicitly
    if pd.api.types.is_datetime64_any_dtype(df[date_column]):
        nat_count = df[date_column].isna().sum()  # This catches NaT
        valid_dates = total - nat_count
        
        # Get the actual date range, excluding NaT
        valid_date_mask = df[date_column].notna()
        if valid_date_mask.any():
            min_date = df.loc[valid_date_mask, date_column].min()
            max_date = df.loc[valid_date_mask, date_column].max()
        else:
            min_date = max_date = None
            
    else:
        # If stored as string, check for actual date parsing
        valid_dates = 0
        nat_count = 0
        min_date = max_date = None
        
        for val in df[date_column]:
            if pd.isna(val) or val == 'NaT' or val == '':
                nat_count += 1
            else:
                try:
                    parsed = pd.to_datetime(val)
                    if pd.notna(parsed):
                        valid_dates += 1
                        if min_date is None or parsed < min_date:
                            min_date = parsed
                        if max_date is None or parsed > max_date:
                            max_date = parsed
                except:
                    nat_count += 1
    
    return {
        "valid_count": valid_dates,
        "invalid_count": nat_count,
        "valid_percentage": (valid_dates / total * 100) if total > 0 else 0,
        "min_date": min_date,
        "max_date": max_date,
        "date_range_makes_sense": min_date is not None and max_date is not None and min_date <= max_date
    }

def check_field_quality(series, field_name):
    """Check the actual quality of data in a field"""
    total = len(series)
    
    # Count different types of "empty" values
    null_count = series.isna().sum()
    
    if series.dtype == 'object':  # String fields
        empty_string_count = (series == '').sum()
        na_string_count = (series.astype(str).str.upper() == '<NA>').sum()
        nan_string_count = (series.astype(str).str.lower() == 'nan').sum()
        none_string_count = (series.astype(str).str.lower() == 'none').sum()
        
        # Count meaningful values
        meaningful = total - null_count - empty_string_count - na_string_count - nan_string_count - none_string_count
        
        # Sample some actual values
        sample_values = series[series.notna() & (series != '') & (series != '<NA>')].head(3).tolist()
        
        return {
            "total": total,
            "meaningful_count": meaningful,
            "meaningful_percentage": (meaningful / total * 100) if total > 0 else 0,
            "null_count": null_count,
            "empty_string_count": empty_string_count,
            "placeholder_count": na_string_count + nan_string_count + none_string_count,
            "sample_values": sample_values
        }
    else:  # Numeric fields
        zero_count = (series == 0).sum()
        
        meaningful = total - null_count
        
        return {
            "total": total,
            "meaningful_count": meaningful,
            "meaningful_percentage": (meaningful / total * 100) if total > 0 else 0,
            "null_count": null_count,
            "zero_count": zero_count,
            "min_value": series.min() if meaningful > 0 else None,
            "max_value": series.max() if meaningful > 0 else None
        }

def deep_audit(parquet_file='workbook/balance_final.parquet'):
    """Perform a deep audit that reveals the true state of the data"""
    
    print("=== TRUE DATA QUALITY AUDIT ===")
    print("This audit checks for USABLE data, not just non-null values\n")
    
    # Read the data
    df = pd.read_parquet(parquet_file)
    
    print(f"Total records loaded: {len(df)}")
    print(f"Unique data sources: {df['DataSourceName'].nunique()}")
    
    # First, let's check the date situation properly
    print("\n=== REAL DATE ANALYSIS ===")
    date_quality = analyze_date_quality(df)
    
    print(f"Valid dates: {date_quality['valid_count']} ({date_quality['valid_percentage']:.1f}%)")
    print(f"Invalid dates (NaT/null): {date_quality['invalid_count']}")
    
    if date_quality['min_date'] and date_quality['max_date']:
        print(f"Actual date range: {date_quality['min_date']} to {date_quality['max_date']}")
        
        # Check for suspicious dates
        if date_quality['min_date'].year < 2020:
            print("⚠️  WARNING: Dates go back before 2020 - might indicate parsing issues")
        if date_quality['max_date'].year > 2025:
            print("⚠️  WARNING: Dates extend beyond 2025 - might indicate parsing issues")
    else:
        print("❌ NO VALID DATE RANGE - All dates are invalid!")
    
    # Check date quality by source
    print("\n=== DATE QUALITY BY SOURCE ===")
    for source in sorted(df['DataSourceName'].unique()):
        source_df = df[df['DataSourceName'] == source]
        source_date_quality = analyze_date_quality(source_df)
        
        status = "✓" if source_date_quality['valid_percentage'] > 95 else "⚠" if source_date_quality['valid_percentage'] > 50 else "✗"
        print(f"{status} {source}: {source_date_quality['valid_percentage']:.1f}% valid dates "
              f"({source_date_quality['valid_count']}/{len(source_df)})")
        
        # If this source has date issues, show some examples
        if source_date_quality['invalid_count'] > 0:
            bad_date_sample = source_df[source_df['Date'].isna()].head(2)
            for _, row in bad_date_sample.iterrows():
                desc = row.get('Description', 'No description')[:40]
                orig_date = row.get('OriginalDate', 'No original date')
                print(f"    Example bad date: '{desc}...', OriginalDate={orig_date}")
    
    # Now let's check critical fields for real quality
    print("\n=== CRITICAL FIELD QUALITY ===")
    critical_fields = ['Amount', 'Description', 'Account', 'Category']
    
    for field in critical_fields:
        if field in df.columns:
            quality = check_field_quality(df[field], field)
            status = "✓" if quality['meaningful_percentage'] > 95 else "⚠" if quality['meaningful_percentage'] > 80 else "✗"
            
            print(f"\n{status} {field}:")
            print(f"  Meaningful values: {quality['meaningful_count']} ({quality['meaningful_percentage']:.1f}%)")
            
            if field == 'Amount':
                print(f"  Zero amounts: {quality.get('zero_count', 0)}")
                print(f"  Range: ${quality.get('min_value', 0):.2f} to ${quality.get('max_value', 0):.2f}")
            elif 'sample_values' in quality and quality['sample_values']:
                print(f"  Sample values: {quality['sample_values'][:2]}")
            
            if quality.get('placeholder_count', 0) > 0:
                print(f"  ⚠️  Found {quality['placeholder_count']} placeholder values (nan, none, <NA>)")
    
    # Check for source-specific issues
    print("\n=== SOURCE-SPECIFIC FIELD AVAILABILITY ===")
    
    # Define what fields each source type SHOULD have
    expected_fields = {
        'bank': ['ReferenceNumber', 'StatementStart', 'StatementEnd', 'PostDate'],
        'aggregator': ['Merchant', 'Category'],
        'all': ['Date', 'Amount', 'Description', 'Account']
    }
    
    # Categorize sources
    bank_sources = ['jordyn_chase_checking_v1', 'jordyn_wells_v1', 'jordyn_discover_card_v1']
    aggregator_sources = ['ryan_monarch_v1', 'ryan_rocket_v1']
    
    for source in sorted(df['DataSourceName'].unique()):
        source_df = df[df['DataSourceName'] == source]
        print(f"\n{source} ({len(source_df)} records):")
        
        # Determine source type
        if source in bank_sources:
            check_fields = expected_fields['all'] + expected_fields['bank']
            source_type = "Bank Export"
        else:
            check_fields = expected_fields['all'] + expected_fields['aggregator']
            source_type = "Aggregator Export"
        
        print(f"  Type: {source_type}")
        
        # Check each expected field
        missing_critical = []
        for field in check_fields:
            if field in df.columns:
                quality = check_field_quality(source_df[field], field)
                if quality['meaningful_percentage'] < 50:
                    missing_critical.append(f"{field} ({quality['meaningful_percentage']:.0f}%)")
        
        if missing_critical:
            print(f"  ❌ Missing/Poor Quality: {', '.join(missing_critical)}")
        else:
            print(f"  ✓ All expected fields have good data")
    
    # Look for the specific date parsing issue
    print("\n=== DATE PARSING INVESTIGATION ===")
    
    # Check if OriginalDate has data where Date is NaT
    if 'OriginalDate' in df.columns:
        date_nat_mask = df['Date'].isna()
        original_valid_mask = df['OriginalDate'].notna()
        
        fixable_dates = (date_nat_mask & original_valid_mask).sum()
        if fixable_dates > 0:
            print(f"❗ Found {fixable_dates} records where Date is invalid but OriginalDate exists")
            print("   This suggests a date parsing configuration issue in the schemas")
            
            # Show which sources have this issue
            for source in df['DataSourceName'].unique():
                source_mask = (df['DataSourceName'] == source) & date_nat_mask & original_valid_mask
                count = source_mask.sum()
                if count > 0:
                    print(f"   - {source}: {count} fixable date records")
    
    # Final summary
    print("\n=== SUMMARY ===")
    
    issues = []
    
    # Check major issues
    if date_quality['invalid_count'] > 0:
        issues.append(f"{date_quality['invalid_count']} records with invalid dates")
    
    amount_quality = check_field_quality(df['Amount'], 'Amount')
    if amount_quality['zero_count'] > 10:
        issues.append(f"{amount_quality['zero_count']} zero-amount transactions")
    
    if len(df) < 3000:
        issues.append(f"Only {len(df)} total records (expected ~3000+)")
    
    if issues:
        print("❌ CRITICAL ISSUES FOUND:")
        for issue in issues:
            print(f"   - {issue}")
        print("\nYour data pipeline is producing corrupted data that will cause analysis failures.")
    else:
        print("✓ Data quality appears acceptable")
    
    return df

if __name__ == "__main__":
    df = deep_audit()