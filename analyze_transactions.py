#!/usr/bin/env python3
"""
Transaction Data Pattern Analyzer
Analyzes financial transaction data to discover optimal cleaning patterns
for OriginalDescription -> Description -> Merchant hierarchies
"""

import pandas as pd
import re
from collections import Counter, defaultdict
from pathlib import Path
import json
from typing import Dict, List, Tuple, Set
import numpy as np

class TransactionAnalyzer:
    def __init__(self, parquet_path: str):
        """Initialize analyzer with your parquet file"""
        self.df = pd.read_parquet(parquet_path)
        self.patterns = defaultdict(Counter)
        self.merchant_variations = defaultdict(set)
        self.cleaning_rules = {}
        
    def analyze_all(self):
        """Run all analyses and generate comprehensive report"""
        print("🔍 Analyzing transaction data patterns...\n")
        
        # Analyze OriginalDescription patterns
        self.analyze_description_patterns()
        
        # Analyze Merchant patterns
        self.analyze_merchant_patterns()
        
        # Analyze relationships between fields
        self.analyze_field_relationships()
        
        # Generate cleaning recommendations
        self.generate_cleaning_recommendations()
        
        # Output results
        self.save_analysis_results()
        
    def analyze_description_patterns(self):
        """Analyze patterns in OriginalDescription field"""
        print("📝 Analyzing OriginalDescription patterns...")
        
        if 'OriginalDescription' not in self.df.columns:
            print("❌ OriginalDescription column not found!")
            return
            
        descriptions = self.df['OriginalDescription'].dropna()
        
        # Analyze prefixes (first 2-4 words)
        prefix_counter = Counter()
        for desc in descriptions:
            words = str(desc).split()[:3]
            for i in range(1, min(4, len(words) + 1)):
                prefix = ' '.join(words[:i])
                prefix_counter[prefix] += 1
        
        # Find common prefixes (appearing in >1% of transactions)
        threshold = len(descriptions) * 0.01
        self.patterns['common_prefixes'] = {
            prefix: count for prefix, count in prefix_counter.items() 
            if count > threshold
        }
        
        # Analyze numeric patterns
        numeric_patterns = {
            'card_numbers': re.compile(r'\b\d{4,6}\*+\d{4}\b'),
            'reference_numbers': re.compile(r'REF\s*\d{6,}', re.I),
            'transaction_ids': re.compile(r'#\d{4,}'),
            'long_numbers': re.compile(r'\b\d{10,}\b'),
            'dates': re.compile(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'),
            'amounts': re.compile(r'\$[\d,]+\.?\d*'),
            'phone_numbers': re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'),
        }
        
        for pattern_name, pattern in numeric_patterns.items():
            matches = descriptions.apply(lambda x: bool(pattern.search(str(x))))
            self.patterns[f'has_{pattern_name}'] = matches.sum()
            
        # Analyze length distribution
        lengths = descriptions.apply(lambda x: len(str(x)))
        self.patterns['length_stats'] = {
            'mean': lengths.mean(),
            'median': lengths.median(),
            'std': lengths.std(),
            'percentile_95': lengths.quantile(0.95),
            'max': lengths.max()
        }
        
        print(f"✓ Analyzed {len(descriptions)} descriptions")
        
    def analyze_merchant_patterns(self):
        """Analyze patterns in Merchant field"""
        print("🏪 Analyzing Merchant patterns...")
        
        if 'Merchant' not in self.df.columns:
            print("❌ Merchant column not found!")
            return
            
        merchants = self.df['Merchant'].dropna()
        
        # Group similar merchants
        for merchant in merchants:
            merchant_str = str(merchant).strip()
            
            # Extract potential base merchant name
            base_name = self._extract_base_merchant(merchant_str)
            self.merchant_variations[base_name].add(merchant_str)
        
        # Analyze merchant formats
        format_patterns = {
            'has_numbers': re.compile(r'\d+'),
            'has_location': re.compile(r'\b(LLC|Inc|Corp|Store|#\d+)\b', re.I),
            'has_state': re.compile(r'\b[A-Z]{2}\b$'),
            'is_transfer': re.compile(r'(Transfer|Payment|Zelle|Venmo|Paypal)', re.I),
            'is_fee': re.compile(r'(Fee|Charge|Interest)', re.I),
            'is_all_caps': lambda x: x.isupper(),
            'is_mixed_case': lambda x: not x.isupper() and not x.islower(),
        }
        
        for pattern_name, pattern in format_patterns.items():
            if callable(pattern):
                matches = merchants.apply(lambda x: pattern(str(x)))
            else:
                matches = merchants.apply(lambda x: bool(pattern.search(str(x))))
            self.patterns[f'merchant_{pattern_name}'] = matches.sum()
            
        print(f"✓ Analyzed {len(merchants)} merchants")
        print(f"✓ Found {len(self.merchant_variations)} unique merchant groups")
        
    def analyze_field_relationships(self):
        """Analyze relationships between different fields"""
        print("🔗 Analyzing field relationships...")
        
        # Check if Description == OriginalDescription
        if 'Description' in self.df.columns and 'OriginalDescription' in self.df.columns:
            same_desc = (self.df['Description'] == self.df['OriginalDescription']).sum()
            self.patterns['description_unchanged'] = same_desc
            
        # Analyze Owner patterns
        if 'Owner' in self.df.columns:
            owner_merchants = defaultdict(Counter)
            for _, row in self.df.iterrows():
                if pd.notna(row.get('Owner')) and pd.notna(row.get('Merchant')):
                    owner_merchants[row['Owner']][row['Merchant']] += 1
            
            # Find merchants unique to each owner
            self.patterns['unique_merchants_by_owner'] = {}
            owners = list(owner_merchants.keys())
            for owner in owners:
                unique = set(owner_merchants[owner].keys())
                for other_owner in owners:
                    if other_owner != owner:
                        unique -= set(owner_merchants[other_owner].keys())
                self.patterns['unique_merchants_by_owner'][owner] = list(unique)[:20]
                
    def _extract_base_merchant(self, merchant: str) -> str:
        """Extract base merchant name for grouping"""
        # Remove common suffixes
        cleaned = re.sub(r'\s*(#\d+|Store \d+|\d{5,})\s*', '', merchant)
        cleaned = re.sub(r'\s*\b[A-Z]{2}\b$', '', cleaned)  # State codes
        cleaned = re.sub(r'\s*\b(LLC|Inc|Corp)\b\s*', '', cleaned, flags=re.I)
        
        # Take first 2-3 meaningful words
        words = cleaned.split()
        meaningful_words = [w for w in words if len(w) > 2][:3]
        
        return ' '.join(meaningful_words).strip().upper()
        
    def generate_cleaning_recommendations(self):
        """Generate specific cleaning recommendations based on patterns"""
        print("💡 Generating cleaning recommendations...")
        
        recommendations = {
            'description_cleaning': {},
            'merchant_standardization': {},
            'special_cases': {}
        }
        
        # Description cleaning recommendations
        if self.patterns.get('common_prefixes'):
            prefixes_to_remove = [
                prefix for prefix, count in self.patterns['common_prefixes'].items()
                if any(keyword in prefix.upper() for keyword in ['POS', 'DEBIT', 'PURCHASE', 'ACH'])
            ]
            recommendations['description_cleaning']['remove_prefixes'] = prefixes_to_remove
            
        # Merchant standardization
        merchant_mappings = {}
        for base_name, variations in self.merchant_variations.items():
            if len(variations) > 1:
                # Choose the most common or cleanest variation
                variation_list = list(variations)
                # Prefer shorter, cleaner names
                best_name = min(variation_list, key=lambda x: (len(x), x.count(' ')))
                for variant in variations:
                    if variant != best_name:
                        merchant_mappings[variant] = best_name
                        
        recommendations['merchant_standardization'] = dict(
            sorted(merchant_mappings.items(), key=lambda x: x[1])
        )
        
        # Special case handlers
        transfer_patterns = [
            merchant for merchant in self.df['Merchant'].dropna().unique()
            if re.search(r'(Transfer|Payment|Zelle|Venmo)', str(merchant), re.I)
        ]
        recommendations['special_cases']['transfer_merchants'] = transfer_patterns
        
        self.cleaning_rules = recommendations
        
    def save_analysis_results(self):
        """Save analysis results to files"""
        output_dir = Path('transaction_analysis_results')
        output_dir.mkdir(exist_ok=True)
        
        # Save pattern analysis
        with open(output_dir / 'pattern_analysis.json', 'w') as f:
            json.dump(dict(self.patterns), f, indent=2, default=str)
            
        # Save merchant variations
        merchant_report = []
        for base_name, variations in sorted(self.merchant_variations.items()):
            if len(variations) > 1:
                merchant_report.append({
                    'base_name': base_name,
                    'variations': sorted(list(variations)),
                    'count': len(variations)
                })
        
        with open(output_dir / 'merchant_variations.json', 'w') as f:
            json.dump(merchant_report[:100], f, indent=2)  # Top 100
            
        # Save cleaning recommendations
        with open(output_dir / 'cleaning_recommendations.json', 'w') as f:
            json.dump(self.cleaning_rules, f, indent=2)
            
        # Generate summary report
        self._generate_summary_report(output_dir)
        
        print(f"\n✅ Analysis complete! Results saved to {output_dir}/")
        
    def _generate_summary_report(self, output_dir: Path):
        """Generate human-readable summary report"""
        with open(output_dir / 'summary_report.txt', 'w') as f:
            f.write("TRANSACTION DATA ANALYSIS SUMMARY\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"Total Transactions Analyzed: {len(self.df)}\n")
            f.write(f"Date Range: {self.df['Date'].min()} to {self.df['Date'].max()}\n\n")
            
            f.write("DESCRIPTION PATTERNS\n")
            f.write("-" * 30 + "\n")
            if 'length_stats' in self.patterns:
                stats = self.patterns['length_stats']
                f.write(f"Average length: {stats['mean']:.1f} characters\n")
                f.write(f"95% are shorter than: {stats['percentile_95']:.0f} characters\n")
                
            f.write(f"\nCommon prefixes found:\n")
            for prefix, count in list(self.patterns.get('common_prefixes', {}).items())[:10]:
                f.write(f"  - '{prefix}': {count} occurrences\n")
                
            f.write("\nMERCHANT ANALYSIS\n")
            f.write("-" * 30 + "\n")
            f.write(f"Unique merchant groups: {len(self.merchant_variations)}\n")
            f.write(f"Merchants with variations: {sum(1 for v in self.merchant_variations.values() if len(v) > 1)}\n")
            
            # Top merchants by frequency
            merchant_counts = self.df['Merchant'].value_counts().head(20)
            f.write("\nTop 20 Merchants:\n")
            for merchant, count in merchant_counts.items():
                f.write(f"  - {merchant}: {count} transactions\n")
                
            f.write("\nCLEANING RECOMMENDATIONS\n")
            f.write("-" * 30 + "\n")
            if 'remove_prefixes' in self.cleaning_rules.get('description_cleaning', {}):
                f.write("Prefixes to remove:\n")
                for prefix in self.cleaning_rules['description_cleaning']['remove_prefixes'][:10]:
                    f.write(f"  - '{prefix}'\n")


# Generate the cleaning functions based on analysis
def generate_cleaning_functions(analysis_results_dir: Path):
    """Generate Python cleaning functions based on analysis results"""
    
    with open(analysis_results_dir / 'cleaning_recommendations.json', 'r') as f:
        rules = json.load(f)
        
    # Generate Python code for cleaning functions
    code = '''# Auto-generated cleaning functions based on data analysis

import re
import pandas as pd

# Prefixes to remove from descriptions
BANK_PREFIXES = {prefixes}

# Merchant standardization mappings
MERCHANT_MAPPINGS = {mappings}

def clean_description(original_desc):
    """Clean description based on discovered patterns"""
    if pd.isna(original_desc):
        return ""
    
    desc = str(original_desc)
    
    # Remove common bank prefixes
    for prefix in BANK_PREFIXES:
        if desc.upper().startswith(prefix.upper()):
            desc = desc[len(prefix):].strip()
    
    # Remove card numbers
    desc = re.sub(r'\\b\\d{{4,6}}\\*+\\d{{4}}\\b', '', desc)
    
    # Remove reference numbers
    desc = re.sub(r'REF\\s*\\d{{6,}}', '', desc, flags=re.I)
    
    # Clean up whitespace
    desc = ' '.join(desc.split())
    
    return desc.strip()

def standardize_merchant(merchant):
    """Standardize merchant names based on discovered patterns"""
    if pd.isna(merchant):
        return "Unknown"
    
    merchant_str = str(merchant).strip()
    
    # Apply direct mappings
    if merchant_str in MERCHANT_MAPPINGS:
        return MERCHANT_MAPPINGS[merchant_str]
    
    # Clean up common patterns
    cleaned = re.sub(r'\\s*(#\\d+|Store \\d+|\\d{{5,}})\\s*', '', merchant_str)
    cleaned = re.sub(r'\\s*\\b[A-Z]{{2}}\\b$', '', cleaned)  # State codes
    
    return cleaned.strip()
'''.format(
        prefixes=rules.get('description_cleaning', {}).get('remove_prefixes', []),
        mappings=rules.get('merchant_standardization', {})
    )
    
    with open(analysis_results_dir / 'generated_cleaning_functions.py', 'w') as f:
        f.write(code)
        

# Main execution
if __name__ == "__main__":
    # Path to your parquet file
    PARQUET_PATH = r"C:\BALANCE\output\financial_data_flexible.parquet"
    
    # Run analysis
    analyzer = TransactionAnalyzer(PARQUET_PATH)
    analyzer.analyze_all()
    
    # Generate cleaning functions
    generate_cleaning_functions(Path('transaction_analysis_results'))
    
    print("\n🎉 Analysis complete! Check the 'transaction_analysis_results' folder for:")
    print("  - pattern_analysis.json: Detailed pattern statistics")
    print("  - merchant_variations.json: Merchants that need standardization")
    print("  - cleaning_recommendations.json: Specific cleaning rules")
    print("  - summary_report.txt: Human-readable summary")
    print("  - generated_cleaning_functions.py: Ready-to-use cleaning code")