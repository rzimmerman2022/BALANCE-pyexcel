# diagnostic_baseline.py - Our Phase 1 observability tool
import pandas as pd
from pathlib import Path
from datetime import datetime
import logging

def analyze_current_parquet(parquet_path):
    """
    Analyze the current Parquet file to establish baseline understanding
    """
    print(f"=== BASELINE ANALYSIS: {datetime.now()} ===")
    
    if not Path(parquet_path).exists():
        print(f"❌ Parquet file not found: {parquet_path}")
        return None # Return None if file not found
    
    # Load and analyze the current file
    df = pd.read_parquet(parquet_path)
    
    print(f"📊 Current file stats:")
    print(f"   Rows: {len(df)}")
    print(f"   Columns: {len(df.columns)}")
    print(f"   File size: {Path(parquet_path).stat().st_size / (1024*1024):.2f} MB")
    print(f"   Last modified: {datetime.fromtimestamp(Path(parquet_path).stat().st_mtime)}")
    
    print(f"\n📋 Current column inventory:")
    # Sort columns for consistent output, easier comparison later
    current_columns = sorted(list(df.columns))
    for i, col in enumerate(current_columns, 1):
        print(f"   {i:2d}. {col}")
    
    # Analyze data freshness by looking at date ranges
    date_columns = [col for col in df.columns if 'date' in col.lower() or col.lower() in ['date']]
    if date_columns:
        print(f"\n📅 Date range analysis:")
        for date_col in sorted(date_columns): # Sort for consistency
            try:
                # Attempt to convert to datetime, coercing errors to NaT
                date_series = pd.to_datetime(df[date_col], errors='coerce')
                if not date_series.isna().all(): # Check if there are any valid dates
                    min_date = date_series.min()
                    max_date = date_series.max()
                    print(f"   {date_col}: {min_date.strftime('%Y-%m-%d') if pd.notna(min_date) else 'N/A'} to {max_date.strftime('%Y-%m-%d') if pd.notna(max_date) else 'N/A'}")
                else:
                    print(f"   {date_col}: All values are NaT or unparseable")
            except Exception as e: # Catch any other unexpected errors during date processing
                print(f"   {date_col}: Could not parse dates. Error: {e}")
    
    # Look for signs of multiple processing approaches
    print(f"\n🔍 Signs of processing inconsistency:")
    duplicate_concepts = []
    
    # Check for duplicate date concepts (more refined check)
    # MASTER_SCHEMA_COLUMNS includes: Date, PostDate, DataSourceDate, StatementStart, StatementEnd
    # Let's count how many of these are present and if there are others.
    master_date_cols = {"Date", "PostDate", "DataSourceDate", "StatementStart", "StatementEnd"}
    present_master_date_cols = [col for col in df.columns if col in master_date_cols]
    other_date_like_cols = [
        col for col in df.columns 
        if ('date' in col.lower() or 'post' in col.lower() or 'trans' in col.lower()) 
        and col not in master_date_cols
    ]
    if other_date_like_cols:
        duplicate_concepts.append(f"Unexpected date-like columns found: {other_date_like_cols}. Master date cols present: {present_master_date_cols}")
    
    # Check for duplicate amount concepts
    # MASTER_SCHEMA_COLUMNS includes: Amount, SplitPercent
    master_amount_cols = {"Amount", "SplitPercent"}
    present_master_amount_cols = [col for col in df.columns if col in master_amount_cols]
    other_amount_like_cols = [
        col for col in df.columns 
        if 'amount' in col.lower() 
        and col not in master_amount_cols
    ]
    if other_amount_like_cols:
        duplicate_concepts.append(f"Unexpected amount-like columns found: {other_amount_like_cols}. Master amount cols present: {present_master_amount_cols}")
        
    # Check for duplicate account concepts
    # MASTER_SCHEMA_COLUMNS includes: Account, AccountLast4, AccountType
    master_account_cols = {"Account", "AccountLast4", "AccountType"}
    present_master_account_cols = [col for col in df.columns if col in master_account_cols]
    other_account_like_cols = [
        col for col in df.columns 
        if any(word in col.lower() for word in ['account', 'last4']) 
        and col not in master_account_cols
    ]
    if other_account_like_cols:
        duplicate_concepts.append(f"Unexpected account-like columns found: {other_account_like_cols}. Master account cols present: {present_master_account_cols}")

    for issue in duplicate_concepts:
        print(f"   ⚠️  {issue}")
    
    if not duplicate_concepts:
        print("   ✅ No obvious duplicate concepts (beyond expected master columns) detected.")
    
    return df

# Run the analysis
if __name__ == "__main__":
    # Updated path to match project structure
    parquet_path = "workbook/balance_final.parquet" # Path relative to project root
    
    # Configure logging for pandas if it's chatty (optional)
    # logging.basicConfig(level=logging.INFO)
    # logging.getLogger("pd").setLevel(logging.WARNING) # Example: quiet pandas info/debug

    analyzed_df = analyze_current_parquet(parquet_path)
    if analyzed_df is not None:
        print("\n✅ Baseline analysis script finished.")
    else:
        print("\n❌ Baseline analysis script could not complete due to missing file.")
