# comprehensive_source_diagnostic.py
"""
The Complete Data Source Reality Check
=====================================
This diagnostic tool reveals the truth about what each of your financial data sources
actually contains versus what your schemas expect them to contain.

Think of this as an MRI for your data pipeline - it shows you exactly what's there,
what's missing, and what's broken, with no sugar-coating or false optimism.
"""

import pandas as pd
import os
import glob
import json
from datetime import datetime
from collections import defaultdict
import numpy as np

class DataSourceInspector:
    """
    A thorough inspector that examines each data source to understand:
    1. What columns actually exist in the source files
    2. What data quality issues exist in those columns
    3. How the source data differs from schema expectations
    4. What's realistically possible with each source
    """
    
    def __init__(self, csv_directory, parquet_file='workbook/balance_final.parquet'):
        self.csv_directory = csv_directory
        self.parquet_file = parquet_file
        self.source_analysis = {}
        
    def inspect_csv_file(self, filepath):
        """
        Deeply inspect a single CSV file to understand its true structure and content
        """
        filename = os.path.basename(filepath)
        print(f"\nInspecting: {filename}")
        print("=" * (len(filename) + 11))
        
        try:
            # Try to read the CSV with different encodings if needed
            try:
                df = pd.read_csv(filepath, encoding='utf-8')
            except:
                df = pd.read_csv(filepath, encoding='latin-1')
            
            analysis = {
                'filename': filename,
                'row_count': len(df),
                'columns': list(df.columns),
                'column_analysis': {}
            }
            
            # Analyze each column in detail
            for col in df.columns:
                col_analysis = self.analyze_column(df[col], col)
                analysis['column_analysis'][col] = col_analysis
                
                # Print summary for this column
                completeness = col_analysis['completeness_percent']
                status = "✓" if completeness > 95 else "⚠" if completeness > 50 else "✗"
                
                print(f"  {status} {col}:")
                print(f"     Completeness: {completeness:.1f}%")
                print(f"     Data type: {col_analysis['detected_type']}")
                
                if col_analysis['sample_values']:
                    print(f"     Samples: {col_analysis['sample_values'][:2]}")
                
                if col_analysis.get('date_formats'):
                    print(f"     Date formats found: {col_analysis['date_formats'][:2]}")
                
                if col_analysis.get('issues'):
                    print(f"     ⚠️  Issues: {', '.join(col_analysis['issues'])}")
            
            return analysis
            
        except Exception as e:
            print(f"  ❌ ERROR reading file: {str(e)}")
            return None
    
    def analyze_column(self, series, column_name):
        """
        Perform deep analysis on a single column to understand its content and quality
        """
        total_rows = len(series)
        non_null = series.notna().sum()
        
        # Basic completeness
        analysis = {
            'total_rows': total_rows,
            'non_null_count': non_null,
            'completeness_percent': (non_null / total_rows * 100) if total_rows > 0 else 0,
            'null_count': series.isna().sum()
        }
        
        # Skip further analysis if column is empty
        if non_null == 0:
            analysis['detected_type'] = 'empty'
            analysis['sample_values'] = []
            return analysis
        
        # Get non-null values for analysis
        non_null_values = series.dropna()
        
        # Detect data type and patterns
        if series.dtype == 'object':
            # String column - check for patterns
            analysis['detected_type'] = 'text'
            analysis['unique_count'] = non_null_values.nunique()
            
            # Check if it might be dates stored as strings
            date_patterns = self.detect_date_patterns(non_null_values.head(100))
            if date_patterns:
                analysis['detected_type'] = 'date_as_text'
                analysis['date_formats'] = date_patterns
            
            # Check for placeholder values
            placeholders = ['<NA>', 'nan', 'NaN', 'None', 'null', 'N/A', '#N/A']
            placeholder_count = non_null_values.isin(placeholders).sum()
            if placeholder_count > 0:
                analysis['placeholder_count'] = placeholder_count
                analysis['issues'] = analysis.get('issues', []) + [f'{placeholder_count} placeholder values']
            
            # Sample values
            analysis['sample_values'] = non_null_values.head(5).tolist()
            
        elif np.issubdtype(series.dtype, np.number):
            # Numeric column
            analysis['detected_type'] = 'numeric'
            analysis['min'] = non_null_values.min()
            analysis['max'] = non_null_values.max()
            analysis['mean'] = non_null_values.mean()
            analysis['zero_count'] = (non_null_values == 0).sum()
            
            # Check for suspicious values
            if analysis['zero_count'] > total_rows * 0.1:  # More than 10% zeros
                analysis['issues'] = analysis.get('issues', []) + [f'{analysis["zero_count"]} zero values']
            
        elif pd.api.types.is_datetime64_any_dtype(series):
            # Datetime column
            analysis['detected_type'] = 'datetime'
            analysis['min_date'] = non_null_values.min()
            analysis['max_date'] = non_null_values.max()
            
            # Check for NaT values (pandas might not count these as null)
            nat_count = pd.isna(series).sum()
            if nat_count > 0:
                analysis['nat_count'] = nat_count
                analysis['issues'] = analysis.get('issues', []) + [f'{nat_count} NaT values']
        
        return analysis
    
    def detect_date_patterns(self, sample_values):
        """
        Try to detect date formats in string values
        """
        date_formats = [
            '%Y-%m-%d',
            '%m/%d/%Y',
            '%m/%d/%y',
            '%d/%m/%Y',
            '%Y/%m/%d',
            '%m-%d-%Y',
            '%d-%m-%Y',
            '%B %d, %Y',
            '%b %d, %Y',
            '%Y-%m-%d %H:%M:%S'
        ]
        
        detected_formats = []
        
        for fmt in date_formats:
            success_count = 0
            for value in sample_values[:20]:  # Test first 20 values
                try:
                    if pd.notna(value) and value != '':
                        datetime.strptime(str(value).strip(), fmt)
                        success_count += 1
                except:
                    pass
            
            if success_count >= 10:  # If at least 10 values match
                detected_formats.append((fmt, success_count))
        
        # Sort by success count
        detected_formats.sort(key=lambda x: x[1], reverse=True)
        return [fmt for fmt, _ in detected_formats]
    
    def compare_with_pipeline_output(self):
        """
        Compare what's in the source CSVs with what ended up in the parquet file
        """
        print("\n\n=== COMPARING SOURCE FILES TO PIPELINE OUTPUT ===")
        
        if not os.path.exists(self.parquet_file):
            print(f"❌ Parquet file not found: {self.parquet_file}")
            return
        
        # Load the parquet file
        parquet_df = pd.read_parquet(self.parquet_file)
        
        # Expected columns in the final schema
        expected_columns = [
            'TxnID', 'Date', 'Amount', 'Category', 'Description', 'Account',
            'PostDate', 'ReferenceNumber', 'Institution', 'AccountLast4',
            'StatementStart', 'StatementEnd', 'StatementPeriodDesc', 'OriginalDate',
            'AccountName', 'AccountNumber', 'OriginalStatement', 'Merchant',
            'Owner', 'DataSourceName', 'DataSourceDate', 'AccountType',
            'SharedFlag', 'SplitPercent', 'Currency', 'Tags', 'Extras'
        ]
        
        # Analyze each data source in the parquet file
        for source_name in parquet_df['DataSourceName'].unique():
            print(f"\n{source_name}:")
            source_data = parquet_df[parquet_df['DataSourceName'] == source_name]
            
            # Find critical missing data
            critical_fields = ['Date', 'Amount', 'Description', 'Account', 'Category']
            for field in critical_fields:
                if field in source_data.columns:
                    # Count meaningful values (not null, not placeholder)
                    if source_data[field].dtype == 'object':
                        meaningful = source_data[field].notna() & ~source_data[field].isin(['<NA>', 'nan', 'None', ''])
                    else:
                        meaningful = source_data[field].notna()
                    
                    meaningful_pct = (meaningful.sum() / len(source_data)) * 100
                    
                    if meaningful_pct < 95:
                        status = "✗" if meaningful_pct < 50 else "⚠"
                        print(f"  {status} {field}: {meaningful_pct:.1f}% meaningful data")
    
    def suggest_realistic_schema(self, source_analysis):
        """
        Based on what actually exists in a source file, suggest a realistic schema mapping
        """
        if not source_analysis:
            return None
        
        print("\n  SUGGESTED REALISTIC MAPPING:")
        
        # Common column name variations and their canonical names
        column_mappings = {
            'date': ['Date', 'Transaction Date', 'Trans Date', 'Posted Date', 'date', 'DATE'],
            'amount': ['Amount', 'Debit', 'Credit', 'Transaction Amount', 'amount', 'AMOUNT'],
            'description': ['Description', 'Memo', 'Transaction Description', 'Details', 'description'],
            'category': ['Category', 'Type', 'Transaction Type', 'category'],
            'account': ['Account', 'Account Name', 'Card', 'account'],
            'merchant': ['Merchant', 'Payee', 'Vendor', 'merchant']
        }
        
        found_mappings = {}
        
        # Try to find matches for critical fields
        for canonical_name, variations in column_mappings.items():
            for col in source_analysis['columns']:
                if col in variations or any(var.lower() in col.lower() for var in variations):
                    col_info = source_analysis['column_analysis'].get(col, {})
                    if col_info.get('completeness_percent', 0) > 50:
                        found_mappings[canonical_name] = {
                            'source_column': col,
                            'completeness': col_info.get('completeness_percent', 0),
                            'type': col_info.get('detected_type', 'unknown')
                        }
                        break
        
        # Print findings
        for canonical, info in found_mappings.items():
            print(f"    {canonical} → {info['source_column']} ({info['completeness']:.0f}% complete)")
        
        # Warn about critical missing fields
        missing_critical = set(['date', 'amount', 'description']) - set(found_mappings.keys())
        if missing_critical:
            print(f"    ⚠️  MISSING CRITICAL FIELDS: {', '.join(missing_critical)}")
        
        return found_mappings
    
    def generate_summary_report(self):
        """
        Generate a comprehensive summary of all findings
        """
        print("\n\n" + "="*80)
        print("EXECUTIVE SUMMARY: THE TRUTH ABOUT YOUR DATA SOURCES")
        print("="*80)
        
        print("\nWhat this diagnostic reveals:")
        print("1. Each data source provides DIFFERENT fields - they're not standardized")
        print("2. Your schemas expect fields that don't exist in many sources")
        print("3. The pipeline fills missing fields with nulls, creating phantom data")
        print("4. This is why Power BI shows a 'cluster' of mostly empty columns")
        
        print("\nRECOMMENDED NEXT STEPS:")
        print("1. Accept that different sources provide different data")
        print("2. Create source-specific schemas that only map existing fields")
        print("3. Build a flexible analysis layer that handles missing fields gracefully")
        print("4. Stop trying to force all sources into the same rigid structure")
        
        print("\nThe path forward isn't to extract fields that don't exist.")
        print("It's to work intelligently with the data each source actually provides.")

