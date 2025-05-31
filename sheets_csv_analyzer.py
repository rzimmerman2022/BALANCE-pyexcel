#!/usr/bin/env python3
"""
Script to analyze CSV exports from Google Sheets rent/expense tracking
to extract patterns and rules for shared expense functionality.

Usage:
    # Process all CSVs in C:\BALANCE (default):
    python sheets_csv_analyzer.py
    
    # Process all CSVs in a specific directory:
    python sheets_csv_analyzer.py "C:\path\to\csvs"
    
    # Process only the New Master CSV files:
    python sheets_csv_analyzer.py --specific-files
    
Expected files in C:\BALANCE:
    - New Master - New Joint Couple Finances (2024).xlsx - Rent Allocation.csv
    - New Master - New Joint Couple Finances (2024).xlsx - Expense History.csv
"""

import csv
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Set, Tuple
import re

class SharedExpenseAnalyzer:
    def __init__(self, csv_directory: str):
        self.csv_dir = Path(csv_directory)
        self.shared_patterns = defaultdict(int)
        self.merchant_sharing = defaultdict(lambda: {"shared": 0, "individual": 0})
        self.category_sharing = defaultdict(lambda: {"shared": 0, "individual": 0})
        self.rent_data = []
        self.expense_data = []
        
    def analyze_all_csvs(self):
        """Process all CSV files in the directory."""
        csv_files = list(self.csv_dir.glob("*.csv"))
        if not csv_files:
            print(f"\n⚠️  No CSV files found in {self.csv_dir}")
            return
            
        print(f"\n📁 Found {len(csv_files)} CSV files in {self.csv_dir}")
        
        for csv_file in csv_files:
            print(f"\nProcessing: {csv_file.name}")
            self.process_csv(csv_file)
            
        self.generate_report()
        
    def process_csv(self, filepath: Path):
        """Determine CSV type and process accordingly."""
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            
            if not headers:
                print(f"  ⚠️  No headers found in {filepath.name}")
                return
                
            # Detect CSV type based on headers
            if any(col in headers for col in ['Tax Base Rent', 'Ryan\'s Rent', 'Jordyn\'s Rent']):
                self.process_rent_tracking_csv(filepath)
            elif 'Allowed Amount' in headers and 'Actual Amount' in headers:
                self.process_expense_allocation_csv(filepath)
            elif any(col in headers for col in ['Amount', 'Merchant', 'Description']):
                self.process_transaction_csv(filepath)
            else:
                print(f"  ⚠️  Unknown CSV format: {headers[:5]}...")
    
    def process_rent_tracking_csv(self, filepath: Path):
        """Process monthly rent tracking data."""
        print("  📊 Processing as rent tracking data...")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not row.get('Month'):
                    continue
                    
                try:
                    rent_record = {
                        'month': row.get('Month', ''),
                        'base_rent': self.parse_amount(row.get('Tax Base Rent', '0')),
                        'garage': self.parse_amount(row.get('Tax Garage', '0')),
                        'trash': self.parse_amount(row.get('Tax Trash', '0')),
                        'courtyard': self.parse_amount(row.get('Tax Courtyard', '0')),
                        'conserve': self.parse_amount(row.get('Conserve', '0')),
                        'gross_total': self.parse_amount(row.get('Gross Total', '0')),
                        'ryan_rent': self.parse_amount(row.get('Ryan\'s Rent (43%)', '0')),
                        'jordyn_rent': self.parse_amount(row.get('Jordyn\'s Rent', '0')),
                        'rent_difference': self.parse_amount(row.get('Rent Difference', '0'))
                    }
                    
                    if rent_record['gross_total'] > 0:
                        self.rent_data.append(rent_record)
                        
                        # Calculate actual split percentages
                        ryan_pct = (rent_record['ryan_rent'] / rent_record['gross_total']) * 100
                        jordyn_pct = (rent_record['jordyn_rent'] / rent_record['gross_total']) * 100
                        
                        print(f"    {rent_record['month']}: Ryan={ryan_pct:.1f}%, Jordyn={jordyn_pct:.1f}%")
                        
                except Exception as e:
                    print(f"    Error processing row: {e}")
    
    def process_expense_allocation_csv(self, filepath: Path):
        """Process expense allocation data with allowed amounts."""
        print("  💰 Processing as expense allocation data...")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not row.get('Merchant'):
                    continue
                    
                try:
                    expense = {
                        'name': row.get('Name', ''),
                        'date': row.get('Date of Purchase', ''),
                        'account': row.get('Account', ''),
                        'merchant': row.get('Merchant', ''),
                        'actual_amount': self.parse_amount(row.get('Actual Amount', '0')),
                        'allowed_amount': self.parse_amount(row.get('Allowed Amount', '0')),
                        'description': row.get('Description', '')
                    }
                    
                    if expense['actual_amount'] > 0:
                        self.expense_data.append(expense)
                        
                        # Track sharing patterns
                        if expense['allowed_amount'] != expense['actual_amount']:
                            self.shared_patterns['partial_reimbursement'] += 1
                            
                        # Analyze merchant patterns
                        merchant_key = self.normalize_merchant(expense['merchant'])
                        if expense['name'].lower() in ['ryan', 'jordyn']:
                            self.merchant_sharing[merchant_key]['individual'] += 1
                        else:
                            self.merchant_sharing[merchant_key]['shared'] += 1
                            
                        # Determine if this is likely a shared expense based on the actual vs allowed
                        if expense['allowed_amount'] > 0 and expense['allowed_amount'] < expense['actual_amount']:
                            # Partial reimbursement suggests sharing
                            self.merchant_sharing[merchant_key]['shared'] += 1
                            
                except Exception as e:
                    print(f"    Error processing row: {e}")
    
    def process_transaction_csv(self, filepath: Path):
        """Process general transaction data."""
        print("  📝 Processing as transaction data...")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    amount = self.parse_amount(row.get('Amount', '0'))
                    merchant = row.get('Merchant', '')
                    description = row.get('Description', '')
                    category = row.get('Category', '')
                    
                    if amount != 0 and merchant:
                        # Look for sharing indicators in description
                        desc_lower = description.lower()
                        if any(term in desc_lower for term in ['split', 'shared', 'half', '50%', 'ryan', 'jordyn']):
                            self.shared_patterns['description_indicator'] += 1
                            
                        # Track category patterns
                        if category:
                            # Guess if shared based on category
                            shared_categories = ['rent', 'utilities', 'groceries', 'household']
                            if any(cat in category.lower() for cat in shared_categories):
                                self.category_sharing[category]['shared'] += 1
                            else:
                                self.category_sharing[category]['individual'] += 1
                                
                except Exception as e:
                    pass  # Skip problematic rows
    
    def parse_amount(self, amount_str: str) -> float:
        """Parse amount string to float, handling currency symbols."""
        if not amount_str:
            return 0.0
        # Remove currency symbols and commas
        cleaned = re.sub(r'[$,()]', '', str(amount_str))
        # Handle parentheses as negative
        if '(' in str(amount_str) and ')' in str(amount_str):
            cleaned = '-' + cleaned
        try:
            return float(cleaned)
        except:
            return 0.0
    
    def normalize_merchant(self, merchant: str) -> str:
        """Normalize merchant name for pattern matching."""
        if not merchant:
            return ""
        # Remove special characters and extra spaces
        normalized = re.sub(r'[^\w\s]', '', merchant)
        normalized = ' '.join(normalized.split())
        return normalized.lower()
    
    def generate_report(self):
        """Generate analysis report with sharing rules."""
        print("\n" + "="*60)
        print("SHARED EXPENSE ANALYSIS REPORT")
        print("="*60)
        
        # Rent Analysis
        if self.rent_data:
            print("\n📊 RENT SPLIT ANALYSIS:")
            total_ryan = sum(r['ryan_rent'] for r in self.rent_data)
            total_jordyn = sum(r['jordyn_rent'] for r in self.rent_data)
            total_rent = total_ryan + total_jordyn
            
            if total_rent > 0:
                ryan_avg_pct = (total_ryan / total_rent) * 100
                jordyn_avg_pct = (total_jordyn / total_rent) * 100
                
                print(f"  Average Split: Ryan={ryan_avg_pct:.1f}%, Jordyn={jordyn_avg_pct:.1f}%")
                print(f"  Total Payments: Ryan=${total_ryan:,.2f}, Jordyn=${total_jordyn:,.2f}")
        
        # Expense Data Summary
        if self.expense_data:
            print("\n💳 EXPENSE ALLOCATION ANALYSIS:")
            total_actual = sum(e['actual_amount'] for e in self.expense_data)
            total_allowed = sum(e['allowed_amount'] for e in self.expense_data)
            print(f"  Total Actual Expenses: ${total_actual:,.2f}")
            print(f"  Total Allowed/Reimbursed: ${total_allowed:,.2f}")
            print(f"  Difference (Shared Portion): ${total_actual - total_allowed:,.2f}")
            print(f"  Number of Expense Records: {len(self.expense_data)}")
        
        # Merchant Patterns
        print("\n🏪 MERCHANT SHARING PATTERNS:")
        print("  Merchants likely to be shared:")
        shared_merchants = []
        for merchant, counts in self.merchant_sharing.items():
            total = counts['shared'] + counts['individual']
            if total > 0:
                shared_pct = (counts['shared'] / total) * 100
                if shared_pct > 60 and total >= 2:
                    shared_merchants.append((merchant, shared_pct, total))
        
        for merchant, pct, count in sorted(shared_merchants, key=lambda x: x[1], reverse=True)[:10]:
            print(f"    - {merchant}: {pct:.0f}% shared ({count} transactions)")
        
        # Category Patterns
        print("\n📁 CATEGORY SHARING PATTERNS:")
        print("  Categories likely to be shared:")
        for category, counts in self.category_sharing.items():
            total = counts['shared'] + counts['individual']
            if total > 0:
                shared_pct = (counts['shared'] / total) * 100
                if shared_pct > 50:
                    print(f"    - {category}: {shared_pct:.0f}% shared")
        
        # Pattern Summary
        print("\n📈 PATTERN SUMMARY:")
        for pattern_type, count in self.shared_patterns.items():
            print(f"  - {pattern_type.replace('_', ' ').title()}: {count} instances")
        
        # Generate Rules JSON
        self.generate_sharing_rules()
        
    def generate_sharing_rules(self):
        """Generate JSON rules for the BALANCE pipeline."""
        rules = {
            "sharing_rules": {
                "default_split": {
                    "ryan": 43,
                    "jordyn": 57
                },
                "merchant_patterns": [],
                "category_patterns": [],
                "description_keywords": {
                    "shared": ["split", "shared", "both", "utilities", "rent", "household"],
                    "ryan": ["ryan only", "ryan's"],
                    "jordyn": ["jordyn only", "jordyn's"]
                }
            }
        }
        
        # Add merchant rules
        for merchant, counts in self.merchant_sharing.items():
            total = counts['shared'] + counts['individual']
            if total >= 2:  # Only include merchants with multiple transactions
                shared_pct = (counts['shared'] / total) * 100
                if shared_pct > 70:
                    rules["sharing_rules"]["merchant_patterns"].append({
                        "pattern": merchant,
                        "action": "shared",
                        "confidence": shared_pct
                    })
        
        # Add category rules
        for category, counts in self.category_sharing.items():
            total = counts['shared'] + counts['individual']
            if total > 0:
                shared_pct = (counts['shared'] / total) * 100
                if shared_pct > 60:
                    rules["sharing_rules"]["category_patterns"].append({
                        "category": category,
                        "action": "shared",
                        "confidence": shared_pct
                    })
        
        # Save rules
        output_file = self.csv_dir / "generated_sharing_rules.json"
        with open(output_file, 'w') as f:
            json.dump(rules, f, indent=2)
        
        print(f"\n✅ Sharing rules saved to: {output_file}")
        print("\nSample rules structure:")
        print(json.dumps(rules, indent=2)[:500] + "...")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze Google Sheets CSV exports for shared expense patterns')
    parser.add_argument('csv_directory', nargs='?', default=r'C:\BALANCE', 
                       help='Directory containing CSV files (default: C:\\BALANCE)')
    parser.add_argument('--specific-files', action='store_true',
                       help='Process only the New Master CSV files')
    
    args = parser.parse_args()
    
    analyzer = SharedExpenseAnalyzer(args.csv_directory)
    
    if args.specific_files:
        # Process specific files
        rent_file = Path(args.csv_directory) / "New Master - New Joint Couple Finances (2024).xlsx - Rent Allocation.csv"
        expense_file = Path(args.csv_directory) / "New Master - New Joint Couple Finances (2024).xlsx - Expense History.csv"
        
        if rent_file.exists():
            print(f"Processing rent allocation file: {rent_file.name}")
            analyzer.process_csv(rent_file)
        else:
            print(f"⚠️  Rent allocation file not found: {rent_file}")
            
        if expense_file.exists():
            print(f"Processing expense history file: {expense_file.name}")
            analyzer.process_csv(expense_file)
        else:
            print(f"⚠️  Expense history file not found: {expense_file}")
            
        analyzer.generate_report()
    else:
        # Process all CSVs in directory
        analyzer.analyze_all_csvs()


if __name__ == "__main__":
    main()