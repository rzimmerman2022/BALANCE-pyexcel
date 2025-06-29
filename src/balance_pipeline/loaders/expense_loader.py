"""
Expense History CSV loader.
Handles multi-section format with repeating headers like:
"September 9th, 2023 - September 24th, 2023"
Name,Date of Purchase,Account,Merchant, Actual Amount , Allowed Amount , Description
[data rows]
[blank lines]
"February 5th, 2024 - March 11th, 2024"
Name,Date of Purchase,Account,Merchant, Actual Amount , Allowed Amount , Description
[data rows]
"""

import pandas as pd
import pathlib
from io import StringIO
from typing import List
from ..column_utils import normalize_cols


def find_latest_expense_file(data_dir: pathlib.Path) -> pathlib.Path:
    """Find the latest Expense_History_*.csv file in data_dir."""
    pattern = "Expense_History_*.csv"
    files = list(data_dir.glob(pattern))
    if not files:
        raise FileNotFoundError(f"No files matching {pattern} found in {data_dir}")
    # Return the latest by filename (lexicographic sort)
    return sorted(files)[-1]


def load_expense_history(data_dir: pathlib.Path) -> pd.DataFrame:
    """
    Load Expense History CSV with multi-section format.
    
    Args:
        data_dir: Directory containing Expense_History_*.csv
        
    Returns:
        CTS-compliant DataFrame
    """
    try:
        expense_file = find_latest_expense_file(data_dir)
    except FileNotFoundError:
        return pd.DataFrame()
    
    # Read all lines
    with open(expense_file, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    # Find all header lines (contain "Date of Purchase")
    header_indices = [
        i for i, line in enumerate(lines) 
        if 'Date of Purchase' in line
    ]
    
    if not header_indices:
        return pd.DataFrame()
    
    data_blocks = []
    
    # Process each section
    for i, header_index in enumerate(header_indices):
        start_index = header_index
        # End is either the next header or end of file
        end_index = header_indices[i + 1] if i + 1 < len(header_indices) else len(lines)
        
        # Extract lines for this block
        block_lines = lines[start_index:end_index]
        
        # Skip if no data rows (only header + empty lines)
        if not any(line.strip() for line in block_lines[1:]):
            continue
        
        # Parse this block as CSV
        try:
            block_io = StringIO("".join(block_lines))
            df_block = pd.read_csv(block_io)
            
            # Skip empty blocks
            if df_block.empty:
                continue
                
            data_blocks.append(df_block)
            
        except Exception as e:
            # Log warning but continue with other blocks
            print(f"Warning: Failed to parse expense block starting at line {start_index}: {e}")
            continue
    
    if not data_blocks:
        return pd.DataFrame()
    
    # Concatenate all blocks
    combined_df = pd.concat(data_blocks, ignore_index=True)
    
    # Remove completely empty rows
    combined_df = combined_df.dropna(how='all')
    
    # Apply CTS normalization
    return normalize_cols(combined_df, 'Expense_History')