def main():
    """
    Run the complete diagnostic suite on your financial data sources
    """
    print("COMPREHENSIVE DATA SOURCE REALITY CHECK")
    print("======================================")
    print("This diagnostic will reveal what your data sources ACTUALLY contain")
    print("versus what your schemas are pretending they contain.\n")
    
    # Initialize the inspector
    csv_dir = r"C:\BALANCE\CSVs"
    inspector = DataSourceInspector(csv_dir)
    
    # Find all CSV files
    print(f"Searching for CSV files in: {csv_dir}")
    
    # Look in both the main directory and subdirectories
    csv_patterns = [
        os.path.join(csv_dir, "*.csv"),
        os.path.join(csv_dir, "*", "*.csv"),
        os.path.join(csv_dir, "*", "*", "*.csv")
    ]
    
    all_csv_files = []
    for pattern in csv_patterns:
        all_csv_files.extend(glob.glob(pattern))
    
    print(f"Found {len(all_csv_files)} CSV files to analyze\n")
    
    # Analyze each source file
    for csv_file in all_csv_files:
        analysis = inspector.inspect_csv_file(csv_file)
        if analysis:
            inspector.source_analysis[csv_file] = analysis
            
            # Suggest realistic schema for this source
            inspector.suggest_realistic_schema(analysis)
    
    # Compare with pipeline output
    inspector.compare_with_pipeline_output()
    
    # Generate summary report
    inspector.generate_summary_report()

if __name__ == "__main__":
    main()