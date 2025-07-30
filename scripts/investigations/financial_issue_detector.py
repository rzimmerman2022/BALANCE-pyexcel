"""
Financial Issue Detection & Analysis System
Comprehensive tool to identify disputes, recurring patterns, anomalies, and potential issues
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import re
from collections import Counter
import warnings
warnings.filterwarnings('ignore')

class FinancialIssueDetector:
    """Comprehensive financial issue detection and analysis system"""
    
    def __init__(self, audit_file="integrated_audit_trail_with_zelle_20250702_103908.csv"):
        """Initialize with the comprehensive audit trail"""
        self.audit_file = audit_file
        self.df = None
        self.issues = {
            'duplicates': [],
            'anomalies': [],
            'disputes': [],
            'recurring_issues': [],
            'balance_discrepancies': [],
            'suspicious_patterns': [],
            'data_quality': []
        }
        
    def load_data(self):
        """Load and prepare the audit trail data"""
        print("🔍 Financial Issue Detection System Starting...")
        print("=" * 60)
        
        try:
            self.df = pd.read_csv(self.audit_file)
            self.df['Date'] = pd.to_datetime(self.df['Date'])
            print(f"✅ Loaded {len(self.df)} transactions from {self.audit_file}")
            return True
        except Exception as e:
            print(f"❌ Error loading data: {e}")
            return False
    
    def detect_all_issues(self):
        """Run comprehensive issue detection"""
        if not self.load_data():
            return None
            
        print("\n🔍 Running Comprehensive Issue Detection...")
        
        # 1. Duplicate Detection
        print("\n📋 Detecting Duplicate Transactions...")
        self.detect_duplicates()
        
        # 2. Amount Anomalies
        print("\n💰 Detecting Amount Anomalies...")
        self.detect_amount_anomalies()
        
        # 3. Dispute Indicators
        print("\n⚠️  Detecting Potential Disputes...")
        self.detect_dispute_indicators()
        
        # 4. Recurring Issues
        print("\n🔄 Detecting Recurring Patterns...")
        self.detect_recurring_issues()
        
        # 5. Balance Discrepancies
        print("\n📊 Checking Balance Discrepancies...")
        self.detect_balance_discrepancies()
        
        # 6. Suspicious Patterns
        print("\n🚨 Detecting Suspicious Patterns...")
        self.detect_suspicious_patterns()
        
        # 7. Data Quality Issues
        print("\n🔧 Checking Data Quality...")
        self.detect_data_quality_issues()
        
        # Generate comprehensive report
        self.generate_issue_report()
        
        return self.issues
    
    def detect_duplicates(self):
        """Detect potential duplicate transactions"""
        # Check for exact duplicates
        exact_dupes = self.df[self.df.duplicated(subset=['Date', 'Person', 'Amount_Paid', 'Description'], keep=False)]
        
        # Check for near-duplicates (same day, person, similar amount)
        near_dupes = []
        for person in self.df['Person'].unique():
            person_df = self.df[self.df['Person'] == person].copy()
            person_df = person_df.sort_values('Date')
            
            for i, row1 in person_df.iterrows():
                for j, row2 in person_df.iterrows():
                    if i >= j:
                        continue
                    
                    # Same day, similar amount (within $5)
                    if (row1['Date'] == row2['Date'] and 
                        abs(row1['Amount_Paid'] - row2['Amount_Paid']) <= 5.0 and
                        row1['Amount_Paid'] > 0 and row2['Amount_Paid'] > 0):
                        near_dupes.append({
                            'type': 'Near Duplicate',
                            'transaction_1': row1['Transaction_Number'],
                            'transaction_2': row2['Transaction_Number'],
                            'person': person,
                            'date': row1['Date'],
                            'amount_1': row1['Amount_Paid'],
                            'amount_2': row2['Amount_Paid'],
                            'desc_1': str(row1['Description'])[:50],
                            'desc_2': str(row2['Description'])[:50]
                        })
        
        self.issues['duplicates'] = {
            'exact_duplicates': len(exact_dupes),
            'near_duplicates': len(near_dupes),
            'exact_details': exact_dupes[['Transaction_Number', 'Date', 'Person', 'Amount_Paid', 'Description']].to_dict('records') if len(exact_dupes) > 0 else [],
            'near_details': near_dupes[:10]  # Top 10 near duplicates
        }
        
        print(f"  📋 Found {len(exact_dupes)} exact duplicates")
        print(f"  📋 Found {len(near_dupes)} potential near duplicates")
    
    def detect_amount_anomalies(self):
        """Detect unusual amounts and patterns"""
        anomalies = []
        
        # Statistical outliers
        amounts = self.df['Amount_Paid'].abs()
        q1, q3 = amounts.quantile([0.25, 0.75])
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        outliers = self.df[(amounts < lower_bound) | (amounts > upper_bound)]
        
        # Round number patterns (potential data entry errors)
        round_amounts = self.df[self.df['Amount_Paid'].apply(lambda x: x % 1 == 0 and x > 100)]
        
        # Unusual decimal patterns
        weird_decimals = self.df[self.df['Amount_Paid'].apply(
            lambda x: len(str(x).split('.')[-1]) > 2 if '.' in str(x) else False
        )]
        
        self.issues['anomalies'] = {
            'statistical_outliers': len(outliers),
            'round_amounts_over_100': len(round_amounts),
            'unusual_decimals': len(weird_decimals),
            'outlier_details': outliers[['Transaction_Number', 'Date', 'Person', 'Amount_Paid', 'Description']].head(10).to_dict('records'),
            'bounds': {'lower': lower_bound, 'upper': upper_bound}
        }
        
        print(f"  💰 Found {len(outliers)} statistical outliers")
        print(f"  💰 Found {len(round_amounts)} round amounts over $100")
        print(f"  💰 Found {len(weird_decimals)} unusual decimal patterns")
    
    def detect_dispute_indicators(self):
        """Detect potential dispute indicators in descriptions and patterns"""
        dispute_keywords = [
            'dispute', 'error', 'mistake', 'wrong', 'incorrect', 'refund', 'return',
            'cancel', 'reverse', 'fix', 'adjust', 'redo', 'owe', 'pay back',
            'question', '??', 'why', 'what happened', 'confused'
        ]
        
        disputes = []
        
        for _, row in self.df.iterrows():
            desc = str(row['Description']).lower()
            for keyword in dispute_keywords:
                if keyword in desc:
                    disputes.append({
                        'transaction_number': row['Transaction_Number'],
                        'date': row['Date'],
                        'person': row['Person'],
                        'amount': row['Amount_Paid'],
                        'description': row['Description'],
                        'keyword_found': keyword,
                        'type': 'Description Dispute Indicator'
                    })
                    break
        
        # Look for negative amounts (potential reversals)
        negative_amounts = self.df[self.df['Amount_Paid'] < 0]
        
        # Look for zero amounts with non-zero shares (potential disputes)
        zero_paid_nonzero_share = self.df[(self.df['Amount_Paid'] == 0) & (self.df['Share_Owed'] != 0)]
        
        self.issues['disputes'] = {
            'description_indicators': len(disputes),
            'negative_amounts': len(negative_amounts),
            'zero_paid_nonzero_share': len(zero_paid_nonzero_share),
            'description_details': disputes[:10],
            'negative_details': negative_amounts[['Transaction_Number', 'Date', 'Person', 'Amount_Paid', 'Description']].to_dict('records'),
            'zero_share_details': zero_paid_nonzero_share[['Transaction_Number', 'Date', 'Person', 'Amount_Paid', 'Share_Owed']].to_dict('records')
        }
        
        print(f"  ⚠️  Found {len(disputes)} description dispute indicators")
        print(f"  ⚠️  Found {len(negative_amounts)} negative amounts")
        print(f"  ⚠️  Found {len(zero_paid_nonzero_share)} zero-paid/non-zero-share transactions")
    
    def detect_recurring_issues(self):
        """Detect recurring patterns that might indicate ongoing issues"""
        # Recurring merchant/description patterns
        desc_counts = Counter()
        for desc in self.df['Description'].fillna(''):
            if len(desc) > 10:  # Only substantial descriptions
                desc_counts[desc] += 1
        
        frequent_descriptions = [(desc, count) for desc, count in desc_counts.items() if count >= 5]
        
        # Recurring amounts
        amount_counts = Counter(self.df['Amount_Paid'].round(2))
        frequent_amounts = [(amount, count) for amount, count in amount_counts.items() if count >= 5 and amount > 0]
        
        # Monthly recurring patterns
        self.df['Month_Year'] = self.df['Date'].dt.to_period('M')
        monthly_patterns = self.df.groupby(['Month_Year', 'Person', 'Transaction_Type']).size().reset_index(name='count')
        recurring_monthly = monthly_patterns[monthly_patterns['count'] >= 3]
        
        self.issues['recurring_issues'] = {
            'frequent_descriptions': len(frequent_descriptions),
            'frequent_amounts': len(frequent_amounts),
            'monthly_patterns': len(recurring_monthly),
            'description_details': frequent_descriptions[:10],
            'amount_details': sorted(frequent_amounts, key=lambda x: x[1], reverse=True)[:10],
            'monthly_details': recurring_monthly.to_dict('records')[:10]
        }
        
        print(f"  🔄 Found {len(frequent_descriptions)} frequently recurring descriptions")
        print(f"  🔄 Found {len(frequent_amounts)} frequently recurring amounts")
        print(f"  🔄 Found {len(recurring_monthly)} monthly recurring patterns")
    
    def detect_balance_discrepancies(self):
        """Check for balance calculation inconsistencies"""
        discrepancies = []
        
        # Check if running balance calculations are consistent
        for person in self.df['Person'].unique():
            person_df = self.df[self.df['Person'] == person].sort_values('Transaction_Number')
            expected_balance = 0
            
            for _, row in person_df.iterrows():
                expected_balance += row['Net_Effect']
                actual_balance = row['Running_Balance']
                
                if abs(expected_balance - actual_balance) > 0.01:  # Allow for small rounding errors
                    discrepancies.append({
                        'transaction_number': row['Transaction_Number'],
                        'person': person,
                        'date': row['Date'],
                        'expected_balance': expected_balance,
                        'actual_balance': actual_balance,
                        'difference': expected_balance - actual_balance
                    })
        
        # Check for impossible balance jumps
        large_jumps = []
        for person in self.df['Person'].unique():
            person_df = self.df[self.df['Person'] == person].sort_values('Transaction_Number')
            prev_balance = 0
            
            for _, row in person_df.iterrows():
                balance_change = abs(row['Running_Balance'] - prev_balance)
                net_effect = abs(row['Net_Effect'])
                
                if balance_change > net_effect * 2:  # Balance changed more than twice the net effect
                    large_jumps.append({
                        'transaction_number': row['Transaction_Number'],
                        'person': person,
                        'date': row['Date'],
                        'balance_change': balance_change,
                        'net_effect': net_effect,
                        'ratio': balance_change / max(net_effect, 0.01)
                    })
                
                prev_balance = row['Running_Balance']
        
        self.issues['balance_discrepancies'] = {
            'calculation_errors': len(discrepancies),
            'large_jumps': len(large_jumps),
            'calculation_details': discrepancies[:10],
            'jump_details': large_jumps[:10]
        }
        
        print(f"  📊 Found {len(discrepancies)} balance calculation discrepancies")
        print(f"  📊 Found {len(large_jumps)} unusual balance jumps")
    
    def detect_suspicious_patterns(self):
        """Detect potentially suspicious transaction patterns"""
        suspicious = []
        
        # Transactions on weekends/holidays that might be data entry errors
        weekend_transactions = self.df[self.df['Date'].dt.dayofweek >= 5]  # Saturday=5, Sunday=6
        
        # Very late night transactions (might be data entry errors)
        # Note: We don't have time data, so this is conceptual
        
        # Transactions with unusual payment vs share relationships
        unusual_share_relationships = self.df[
            (self.df['Amount_Paid'] > 0) & 
            (self.df['Share_Owed'] > self.df['Amount_Paid'] * 2)
        ]
        
        # Personal expenses incorrectly marked as shared
        potential_personal_marked_shared = self.df[
            (self.df['Transaction_Type'].str.contains('Personal', na=False)) &
            (self.df['Share_Owed'] > 0)
        ]
        
        self.issues['suspicious_patterns'] = {
            'weekend_transactions': len(weekend_transactions),
            'unusual_share_relationships': len(unusual_share_relationships),
            'personal_marked_shared': len(potential_personal_marked_shared),
            'weekend_details': weekend_transactions[['Transaction_Number', 'Date', 'Person', 'Amount_Paid']].head(10).to_dict('records'),
            'share_details': unusual_share_relationships[['Transaction_Number', 'Date', 'Person', 'Amount_Paid', 'Share_Owed']].to_dict('records'),
            'personal_shared_details': potential_personal_marked_shared[['Transaction_Number', 'Date', 'Person', 'Transaction_Type', 'Amount_Paid', 'Share_Owed']].to_dict('records')
        }
        
        print(f"  🚨 Found {len(weekend_transactions)} weekend transactions")
        print(f"  🚨 Found {len(unusual_share_relationships)} unusual share relationships")
        print(f"  🚨 Found {len(potential_personal_marked_shared)} personal expenses marked as shared")
    
    def detect_data_quality_issues(self):
        """Check for data quality problems"""
        quality_issues = {}
        
        # Missing descriptions
        missing_descriptions = self.df[self.df['Description'].isna() | (self.df['Description'] == '')]
        
        # Missing or zero amounts where they shouldn't be
        missing_amounts = self.df[self.df['Amount_Paid'].isna()]
        
        # Inconsistent transaction types
        type_inconsistencies = self.df[self.df['Transaction_Type'].isna()]
        
        # Source file inconsistencies
        missing_sources = self.df[self.df['Source_File'].isna()]
        
        # Date inconsistencies
        future_dates = self.df[self.df['Date'] > datetime.now()]
        very_old_dates = self.df[self.df['Date'] < datetime(2020, 1, 1)]
        
        self.issues['data_quality'] = {
            'missing_descriptions': len(missing_descriptions),
            'missing_amounts': len(missing_amounts),
            'missing_transaction_types': len(type_inconsistencies),
            'missing_sources': len(missing_sources),
            'future_dates': len(future_dates),
            'very_old_dates': len(very_old_dates),
            'total_records': len(self.df)
        }
        
        print(f"  🔧 Found {len(missing_descriptions)} missing descriptions")
        print(f"  🔧 Found {len(missing_amounts)} missing amounts")
        print(f"  🔧 Found {len(type_inconsistencies)} missing transaction types")
        print(f"  🔧 Found {len(future_dates)} future dates")
    
    def generate_issue_report(self):
        """Generate comprehensive issue report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"financial_issues_report_{timestamp}.txt"
        
        with open(report_file, 'w') as f:
            f.write("BALANCE PROJECT - FINANCIAL ISSUES ANALYSIS REPORT\n")
            f.write("=" * 60 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Source File: {self.audit_file}\n")
            f.write(f"Total Transactions Analyzed: {len(self.df)}\n\n")
            
            # Summary of all issues
            f.write("ISSUE SUMMARY:\n")
            f.write("-" * 30 + "\n")
            
            total_issues = 0
            for category, data in self.issues.items():
                if isinstance(data, dict):
                    category_total = sum(v for k, v in data.items() if isinstance(v, int))
                    total_issues += category_total
                    f.write(f"{category.upper()}: {category_total} issues found\n")
            
            f.write(f"\nTOTAL ISSUES IDENTIFIED: {total_issues}\n\n")
            
            # Detailed breakdown
            for category, data in self.issues.items():
                f.write(f"\n{category.upper()} DETAILS:\n")
                f.write("-" * 40 + "\n")
                
                if isinstance(data, dict):
                    for key, value in data.items():
                        if isinstance(value, (int, float)):
                            f.write(f"  {key}: {value}\n")
                        elif isinstance(value, list) and value:
                            f.write(f"  {key}: {len(value)} items\n")
                            if key.endswith('_details') and len(value) > 0:
                                f.write(f"    Sample: {str(value[0])[:100]}...\n")
        
        print(f"\n📝 Comprehensive issue report saved: {report_file}")
        return report_file

def main():
    """Run the financial issue detection system"""
    detector = FinancialIssueDetector()
    issues = detector.detect_all_issues()
    
    if issues:
        print("\n🎯 ISSUE DETECTION COMPLETE!")
        print("=" * 60)
        
        # Print summary
        for category, data in issues.items():
            if isinstance(data, dict):
                total = sum(v for k, v in data.items() if isinstance(v, int))
                if total > 0:
                    print(f"⚠️  {category.upper()}: {total} issues found")
        
        print("\n💡 Review the generated report file for detailed analysis!")
    
    return issues

if __name__ == "__main__":
    main()
