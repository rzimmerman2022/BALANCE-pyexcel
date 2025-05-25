"""
CSV Structure Analyzer for BALANCE Pipeline
===========================================

This script will show you exactly what data structure you have in all your CSV files,
so we can stop making assumptions and build something that actually works for YOUR data.

It will:
1. Find all CSV files in your directory structure
2. Show the headers/columns for each
3. Display sample data (first 5 rows)
4. Identify data types and patterns
5. Create a comprehensive report
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
from datetime import datetime
import re
from typing import Dict, List, Any


class NumpyJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles numpy and pandas types"""
    def default(self, obj):
        # Handle numpy integer types
        if isinstance(obj, (np.integer, np.int64, np.int32, np.int16, np.int8)):
            return int(obj)
        
        # Handle numpy floating point types
        elif isinstance(obj, (np.floating, np.float64, np.float32, np.float16)):
            return float(obj)
        
        # Handle numpy arrays
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        
        # Handle numpy booleans
        elif isinstance(obj, (np.bool_, np.bool8)):
            return bool(obj)
        
        # Handle pandas timestamps
        elif isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        
        # Handle datetime objects
        elif isinstance(obj, datetime):
            return obj.isoformat()
        
        # Handle Path objects
        elif isinstance(obj, Path):
            return str(obj)
        
        # Let the base class handle other types
        return super().default(obj)


def convert_to_json_serializable(obj):
    """Recursively convert numpy/pandas types to JSON serializable types"""
    if isinstance(obj, dict):
        return {k: convert_to_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_json_serializable(item) for item in obj]
    elif isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, (np.bool_, np.bool8)):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif pd.isna(obj):
        return None
    else:
        return obj


