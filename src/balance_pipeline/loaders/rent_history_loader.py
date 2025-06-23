"""
Rent History CSV loader.
Handles pivot table format that needs to be melted:
,January 2024 Budgeted,January 2024 Actual,February 2024 Budgeted,February 2024 Actual,...
Tax Base Rent - Residential,"$1,946.00",$778.40,"$1,946.00",$836.78,...
Tax Garage - Residential,$100.00,$40.00,$100.00,$43.00,...
[more rows]

Melts this into tall format with separate transactions.
"""

import pandas as pd
import pathlib
import re
from ..column_utils import normalize_cols


def find_latest_rent_history_file(data_dir: pathlib.Path) -> pathlib.Path:
    """Find the latest Rent_History_*.csv file in data_dir."""
    pattern = "Rent_History_*.csv"
    files = list(data_dir.glob(pattern))
    if not files:
        raise FileNotFoundError(f"No files matching {pattern} found in {data_dir}")
    # Return the latest by filename (lexicographic sort)
    return sorted(files)[-1]


def parse_month_year_from_column(col_name: str) -> str:
    """
    Extract month-year from column names like 'January 2024 Actual' -> 'Jan-24'
    """
    # Look for month name and year
    month_match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)', col_name, re.IGNORECASE)
    year_match = re.search(r'20\d{2}', col_name)
    
    if month_match and year_match:
        month_name = month_match.group(1)
        year = year_match.group(0)
        
        # Convert to short format
        month_abbrev = {
            'January': 'Jan', 'February': 'Feb', 'March': 'Mar',
            'April': 'Apr', 'May': 'May', 'June': 'Jun',
            'July': 'Jul', 'August': 'Aug', 'September': 'Sep',
            'October': 'Oct', 'November': 'Nov', 'December': 'Dec'
        }.get(month_name, month_name[:3])
        
        return f"{month_abbrev}-{year[2:]}"
    
    return col_name  # Fallback


def load_rent_history(data_dir: pathlib.Path) -> pd.DataFrame:
    """
    Load Rent History CSV and melt pivot table into tall format.
    
    Args:
        data_dir: Directory containing Rent_History_*.csv
        
    Returns:
        CTS-compliant DataFrame with melted rent history data
    """
    try:
        rent_file = find_latest_rent_history_file(data_dir)
    except FileNotFoundError:
        return pd.DataFrame()
    
    try:
        # Load the rent history CSV
        df = pd.read_csv(rent_file, index_col=0)
        
        if df.empty:
            return pd.DataFrame()
        
        # Remove completely empty rows and columns
        df = df.dropna(how='all').dropna(axis=1, how='all')
        
        if df.empty:
            return pd.DataFrame()
        
        rent_transactions = []
        
        # Process each column (month/type combination)
        for col_name in df.columns:
            if pd.isna(col_name) or str(col_name).strip() == '':
                continue
            
            # Parse the month-year from column name
            month_date = parse_month_year_from_column(str(col_name))
            
            # Determine if this is budgeted or actual
            is_actual = 'actual' in str(col_name).lower()
            transaction_type = 'Actual' if is_actual else 'Budgeted'
            
            # Process each row (rent component)
            for row_name, value in df[col_name].items():
                if pd.isna(value) or pd.isna(row_name):
                    continue
                
                # Skip summary rows
                if any(skip_word in str(row_name).lower() for skip_word in ['total', 'less', 'net']):
                    continue
                
                # Create transaction record
                transaction = {
                    'date': month_date,
                    'person': 'Ryan',  # Rent history typically tracks Ryan's perspective
                    'merchant': 'Rent',
                    'description': f"{transaction_type}: {row_name}",
                    'actual_amount': value if is_actual else 0,
                    'allowed_amount': value if not is_actual else 0,
                    'source_file': 'Rent_History'
                }
                rent_transactions.append(transaction)
        
        if not rent_transactions:
            return pd.DataFrame()
        
        # Create DataFrame from transactions
        rent_df = pd.DataFrame(rent_transactions)
        
        # Apply CTS normalization
        return normalize_cols(rent_df, 'Rent_History')
        
    except Exception as e:
        print(f"Warning: Failed to parse rent history {rent_file}: {e}")
        return pd.DataFrame()
