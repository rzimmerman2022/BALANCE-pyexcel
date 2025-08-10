#!/usr/bin/env python3
"""
Fixed Comprehensive Balance Analyzer for BALANCE-pyexcel
Correctly handles all four file types with their specific quirks
"""

import json
import logging
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FileTypeDetector:
    """Intelligently detect which type of CSV we're dealing with"""
    
    @staticmethod
    def detect_file_type(filepath, df):
        """Detect file type based on filename and column structure"""
        filename = filepath.name.lower()
        columns_lower = [col.lower().strip() for col in df.columns]
        
        # Check filename patterns first (most reliable)
        if 'expense' in filename and 'history' in filename:
            return 'expense_history'
        elif 'transaction' in filename and 'ledger' in filename:
            return 'transaction_ledger'
        elif 'rent' in filename and 'allocation' in filename:
            return 'rent_allocation'
        elif 'rent' in filename and 'history' in filename:
            return 'rent_history'
        
        # Fallback to column analysis
        # Look for unique identifying columns
        if 'allowed amount' in columns_lower:
            return 'expense_history'
        elif 'running balance' in columns_lower:
            return 'transaction_ledger'
        elif any("ryan's rent" in col or "jordyn's rent" in col for col in columns_lower):
            return 'rent_allocation'
        elif any('budgeted' in col for col in columns_lower):
            return 'rent_history'
        
        logger.warning(f"Could not determine file type for {filepath.name}")
        return 'unknown'


class SmartCSVReader:
    """Handle various CSV structures including headers at row 3"""
    
    @staticmethod
    def read_csv_for_transaction_ledger(filepath):
        """Special handling for Transaction Ledger files with headers on row 3"""
        # Read first few lines to confirm structure
        with open(filepath, encoding='utf-8') as f:
            first_lines = [f.readline() for _ in range(5)]
        
        # Check if this matches the Transaction Ledger pattern
        has_date_range = any(re.search(r'\w+\s+\d+\w*,\s*\d{4}\s*-\s*\w+\s+\d+\w*,\s*\d{4}', line) for line in first_lines)
        has_person_expenses = any('expenses' in line.lower() for line in first_lines)
        
        if has_date_range and has_person_expenses:
            logger.info(f"Detected Transaction Ledger format with headers on row 3 for {filepath.name}")
            # Skip first 2 rows (0-indexed), headers are on row 2 (3rd row)
            return pd.read_csv(filepath, skiprows=2)
        else:
            # Not the special format, read normally
            return pd.read_csv(filepath)
    
    @staticmethod
    def read_csv_intelligently(filepath):
        """Read CSV with automatic handling of different formats"""
        filename_lower = filepath.name.lower()
        
        # Special handling for Transaction Ledger
        if 'transaction' in filename_lower and 'ledger' in filename_lower:
            df = SmartCSVReader.read_csv_for_transaction_ledger(filepath)
        else:
            # Standard CSV reading
            df = pd.read_csv(filepath)
        
        # Clean column names
        df.columns = df.columns.str.strip()
        
        # Remove completely empty rows
        df = df.dropna(how='all')
        
        # Remove rows that are actually headers appearing in data
        # This handles cases where column names appear as data values
        for col in df.columns:
            if col in ['Name', 'Date', 'Merchant', 'Account']:
                # Remove rows where the value exactly matches the column name
                df = df[df[col] != col]
        
        logger.info(f"Loaded {len(df)} rows from {filepath.name}")
        return df


