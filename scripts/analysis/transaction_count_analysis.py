"""
Detailed Transaction Count Analysis
Let's trace exactly what happens to every transaction at each filtering step
"""

from datetime import datetime

import pandas as pd


def clean_currency_string(value):
    """Convert currency strings like '$1,946.00 ' to float"""
    if pd.isna(value) or value == '':
        return 0.0
    
    # Convert to string and clean
    str_val = str(value).strip()
    
    # Skip header values
    if 'Amount' in str_val:
        return 0.0
    
    # Handle negative values in parentheses like '($9.23)'
    is_negative = False
    if str_val.startswith('(') and str_val.endswith(')'):
        is_negative = True
        str_val = str_val[1:-1]  # Remove parentheses
    
    # Remove dollar signs, commas, and spaces
    cleaned = str_val.replace('$', '').replace(',', '').replace(' ', '')
    
    # Handle special cases like '$ -   '
    if cleaned == '-' or cleaned == '':
        return 0.0
    
    try:
        result = float(cleaned)
        return -result if is_negative else result
    except ValueError:
        print(f"Warning: Could not convert '{value}' to float, using 0.0")
        return 0.0

def analyze_expense_data_step_by_step():
    """Analyze expense data with detailed step-by-step filtering"""
    print("=" * 80)
    print("DETAILED EXPENSE DATA ANALYSIS")
    print("=" * 80)
    
    file_path = "data/Consolidated_Expense_History_20250622.csv"
    
    # Step 1: Load raw data
    print("\nSTEP 1: Loading raw data")
    try:
        df = pd.read_csv(file_path)
        print(f"Raw CSV loaded: {len(df)} rows")
        print(f"Columns: {list(df.columns)}")
        
        # Look at first few rows
        print("\nFirst 5 rows:")
        print(df.head())
        
        # Check unique names in raw data
        print(f"\nUnique names in raw data: {df['Name'].value_counts()}")
        
    except Exception as e:
        print(f"Error loading data: {e}")
        return None
    
    # Step 2: Remove header rows
    print("\nSTEP 2: Removing header rows")
    before_header_filter = len(df)
    df = df[df['Name'].notna() & ~df['Name'].str.contains('Name', na=False)]
    print(f"After removing header rows: {len(df)} rows (removed {before_header_filter - len(df)})")
    
    # Step 3: Clean names and filter to Ryan/Jordyn
    print("\nSTEP 3: Filtering to Ryan/Jordyn")
    df['Name'] = df['Name'].str.strip()
    df.loc[df['Name'].str.contains('Jordyn', case=False, na=False), 'Name'] = 'Jordyn'
    df.loc[df['Name'].str.contains('Ryan', case=False, na=False), 'Name'] = 'Ryan'
    
    print(f"After name cleaning: {df['Name'].value_counts()}")
    
    before_person_filter = len(df)
    df = df[df['Name'].isin(['Ryan', 'Jordyn'])]
    print(f"After filtering to Ryan/Jordyn: {len(df)} rows (removed {before_person_filter - len(df)})")
    
    # Step 4: Date filtering
    print("\nSTEP 4: Date analysis and filtering")
    df['Date of Purchase'] = pd.to_datetime(df['Date of Purchase'], errors='coerce')
    
    # Check date range
    valid_dates = df[df['Date of Purchase'].notna()]
    if len(valid_dates) > 0:
        print(f"Date range: {valid_dates['Date of Purchase'].min()} to {valid_dates['Date of Purchase'].max()}")
        
        # Count by year
        valid_dates['Year'] = valid_dates['Date of Purchase'].dt.year
        print(f"Transactions by year:\n{valid_dates['Year'].value_counts().sort_index()}")
    
    # Filter to 2024+
    cutoff_date = datetime(2024, 1, 1)
    before_date_filter = len(df)
    df_2024 = df[df['Date of Purchase'] >= cutoff_date]
    print(f"After filtering to 2024+: {len(df_2024)} rows (removed {before_date_filter - len(df_2024)})")
    
    # Step 5: Check for amount filtering
    print("\nSTEP 5: Amount analysis")
    
    # Clean column names first
    df_2024.columns = df_2024.columns.str.strip()
    print(f"Cleaned columns: {list(df_2024.columns)}")
    
    df_2024['Actual Amount'] = df_2024['Actual Amount'].apply(clean_currency_string)
    df_2024['Allowed Amount'] = df_2024['Allowed Amount'].apply(clean_currency_string)
    
    # Check for zero amounts
    zero_actual = df_2024[df_2024['Actual Amount'] == 0]
    zero_allowed = df_2024[df_2024['Allowed Amount'] == 0]
    print(f"Transactions with zero actual amount: {len(zero_actual)}")
    print(f"Transactions with zero allowed amount: {len(zero_allowed)}")
    
    # Check for any other filtering that might be happening
    print(f"\nFinal 2024+ expense transactions: {len(df_2024)}")
    print(f"By person: \n{df_2024['Name'].value_counts()}")
    
    return df_2024