def analyze_csv_structure(csv_path: Path) -> Dict[str, Any]:
    """
    Thoroughly analyze a single CSV file's structure and content.
    """
    print(f"\n{'='*80}")
    print(f"Analyzing: {csv_path}")
    print(f"{'='*80}")
    
    analysis = {
        "file_path": str(csv_path),
        "file_name": csv_path.name,
        "file_size": int(csv_path.stat().st_size),  # Convert to regular int
        "owner": "Unknown",
        "source_type": "Unknown"
    }
    
    # Infer owner from path
    path_str = str(csv_path).lower()
    if "ryan" in path_str:
        analysis["owner"] = "Ryan"
    elif "jordyn" in path_str:
        analysis["owner"] = "Jordyn"
    
    # Infer source type from filename
    filename_lower = csv_path.name.lower()
    if "rocket" in filename_lower:
        analysis["source_type"] = "Rocket Money"
    elif "monarch" in filename_lower:
        analysis["source_type"] = "Monarch Money"
    elif "wells" in filename_lower:
        analysis["source_type"] = "Wells Fargo"
    elif "chase" in filename_lower:
        analysis["source_type"] = "Chase"
    elif "discover" in filename_lower:
        analysis["source_type"] = "Discover"
    
    try:
        # Read the CSV
        df = pd.read_csv(csv_path, nrows=None)  # Read all rows first
        
        analysis["total_rows"] = int(len(df))  # Ensure it's a regular int
        analysis["columns"] = list(df.columns)
        analysis["column_count"] = int(len(df.columns))  # Ensure it's a regular int
        
        # Analyze each column
        column_analysis = {}
        
        for col in df.columns:
            col_info = {
                "dtype": str(df[col].dtype),
                "non_null_count": int(df[col].notna().sum()),  # Convert to regular int
                "null_count": int(df[col].isna().sum()),  # Convert to regular int
                "unique_count": int(df[col].nunique()),  # Convert to regular int
                "sample_values": []
            }
            
            # Get sample values (up to 5 unique non-null values)
            non_null_values = df[col].dropna()
            if len(non_null_values) > 0:
                unique_values = non_null_values.unique()
                sample_size = min(5, len(unique_values))
                col_info["sample_values"] = [str(v) for v in unique_values[:sample_size]]
            
            # Check if it might be a date column
            if "date" in col.lower() or df[col].dtype == 'object':
                # Try to parse as date to see if it works
                try:
                    test_dates = pd.to_datetime(df[col].dropna().head(10), errors='coerce')
                    if test_dates.notna().sum() > 5:  # Most parsed successfully
                        col_info["likely_date"] = True
                        # Determine date format
                        sample_date_str = str(non_null_values.iloc[0]) if len(non_null_values) > 0 else ""
                        if "/" in sample_date_str:
                            if len(sample_date_str.split("/")[2]) == 4:
                                col_info["date_format_guess"] = "MM/DD/YYYY or DD/MM/YYYY"
                            else:
                                col_info["date_format_guess"] = "MM/DD/YY or DD/MM/YY"
                        elif "-" in sample_date_str:
                            col_info["date_format_guess"] = "YYYY-MM-DD or similar"
                except:
                    pass
            
            # Check if it might be an amount column
            if "amount" in col.lower() or "balance" in col.lower() or any(
                keyword in col.lower() for keyword in ["debit", "credit", "payment", "deposit"]
            ):
                col_info["likely_amount"] = True
                # Check for currency symbols
                if df[col].dtype == 'object' and len(non_null_values) > 0:
                    sample_str = str(non_null_values.iloc[0])
                    if "$" in sample_str:
                        col_info["has_currency_symbol"] = True
                    if "(" in sample_str and ")" in sample_str:
                        col_info["parentheses_for_negative"] = True
            
            # Check if it might be a description/merchant column
            if any(keyword in col.lower() for keyword in ["description", "merchant", "payee", "name", "statement"]):
                col_info["likely_description"] = True
                # Calculate average length
                if df[col].dtype == 'object' and len(non_null_values) > 0:
                    avg_length = non_null_values.astype(str).str.len().mean()
                    col_info["avg_length"] = round(float(avg_length), 1)  # Convert to regular float
            
            column_analysis[col] = col_info
        
        analysis["column_analysis"] = column_analysis
        
        # Get first 5 rows as sample data
        sample_df = df.head(5).copy()
        
        # Convert to dict for JSON serialization
        sample_data = []
        for idx, row in sample_df.iterrows():
            row_dict = {}
            for col in sample_df.columns:
                val = row[col]
                # Convert numpy/pandas types to Python native types
                if pd.isna(val):
                    row_dict[col] = None
                elif isinstance(val, (np.integer, np.floating)):
                    row_dict[col] = float(val) if isinstance(val, np.floating) else int(val)
                else:
                    row_dict[col] = str(val)
            sample_data.append(row_dict)
        
        analysis["sample_rows"] = sample_data
        
        # Additional pattern detection
        patterns = detect_patterns(df)
        analysis["patterns"] = patterns
        
    except Exception as e:
        analysis["error"] = str(e)
        print(f"ERROR reading {csv_path}: {e}")
    
    return analysis


