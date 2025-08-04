#!/usr/bin/env python3
"""
audit_all_sources.py - Comprehensive Schema Discovery and Analysis Tool

This script analyzes multiple CSV data sources to provide evidence-based 
recommendations for canonical schema definition. It examines column coverage,
data types, completeness, and cross-source patterns to inform schema decisions.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from collections import defaultdict, Counter
import json
import yaml
import sys
from datetime import datetime
import re
from typing import Dict, List, Set, Tuple, Any, Optional

# Configuration
CSV_BASE_PATH = Path(r"C:\BALANCE\BALANCE-pyexcel-repository\CSVs")
RULES_PATH = Path("rules")
OUTPUT_DIR = Path("logs/audit_output")

# The 5 confirmed source files
SOURCE_FILES = [
    CSV_BASE_PATH / "Jordyn" / "Jordyn - Chase Bank - Total Checking x6173 - All.csv",
    CSV_BASE_PATH / "Jordyn" / "Jordyn - Discover - Discover It Card x1544 - CSV.csv",
    CSV_BASE_PATH / "Jordyn" / "Jordyn - Wells Fargo - Active Cash Visa Signature Card x4296 - CSV.csv",
    CSV_BASE_PATH / "Ryan" / "Ryan - Monarch Money - 20250412.csv",
    CSV_BASE_PATH / "Ryan" / "Ryan - Rocket Money - 20250412.csv"
]

# Current canonical columns for reference
CURRENT_MASTER_SCHEMA = [
    "Date", "PostDate", "Merchant", "OriginalDescription", "Category",
    "Amount", "Account", "AccountLast4", "AccountType", "Institution",
    "Owner", "DataSourceName", "OriginalDate", "CustomName", "Notes",
    "ReferenceNumber", "TxnID", "StatementStart", "StatementEnd", 
    "StatementPeriodDesc", "SharedFlag", "SplitPercent", "Currency",
    "Source", "IgnoredFrom", "TaxDeductible", "DataSourceDate", "Tags",
    "Description"
]


class SchemaAuditor:
    """Main class for analyzing CSV sources and deriving schema insights"""
    
    def __init__(self):
        self.source_data = {}  # Store raw DataFrames
        self.schema_rules = {}  # Store loaded YAML rules
        self.column_stats = defaultdict(lambda: {
            'sources': [],
            'total_records': 0,
            'non_null_count': 0,
            'data_types': Counter(),
            'unique_values_sample': set(),
            'original_names': defaultdict(list),  # Map source to original column names
            'mapped_name': None
        })
        self.source_summaries = {}
        
    def load_schema_rules(self):
        """Load all schema YAML files from rules directory"""
        print("\n=== Loading Schema Rules ===")
        
        for yaml_file in RULES_PATH.glob("*.yaml"):
            if yaml_file.name == "schema_registry.yml":
                continue  # Skip the old registry
                
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    rules = yaml.safe_load(f)
                    schema_id = rules.get('id', yaml_file.stem)
                    self.schema_rules[schema_id] = rules
                    print(f"  ✓ Loaded: {schema_id}")
            except Exception as e:
                print(f"  ✗ Error loading {yaml_file}: {e}")
                
    def normalize_header(self, header: str) -> str:
        """Normalize header for comparison (similar to _canon in schema_registry)"""
        # Convert to lowercase, remove non-alphanumeric, collapse whitespace
        normalized = re.sub(r'[^a-z0-9]+', '', header.lower().strip())
        return normalized
        
    def find_schema_for_csv(self, headers: List[str], filepath: Path) -> Optional[Dict]:
        """Find matching schema for given CSV headers"""
        # Normalize input headers
        normalized_headers = {self.normalize_header(h) for h in headers}
        
        best_match = None
        best_score = -1
        
        for schema_id, rules in self.schema_rules.items():
            if schema_id == 'generic_csv':
                continue  # Skip generic for now
                
            signature = rules.get('header_signature', [])
            if not signature:
                continue
                
            # Normalize schema signature
            normalized_signature = {self.normalize_header(h) for h in signature}
            
            # Check if schema signature is subset of CSV headers
            if normalized_signature.issubset(normalized_headers):
                # Calculate match score (more specific signatures score higher)
                score = len(normalized_signature)
                extra_headers = len(normalized_headers - normalized_signature)
                score -= extra_headers * 0.1  # Penalty for extra columns
                
                if score > best_score:
                    best_score = score
                    best_match = rules
                    
        # Fall back to generic if no match
        if best_match is None and 'generic_csv' in self.schema_rules:
            best_match = self.schema_rules['generic_csv']
            
        return best_match
        
    def load_and_analyze_csv(self, filepath: Path) -> Dict[str, Any]:
        """Load a CSV file and perform initial analysis"""
        print(f"\n--- Analyzing: {filepath.name} ---")
        
        # Read CSV with all columns as strings initially
        try:
            df = pd.read_csv(filepath, dtype=str, encoding='utf-8')
        except Exception as e:
            print(f"  ✗ Error reading CSV: {e}")
            return None
            
        print(f"  Shape: {df.shape} ({len(df)} rows, {len(df.columns)} columns)")
        
        # Find matching schema
        headers = df.columns.tolist()
        matched_schema = self.find_schema_for_csv(headers, filepath)
        schema_name = matched_schema.get('id', 'unknown') if matched_schema else 'no_match'
        print(f"  Matched Schema: {schema_name}")
        
        # Store raw data
        source_key = filepath.stem
        self.source_data[source_key] = {
            'filepath': filepath,
            'dataframe': df,
            'matched_schema': matched_schema,
            'schema_name': schema_name,
            'headers': headers
        }
        
        # Analyze each column
        source_analysis = {
            'filepath': str(filepath),
            'total_rows': len(df),
            'schema_applied': schema_name,
            'columns': {},
            'unmapped_columns': [],
            'missing_expected_columns': []
        }
        
        # Get column mapping if schema matched
        column_map = {}
        extras_ignore = []
        if matched_schema:
            column_map = matched_schema.get('column_map', {})
            extras_ignore = matched_schema.get('extras_ignore', [])
            
        # Analyze each column in the CSV
        for col in df.columns:
            # Calculate statistics
            non_null = df[col].notna().sum()
            null_count = df[col].isna().sum()
            completeness = (non_null / len(df) * 100) if len(df) > 0 else 0
            
            # Sample unique values (limit to prevent memory issues)
            unique_vals = df[col].dropna().unique()
            sample_size = min(10, len(unique_vals))
            unique_sample = list(unique_vals[:sample_size])
            
            # Infer data types from non-null values
            type_counts = Counter()
            for val in df[col].dropna().sample(min(100, non_null)) if non_null > 0 else []:
                if pd.isna(val):
                    continue
                val_str = str(val).strip()
                
                # Try to infer type
                if val_str.lower() in ['true', 'false', '1', '0']:
                    type_counts['boolean'] += 1
                elif re.match(r'^-?\d+$', val_str):
                    type_counts['integer'] += 1
                elif re.match(r'^-?\d*\.\d+$', val_str):
                    type_counts['float'] += 1
                elif re.match(r'^\d{4}-\d{2}-\d{2}', val_str) or re.match(r'^\d{1,2}/\d{1,2}/\d{2,4}', val_str):
                    type_counts['date'] += 1
                else:
                    type_counts['string'] += 1
                    
            # Determine canonical name (mapped name or original)
            canonical_name = column_map.get(col, col)
            
            # Store column analysis
            source_analysis['columns'][col] = {
                'original_name': col,
                'mapped_name': canonical_name if col in column_map else None,
                'non_null_count': int(non_null),
                'null_count': int(null_count),
                'completeness_pct': round(completeness, 2),
                'unique_count': len(unique_vals),
                'unique_sample': unique_sample,
                'inferred_types': dict(type_counts),
                'is_mapped': col in column_map,
                'is_ignored': col in extras_ignore
            }
            
            # Update global column statistics
            self.column_stats[canonical_name]['sources'].append(source_key)
            self.column_stats[canonical_name]['total_records'] += len(df)
            self.column_stats[canonical_name]['non_null_count'] += non_null
            self.column_stats[canonical_name]['data_types'].update(type_counts)
            self.column_stats[canonical_name]['original_names'][source_key].append(col)
            self.column_stats[canonical_name]['unique_values_sample'].update(unique_sample[:5])
            
            # Track unmapped columns
            if col not in column_map and col not in extras_ignore:
                source_analysis['unmapped_columns'].append(col)
                
        # Check for missing expected columns (in schema but not in CSV)
        if matched_schema:
            for expected_col in column_map.keys():
                if expected_col not in df.columns:
                    source_analysis['missing_expected_columns'].append(expected_col)
                    
        self.source_summaries[source_key] = source_analysis
        return source_analysis
        
    def generate_canonical_recommendations(self) -> Dict[str, List[str]]:
        """Analyze global column statistics to recommend canonical schema"""
        recommendations = {
            'required_columns': [],      # >90% populated across sources
            'optional_columns': [],      # Valuable but source-specific
            'removal_candidates': [],    # <5% populated
            'derived_only': [],         # Not in raw data, only derived
            'mapping_gaps': []          # Present but unmapped
        }
        
        # Analyze each unique column concept
        for col_name, stats in self.column_stats.items():
            total_possible = stats['total_records']
            if total_possible == 0:
                continue
                
            overall_completeness = (stats['non_null_count'] / total_possible * 100)
            num_sources = len(stats['sources'])
            
            # Categorize based on coverage
            if overall_completeness >= 90 and num_sources >= 3:
                recommendations['required_columns'].append({
                    'name': col_name,
                    'completeness': round(overall_completeness, 1),
                    'sources': stats['sources'],
                    'primary_type': stats['data_types'].most_common(1)[0][0] if stats['data_types'] else 'unknown'
                })
            elif overall_completeness >= 50 or (overall_completeness >= 80 and num_sources >= 1):
                recommendations['optional_columns'].append({
                    'name': col_name,
                    'completeness': round(overall_completeness, 1),
                    'sources': stats['sources'],
                    'primary_type': stats['data_types'].most_common(1)[0][0] if stats['data_types'] else 'unknown'
                })
            elif overall_completeness < 5:
                recommendations['removal_candidates'].append({
                    'name': col_name,
                    'completeness': round(overall_completeness, 1),
                    'sources': stats['sources'],
                    'reason': 'Low overall population'
                })
                
            # Check if it's a derived-only column (in master schema but not in any raw data)
            if col_name in CURRENT_MASTER_SCHEMA and stats['non_null_count'] == 0:
                recommendations['derived_only'].append(col_name)
                
        return recommendations
        
    def generate_report(self):
        """Generate comprehensive audit report"""
        print("\n" + "="*80)
        print("COMPREHENSIVE SCHEMA AUDIT REPORT")
        print("="*80)
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Analyzed {len(self.source_data)} source files")
        
        # Section 1: Column Coverage Analysis
        print("\n\n=== SECTION 1: COLUMN COVERAGE ANALYSIS ===")
        
        # Sort columns by overall completeness
        sorted_columns = sorted(
            self.column_stats.items(),
            key=lambda x: x[1]['non_null_count'] / max(x[1]['total_records'], 1),
            reverse=True
        )
        
        print("\nColumn Coverage Summary (sorted by completeness):")
        print("-" * 120)
        print(f"{'Canonical Name':<30} {'Sources':<10} {'Overall %':<10} {'Type':<15} {'Original Names':<40}")
        print("-" * 120)
        
        for col_name, stats in sorted_columns[:30]:  # Show top 30
            if stats['total_records'] == 0:
                continue
                
            completeness = (stats['non_null_count'] / stats['total_records'] * 100)
            primary_type = stats['data_types'].most_common(1)[0][0] if stats['data_types'] else 'unknown'
            
            # Get sample of original names
            orig_names = []
            for source, names in stats['original_names'].items():
                for name in names[:1]:  # Just first mapping per source
                    orig_names.append(f"{source.split(' - ')[0]}:{name}")
            orig_names_str = ', '.join(orig_names[:2])  # Show up to 2 examples
            
            print(f"{col_name:<30} {len(stats['sources']):<10} {completeness:<10.1f} {primary_type:<15} {orig_names_str:<40}")
            
        # Section 2: Canonical Schema Recommendations
        print("\n\n=== SECTION 2: CANONICAL SCHEMA RECOMMENDATIONS ===")
        
        recommendations = self.generate_canonical_recommendations()
        
        print("\n--- REQUIRED COLUMNS (Core fields, >90% populated) ---")
        for col in recommendations['required_columns']:
            print(f"  • {col['name']} ({col['completeness']}% complete, type: {col['primary_type']})")
            
        print("\n--- OPTIONAL COLUMNS (Valuable but source-specific) ---")
        for col in recommendations['optional_columns']:
            sources_str = ', '.join([s.split(' - ')[0] for s in col['sources']])
            print(f"  • {col['name']} ({col['completeness']}% complete, sources: {sources_str})")
            
        print("\n--- REMOVAL CANDIDATES (Low population, <5%) ---")
        for col in recommendations['removal_candidates']:
            print(f"  • {col['name']} ({col['completeness']}% complete)")
            
        print("\n--- DERIVED-ONLY COLUMNS (Not in raw data) ---")
        for col in recommendations['derived_only']:
            print(f"  • {col}")
            
        # Section 3: Per-Source Diagnostics
        print("\n\n=== SECTION 3: PER-SOURCE DIAGNOSTICS ===")
        
        for source_key, analysis in self.source_summaries.items():
            print(f"\n--- {source_key} ---")
            print(f"  File: {Path(analysis['filepath']).name}")
            print(f"  Rows: {analysis['total_rows']}")
            print(f"  Schema Applied: {analysis['schema_applied']}")
            print(f"  Total Columns: {len(analysis['columns'])}")
            
            # High completeness columns
            high_complete = [
                (col, info['completeness_pct']) 
                for col, info in analysis['columns'].items() 
                if info['completeness_pct'] >= 90
            ]
            print(f"\n  High Completeness Columns (>90%):")
            for col, pct in sorted(high_complete, key=lambda x: x[1], reverse=True)[:10]:
                print(f"    • {col}: {pct}%")
                
            # Unmapped columns
            if analysis['unmapped_columns']:
                print(f"\n  ⚠️  Unmapped Columns (not in schema):")
                for col in analysis['unmapped_columns'][:10]:
                    print(f"    • {col}")
                    
            # Missing expected columns
            if analysis['missing_expected_columns']:
                print(f"\n  ⚠️  Missing Expected Columns:")
                for col in analysis['missing_expected_columns']:
                    print(f"    • {col}")
                    
        # Section 4: Cross-Source Comparison
        print("\n\n=== SECTION 4: CROSS-SOURCE COLUMN COMPARISON ===")
        
        # Create a matrix of which sources have which canonical columns
        all_canonical_cols = sorted(self.column_stats.keys())
        source_keys = sorted(self.source_data.keys())
        
        print("\nColumn Presence Matrix (✓ = present, ✗ = absent):")
        print("-" * (35 + len(source_keys) * 12))
        
        # Header
        header = "Canonical Column".ljust(35)
        for sk in source_keys:
            header += sk.split(' - ')[0][:10].center(12)
        print(header)
        print("-" * (35 + len(source_keys) * 12))
        
        # Only show columns present in at least one source
        for col in all_canonical_cols[:40]:  # Limit to 40 rows for readability
            if self.column_stats[col]['non_null_count'] == 0:
                continue
                
            row = col[:34].ljust(35)
            for sk in source_keys:
                if sk in self.column_stats[col]['sources']:
                    # Find completeness for this source
                    source_completeness = 0
                    for orig_col, info in self.source_summaries[sk]['columns'].items():
                        if info.get('mapped_name') == col or orig_col == col:
                            source_completeness = info['completeness_pct']
                            break
                    
                    if source_completeness >= 50:
                        row += "✓".center(12)
                    else:
                        row += f"({source_completeness:.0f}%)".center(12)
                else:
                    row += "✗".center(12)
            print(row)
            
        # Save detailed output
        self.save_detailed_output(recommendations)
        
    def save_detailed_output(self, recommendations):
        """Save detailed analysis to files"""
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
        # Save recommendations as YAML
        yaml_output = {
            'canonical_schema_recommendations': {
                'required_columns': [col['name'] for col in recommendations['required_columns']],
                'optional_columns': [col['name'] for col in recommendations['optional_columns']],
                'derived_columns': recommendations['derived_only'],
                'metadata': {
                    'generated': datetime.now().isoformat(),
                    'sources_analyzed': len(self.source_data),
                    'total_records': sum(s['total_rows'] for s in self.source_summaries.values())
                }
            }
        }
        
        with open(OUTPUT_DIR / 'canonical_schema_recommendations.yaml', 'w') as f:
            yaml.dump(yaml_output, f, default_flow_style=False)
            
        # Save detailed column statistics as CSV
        rows = []
        for col_name, stats in self.column_stats.items():
            if stats['total_records'] == 0:
                continue
                
            rows.append({
                'canonical_name': col_name,
                'sources_count': len(stats['sources']),
                'sources': ', '.join(stats['sources']),
                'total_records': stats['total_records'],
                'non_null_count': stats['non_null_count'],
                'completeness_pct': round(stats['non_null_count'] / stats['total_records'] * 100, 2),
                'primary_type': stats['data_types'].most_common(1)[0][0] if stats['data_types'] else 'unknown',
                'in_current_master': col_name in CURRENT_MASTER_SCHEMA
            })
            
        pd.DataFrame(rows).to_csv(OUTPUT_DIR / 'column_statistics.csv', index=False)
        
        # Save per-source summaries as JSON
        with open(OUTPUT_DIR / 'source_summaries.json', 'w') as f:
            json.dump(self.source_summaries, f, indent=2)
            
        print(f"\n\n✓ Detailed outputs saved to: {OUTPUT_DIR.absolute()}")
        
    def run(self):
        """Execute the complete audit process"""
        print("Starting Comprehensive Schema Audit...")
        
        # Load schema rules
        self.load_schema_rules()
        
        # Analyze each source file
        for filepath in SOURCE_FILES:
            if filepath.exists():
                self.load_and_analyze_csv(filepath)
            else:
                print(f"\n⚠️  Warning: File not found: {filepath}")
                
        # Generate and display report
        self.generate_report()


def main():
    """Main entry point"""
    auditor = SchemaAuditor()
    auditor.run()


if __name__ == "__main__":
    main()