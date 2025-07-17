#!/usr/bin/env python3
"""
Comprehensive Balance Analyzer for BALANCE-pyexcel
Processes all four file types without context window limitations
"""

import pandas as pd
import numpy as np
import re
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FileTypeDetector:
    """Intelligently detect which type of CSV we're dealing with"""
    
    @staticmethod
    def detect_file_type(filepath, df):
        """Detect file type based on filename and column structure"""
        filename = filepath.name.lower()
        columns = set(df.columns.str.strip().str.lower())
        
        # Check filename patterns first
        if 'expense' in filename and 'history' in filename:
            return 'expense_history'
        elif 'transaction' in filename and 'ledger' in filename:
            return 'transaction_ledger'
        elif 'rent' in filename and 'allocation' in filename:
            return 'rent_allocation'
        elif 'rent' in filename and 'history' in filename:
            return 'rent_history'
        
        # Fallback to column analysis
        if 'allowed amount' in columns:
            return 'expense_history'
        elif 'running balance' in columns or 'category' in columns:
            return 'transaction_ledger'
        elif "ryan's rent" in columns or "jordyn's rent" in columns:
            return 'rent_allocation'
        elif any('budgeted' in col for col in columns):
            return 'rent_history'
        
        return 'unknown'


class SmartCSVReader:
    """Handle various CSV structures including headers at row 3"""
    
    @staticmethod
    def find_header_row(filepath, max_rows=10):
        """Find where actual data headers start"""
        header_keywords = ['Name', 'Date', 'Amount', 'Merchant', 'Description', 
                          'Account', 'Month', 'Rent', 'Category', 'Balance']
        
        with open(filepath, 'r', encoding='utf-8') as f:
            for i in range(max_rows):
                line = f.readline()
                if not line:
                    break
                    
                # Count header keywords in this line
                keyword_count = sum(1 for keyword in header_keywords 
                                  if keyword.lower() in line.lower())
                
                if keyword_count >= 2:  # Found likely header row
                    logger.info(f"Found header row at index {i} in {filepath.name}")
                    return i
        
        return 0  # Default to first row
    
    @staticmethod
    def read_csv_intelligently(filepath):
        """Read CSV with automatic header detection and cleaning"""
        # Find header row
        header_row = SmartCSVReader.find_header_row(filepath)
        
        # Read with detected header
        df = pd.read_csv(filepath, skiprows=header_row)
        
        # Clean column names
        df.columns = df.columns.str.strip()
        
        # Remove empty rows
        df = df.dropna(how='all')
        
        # Remove duplicate header rows within data
        for col in ['Name', 'Date', 'Merchant']:
            if col in df.columns:
                df = df[~df[col].astype(str).str.contains(col, na=False, case=False)]
        
        logger.info(f"Loaded {len(df)} rows from {filepath.name}")
        return df