def detect_patterns(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Detect patterns in the data that might be important for processing.
    """
    patterns = {}
    
    # Check for potential duplicate columns (similar names)
    columns_lower = [col.lower().strip() for col in df.columns]
    potential_duplicates = []
    
    for i, col1 in enumerate(columns_lower):
        for j, col2 in enumerate(columns_lower[i+1:], i+1):
            # Check if columns are very similar
            if col1 in col2 or col2 in col1:
                potential_duplicates.append((df.columns[i], df.columns[j]))
    
    if potential_duplicates:
        patterns["potential_duplicate_columns"] = potential_duplicates
    
    # Check for amount sign patterns
    amount_columns = [col for col in df.columns if "amount" in col.lower()]
    for col in amount_columns:
        if df[col].dtype in ['float64', 'int64']:
            neg_count = int((df[col] < 0).sum())  # Convert to regular int
            pos_count = int((df[col] > 0).sum())  # Convert to regular int
            if neg_count > 0 and pos_count > 0:
                patterns[f"{col}_has_mixed_signs"] = {
                    "negative_count": neg_count,
                    "positive_count": pos_count
                }
            elif pos_count > 0 and neg_count == 0:
                patterns[f"{col}_all_positive"] = True
            elif neg_count > 0 and pos_count == 0:
                patterns[f"{col}_all_negative"] = True
    
    return patterns


def create_summary_report(all_analyses: List[Dict[str, Any]]) -> None:
    """
    Create a summary report of all CSV files analyzed.
    """
    print("\n" + "="*80)
    print("SUMMARY REPORT")
    print("="*80)
    
    # Group by owner
    by_owner = {}
    for analysis in all_analyses:
        owner = analysis["owner"]
        if owner not in by_owner:
            by_owner[owner] = []
        by_owner[owner].append(analysis)
    
    for owner, files in by_owner.items():
        print(f"\n{owner}'s Files ({len(files)} files):")
        print("-" * 40)
        
        for analysis in files:
            print(f"\n  File: {analysis['file_name']}")
            print(f"  Source Type: {analysis['source_type']}")
            print(f"  Rows: {analysis.get('total_rows', 'ERROR')}")
            print(f"  Columns: {analysis.get('column_count', 'ERROR')}")
            
            if "columns" in analysis:
                print(f"  Column Names:")
                for col in analysis["columns"]:
                    print(f"    - {col}")
            
            if "patterns" in analysis:
                print(f"  Detected Patterns:")
                for pattern, value in analysis["patterns"].items():
                    print(f"    - {pattern}: {value}")
    
    # Find common columns across files
    print("\n" + "="*80)
    print("COLUMN COMMONALITY ANALYSIS")
    print("="*80)
    
    all_columns = {}
    for analysis in all_analyses:
        if "columns" in analysis:
            for col in analysis["columns"]:
                if col not in all_columns:
                    all_columns[col] = []
                all_columns[col].append(analysis["file_name"])
    
    # Show columns that appear in multiple files
    print("\nColumns appearing in multiple files:")
    for col, files in sorted(all_columns.items()):
        if len(files) > 1:
            print(f"  '{col}' appears in: {', '.join(files)}")
    
    # Show unique columns per file type
    print("\nUnique columns per source type:")
    by_source = {}
    for analysis in all_analyses:
        source = analysis["source_type"]
        if source not in by_source:
            by_source[source] = set()
        if "columns" in analysis:
            by_source[source].update(analysis["columns"])
    
    for source, columns in by_source.items():
        unique_cols = columns.copy()
        for other_source, other_cols in by_source.items():
            if other_source != source:
                unique_cols -= other_cols
        if unique_cols:
            print(f"\n  {source} unique columns:")
            for col in sorted(unique_cols):
                print(f"    - {col}")


def save_detailed_analysis(all_analyses: List[Dict[str, Any]], output_path: Path) -> None:
    """
    Save the detailed analysis to a JSON file for further review.
    """
    # Convert all analyses to ensure JSON serializability
    cleaned_analyses = convert_to_json_serializable(all_analyses)
    
    output_data = {
        "analysis_timestamp": datetime.now().isoformat(),
        "total_files_analyzed": len(cleaned_analyses),
        "files": cleaned_analyses
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False, cls=NumpyJSONEncoder)
    
    print(f"\nDetailed analysis saved to: {output_path}")


def main():
    """
    Main function to analyze all CSV files in the directory structure.
    """
    # Configure the base directory
    csv_directory = Path(r"C:\BALANCE\CSVs")  # Update this path as needed
    
    if not csv_directory.exists():
        print(f"ERROR: Directory not found: {csv_directory}")
        print("Please update the csv_directory path in the script.")
        return
    
    print(f"Scanning for CSV files in: {csv_directory}")
    
    # Find all CSV files
    csv_files = list(csv_directory.rglob("*.csv"))
    
    if not csv_files:
        print("No CSV files found!")
        return
    
    print(f"Found {len(csv_files)} CSV files to analyze")
    
    # Analyze each file
    all_analyses = []
    
    for csv_file in sorted(csv_files):
        analysis = analyze_csv_structure(csv_file)
        all_analyses.append(analysis)
        
        # Print sample data for immediate review
        if "sample_rows" in analysis and analysis["sample_rows"]:
            print(f"\nFirst few rows of data:")
            print("-" * 40)
            
            # Print in a nice table format
            sample_df = pd.DataFrame(analysis["sample_rows"])
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', None)
            pd.set_option('display.max_colwidth', 50)
            print(sample_df.to_string(index=False))
    
    # Create summary report
    create_summary_report(all_analyses)
    
    # Save detailed analysis
    output_path = csv_directory.parent / "csv_structure_analysis.json"
    save_detailed_analysis(all_analyses, output_path)
    
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    print(f"\nThe detailed analysis has been saved to: {output_path}")
    print("You can share this file to show the exact structure of your CSV files.")


if __name__ == "__main__":
    main()