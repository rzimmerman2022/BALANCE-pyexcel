#!/usr/bin/env python3
"""
Comprehensive Transaction Data Analyzer
Analyzes ALL columns in financial transaction data to discover cleaning needs
"""

import pandas as pd
import numpy as np
import re
from collections import Counter, defaultdict
from pathlib import Path
import json
from typing import Dict, List, Set, Any
from datetime import datetime

class ComprehensiveAnalyzer:
    def __init__(self, parquet_path: str):
        """Initialize analyzer with your parquet file"""
        self.df = pd.read_parquet(parquet_path)
        self.analysis_results = {}
        
    def analyze_all_columns(self):
        """Run analysis on every column in the dataset"""
        print("🔍 Starting Comprehensive Column Analysis...\n")
        print(f"Dataset shape: {self.df.shape[0]} rows × {self.df.shape[1]} columns")
        print(f"Columns found: {list(self.df.columns)}\n")
        
        # Analyze each column based on its type and content
        for col in self.df.columns:
            print(f"{'='*60}")
            print(f"Analyzing column: {col}")
            print(f"{'='*60}")
            
            self.analyze_single_column(col)
            print()
        
        # Analyze relationships between columns
        self.analyze_column_relationships()
        
        # Generate cleaning recommendations
        self.generate_comprehensive_recommendations()
        
        # Save results
        self.save_analysis_results()
    
    def analyze_single_column(self, col_name: str):
        """Analyze a single column comprehensively"""
        col_data = self.df[col_name]
        self.analysis_results[col_name] = {
            'dtype': str(col_data.dtype),
            'null_count': col_data.isna().sum(),
            'null_percentage': (col_data.isna().sum() / len(col_data)) * 100,
            'unique_count': col_data.nunique(),
            'sample_values': []
        }
        
        # Get non-null sample
        non_null_data = col_data.dropna()
        if len(non_null_data) > 0:
            # Take stratified sample - some from top, middle, bottom
            sample_size = min(10, len(non_null_data))
            sample_indices = np.linspace(0, len(non_null_data)-1, sample_size, dtype=int)
            self.analysis_results[col_name]['sample_values'] = [
                str(non_null_data.iloc[i]) for i in sample_indices
            ]
        
        print(f"Data type: {col_data.dtype}")
        print(f"Null values: {self.analysis_results[col_name]['null_count']} ({self.analysis_results[col_name]['null_percentage']:.1f}%)")
        print(f"Unique values: {self.analysis_results[col_name]['unique_count']}")
        
        # Type-specific analysis
        if pd.api.types.is_string_dtype(col_data):
            self.analyze_text_column(col_name, col_data)
        elif pd.api.types.is_numeric_dtype(col_data):
            self.analyze_numeric_column(col_name, col_data)
        elif pd.api.types.is_datetime64_any_dtype(col_data):
            self.analyze_datetime_column(col_name, col_data)
        elif pd.api.types.is_bool_dtype(col_data):
            self.analyze_boolean_column(col_name, col_data)
    
    def analyze_text_column(self, col_name: str, col_data: pd.Series):
        """Deep analysis for text columns"""
        non_null_data = col_data.dropna().astype(str)
        if len(non_null_data) == 0:
            return
        
        # Length statistics
        lengths = non_null_data.str.len()
        self.analysis_results[col_name]['length_stats'] = {
            'min': int(lengths.min()),
            'max': int(lengths.max()),
            'mean': float(lengths.mean()),
            'median': float(lengths.median()),
            'std': float(lengths.std())
        }
        
        print(f"\nLength statistics:")
        print(f"  Min: {lengths.min()}, Max: {lengths.max()}, Mean: {lengths.mean():.1f}")
        
        # Pattern detection
        patterns_found = {}
        
        # Check for common patterns
        pattern_checks = {
            'has_numbers': r'\d+',
            'has_dates': r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            'has_amounts': r'\$[\d,]+\.?\d*',
            'has_all_caps': lambda x: x.isupper() if len(x) > 3 else False,
            'has_email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            'has_phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            'has_transaction_id': r'[A-Z0-9]{8,}',
            'has_reference_num': r'REF\s*\d+',
            'has_store_num': r'#\d{3,}|Store\s*\d+',
            'starts_with_pos': lambda x: x.upper().startswith('POS'),
            'starts_with_ach': lambda x: x.upper().startswith('ACH'),
            'starts_with_online': lambda x: x.upper().startswith('ONLINE'),
        }
        
        for pattern_name, pattern in pattern_checks.items():
            if callable(pattern):
                count = non_null_data.apply(pattern).sum()
            else:
                count = non_null_data.str.contains(pattern, regex=True, na=False).sum()
            if count > 0:
                patterns_found[pattern_name] = count
                percentage = (count / len(non_null_data)) * 100
                print(f"  {pattern_name}: {count} ({percentage:.1f}%)")
        
        self.analysis_results[col_name]['patterns'] = patterns_found
        
        # Common prefixes/suffixes
        if len(non_null_data) > 100:
            # Prefixes (first 2-4 words)
            prefix_counter = Counter()
            for text in non_null_data.sample(min(1000, len(non_null_data))):
                words = text.split()[:3]
                for i in range(1, min(4, len(words) + 1)):
                    prefix = ' '.join(words[:i])
                    if len(prefix) > 2:  # Skip very short prefixes
                        prefix_counter[prefix] += 1
            
            common_prefixes = [
                (prefix, count) for prefix, count in prefix_counter.most_common(10)
                if count > len(non_null_data) * 0.01  # More than 1%
            ]
            
            if common_prefixes:
                self.analysis_results[col_name]['common_prefixes'] = common_prefixes
                print(f"\nCommon prefixes:")
                for prefix, count in common_prefixes[:5]:
                    print(f"  '{prefix}': {count}")
        
        # Sample values
        print(f"\nSample values:")
        for val in self.analysis_results[col_name]['sample_values'][:5]:
            print(f"  '{val}'")
    
    def analyze_numeric_column(self, col_name: str, col_data: pd.Series):
        """Analysis for numeric columns"""
        non_null_data = col_data.dropna()
        if len(non_null_data) == 0:
            return
        
        stats = {
            'min': float(non_null_data.min()),
            'max': float(non_null_data.max()),
            'mean': float(non_null_data.mean()),
            'median': float(non_null_data.median()),
            'std': float(non_null_data.std()),
            'negative_count': int((non_null_data < 0).sum()),
            'zero_count': int((non_null_data == 0).sum()),
            'positive_count': int((non_null_data > 0).sum())
        }
        
        self.analysis_results[col_name]['numeric_stats'] = stats
        
        print(f"\nNumeric statistics:")
        print(f"  Range: {stats['min']:.2f} to {stats['max']:.2f}")
        print(f"  Mean: {stats['mean']:.2f}, Median: {stats['median']:.2f}")
        print(f"  Negative: {stats['negative_count']}, Zero: {stats['zero_count']}, Positive: {stats['positive_count']}")
    
    def analyze_datetime_column(self, col_name: str, col_data: pd.Series):
        """Analysis for datetime columns"""
        non_null_data = col_data.dropna()
        if len(non_null_data) == 0:
            return
        
        date_stats = {
            'earliest': str(non_null_data.min()),
            'latest': str(non_null_data.max()),
            'date_range_days': (non_null_data.max() - non_null_data.min()).days
        }
        
        self.analysis_results[col_name]['date_stats'] = date_stats
        
        print(f"\nDate statistics:")
        print(f"  Range: {date_stats['earliest']} to {date_stats['latest']}")
        print(f"  Span: {date_stats['date_range_days']} days")
    
    def analyze_boolean_column(self, col_name: str, col_data: pd.Series):
        """Analysis for boolean columns"""
        value_counts = col_data.value_counts(dropna=False)
        self.analysis_results[col_name]['value_counts'] = value_counts.to_dict()
        
        print(f"\nBoolean distribution:")
        for val, count in value_counts.items():
            percentage = (count / len(col_data)) * 100
            print(f"  {val}: {count} ({percentage:.1f}%)")
    
    def analyze_column_relationships(self):
        """Analyze relationships between columns"""
        print(f"\n{'='*60}")
        print("ANALYZING COLUMN RELATIONSHIPS")
        print(f"{'='*60}\n")
        
        relationships = {}
        
        # Check Description vs OriginalDescription
        if 'Description' in self.df.columns and 'OriginalDescription' in self.df.columns:
            same_count = (self.df['Description'] == self.df['OriginalDescription']).sum()
            relationships['description_unchanged'] = {
                'count': same_count,
                'percentage': (same_count / len(self.df)) * 100
            }
            print(f"Description == OriginalDescription: {same_count} ({relationships['description_unchanged']['percentage']:.1f}%)")
        
        # Check if OriginalMerchant exists
        if 'OriginalMerchant' in self.df.columns:
            print(f"OriginalMerchant column exists")
            # Check relationship with Merchant
            if 'Merchant' in self.df.columns:
                same_merchant = (self.df['OriginalMerchant'] == self.df['Merchant']).sum()
                print(f"OriginalMerchant == Merchant: {same_merchant} ({(same_merchant/len(self.df))*100:.1f}%)")
        else:
            print("OriginalMerchant column is MISSING - this needs to be created!")
        
        self.analysis_results['relationships'] = relationships
    
    def generate_comprehensive_recommendations(self):
        """Generate specific recommendations based on analysis"""
        print(f"\n{'='*60}")
        print("CLEANING RECOMMENDATIONS")
        print(f"{'='*60}\n")
        
        recommendations = {
            'missing_columns': [],
            'columns_needing_cleaning': {},
            'new_columns_to_derive': []
        }
        
        # Check for missing intermediate columns
        if 'OriginalMerchant' not in self.df.columns:
            recommendations['missing_columns'].append('OriginalMerchant')
            recommendations['new_columns_to_derive'].append({
                'name': 'OriginalMerchant',
                'source': 'OriginalDescription',
                'method': 'Extract merchant with light cleaning (preserve location/ID info)'
            })
        
        # Check each column for cleaning needs
        for col_name, analysis in self.analysis_results.items():
            if col_name in ['Description', 'Merchant', 'OriginalDescription']:
                continue  # Skip already analyzed columns
            
            if 'patterns' in analysis:
                # Text column - check if it needs cleaning
                patterns = analysis['patterns']
                if any(key in patterns for key in ['has_transaction_id', 'has_reference_num', 'starts_with_pos']):
                    recommendations['columns_needing_cleaning'][col_name] = {
                        'reason': 'Contains transaction IDs, reference numbers, or bank prefixes',
                        'patterns_found': patterns
                    }
        
        self.analysis_results['recommendations'] = recommendations
        
        # Print recommendations
        if recommendations['missing_columns']:
            print("MISSING COLUMNS THAT NEED TO BE CREATED:")
            for col in recommendations['missing_columns']:
                print(f"  - {col}")
        
        if recommendations['new_columns_to_derive']:
            print("\nNEW COLUMNS TO DERIVE:")
            for col_info in recommendations['new_columns_to_derive']:
                print(f"  - {col_info['name']}: {col_info['method']}")
        
        if recommendations['columns_needing_cleaning']:
            print("\nCOLUMNS THAT NEED CLEANING:")
            for col, info in recommendations['columns_needing_cleaning'].items():
                print(f"  - {col}: {info['reason']}")
    
    def save_analysis_results(self):
        """Save analysis results to files"""
        output_dir = Path('comprehensive_analysis_results')
        output_dir.mkdir(exist_ok=True)
        
        # Save detailed analysis
        with open(output_dir / 'full_column_analysis.json', 'w') as f:
            json.dump(self.analysis_results, f, indent=2, default=str)
        
        # Generate summary report
        with open(output_dir / 'analysis_summary.txt', 'w') as f:
            f.write("COMPREHENSIVE TRANSACTION DATA ANALYSIS\n")
            f.write("="*60 + "\n\n")
            f.write(f"Total Rows: {len(self.df)}\n")
            f.write(f"Total Columns: {len(self.df.columns)}\n")
            f.write(f"Date Range: {self.df['Date'].min()} to {self.df['Date'].max()}\n\n")
            
            f.write("COLUMNS ANALYZED:\n")
            for col in self.df.columns:
                f.write(f"  - {col} ({self.analysis_results[col]['dtype']})\n")
            
            if 'recommendations' in self.analysis_results:
                f.write("\n\nKEY RECOMMENDATIONS:\n")
                recs = self.analysis_results['recommendations']
                if recs['missing_columns']:
                    f.write("\nMissing columns to create:\n")
                    for col in recs['missing_columns']:
                        f.write(f"  - {col}\n")
        
        print(f"\n✅ Analysis complete! Results saved to {output_dir}/")


# Main execution
if __name__ == "__main__":
    # Path to your parquet file
    PARQUET_PATH = r"C:\BALANCE\output\financial_data_flexible.parquet"
    
    # Run comprehensive analysis
    analyzer = ComprehensiveAnalyzer(PARQUET_PATH)
    analyzer.analyze_all_columns()