def analyze_rent_data_step_by_step():
    """Analyze rent data with detailed step-by-step filtering"""
    print("\n" + "=" * 80)
    print("DETAILED RENT DATA ANALYSIS")
    print("=" * 80)
    
    file_path = "data/Consolidated_Rent_Allocation_20250527.csv"
    
    # Step 1: Load raw data
    print("\nSTEP 1: Loading raw rent data")
    try:
        df = pd.read_csv(file_path)
        print(f"Raw rent CSV loaded: {len(df)} rows")
        print(f"Columns: {list(df.columns)}")
        
        # Look at all rows
        print("\nAll rent data:")
        print(df.to_string())
        
    except Exception as e:
        print(f"Error loading rent data: {e}")
        return None
    
    # Step 2: Process dates
    print("\nSTEP 2: Date processing")
    
    # The rent file has 'Month' column, not 'Date'
    # Convert Month (e.g., 'Jan-24') to actual dates
    month_to_date = []
    for month_str in df['Month']:
        try:
            # Parse formats like 'Jan-24' to January 1, 2024
            month_part, year_part = month_str.split('-')
            year = 2000 + int(year_part)  # Convert '24' to 2024
            
            month_mapping = {
                'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
            }
            month = month_mapping.get(month_part, 1)
            date = datetime(year, month, 1)
            month_to_date.append(date)
        except:
            month_to_date.append(None)
    
    df['Date'] = month_to_date
    print(f"Converted {len([d for d in month_to_date if d is not None])} month strings to dates")
    
    valid_dates = df[df['Date'].notna()]
    if len(valid_dates) > 0:
        print(f"Date range: {valid_dates['Date'].min()} to {valid_dates['Date'].max()}")
        
        # Count by year
        valid_dates['Year'] = valid_dates['Date'].dt.year
        print(f"Rent transactions by year:\n{valid_dates['Year'].value_counts().sort_index()}")
    
    # Filter to 2024+
    cutoff_date = datetime(2024, 1, 1)
    before_date_filter = len(df)
    df_2024 = df[df['Date'] >= cutoff_date]
    print(f"After filtering to 2024+: {len(df_2024)} rows (removed {before_date_filter - len(df_2024)})")
    
    # Each rent row generates 2 transactions (Ryan pays, Jordyn owes)
    print(f"Total rent transactions generated (2 per row): {len(df_2024) * 2}")
    
    return df_2024

def main():
    """Run the complete analysis"""
    print("COMPREHENSIVE TRANSACTION COUNT ANALYSIS")
    print("This will trace every step of our filtering process")
    
    expense_df = analyze_expense_data_step_by_step()
    rent_df = analyze_rent_data_step_by_step()
    
    print("\n" + "=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)
    
    if expense_df is not None:
        print(f"Final expense transactions (2024+): {len(expense_df)}")
    
    if rent_df is not None:
        print(f"Final rent rows (2024+): {len(rent_df)}")
        print(f"Final rent transactions (2024+): {len(rent_df) * 2}")
    
    if expense_df is not None and rent_df is not None:
        total = len(expense_df) + (len(rent_df) * 2)
        print(f"TOTAL TRANSACTIONS: {total}")
        
        # Compare to our expected 1,206
        print("Expected from our system: 1,206")
        print(f"Difference: {total - 1206}")

if __name__ == "__main__":
    main()
