"""
ZELLE MATCHER - Cross-reference Zelle payments with existing expense data
Identifies which Zelle payments are already included and which are missing
"""

from datetime import datetime

import pandas as pd


def load_existing_expense_data():
    """Load the existing expense data for comparison"""
    print("Loading existing expense data...")
    
    try:
        df = pd.read_csv("data/Consolidated_Expense_History_20250622.csv")
        
        # Clean column names
        df.columns = df.columns.str.strip()
        
        # Clean the data similar to our main processing
        df = df[df['Name'].notna() & ~df['Name'].str.contains('Name', na=False)]
        df['Date of Purchase'] = pd.to_datetime(df['Date of Purchase'], errors='coerce')
        
        # Filter to 2024+
        cutoff_date = datetime(2024, 1, 1)
        df = df[df['Date of Purchase'] >= cutoff_date]
        
        # Clean amounts
        def clean_amount(value):
            if pd.isna(value):
                return 0.0
            str_val = str(value).strip().replace('$', '').replace(',', '').replace(' ', '')
            try:
                return float(str_val)
            except:
                return 0.0
        
        df['Actual Amount'] = df['Actual Amount'].apply(clean_amount)
        
        print(f"Loaded {len(df)} existing expense transactions from 2024+")
        return df
        
    except Exception as e:
        print(f"Error loading expense data: {e}")
        return None

def load_zelle_data():
    """Load the processed Zelle data"""
    print("Loading processed Zelle data...")
    
    try:
        df = pd.read_csv("data/processed_zelle_transactions.csv")
        print(f"Loaded {len(df)} Zelle transactions")
        return df
    except Exception as e:
        print(f"Error loading Zelle data: {e}")
        print("Make sure you've run zelle_data_loader.py first!")
        return None

def find_potential_matches(zelle_df, expense_df, date_tolerance_days=3, amount_tolerance_pct=0.05):
    """
    Find potential matches between Zelle payments and existing expenses
    
    Args:
        date_tolerance_days: How many days difference to allow for date matching
        amount_tolerance_pct: Percentage tolerance for amount matching (e.g., 0.05 = 5%)
    """
    print(f"\nFinding matches with {date_tolerance_days} day date tolerance and {amount_tolerance_pct*100}% amount tolerance...")
    
    matches = []
    
    for zelle_idx, zelle_row in zelle_df.iterrows():
        zelle_date = pd.to_datetime(zelle_row['Date'])
        zelle_amount = abs(zelle_row['Amount_Clean'])  # Use absolute value
        
        # Look for potential matches in expense data
        for expense_idx, expense_row in expense_df.iterrows():
            expense_date = pd.to_datetime(expense_row['Date of Purchase'])
            expense_amount = abs(expense_row['Actual Amount'])
            
            # Check date proximity
            date_diff = abs((zelle_date - expense_date).days)
            if date_diff > date_tolerance_days:
                continue
            
            # Check amount proximity
            if expense_amount == 0:
                continue
            
            amount_diff_pct = abs(zelle_amount - expense_amount) / expense_amount
            if amount_diff_pct > amount_tolerance_pct:
                continue
            
            # Found a potential match!
            match = {
                'zelle_idx': zelle_idx,
                'expense_idx': expense_idx,
                'zelle_date': zelle_date,
                'expense_date': expense_date,
                'date_diff_days': date_diff,
                'zelle_amount': zelle_amount,
                'expense_amount': expense_amount,
                'amount_diff_pct': amount_diff_pct,
                'zelle_description': zelle_row['Description'],
                'expense_description': expense_row.get('Description', ''),
                'expense_merchant': expense_row.get('Merchant', ''),
                'zelle_person': zelle_row.get('Person', 'Unknown'),
                'expense_person': expense_row.get('Name', 'Unknown'),
                'match_confidence': 1.0 - (date_diff / date_tolerance_days + amount_diff_pct)
            }
            
            matches.append(match)
    
    # Convert to DataFrame and sort by confidence
    if matches:
        matches_df = pd.DataFrame(matches)
        matches_df = matches_df.sort_values('match_confidence', ascending=False)
        print(f"Found {len(matches_df)} potential matches")
        return matches_df
    else:
        print("No potential matches found")
        return pd.DataFrame()