class ComprehensiveAnalyzer:
    """Main analyzer that handles all four file types"""
    
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
            'pattern_analysis': defaultdict(dict),
            'business_rules': {},
            'data_quality': {},
            'recommendations': {}
        }
    
    def clean_amount(self, amount_str):
        """Convert various amount formats to float"""
        if pd.isna(amount_str):
            return 0.0
        
        amount_str = str(amount_str).strip()
        
        # Handle special cases
        if amount_str in ['', '-', '$ -', '$-']:
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
    
    def analyze_expense_history(self, df, filepath):
        """Analyze Expense History file with Allowed Amount logic"""
        analysis = {
            'file_type': 'expense_history',
            'total_transactions': len(df),
            'date_range': {},
            'allowed_amount_analysis': {},
            'pattern_analysis': {},
            'person_breakdown': {}
        }
        
        # Date range
        if 'Date' in df.columns or 'Date of Purchase' in df.columns:
            date_col = 'Date' if 'Date' in df.columns else 'Date of Purchase'
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
            
            # Calculate differences
            df['Has_Adjustment'] = df['Actual_Clean'] != df['Allowed_Clean']
            df['Adjustment_Type'] = 'No Adjustment'
            
            # Categorize adjustments
            mask_zero = (df['Allowed_Clean'] == 0) & (df['Actual_Clean'] > 0)
            df.loc[mask_zero, 'Adjustment_Type'] = 'Fully Disallowed'
            
            mask_partial = (df['Allowed_Clean'] > 0) & (df['Allowed_Clean'] < df['Actual_Clean'])
            df.loc[mask_partial, 'Adjustment_Type'] = 'Partially Allowed'
            
            mask_increased = df['Allowed_Clean'] > df['Actual_Clean']
            df.loc[mask_increased, 'Adjustment_Type'] = 'Increased Amount'
            
            # Summary statistics
            adjustment_counts = df['Adjustment_Type'].value_counts().to_dict()
            analysis['allowed_amount_analysis'] = {
                'total_with_adjustments': int(df['Has_Adjustment'].sum()),
                'adjustment_rate': float(df['Has_Adjustment'].mean() * 100),
                'adjustment_types': adjustment_counts,
                'average_reduction': float(df[mask_partial]['Allowed_Clean'].mean()) if len(df[mask_partial]) > 0 else 0
            }
        
        # Pattern analysis in descriptions
        if 'Description' in df.columns:
            patterns = self.analyze_description_patterns(df['Description'])
            analysis['pattern_analysis'] = patterns
        
        # Person breakdown
        if 'Name' in df.columns:
            person_stats = df.groupby('Name').agg({
                'Actual_Clean': ['count', 'sum', 'mean'],
                'Allowed_Clean': ['sum', 'mean']
            }).round(2)
            
            analysis['person_breakdown'] = {
                name: {
                    'transaction_count': int(stats[('Actual_Clean', 'count')]),
                    'total_actual': float(stats[('Actual_Clean', 'sum')]),
                    'total_allowed': float(stats[('Allowed_Clean', 'sum')]),
                    'avg_transaction': float(stats[('Actual_Clean', 'mean')])
                }
                for name, stats in person_stats.iterrows()
            }
        
        return analysis
    
    def analyze_transaction_ledger(self, df, filepath):
        """Analyze Transaction Ledger file structure"""
        analysis = {
            'file_type': 'transaction_ledger',
            'total_transactions': len(df),
            'unique_features': {},
            'category_breakdown': {},
            'running_balance_analysis': {}
        }
        
        # Check for unique columns
        unique_cols = []
        for col in ['Running Balance', 'Category', 'Posted Balance']:
            if col in df.columns:
                unique_cols.append(col)
        
        analysis['unique_features']['unique_columns'] = unique_cols
        
        # Category analysis
        if 'Category' in df.columns:
            category_counts = df['Category'].value_counts().head(20).to_dict()
            analysis['category_breakdown'] = category_counts
        
        # Running balance analysis
        if 'Running Balance' in df.columns:
            df['Balance_Clean'] = df['Running Balance'].apply(self.clean_amount)
            analysis['running_balance_analysis'] = {
                'starting_balance': float(df['Balance_Clean'].iloc[0]) if len(df) > 0 else 0,
                'ending_balance': float(df['Balance_Clean'].iloc[-1]) if len(df) > 0 else 0,
                'min_balance': float(df['Balance_Clean'].min()),
                'max_balance': float(df['Balance_Clean'].max())
            }
        
        # Since no Allowed Amount, check descriptions for rules
        if 'Description' in df.columns:
            patterns = self.analyze_description_patterns(df['Description'])
            analysis['pattern_analysis'] = patterns
            
            # Estimate how many transactions would need adjustment
            special_instruction_count = sum(patterns.values())
            analysis['estimated_adjustments'] = {
                'transactions_with_special_instructions': special_instruction_count,
                'percentage': float(special_instruction_count / len(df) * 100) if len(df) > 0 else 0
            }
        
        return analysis
    
    def analyze_rent_allocation(self, df, filepath):
        """Analyze Rent Allocation file structure"""
        analysis = {
            'file_type': 'rent_allocation',
            'total_months': len(df),
            'rent_components': [],
            'split_analysis': {}
        }
        
        # Identify rent components (columns that aren't Month, Total, or person-specific)
        exclude_cols = ['Month', 'Gross Total', "Ryan's Rent", "Jordyn's Rent"]
        rent_components = [col for col in df.columns if col not in exclude_cols]
        analysis['rent_components'] = rent_components
        
        # Analyze the split
        if "Ryan's Rent" in df.columns and "Jordyn's Rent" in df.columns:
            df['Ryan_Clean'] = df["Ryan's Rent"].apply(self.clean_amount)
            df['Jordyn_Clean'] = df["Jordyn's Rent"].apply(self.clean_amount)
            df['Total_Clean'] = df['Ryan_Clean'] + df['Jordyn_Clean']
            
            # Calculate split percentages
            df['Ryan_Percent'] = (df['Ryan_Clean'] / df['Total_Clean'] * 100).round(1)
            df['Jordyn_Percent'] = (df['Jordyn_Clean'] / df['Total_Clean'] * 100).round(1)
            
            analysis['split_analysis'] = {
                'average_split': {
                    'ryan': float(df['Ryan_Percent'].mean()),
                    'jordyn': float(df['Jordyn_Percent'].mean())
                },
                'total_rent': {
                    'ryan': float(df['Ryan_Clean'].sum()),
                    'jordyn': float(df['Jordyn_Clean'].sum())
                },
                'monthly_average': {
                    'ryan': float(df['Ryan_Clean'].mean()),
                    'jordyn': float(df['Jordyn_Clean'].mean())
                }
            }
        
        return analysis
    
    def analyze_rent_history(self, df, filepath):
        """Analyze Rent History file with budget vs actual"""
        analysis = {
            'file_type': 'rent_history',
            'structure': 'wide_format',
            'months_covered': [],
            'variance_analysis': {}
        }
        
        # Identify months from column names
        month_pattern = re.compile(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}')
        months = set()
        
        for col in df.columns:
            match = month_pattern.search(col)
            if match:
                months.add(match.group(0))
        
        analysis['months_covered'] = sorted(list(months))
        
        # Calculate budget vs actual variances
        variances = []
        for month in months:
            budget_col = f"{month} Budgeted"
            actual_col = f"{month} Actual"
            
            if budget_col in df.columns and actual_col in df.columns:
                df[f"{month}_Budget_Clean"] = df[budget_col].apply(self.clean_amount)
                df[f"{month}_Actual_Clean"] = df[actual_col].apply(self.clean_amount)
                
                total_budget = df[f"{month}_Budget_Clean"].sum()
                total_actual = df[f"{month}_Actual_Clean"].sum()
                variance = total_actual - total_budget
                
                variances.append({
                    'month': month,
                    'budgeted': float(total_budget),
                    'actual': float(total_actual),
                    'variance': float(variance),
                    'variance_percent': float(variance / total_budget * 100) if total_budget > 0 else 0
                })
        
        analysis['variance_analysis'] = {
            'monthly_variances': variances,
            'average_variance': float(np.mean([v['variance'] for v in variances])) if variances else 0,
            'total_variance': float(sum(v['variance'] for v in variances)) if variances else 0
        }
        
        return analysis
    
    def analyze_description_patterns(self, descriptions):
        """Extract patterns from description fields"""
        patterns = {
            'full_allocation_100_percent': 0,
            'full_allocation_person_only': 0,
            'multiplier_2x': 0,
            'multiplier_other': 0,
            'gift_or_present': 0,
            'free_for_person': 0,
            'reassess_next_time': 0,
            'rent_payment': 0,
            'refund': 0,
            'personal_marker': 0
        }
        
        pattern_examples = defaultdict(list)
        
        for desc in descriptions.dropna():
            desc_str = str(desc).strip()
            
            # 100% allocation
            if re.search(r'100\s*%\s*(Ryan|Jordyn)', desc_str, re.IGNORECASE):
                patterns['full_allocation_100_percent'] += 1
                pattern_examples['full_allocation_100_percent'].append(desc_str[:100])
            
            # Person only
            if re.search(r'(Ryan|Jordyn)\s+only', desc_str, re.IGNORECASE):
                patterns['full_allocation_person_only'] += 1
                pattern_examples['full_allocation_person_only'].append(desc_str[:100])
            
            # 2x multiplier
            if re.search(r'2x\s+to\s+calculate', desc_str, re.IGNORECASE):
                patterns['multiplier_2x'] += 1
                pattern_examples['multiplier_2x'].append(desc_str[:100])
            
            # Other multipliers
            elif re.search(r'(\d+)x\s+to\s+calculate', desc_str, re.IGNORECASE):
                patterns['multiplier_other'] += 1
                pattern_examples['multiplier_other'].append(desc_str[:100])
            
            # Gift/Present
            if re.search(r'\bgift\b|\bpresent\b|\bbirthday\b|\bchristmas\b', desc_str, re.IGNORECASE):
                patterns['gift_or_present'] += 1
                pattern_examples['gift_or_present'].append(desc_str[:100])
            
            # Free for person
            if re.search(r'free\s+for\s+(Ryan|Jordyn|my|babbbby)', desc_str, re.IGNORECASE):
                patterns['free_for_person'] += 1
                pattern_examples['free_for_person'].append(desc_str[:100])
            
            # Reassess
            if re.search(r'reassess\s+next\s+time', desc_str, re.IGNORECASE):
                patterns['reassess_next_time'] += 1
                pattern_examples['reassess_next_time'].append(desc_str[:100])
            
            # Rent
            if re.search(r'\brent\b', desc_str, re.IGNORECASE):
                patterns['rent_payment'] += 1
            
            # Refund
            if re.search(r'\brefund\b', desc_str, re.IGNORECASE):
                patterns['refund'] += 1
            
            # Personal markers
            if re.search(r'personal|my\s+own|private', desc_str, re.IGNORECASE):
                patterns['personal_marker'] += 1
        
        # Store examples for verification
        self.results['pattern_examples'] = dict(pattern_examples)
        
        return patterns
    
    def check_for_duplicates(self, all_dfs):
        """Check for duplicate transactions across files"""
        duplicate_analysis = {
            'potential_duplicates': [],
            'cross_file_matches': 0
        }
        
        # Create transaction fingerprints from each file
        all_transactions = []
        
        for filename, df_info in all_dfs.items():
            df = df_info['dataframe']
            file_type = df_info['file_type']
            
            # Get date and amount columns
            date_col = None
            amount_col = None
            
            for col in df.columns:
                if 'Date' in col:
                    date_col = col
                if 'Amount' in col and 'Actual' in col:
                    amount_col = col
                elif 'Amount' in col and amount_col is None:
                    amount_col = col
            
            if date_col and amount_col:
                for idx, row in df.iterrows():
                    try:
                        date_str = str(row[date_col])
                        amount = self.clean_amount(row[amount_col])
                        
                        if amount != 0:
                            fingerprint = f"{date_str}_{amount:.2f}"
                            all_transactions.append({
                                'fingerprint': fingerprint,
                                'file': filename,
                                'file_type': file_type,
                                'date': date_str,
                                'amount': amount,
                                'merchant': row.get('Merchant', 'Unknown')
                            })
                    except:
                        continue
        
        # Find duplicates
        fingerprint_counts = Counter(t['fingerprint'] for t in all_transactions)
        
        for fingerprint, count in fingerprint_counts.items():
            if count > 1:
                duplicate_txns = [t for t in all_transactions if t['fingerprint'] == fingerprint]
                
                # Check if duplicates are across different file types
                file_types = set(t['file_type'] for t in duplicate_txns)
                if len(file_types) > 1:
                    duplicate_analysis['cross_file_matches'] += 1
                
                duplicate_analysis['potential_duplicates'].append({
                    'fingerprint': fingerprint,
                    'count': count,
                    'transactions': duplicate_txns[:5]  # Limit to first 5
                })
        
        return duplicate_analysis
    
    def generate_business_rules(self):
        """Generate comprehensive business rules from analysis"""
        rules = {
            'core_rules': [],
            'edge_cases': [],
            'data_quality_rules': []
        }
        
        # Core rule 1: Allowed Amount Override
        if any('expense_history' in f for f in self.results['files_analyzed']):
            rules['core_rules'].append({
                'rule': 'Always use Allowed Amount when present',
                'priority': 1,
                'description': 'When Allowed Amount differs from Actual Amount, use Allowed Amount for calculations'
            })
        
        # Core rule 2: Description Field Instructions
        total_patterns = sum(
            sum(patterns.values()) 
            for patterns in self.results['pattern_analysis'].values()
        )
        
        if total_patterns > 0:
            rules['core_rules'].append({
                'rule': 'Parse Description field for special instructions',
                'priority': 2,
                'description': 'Description field contains allocation overrides like "100% Person", "2x to calculate"',
                'pattern_counts': dict(self.results['pattern_analysis'])
            })
        
        # Core rule 3: Default Split
        rules['core_rules'].append({
            'rule': 'Default 50/50 split when no special instructions',
            'priority': 3,
            'description': 'Transactions without special instructions are split equally'
        })
        
        # Core rule 4: Rent Split
        rent_files = [f for f in self.results['files_analyzed'] if 'rent' in f.lower()]
        if rent_files:
            rules['core_rules'].append({
                'rule': 'Rent uses fixed 43% Ryan, 57% Jordyn split',
                'priority': 4,
                'description': 'All rent-related expenses use this predetermined split'
            })
        
        # Edge cases
        for file_analysis in self.results['files_analyzed'].values():
            if 'allowed_amount_analysis' in file_analysis:
                if file_analysis['allowed_amount_analysis'].get('adjustment_types', {}).get('Increased Amount', 0) > 0:
                    rules['edge_cases'].append({
                        'case': 'Allowed Amount > Actual Amount',
                        'frequency': file_analysis['allowed_amount_analysis']['adjustment_types']['Increased Amount'],
                        'handling': 'Usually indicates "2x to calculate" or reimbursement scenario'
                    })
        
        return rules
    
    def run_comprehensive_analysis(self):
        """Main analysis pipeline"""
        logger.info("Starting comprehensive analysis of all CSV files...")
        
        # Find all CSV files
        csv_files = list(self.data_dir.glob("*.csv"))
        logger.info(f"Found {len(csv_files)} CSV files to analyze")
        
        # Load and analyze each file
        all_dfs = {}
        
        for filepath in csv_files:
            try:
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
                else:
                    logger.warning(f"Unknown file type for {filepath.name}")
                
            except Exception as e:
                logger.error(f"Error processing {filepath.name}: {e}")
                self.results['files_analyzed'][filepath.name] = {'error': str(e)}
        
        # Cross-file analysis
        logger.info("Performing cross-file analysis...")
        
        # Check for duplicates
        if len(all_dfs) > 1:
            self.results['duplicate_analysis'] = self.check_for_duplicates(all_dfs)
        
        # Generate business rules
        self.results['business_rules'] = self.generate_business_rules()
        
        # Data quality summary
        self.results['data_quality'] = {
            'total_files_processed': len(csv_files),
            'successful_analyses': len([f for f in self.results['files_analyzed'].values() if 'error' not in f]),
            'file_types_found': list(set(info['file_type'] for info in all_dfs.values())),
            'total_transactions': sum(
                f.get('total_transactions', 0) 
                for f in self.results['files_analyzed'].values() 
                if isinstance(f, dict)
            )
        }
        
        # Generate recommendations
        self.generate_recommendations()
        
        # Save results
        self.save_results()
        
        # Print summary
        self.print_summary()
        
        return self.results
    
    def generate_recommendations(self):
        """Generate actionable recommendations based on analysis"""
        recs = []
        
        # Check if Transaction Ledger lacks Allowed Amount
        has_transaction_ledger = any(
            f.get('file_type') == 'transaction_ledger' 
            for f in self.results['files_analyzed'].values()
        )
        
        if has_transaction_ledger:
            recs.append({
                'priority': 'High',
                'recommendation': 'Add Allowed Amount column to Transaction Ledger',
                'rationale': 'Transaction Ledger files lack the crucial Allowed Amount field, requiring description parsing for rules'
            })
        
        # Check pattern usage
        total_patterns = sum(
            sum(p.values()) for p in self.results['pattern_analysis'].values()
        )
        
        if total_patterns > 100:
            recs.append({
                'priority': 'Medium',
                'recommendation': 'Standardize description field entries',
                'rationale': f'Found {total_patterns} special instructions in descriptions. Consider structured fields for common patterns.'
            })
        
        # Check duplicate transactions
        if self.results.get('duplicate_analysis', {}).get('cross_file_matches', 0) > 0:
            recs.append({
                'priority': 'High',
                'recommendation': 'Implement deduplication logic',
                'rationale': f"Found {self.results['duplicate_analysis']['cross_file_matches']} potential duplicate transactions across files"
            })
        
        self.results['recommendations'] = recs
    
    def save_results(self):
        """Save all analysis results"""
        # Main results JSON
        output_path = self.output_dir / 'comprehensive_analysis_results.json'
        with open(output_path, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        logger.info(f"Results saved to {output_path}")
        
        # Pattern examples CSV
        if 'pattern_examples' in self.results:
            examples_df = pd.DataFrame([
                {'pattern': pattern, 'example': ex}
                for pattern, examples in self.results['pattern_examples'].items()
                for ex in examples[:5]  # Limit to 5 examples per pattern
            ])
            examples_path = self.output_dir / 'pattern_examples.csv'
            examples_df.to_csv(examples_path, index=False)
            logger.info(f"Pattern examples saved to {examples_path}")
    
    def print_summary(self):
        """Print analysis summary"""
        print("\n" + "="*80)
        print("COMPREHENSIVE BALANCE ANALYSIS SUMMARY")
        print("="*80)
        
        print(f"\nFiles Analyzed: {self.results['data_quality']['total_files_processed']}")
        print(f"Total Transactions: {self.results['data_quality']['total_transactions']:,}")
        print(f"File Types Found: {', '.join(self.results['data_quality']['file_types_found'])}")
        
        # Pattern summary
        print("\n[PATTERN ANALYSIS]")
        print("-"*40)
        total_by_pattern = defaultdict(int)
        for file_patterns in self.results['pattern_analysis'].values():
            for pattern, count in file_patterns.items():
                total_by_pattern[pattern] += count
        
        for pattern, count in sorted(total_by_pattern.items(), key=lambda x: x[1], reverse=True):
            if count > 0:
                print(f"  {pattern}: {count}")
        
        # File-specific insights
        print("\n[FILE-SPECIFIC INSIGHTS]")
        print("-"*40)
        for filename, analysis in self.results['files_analyzed'].items():
            if 'error' not in analysis:
                print(f"\n{filename} ({analysis.get('file_type', 'unknown')}):")
                
                if 'allowed_amount_analysis' in analysis:
                    adj_rate = analysis['allowed_amount_analysis']['adjustment_rate']
                    print(f"  - Adjustment Rate: {adj_rate:.1f}%")
                
                if 'split_analysis' in analysis:
                    split = analysis['split_analysis']['average_split']
                    print(f"  - Average Split: Ryan {split['ryan']:.1f}%, Jordyn {split['jordyn']:.1f}%")
                
                if 'variance_analysis' in analysis:
                    avg_var = analysis['variance_analysis']['average_variance']
                    print(f"  - Average Budget Variance: ${avg_var:,.2f}")
        
        # Duplicates
        if 'duplicate_analysis' in self.results:
            dup_count = len(self.results['duplicate_analysis']['potential_duplicates'])
            cross_file = self.results['duplicate_analysis']['cross_file_matches']
            print(f"\n[DUPLICATE ANALYSIS]")
            print(f"  - Potential Duplicates: {dup_count}")
            print(f"  - Cross-File Matches: {cross_file}")
        
        # Recommendations
        print("\n[TOP RECOMMENDATIONS]")
        print("-"*40)
        for rec in self.results.get('recommendations', [])[:3]:
            print(f"  [{rec['priority']}] {rec['recommendation']}")
        
        print("\n[OK] Analysis complete! Check 'analysis_output' directory for detailed results.")
        print("="*80)


def main():
    """Run the comprehensive analysis"""
    analyzer = ComprehensiveAnalyzer()
    results = analyzer.run_comprehensive_analysis()
    
    return results


if __name__ == "__main__":
    main()