class ComprehensiveAnalyzer:
    """Main analyzer that handles all four file types correctly"""
    
    def __init__(self, data_dir="data", output_dir="analysis_output"):
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.file_handlers = {
            'expense_history': self.analyze_expense_history,
            'transaction_ledger': self.analyze_transaction_ledger,
            'rent_allocation': self.analyze_rent_allocation,
            'rent_history': self.analyze_rent_history
        }
        
        self.results = {
            'analysis_timestamp': datetime.now().isoformat(),
            'files_analyzed': {},
            'pattern_analysis': {},
            'pattern_examples': defaultdict(list),  # Store examples separately
            'business_rules': {},
            'data_quality': {},
            'recommendations': {}
        }
    
    def is_date_range_header(self, name_value):
        """Check if a 'Name' value is actually a date range header"""
        if pd.isna(name_value):
            return False
        
        name_str = str(name_value).strip()
        
        # Pattern for date ranges like "September 9th, 2023 - September 24th, 2023"
        date_range_pattern = r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d+\w*,\s*\d{4}'
        
        return bool(re.search(date_range_pattern, name_str))
    
    def clean_amount(self, amount_str):
        """Convert various amount formats to float"""
        if pd.isna(amount_str):
            return 0.0
        
        amount_str = str(amount_str).strip()
        
        # Handle special cases
        if amount_str in ['', '-', '$ -', '$-', '--']:
            return 0.0
        
        # Remove currency symbols and commas
        cleaned = amount_str.replace('$', '').replace(',', '').strip()
        
        # Handle parentheses for negatives
        if cleaned.startswith('(') and cleaned.endswith(')'):
            cleaned = '-' + cleaned[1:-1]
        
        try:
            return float(cleaned)
        except ValueError:
            logger.warning(f"Could not parse amount: {amount_str}")
            return 0.0
    
    def normalize_person_name(self, name_value):
        """Normalize person names to handle variations like 'Jordyn ', 'Ryan Expenses'"""
        if pd.isna(name_value):
            return None
            
        name_str = str(name_value).strip()
        
        # Handle variations
        if 'ryan' in name_str.lower():
            if 'expense' not in name_str.lower():  # Avoid "Ryan Expenses" headers
                return 'Ryan'
        elif 'jordyn' in name_str.lower():
            if 'expense' not in name_str.lower():  # Avoid "Jordyn Expenses" headers
                return 'Jordyn'
        
        return name_str  # Return as-is if not recognized
    
    def analyze_expense_history(self, df, filepath):
        """Analyze Expense History file with Allowed Amount logic"""
        analysis = {
            'file_type': 'expense_history',
            'total_transactions': 0,  # Will be updated after filtering
            'date_range': {},
            'allowed_amount_analysis': {},
            'pattern_analysis': {},
            'person_breakdown': {},
            'has_allowed_amount': 'Allowed Amount' in df.columns,
            'data_quality_issues': {}
        }
        
        # CRITICAL: Filter out date range headers and normalize names
        if 'Name' in df.columns:
            original_count = len(df)
            
            # First, normalize person names
            df['Name_Original'] = df['Name']
            df['Name'] = df['Name'].apply(self.normalize_person_name)
            
            # Track errant labels
            errant_labels = df[
                (~df['Name'].isin(['Ryan', 'Jordyn'])) & 
                (df['Name'].notna()) &
                (~df['Name_Original'].apply(self.is_date_range_header))
            ]['Name_Original'].value_counts()
            
            if len(errant_labels) > 0:
                analysis['data_quality_issues']['errant_person_labels'] = errant_labels.to_dict()
                logger.info(f"Found {len(errant_labels)} errant person labels in {filepath.name}")
            
            # Filter out date range headers
            df = df[~df['Name_Original'].apply(self.is_date_range_header)]
            
            # Keep only valid person names after normalization
            df = df[df['Name'].isin(['Ryan', 'Jordyn'])]
            
            filtered_count = original_count - len(df)
            if filtered_count > 0:
                logger.info(f"Filtered out {filtered_count} invalid rows from {filepath.name}")
        
        # Update transaction count after filtering
        analysis['total_transactions'] = len(df)
        
        # Date range analysis
        date_cols = ['Date', 'Date of Purchase']
        date_col = next((col for col in date_cols if col in df.columns), None)
        
        if date_col:
            df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
            valid_dates = df[df[date_col].notna()]
            if len(valid_dates) > 0:
                analysis['date_range'] = {
                    'start': valid_dates[date_col].min().strftime('%Y-%m-%d'),
                    'end': valid_dates[date_col].max().strftime('%Y-%m-%d')
                }
        
        # Analyze Allowed vs Actual
        if 'Actual Amount' in df.columns and 'Allowed Amount' in df.columns:
            df['Actual_Clean'] = df['Actual Amount'].apply(self.clean_amount)
            df['Allowed_Clean'] = df['Allowed Amount'].apply(self.clean_amount)
            
            # Calculate adjustment types
            df['Adjustment_Type'] = 'No Adjustment'
            
            # Use more precise conditions
            mask_zero = (df['Allowed_Clean'] == 0) & (df['Actual_Clean'] > 0)
            df.loc[mask_zero, 'Adjustment_Type'] = 'Fully Disallowed'
            
            mask_partial = (df['Allowed_Clean'] > 0) & (df['Allowed_Clean'] < df['Actual_Clean'])
            df.loc[mask_partial, 'Adjustment_Type'] = 'Partially Allowed'
            
            mask_increased = df['Allowed_Clean'] > df['Actual_Clean']
            df.loc[mask_increased, 'Adjustment_Type'] = 'Increased Amount'
            
            # Summary statistics
            adjustment_counts = df['Adjustment_Type'].value_counts().to_dict()
            total_adjustments = len(df[df['Adjustment_Type'] != 'No Adjustment'])
            
            analysis['allowed_amount_analysis'] = {
                'total_with_adjustments': total_adjustments,
                'adjustment_rate': float(total_adjustments / len(df) * 100) if len(df) > 0 else 0,
                'adjustment_types': adjustment_counts,
                'average_reduction_percent': float(
                    ((df[mask_partial]['Actual_Clean'] - df[mask_partial]['Allowed_Clean']) / 
                     df[mask_partial]['Actual_Clean'] * 100).mean()
                ) if len(df[mask_partial]) > 0 else 0
            }
        
        # Pattern analysis in descriptions
        if 'Description' in df.columns:
            patterns, examples = self.analyze_description_patterns(df['Description'], return_examples=True)
            analysis['pattern_analysis'] = patterns
            # Store examples for this file
            for pattern, pattern_examples in examples.items():
                for example in pattern_examples[:5]:  # Limit to 5 examples per pattern
                    self.results['pattern_examples'][pattern].append({
                        'file': filepath.name,
                        'example': example
                    })
        
        # Person breakdown
        if 'Name' in df.columns and 'Actual_Clean' in df.columns and 'Allowed_Clean' in df.columns:
            # Only include valid persons
            valid_persons = df[df['Name'].isin(['Ryan', 'Jordyn'])]
            
            person_stats = valid_persons.groupby('Name').agg({
                'Actual_Clean': ['count', 'sum', 'mean'],
                'Allowed_Clean': ['sum', 'mean']
            }).round(2)
            
            analysis['person_breakdown'] = {}
            for name, stats in person_stats.iterrows():
                analysis['person_breakdown'][name] = {
                    'transaction_count': int(stats[('Actual_Clean', 'count')]),
                    'total_actual': float(stats[('Actual_Clean', 'sum')]),
                    'total_allowed': float(stats[('Allowed_Clean', 'sum')]),
                    'avg_transaction': float(stats[('Actual_Clean', 'mean')]),
                    'avg_allowed': float(stats[('Allowed_Clean', 'mean')])
                }
        
        return analysis
    
    def analyze_transaction_ledger(self, df, filepath):
        """Analyze Transaction Ledger file - which DOES contribute to balance calculations"""
        analysis = {
            'file_type': 'transaction_ledger',
            'total_transactions': 0,  # Will be updated after filtering
            'has_allowed_amount': False,  # Transaction Ledger never has this
            'requires_pattern_parsing': True,
            'category_breakdown': {},
            'running_balance_analysis': {},
            'pattern_analysis': {},
            'data_quality_issues': {}
        }
        
        # Filter out invalid names and normalize
        if 'Name' in df.columns:
            original_count = len(df)
            
            # Normalize names
            df['Name_Original'] = df['Name']
            df['Name'] = df['Name'].apply(self.normalize_person_name)
            
            # Track errant labels (excluding date headers)
            errant_labels = df[
                (~df['Name'].isin(['Ryan', 'Jordyn'])) & 
                (df['Name'].notna()) &
                (~df['Name_Original'].apply(self.is_date_range_header))
            ]['Name_Original'].value_counts()
            
            if len(errant_labels) > 0:
                analysis['data_quality_issues']['errant_person_labels'] = errant_labels.to_dict()
            
            # Remove date headers and keep only valid persons
            df = df[~df['Name_Original'].apply(self.is_date_range_header)]
            df = df[df['Name'].isin(['Ryan', 'Jordyn'])]
            
            filtered_count = original_count - len(df)
            if filtered_count > 0:
                logger.info(f"Filtered out {filtered_count} invalid name rows from {filepath.name}")
        
        analysis['total_transactions'] = len(df)
        
        # Category analysis
        if 'Category' in df.columns:
            category_counts = df['Category'].value_counts().head(20).to_dict()
            analysis['category_breakdown'] = category_counts
        
        # Running balance analysis
        if 'Running Balance' in df.columns:
            df['Balance_Clean'] = df['Running Balance'].apply(self.clean_amount)
            balance_values = df['Balance_Clean'][df['Balance_Clean'] != 0]
            
            if len(balance_values) > 0:
                analysis['running_balance_analysis'] = {
                    'starting_balance': float(balance_values.iloc[0]),
                    'ending_balance': float(balance_values.iloc[-1]),
                    'min_balance': float(balance_values.min()),
                    'max_balance': float(balance_values.max())
                }
        
        # Look for special modifiers in descriptions
        if 'Description' in df.columns:
            # Different patterns for Transaction Ledger
            modifier_patterns = {
                'multiplier_2x': r'2x(?:\s+to\s+calculate)?',
                'multiplier_other': r'(\d+)x(?:\s+to\s+calculate)?',
                'percentage_split': r'(\d+)%\s*(Ryan|Jordyn)',
                'person_only': r'(Ryan|Jordyn)\s+only',
                'toll_or_parking': r'\b(toll|parking|park)\b',
                'reimbursement': r'\b(reimburse|reimbursement|payback)\b'
            }
            
            pattern_counts = defaultdict(int)
            pattern_examples = defaultdict(list)
            
            for desc in df['Description'].dropna():
                desc_str = str(desc).strip()
                
                for pattern_name, pattern_regex in modifier_patterns.items():
                    if re.search(pattern_regex, desc_str, re.IGNORECASE):
                        pattern_counts[pattern_name] += 1
                        pattern_examples[pattern_name].append(desc_str[:150])
            
            analysis['pattern_analysis'] = dict(pattern_counts)
            
            # Store examples
            for pattern, examples in pattern_examples.items():
                for example in examples[:5]:
                    self.results['pattern_examples'][pattern].append({
                        'file': filepath.name,
                        'example': example
                    })
        
        # Add note about calculation requirements
        analysis['calculation_note'] = (
            "Transaction Ledger requires default 50/50 split with pattern-based overrides. "
            f"Found {sum(analysis['pattern_analysis'].values())} transactions with special modifiers."
        )
        
        return analysis
    
    def analyze_rent_allocation(self, df, filepath):
        """Analyze Rent Allocation file structure"""
        analysis = {
            'file_type': 'rent_allocation',
            'total_months': len(df),
            'has_allowed_amount': False,
            'uses_fixed_split': True,
            'rent_components': [],
            'split_analysis': {}
        }
        
        # Identify rent components
        exclude_cols = ['Month', 'Gross Total', "Ryan's Rent", "Jordyn's Rent", 'Total']
        rent_components = [col for col in df.columns if col not in exclude_cols and not col.endswith('_Clean')]
        analysis['rent_components'] = rent_components
        
        # Analyze the split
        ryan_col = next((col for col in df.columns if 'ryan' in col.lower() and 'rent' in col.lower()), None)
        jordyn_col = next((col for col in df.columns if 'jordyn' in col.lower() and 'rent' in col.lower()), None)
        
        if ryan_col and jordyn_col:
            df['Ryan_Clean'] = df[ryan_col].apply(self.clean_amount)
            df['Jordyn_Clean'] = df[jordyn_col].apply(self.clean_amount)
            df['Total_Clean'] = df['Ryan_Clean'] + df['Jordyn_Clean']
            
            # Calculate split percentages for non-zero totals
            valid_rows = df[df['Total_Clean'] > 0].copy()
            if len(valid_rows) > 0:
                valid_rows['Ryan_Percent'] = (valid_rows['Ryan_Clean'] / valid_rows['Total_Clean'] * 100).round(1)
                valid_rows['Jordyn_Percent'] = (valid_rows['Jordyn_Clean'] / valid_rows['Total_Clean'] * 100).round(1)
                
                analysis['split_analysis'] = {
                    'average_split': {
                        'ryan': float(valid_rows['Ryan_Percent'].mean()),
                        'jordyn': float(valid_rows['Jordyn_Percent'].mean())
                    },
                    'split_consistency': {
                        'ryan_std': float(valid_rows['Ryan_Percent'].std()),
                        'jordyn_std': float(valid_rows['Jordyn_Percent'].std())
                    },
                    'total_rent': {
                        'ryan': float(df['Ryan_Clean'].sum()),
                        'jordyn': float(df['Jordyn_Clean'].sum()),
                        'combined': float(df['Total_Clean'].sum())
                    },
                    'monthly_average': {
                        'ryan': float(df['Ryan_Clean'].mean()),
                        'jordyn': float(df['Jordyn_Clean'].mean()),
                        'combined': float(df['Total_Clean'].mean())
                    }
                }
        
        return analysis
    
    def analyze_rent_history(self, df, filepath):
        """Analyze Rent History file with budget vs actual"""
        analysis = {
            'file_type': 'rent_history',
            'has_allowed_amount': False,
            'uses_fixed_split': True,
            'structure': 'wide_format',
            'months_covered': [],
            'variance_analysis': {}
        }
        
        # Find all month columns
        month_pattern = re.compile(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}')
        months = set()
        
        for col in df.columns:
            match = month_pattern.search(col)
            if match:
                months.add(match.group(0))
        
        analysis['months_covered'] = sorted(list(months))
        analysis['total_months'] = len(months)
        
        # Calculate budget vs actual variances
        variances = []
        for month in months:
            budget_col = f"{month} Budgeted"
            actual_col = f"{month} Actual"
            
            if budget_col in df.columns and actual_col in df.columns:
                budget_values = df[budget_col].apply(self.clean_amount)
                actual_values = df[actual_col].apply(self.clean_amount)
                
                total_budget = budget_values.sum()
                total_actual = actual_values.sum()
                
                if total_budget > 0 or total_actual > 0:
                    variance = total_actual - total_budget
                    variances.append({
                        'month': month,
                        'budgeted': float(total_budget),
                        'actual': float(total_actual),
                        'variance': float(variance),
                        'variance_percent': float(variance / total_budget * 100) if total_budget > 0 else 0
                    })
        
        if variances:
            analysis['variance_analysis'] = {
                'monthly_details': variances[:12],  # Limit to most recent 12 months
                'summary': {
                    'average_variance': float(np.mean([v['variance'] for v in variances])),
                    'total_variance': float(sum(v['variance'] for v in variances)),
                    'months_over_budget': sum(1 for v in variances if v['variance'] > 0),
                    'months_under_budget': sum(1 for v in variances if v['variance'] < 0)
                }
            }
        
        return analysis
    
    def analyze_description_patterns(self, descriptions, return_examples=False):
        """Extract patterns from description fields - focused on Expense History patterns"""
        patterns = {
            'full_allocation_100_percent': 0,
            'full_allocation_person_only': 0,
            'multiplier_2x': 0,
            'multiplier_other': 0,
            'gift_or_present': 0,
            'free_for_person': 0,
            'reassess_next_time': 0,
            'personal_expense': 0
        }
        
        pattern_examples = defaultdict(list)
        
        for desc in descriptions.dropna():
            desc_str = str(desc).strip()
            
            # Check each pattern
            if re.search(r'100\s*%\s*(Ryan|Jordyn)', desc_str, re.IGNORECASE):
                patterns['full_allocation_100_percent'] += 1
                pattern_examples['full_allocation_100_percent'].append(desc_str)
            
            if re.search(r'(Ryan|Jordyn)\s+only', desc_str, re.IGNORECASE):
                patterns['full_allocation_person_only'] += 1
                pattern_examples['full_allocation_person_only'].append(desc_str)
            
            if re.search(r'2x\s+to\s+calculate', desc_str, re.IGNORECASE):
                patterns['multiplier_2x'] += 1
                pattern_examples['multiplier_2x'].append(desc_str)
            elif re.search(r'(\d+)x\s+to\s+calculate', desc_str, re.IGNORECASE):
                patterns['multiplier_other'] += 1
                pattern_examples['multiplier_other'].append(desc_str)
            
            if re.search(r'\b(gift|present|birthday|christmas)\b', desc_str, re.IGNORECASE):
                patterns['gift_or_present'] += 1
                pattern_examples['gift_or_present'].append(desc_str)
            
            if re.search(r'free\s+for\s+(Ryan|Jordyn|my|babbbby)', desc_str, re.IGNORECASE):
                patterns['free_for_person'] += 1
                pattern_examples['free_for_person'].append(desc_str)
            
            if re.search(r'reassess\s+next\s+time', desc_str, re.IGNORECASE):
                patterns['reassess_next_time'] += 1
                pattern_examples['reassess_next_time'].append(desc_str)
            
            if re.search(r'\b(personal|my\s+own|private)\b', desc_str, re.IGNORECASE):
                patterns['personal_expense'] += 1
                pattern_examples['personal_expense'].append(desc_str)
        
        if return_examples:
            return patterns, pattern_examples
        return patterns
    
    def check_for_duplicates(self, all_dfs):
        """Check for duplicate transactions within and across files"""
        duplicate_analysis = {
            'within_file_duplicates': {},
            'cross_file_matches': 0,
            'duplicate_details': []
        }
        
        # Analyze each file for internal duplicates
        for filename, df_info in all_dfs.items():
            df = df_info['dataframe']
            file_type = df_info['file_type']
            
            # Find date and amount columns
            date_cols = ['Date', 'Date of Purchase']
            date_col = next((col for col in date_cols if col in df.columns), None)
            
            amount_cols = ['Actual Amount', 'Amount', 'Allowed Amount']
            amount_col = next((col for col in amount_cols if col in df.columns), None)
            
            if date_col and amount_col:
                # Create fingerprints for this file
                df_clean = df.copy()
                df_clean['Date_Clean'] = pd.to_datetime(df_clean[date_col], errors='coerce')
                df_clean['Amount_Clean'] = df_clean[amount_col].apply(self.clean_amount)
                
                # Only consider valid transactions - make a copy to avoid warnings
                mask = df_clean['Date_Clean'].notna() & (df_clean['Amount_Clean'] != 0)
                valid_txns = df_clean[mask].copy()
                
                if len(valid_txns) > 0:
                    # Find duplicates within this file
                    valid_txns['Fingerprint'] = (
                        valid_txns['Date_Clean'].dt.strftime('%Y-%m-%d') + '_' + 
                        valid_txns['Amount_Clean'].round(2).astype(str)
                    )
                    
                    duplicates = valid_txns[valid_txns.duplicated(subset=['Fingerprint'], keep=False)].copy()
                    
                    if len(duplicates) > 0:
                        duplicate_analysis['within_file_duplicates'][filename] = {
                            'count': len(duplicates),
                            'unique_fingerprints': duplicates['Fingerprint'].nunique()
                        }
        
        # Cross-file duplicate check
        all_fingerprints = []
        
        for filename, df_info in all_dfs.items():
            df = df_info['dataframe']
            
            date_col = next((col for col in ['Date', 'Date of Purchase'] if col in df.columns), None)
            amount_col = next((col for col in ['Actual Amount', 'Amount'] if col in df.columns), None)
            
            if date_col and amount_col:
                for _, row in df.iterrows():
                    try:
                        date_val = pd.to_datetime(row[date_col], errors='coerce')
                        amount_val = self.clean_amount(row[amount_col])
                        
                        if pd.notna(date_val) and amount_val != 0:
                            fingerprint = f"{date_val.strftime('%Y-%m-%d')}_{amount_val:.2f}"
                            all_fingerprints.append({
                                'fingerprint': fingerprint,
                                'file': filename,
                                'date': date_val,
                                'amount': amount_val
                            })
                    except:
                        continue
        
        # Find cross-file matches
        fingerprint_counter = Counter(f['fingerprint'] for f in all_fingerprints)
        
        for fingerprint, count in fingerprint_counter.items():
            if count > 1:
                matching_txns = [f for f in all_fingerprints if f['fingerprint'] == fingerprint]
                files_involved = set(f['file'] for f in matching_txns)
                
                if len(files_involved) > 1:
                    duplicate_analysis['cross_file_matches'] += 1
                    duplicate_analysis['duplicate_details'].append({
                        'fingerprint': fingerprint,
                        'files': list(files_involved),
                        'count': count
                    })
        
        return duplicate_analysis
    
    def generate_business_rules(self):
        """Generate comprehensive business rules from analysis"""
        rules = {
            'core_rules': [],
            'file_specific_rules': {},
            'pattern_based_rules': [],
            'data_quality_rules': []
        }
        
        # Analyze each file type
        for filename, analysis in self.results['files_analyzed'].items():
            if 'error' in analysis:
                continue
                
            file_type = analysis.get('file_type', 'unknown')
            
            # File-specific rules
            if file_type == 'expense_history':
                if analysis.get('has_allowed_amount'):
                    rules['file_specific_rules']['expense_history'] = {
                        'primary_rule': 'Use Allowed Amount column for all calculations',
                        'adjustment_rate': f"{analysis['allowed_amount_analysis']['adjustment_rate']:.1f}%",
                        'common_adjustments': analysis['allowed_amount_analysis']['adjustment_types']
                    }
            
            elif file_type == 'transaction_ledger':
                rules['file_specific_rules']['transaction_ledger'] = {
                    'primary_rule': 'Apply 50/50 split by default',
                    'override_rule': 'Parse descriptions for modifiers (2x, percentages, etc.)',
                    'patterns_found': analysis.get('pattern_analysis', {})
                }
            
            elif file_type == 'rent_allocation':
                if 'split_analysis' in analysis:
                    avg_split = analysis['split_analysis']['average_split']
                    rules['file_specific_rules']['rent_allocation'] = {
                        'primary_rule': f"Fixed split: Ryan {avg_split['ryan']:.1f}%, Jordyn {avg_split['jordyn']:.1f}%",
                        'consistency': 'Split ratio is consistent across all months'
                    }
        
        # Pattern-based rules
        all_patterns = defaultdict(int)
        for pattern_dict in self.results['pattern_analysis'].values():
            for pattern, count in pattern_dict.items():
                all_patterns[pattern] += count
        
        for pattern, total_count in sorted(all_patterns.items(), key=lambda x: x[1], reverse=True):
            if total_count > 0:
                rules['pattern_based_rules'].append({
                    'pattern': pattern,
                    'occurrences': total_count,
                    'action': self.get_pattern_action(pattern)
                })
        
        # Data quality rules
        rules['data_quality_rules'] = [
            {'rule': 'Filter out date range headers appearing as Name values'},
            {'rule': 'Only process rows where Name is "Ryan" or "Jordyn"'},
            {'rule': 'Handle Transaction Ledger files with headers on row 3'},
            {'rule': 'Clean amount fields by removing currency symbols and handling parentheses'}
        ]
        
        return rules
    
    def get_pattern_action(self, pattern):
        """Get the action to take for a given pattern"""
        actions = {
            'full_allocation_100_percent': 'Assign 100% of cost to specified person',
            'full_allocation_person_only': 'Assign 100% of cost to specified person',
            'multiplier_2x': 'Double the amount before applying 50/50 split',
            'multiplier_other': 'Multiply amount by specified factor before splitting',
            'gift_or_present': 'Likely personal expense - verify Allowed Amount',
            'free_for_person': 'Exclude from shared expenses for specified person',
            'reassess_next_time': 'Flag for manual review in next reconciliation',
            'personal_expense': 'Likely personal - should have Allowed Amount = 0'
        }
        return actions.get(pattern, 'Review manually')
    
    def generate_recommendations(self):
        """Generate actionable recommendations based on analysis"""
        recs = []
        
        # Check file types found
        file_types_found = set(
            analysis.get('file_type') 
            for analysis in self.results['files_analyzed'].values() 
            if 'error' not in analysis
        )
        
        # Recommendation 1: Transaction Ledger improvements
        has_transaction_ledger = 'transaction_ledger' in file_types_found
        if has_transaction_ledger:
            # Fix: Properly sum pattern counts from transaction ledger analyses
            tl_patterns = 0
            for analysis in self.results['files_analyzed'].values():
                if analysis.get('file_type') == 'transaction_ledger':
                    patterns_dict = analysis.get('pattern_analysis', {})
                    # Sum all values in the patterns dictionary
                    tl_patterns += sum(patterns_dict.values()) if patterns_dict else 0
            
            recs.append({
                'priority': 'High',
                'recommendation': 'Add Allowed Amount column to Transaction Ledger',
                'rationale': f'Currently requires parsing {tl_patterns} pattern-based overrides from descriptions',
                'impact': 'Would eliminate need for description parsing and reduce errors'
            })
        
        # Recommendation 2: Standardize patterns
        total_patterns = sum(len(v) for v in self.results['pattern_examples'].values())
        if total_patterns > 50:
            recs.append({
                'priority': 'Medium',
                'recommendation': 'Standardize description patterns',
                'rationale': f'Found {total_patterns} instances of patterns across files',
                'impact': 'More consistent parsing and fewer edge cases'
            })
        
        # Recommendation 3: Data quality
        date_headers_found = any(
            'date range header rows' in str(analysis)
            for analysis in self.results['files_analyzed'].values()
        )
        
        if date_headers_found:
            recs.append({
                'priority': 'Low',
                'recommendation': 'Consider removing date range headers from CSV exports',
                'rationale': 'Date headers complicate parsing and can contaminate data',
                'impact': 'Simpler, more reliable data processing'
            })
        
        self.results['recommendations'] = recs
    
    def save_results(self):
        """Save all analysis results"""
        # Main results JSON
        output_path = self.output_dir / 'comprehensive_analysis_results.json'
        
        # Convert defaultdict to regular dict for JSON serialization
        results_copy = self.results.copy()
        results_copy['pattern_examples'] = dict(results_copy['pattern_examples'])
        
        with open(output_path, 'w') as f:
            json.dump(results_copy, f, indent=2, default=str)
        
        logger.info(f"Results saved to {output_path}")
        
        # Pattern examples CSV - properly formatted
        pattern_rows = []
        for pattern, examples_list in self.results['pattern_examples'].items():
            for example_dict in examples_list:
                pattern_rows.append({
                    'Pattern': pattern,
                    'File': example_dict['file'],
                    'Example': example_dict['example'][:200]  # Limit length
                })
        
        if pattern_rows:
            examples_df = pd.DataFrame(pattern_rows)
            examples_path = self.output_dir / 'pattern_examples.csv'
            examples_df.to_csv(examples_path, index=False)
            logger.info(f"Pattern examples saved to {examples_path}")
        else:
            logger.warning("No pattern examples found to save")
    
    def print_summary(self):
        """Print enhanced analysis summary"""
        print("\n" + "="*80)
        print("COMPREHENSIVE BALANCE ANALYSIS SUMMARY")
        print("="*80)
        
        print(f"\nAnalysis completed at: {self.results['analysis_timestamp']}")
        print(f"Files Analyzed: {self.results['data_quality']['total_files_processed']}")
        print(f"Total Transactions: {self.results['data_quality']['total_transactions']:,}")
        
        # File type summary
        print("\n[FILE TYPES DETECTED]")
        print("-"*40)
        file_type_counts = defaultdict(int)
        for analysis in self.results['files_analyzed'].values():
            if 'error' not in analysis:
                file_type_counts[analysis['file_type']] += 1
        
        for file_type, count in file_type_counts.items():
            print(f"  {file_type}: {count} file(s)")
        
        # Key findings by file type
        print("\n[KEY FINDINGS BY FILE TYPE]")
        print("-"*40)
        
        for filename, analysis in self.results['files_analyzed'].items():
            if 'error' in analysis:
                continue
                
            print(f"\n{filename}:")
            print(f"  Type: {analysis['file_type']}")
            print(f"  Transactions: {analysis.get('total_transactions', 'N/A')}")
            
            if analysis['file_type'] == 'expense_history':
                if 'allowed_amount_analysis' in analysis:
                    adj_rate = analysis['allowed_amount_analysis']['adjustment_rate']
                    print("  Has Allowed Amount: Yes")
                    print(f"  Adjustment Rate: {adj_rate:.1f}%")
                    
                if 'person_breakdown' in analysis:
                    for person, stats in analysis['person_breakdown'].items():
                        print(f"  {person}: {stats['transaction_count']} transactions, "
                              f"${stats['total_allowed']:,.2f} allowed")
            
            elif analysis['file_type'] == 'transaction_ledger':
                print("  Has Allowed Amount: No (requires 50/50 default)")
                if 'pattern_analysis' in analysis:
                    total_patterns = sum(analysis['pattern_analysis'].values())
                    print(f"  Pattern Overrides Found: {total_patterns}")
                    
            elif analysis['file_type'] == 'rent_allocation':
                if 'split_analysis' in analysis:
                    split = analysis['split_analysis']['average_split']
                    print(f"  Rent Split: Ryan {split['ryan']:.1f}%, Jordyn {split['jordyn']:.1f}%")
        
        # Pattern summary
        print("\n[PATTERN ANALYSIS SUMMARY]")
        print("-"*40)
        all_patterns = defaultdict(int)
        for pattern_dict in self.results['pattern_analysis'].values():
            for pattern, count in pattern_dict.items():
                all_patterns[pattern] += count
        
        if all_patterns:
            for pattern, count in sorted(all_patterns.items(), key=lambda x: x[1], reverse=True):
                if count > 0:
                    print(f"  {pattern}: {count} occurrences")
        else:
            print("  No patterns found")
        
        # Recommendations
        print("\n[TOP RECOMMENDATIONS]")
        print("-"*40)
        for i, rec in enumerate(self.results.get('recommendations', [])[:3], 1):
            print(f"{i}. [{rec['priority']}] {rec['recommendation']}")
            print(f"   Rationale: {rec['rationale']}")
        
        print("\n[COMPLETE] Full results saved to 'analysis_output' directory")
        print("="*80)
    
    def run_comprehensive_analysis(self):
        """Main analysis pipeline with improved error handling"""
        logger.info("Starting comprehensive analysis of all CSV files...")
        
        # Find all CSV files
        csv_files = list(self.data_dir.glob("*.csv"))
        if not csv_files:
            logger.error(f"No CSV files found in {self.data_dir}")
            return self.results
            
        logger.info(f"Found {len(csv_files)} CSV files to analyze")
        
        # Load and analyze each file
        all_dfs = {}
        
        for filepath in csv_files:
            try:
                logger.info(f"\nProcessing {filepath.name}...")
                
                # Read CSV intelligently
                df = SmartCSVReader.read_csv_intelligently(filepath)
                
                # Detect file type
                file_type = FileTypeDetector.detect_file_type(filepath, df)
                logger.info(f"Detected {filepath.name} as type: {file_type}")
                
                # Store for cross-file analysis
                all_dfs[filepath.name] = {
                    'dataframe': df,
                    'file_type': file_type
                }
                
                # Run appropriate analysis
                if file_type in self.file_handlers:
                    analysis = self.file_handlers[file_type](df, filepath)
                    self.results['files_analyzed'][filepath.name] = analysis
                    
                    # Collect pattern analysis
                    if 'pattern_analysis' in analysis:
                        self.results['pattern_analysis'][filepath.name] = analysis['pattern_analysis']
                else:
                    logger.warning(f"Unknown file type for {filepath.name}")
                    self.results['files_analyzed'][filepath.name] = {
                        'error': f'Unknown file type: {file_type}'
                    }
                
            except Exception as e:
                logger.error(f"Error processing {filepath.name}: {str(e)}")
                self.results['files_analyzed'][filepath.name] = {
                    'error': str(e),
                    'file_type': 'error'
                }
        
        # Cross-file analysis
        logger.info("\nPerforming cross-file analysis...")
        
        # Check for duplicates
        if len(all_dfs) > 1:
            self.results['duplicate_analysis'] = self.check_for_duplicates(all_dfs)
        
        # Generate business rules
        self.results['business_rules'] = self.generate_business_rules()
        
        # Data quality summary
        successful_analyses = [
            f for f in self.results['files_analyzed'].values() 
            if 'error' not in f
        ]
        
        self.results['data_quality'] = {
            'total_files_processed': len(csv_files),
            'successful_analyses': len(successful_analyses),
            'failed_analyses': len(csv_files) - len(successful_analyses),
            'file_types_found': list(set(
                f.get('file_type', 'unknown') 
                for f in successful_analyses
            )),
            'total_transactions': sum(
                f.get('total_transactions', 0) 
                for f in successful_analyses
            )
        }
        
        # Generate recommendations
        self.generate_recommendations()
        
        # Save results
        self.save_results()
        
        # Print summary
        self.print_summary()
        
        return self.results


def main():
    """Run the comprehensive analysis"""
    analyzer = ComprehensiveAnalyzer()
    results = analyzer.run_comprehensive_analysis()
    
    return results


if __name__ == "__main__":
    main()