def identify_unmatched_zelle_payments(zelle_df, matches_df):
    """Identify Zelle payments that don't have matches in existing expense data"""
    if len(matches_df) == 0:
        return zelle_df  # All Zelle payments are unmatched
    
    matched_zelle_indices = matches_df['zelle_idx'].unique()
    unmatched_mask = ~zelle_df.index.isin(matched_zelle_indices)
    unmatched_df = zelle_df[unmatched_mask].copy()
    
    print(f"Found {len(unmatched_df)} unmatched Zelle payments that need to be added")
    return unmatched_df

def generate_match_report(matches_df, zelle_df, expense_df):
    """Generate a detailed report of matches and recommendations"""
    print("\n" + "=" * 80)
    print("ZELLE MATCHING REPORT")
    print("=" * 80)
    
    if len(matches_df) == 0:
        print("No matches found between Zelle and existing expense data")
        print(f"All {len(zelle_df)} Zelle payments should be added to reconciliation")
        return
    
    print(f"Total Zelle transactions: {len(zelle_df)}")
    print(f"Potential matches found: {len(matches_df)}")
    print(f"Unique Zelle payments with matches: {matches_df['zelle_idx'].nunique()}")
    print(f"Unique expense records with matches: {matches_df['expense_idx'].nunique()}")
    
    # High confidence matches (likely duplicates)
    high_confidence = matches_df[matches_df['match_confidence'] > 0.8]
    print(f"\nHigh confidence matches (likely duplicates): {len(high_confidence)}")
    
    if len(high_confidence) > 0:
        print("Top high-confidence matches:")
        display_cols = ['zelle_date', 'expense_date', 'zelle_amount', 'expense_amount', 
                       'zelle_description', 'expense_merchant', 'match_confidence']
        print(high_confidence[display_cols].head(10).to_string(index=False))
    
    # Medium confidence matches (need review)
    medium_confidence = matches_df[
        (matches_df['match_confidence'] > 0.5) & 
        (matches_df['match_confidence'] <= 0.8)
    ]
    print(f"\nMedium confidence matches (need manual review): {len(medium_confidence)}")
    
    # Low confidence matches (probably not duplicates)
    low_confidence = matches_df[matches_df['match_confidence'] <= 0.5]
    print(f"Low confidence matches (probably different transactions): {len(low_confidence)}")
    
    # Unmatched Zelle payments
    matched_zelle_indices = matches_df['zelle_idx'].unique()
    unmatched_count = len(zelle_df) - len(matched_zelle_indices)
    print(f"\nUnmatched Zelle payments (should be added): {unmatched_count}")

def save_matching_results(matches_df, unmatched_zelle_df, timestamp=None):
    """Save the matching results for review"""
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save matches
    if len(matches_df) > 0:
        matches_file = f"zelle_matches_{timestamp}.csv"
        matches_df.to_csv(matches_file, index=False)
        print(f"Potential matches saved to: {matches_file}")
    
    # Save unmatched Zelle payments
    if len(unmatched_zelle_df) > 0:
        unmatched_file = f"unmatched_zelle_payments_{timestamp}.csv"
        unmatched_zelle_df.to_csv(unmatched_file, index=False)
        print(f"Unmatched Zelle payments saved to: {unmatched_file}")

def main():
    """Main matching process"""
    print("ZELLE PAYMENT MATCHER")
    print("=" * 50)
    
    # Load data
    expense_df = load_existing_expense_data()
    zelle_df = load_zelle_data()
    
    if expense_df is None or zelle_df is None:
        print("Cannot proceed without both datasets")
        return
    
    # Find matches
    matches_df = find_potential_matches(zelle_df, expense_df)
    
    # Identify unmatched Zelle payments
    unmatched_zelle_df = identify_unmatched_zelle_payments(zelle_df, matches_df)
    
    # Generate report
    generate_match_report(matches_df, zelle_df, expense_df)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_matching_results(matches_df, unmatched_zelle_df, timestamp)
    
    print("\n" + "=" * 80)
    print("NEXT STEPS:")
    print("1. Review the match files to confirm which are duplicates")
    print("2. Use zelle_integration.py to add unmatched payments to reconciliation")
    print("=" * 80)

if __name__ == "__main__":
    main()
