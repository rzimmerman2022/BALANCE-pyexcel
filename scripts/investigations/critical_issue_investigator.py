"""
Critical Issue Investigation Tool
Interactive tool to investigate and resolve the most important financial issues
"""


import pandas as pd


class CriticalIssueInvestigator:
    """Tool for investigating and resolving critical financial issues"""
    
    def __init__(self, audit_file="integrated_audit_trail_with_zelle_20250702_103908.csv"):
        self.audit_file = audit_file
        self.df = None
        self.load_data()
    
    def load_data(self):
        """Load the audit trail data"""
        try:
            self.df = pd.read_csv(self.audit_file)
            self.df['Date'] = pd.to_datetime(self.df['Date'])
            print(f"✅ Loaded {len(self.df)} transactions")
        except Exception as e:
            print(f"❌ Error loading data: {e}")
    
    def investigate_exact_duplicates(self):
        """Show exact duplicates for manual review"""
        print("\n🔍 EXACT DUPLICATES INVESTIGATION")
        print("=" * 50)
        
        # Find exact duplicates
        duplicate_mask = self.df.duplicated(subset=['Date', 'Person', 'Amount_Paid', 'Description'], keep=False)
        duplicates = self.df[duplicate_mask].sort_values(['Date', 'Person', 'Amount_Paid'])
        
        if len(duplicates) == 0:
            print("✅ No exact duplicates found!")
            return None
        
        print(f"Found {len(duplicates)} duplicate transactions:")
        print("-" * 50)
        
        # Group duplicates for easier review
        grouped = duplicates.groupby(['Date', 'Person', 'Amount_Paid', 'Description'])
        
        for i, (key, group) in enumerate(grouped, 1):
            date, person, amount, desc = key
            print(f"\n{i}. DUPLICATE GROUP:")
            print(f"   Date: {date.strftime('%Y-%m-%d')}")
            print(f"   Person: {person}")
            print(f"   Amount: ${amount:.2f}")
            print(f"   Description: {str(desc)[:60]}...")
            print(f"   Transaction Numbers: {list(group['Transaction_Number'])}")
            print(f"   Source Files: {list(group['Source_File'].unique())}")
            
            if i >= 10:  # Limit to first 10 groups
                print(f"\n... and {len(grouped) - 10} more duplicate groups")
                break
        
        return duplicates
    
    def investigate_dispute_indicators(self):
        """Show transactions with dispute keywords"""
        print("\n⚠️  DISPUTE INDICATORS INVESTIGATION")
        print("=" * 50)
        
        dispute_keywords = ['error', 'mistake', 'wrong', 'incorrect', 'why', '??', 'confused', 'question']
        
        disputes = []
        for _, row in self.df.iterrows():
            desc = str(row['Description']).lower()
            for keyword in dispute_keywords:
                if keyword in desc:
                    disputes.append({
                        'transaction': row['Transaction_Number'],
                        'date': row['Date'],
                        'person': row['Person'],
                        'amount': row['Amount_Paid'],
                        'description': row['Description'],
                        'keyword': keyword,
                        'balance_impact': row['Net_Effect']
                    })
                    break
        
        if len(disputes) == 0:
            print("✅ No dispute indicators found!")
            return None
        
        print(f"Found {len(disputes)} transactions with dispute indicators:")
        print("-" * 50)
        
        for i, dispute in enumerate(disputes[:15], 1):  # Show first 15
            print(f"\n{i}. Transaction #{dispute['transaction']}")
            print(f"   Date: {dispute['date'].strftime('%Y-%m-%d')}")
            print(f"   Person: {dispute['person']}")
            print(f"   Amount: ${dispute['amount']:.2f}")
            print(f"   Balance Impact: ${dispute['balance_impact']:.2f}")
            print(f"   Keyword Found: '{dispute['keyword']}'")
            print(f"   Description: {dispute['description']}")
        
        if len(disputes) > 15:
            print(f"\n... and {len(disputes) - 15} more dispute indicators")
        
        return disputes
    
    def investigate_negative_amounts(self):
        """Show transactions with negative amounts (potential reversals)"""
        print("\n💸 NEGATIVE AMOUNTS INVESTIGATION")
        print("=" * 50)
        
        negative = self.df[self.df['Amount_Paid'] < 0]
        
        if len(negative) == 0:
            print("✅ No negative amounts found!")
            return None
        
        print(f"Found {len(negative)} transactions with negative amounts:")
        print("-" * 50)
        
        for _, row in negative.iterrows():
            print(f"\nTransaction #{row['Transaction_Number']}")
            print(f"  Date: {row['Date'].strftime('%Y-%m-%d')}")
            print(f"  Person: {row['Person']}")
            print(f"  Amount: ${row['Amount_Paid']:.2f}")
            print(f"  Type: {row['Transaction_Type']}")
            print(f"  Description: {row['Description']}")
            print(f"  Source: {row['Source_File']}")
            print(f"  Balance Impact: ${row['Net_Effect']:.2f}")
        
        return negative
    
    def investigate_missing_descriptions(self):
        """Show transactions with missing descriptions"""
        print("\n📝 MISSING DESCRIPTIONS INVESTIGATION")
        print("=" * 50)
        
        missing_desc = self.df[self.df['Description'].isna() | (self.df['Description'] == '')]
        
        if len(missing_desc) == 0:
            print("✅ All transactions have descriptions!")
            return None
        
        print(f"Found {len(missing_desc)} transactions with missing descriptions:")
        print("-" * 50)
        
        # Group by person and show summary
        summary = missing_desc.groupby('Person').agg({
            'Transaction_Number': 'count',
            'Amount_Paid': ['sum', 'mean']
        }).round(2)
        
        print("\nSUMMARY BY PERSON:")
        for person, data in summary.iterrows():
            count = data[('Transaction_Number', 'count')]
            total = data[('Amount_Paid', 'sum')]
            avg = data[('Amount_Paid', 'mean')]
            print(f"  {person}: {count} transactions, ${total:.2f} total, ${avg:.2f} average")
        
        # Show recent missing descriptions
        print("\nRECENT TRANSACTIONS WITH MISSING DESCRIPTIONS:")
        recent_missing = missing_desc.nlargest(10, 'Date')
        
        for _, row in recent_missing.iterrows():
            print(f"\n  Transaction #{row['Transaction_Number']}")
            print(f"    Date: {row['Date'].strftime('%Y-%m-%d')}")
            print(f"    Person: {row['Person']}")
            print(f"    Amount: ${row['Amount_Paid']:.2f}")
            print(f"    Type: {row['Transaction_Type']}")
            print(f"    Source: {row['Source_File']}")
        
        return missing_desc
    
    def investigate_rent_allocation_issues(self):
        """Show rent allocation discrepancies"""
        print("\n🏠 RENT ALLOCATION ISSUES INVESTIGATION")
        print("=" * 50)
        
        # Zero paid but non-zero share owed
        rent_issues = self.df[(self.df['Amount_Paid'] == 0) & (self.df['Share_Owed'] != 0)]
        
        if len(rent_issues) == 0:
            print("✅ No rent allocation issues found!")
            return None
        
        print(f"Found {len(rent_issues)} rent allocation discrepancies:")
        print("-" * 50)
        
        for _, row in rent_issues.iterrows():
            print(f"\nTransaction #{row['Transaction_Number']}")
            print(f"  Date: {row['Date'].strftime('%Y-%m-%d')}")
            print(f"  Person: {row['Person']}")
            print(f"  Amount Paid: ${row['Amount_Paid']:.2f}")
            print(f"  Share Owed: ${row['Share_Owed']:.2f}")
            print(f"  Net Effect: ${row['Net_Effect']:.2f}")
            print(f"  Description: {row['Description']}")
            print(f"  Type: {row['Transaction_Type']}")
        
        return rent_issues
    
    def investigate_large_outliers(self):
        """Show largest transaction outliers"""
        print("\n💰 LARGE TRANSACTION OUTLIERS")
        print("=" * 50)
        
        # Get top 20 largest amounts
        largest = self.df.nlargest(20, 'Amount_Paid')
        
        print("Top 20 largest transactions:")
        print("-" * 50)
        
        for i, (_, row) in enumerate(largest.iterrows(), 1):
            print(f"\n{i}. Transaction #{row['Transaction_Number']}")
            print(f"   Date: {row['Date'].strftime('%Y-%m-%d')}")
            print(f"   Person: {row['Person']}")
            print(f"   Amount: ${row['Amount_Paid']:,.2f}")
            print(f"   Type: {row['Transaction_Type']}")
            print(f"   Description: {str(row['Description'])[:60]}...")
        
        return largest
    
    def run_priority_investigation(self):
        """Run investigation on all priority issues"""
        print("🔍 CRITICAL ISSUES PRIORITY INVESTIGATION")
        print("=" * 60)
        print(f"Analyzing {len(self.df)} transactions...")
        
        # Run all investigations
        self.investigate_exact_duplicates()
        self.investigate_dispute_indicators()
        self.investigate_negative_amounts()
        self.investigate_rent_allocation_issues()
        self.investigate_missing_descriptions()
        self.investigate_large_outliers()
        
        print("\n✅ PRIORITY INVESTIGATION COMPLETE!")
        print("=" * 60)
        print("Review the findings above and prioritize resolution based on:")
        print("1. Exact duplicates (highest priority)")
        print("2. Dispute indicators (transaction errors)")
        print("3. Negative amounts (potential reversals)")
        print("4. Rent allocation issues (balance accuracy)")
        print("5. Missing descriptions (audit compliance)")
        print("6. Large outliers (verification needed)")

def main():
    """Run the critical issue investigator"""
    investigator = CriticalIssueInvestigator()
    investigator.run_priority_investigation()

if __name__ == "__main__":
    main()
