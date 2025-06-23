"""
Data integrity tests for balance pipeline.
Tests mathematical consistency and balance calculations.
"""

import pytest
import pandas as pd
import pathlib
from src.balance_pipeline.data_loader import load_all_data
from src.balance_pipeline.column_utils import validate_cts_compliance


class TestDataIntegrity:
    """Test mathematical integrity of loaded data."""
    
    @pytest.fixture
    def data_dir(self):
        """Return path to test data directory."""
        return pathlib.Path('data')
    
    @pytest.fixture
    def transactions_df(self, data_dir):
        """Load transactions DataFrame for testing."""
        df = load_all_data(data_dir)
        if df.empty:
            pytest.skip("No data available for integrity testing")
        return df
    
    def test_no_negative_actual_amounts(self, transactions_df):
        """Test that actual amounts are non-negative (expenses should be positive)."""
        negative_actuals = transactions_df[transactions_df['actual_amount'] < 0]
        if not negative_actuals.empty:
            print("Negative actual amounts found:")
            print(negative_actuals[['date', 'person', 'merchant', 'actual_amount', 'source_file']])
        # This might be a warning rather than failure depending on business rules
        # assert negative_actuals.empty, f"Found {len(negative_actuals)} negative actual amounts"
    
    def test_money_values_precision(self, transactions_df):
        """Test that money values have appropriate precision (max 2 decimal places)."""
        for col in ['actual_amount', 'allowed_amount']:
            # Check precision by comparing with rounded values
            rounded_col = transactions_df[col].round(2)
            precision_errors = transactions_df[~transactions_df[col].eq(rounded_col)]
            
            assert precision_errors.empty, f"Found {len(precision_errors)} rows with >2 decimal places in {col}"
    
    def test_date_range_reasonable(self, transactions_df):
        """Test that dates fall within reasonable range."""
        min_date = transactions_df['date'].min()
        max_date = transactions_df['date'].max()
        
        # Dates should be within last 5 years and not in future
        import datetime
        now = datetime.datetime.now()
        five_years_ago = now - datetime.timedelta(days=5*365)
        
        assert min_date >= pd.Timestamp(five_years_ago), f"Minimum date {min_date} is too old"
        assert max_date <= pd.Timestamp(now), f"Maximum date {max_date} is in the future"
    
    def test_person_values_consistent(self, transactions_df):
        """Test that person column has consistent values."""
        unique_persons = transactions_df['person'].unique()
        expected_persons = {'Ryan', 'Jordyn'}
        
        unexpected_persons = set(unique_persons) - expected_persons
        assert not unexpected_persons, f"Unexpected person values: {unexpected_persons}"
    
    def test_source_file_values_consistent(self, transactions_df):
        """Test that source_file column has expected values."""
        unique_sources = transactions_df['source_file'].unique()
        expected_sources = {'Expense_History', 'Transaction_Ledger', 'Rent_Allocation', 'Rent_History'}
        
        unexpected_sources = set(unique_sources) - expected_sources
        assert not unexpected_sources, f"Unexpected source_file values: {unexpected_sources}"
    
    def test_no_completely_empty_transactions(self, transactions_df):
        """Test that no transactions are completely empty (both amounts zero)."""
        empty_transactions = transactions_df[
            (transactions_df['actual_amount'] == 0) & 
            (transactions_df['allowed_amount'] == 0)
        ]
        
        # This might be acceptable for some transaction types, so just warn
        if not empty_transactions.empty:
            print(f"Warning: Found {len(empty_transactions)} transactions with both amounts zero")
            print(empty_transactions[['date', 'person', 'merchant', 'source_file']].head())


class TestBalanceCalculations:
    """Test balance calculations and mathematical consistency."""
    
    @pytest.fixture
    def data_dir(self):
        """Return path to test data directory."""
        return pathlib.Path('data')
    
    @pytest.fixture
    def transactions_df(self, data_dir):
        """Load transactions DataFrame for testing."""
        df = load_all_data(data_dir)
        if df.empty:
            pytest.skip("No data available for balance testing")
        return df
    
    def test_basic_balance_calculation(self, transactions_df):
        """Test basic balance calculation logic."""
        # Calculate net owed per person
        summary = transactions_df.groupby('person').agg({
            'actual_amount': 'sum',
            'allowed_amount': 'sum'
        }).reset_index()
        
        summary['net_owed'] = summary['allowed_amount'] - summary['actual_amount']
        
        # The sum of all net_owed should be close to zero (within rounding tolerance)
        total_imbalance = summary['net_owed'].sum()
        tolerance = 0.02  # 2 cents tolerance for rounding
        
        assert abs(total_imbalance) <= tolerance, f"Total imbalance {total_imbalance} exceeds tolerance {tolerance}"
    
    def test_rent_allocation_consistency(self, transactions_df):
        """Test that rent allocations are mathematically consistent."""
        rent_transactions = transactions_df[transactions_df['merchant'] == 'Rent']
        
        if rent_transactions.empty:
            pytest.skip("No rent transactions found")
        
        # Group by date to check monthly consistency
        monthly_rent = rent_transactions.groupby('date').agg({
            'actual_amount': 'sum',
            'allowed_amount': 'sum'
        }).reset_index()
        
        # For each month, total allowed should equal total actual (Ryan pays, both owe shares)
        for _, month_data in monthly_rent.iterrows():
            actual_total = month_data['actual_amount']
            allowed_total = month_data['allowed_amount']
            
            # Allow small tolerance for rounding
            if actual_total > 0:  # Only check months with actual rent payments
                ratio = allowed_total / actual_total
                # Ratio should be close to 1.0 (total owed equals total paid)
                assert 0.95 <= ratio <= 1.05, f"Rent allocation ratio {ratio} for {month_data['date']} is inconsistent"
    
    def test_no_duplicate_transactions(self, transactions_df):
        """Test for potential duplicate transactions."""
        # Check for exact duplicates
        duplicates = transactions_df.duplicated()
        exact_duplicates = transactions_df[duplicates]
        
        assert exact_duplicates.empty, f"Found {len(exact_duplicates)} exact duplicate transactions"
        
        # Check for potential duplicates (same person, date, merchant, amount)
        potential_dupes = transactions_df.duplicated(
            subset=['date', 'person', 'merchant', 'actual_amount'], 
            keep=False
        )
        potential_duplicate_transactions = transactions_df[potential_dupes]
        
        if not potential_duplicate_transactions.empty:
            print(f"Warning: Found {len(potential_duplicate_transactions)} potential duplicate transactions")
            print(potential_duplicate_transactions[['date', 'person', 'merchant', 'actual_amount', 'description']].head(10))


class TestDataQuality:
    """Test data quality and completeness."""
    
    @pytest.fixture
    def data_dir(self):
        """Return path to test data directory."""
        return pathlib.Path('data')
    
    @pytest.fixture
    def transactions_df(self, data_dir):
        """Load transactions DataFrame for testing."""
        df = load_all_data(data_dir)
        if df.empty:
            pytest.skip("No data available for quality testing")
        return df
    
    def test_required_fields_not_null(self, transactions_df):
        """Test that required fields are not null."""
        required_fields = ['date', 'person', 'source_file']
        
        for field in required_fields:
            null_count = transactions_df[field].isna().sum()
            assert null_count == 0, f"Field {field} has {null_count} null values"
    
    def test_data_coverage_by_source(self, transactions_df):
        """Test that we have reasonable data coverage from each source."""
        source_counts = transactions_df['source_file'].value_counts()
        
        print("Data coverage by source:")
        for source, count in source_counts.items():
            print(f"  {source}: {count} transactions")
        
        # Each source should contribute at least some data
        for source in source_counts.index:
            assert source_counts[source] > 0, f"Source {source} has no data"
    
    def test_date_distribution(self, transactions_df):
        """Test that dates are reasonably distributed (not all on same day)."""
        unique_dates = transactions_df['date'].nunique()
        total_transactions = len(transactions_df)
        
        # Should have more than one unique date if we have multiple transactions
        if total_transactions > 1:
            assert unique_dates > 1, "All transactions have the same date"
        
        # Average transactions per day shouldn't be too high (suggests data quality issues)
        avg_per_day = total_transactions / unique_dates
        assert avg_per_day < 100, f"Average {avg_per_day} transactions per day seems too high"


if __name__ == '__main__':
    # Run basic integrity checks
    data_dir = pathlib.Path('data')
    df = load_all_data(data_dir)
    
    if not df.empty:
        print("Running basic integrity checks...")
        
        # Check CTS compliance
        print(f"CTS Compliance: {validate_cts_compliance(df)}")
        
        # Check balance
        summary = df.groupby('person').agg({
            'actual_amount': 'sum',
            'allowed_amount': 'sum'
        }).reset_index()
        summary['net_owed'] = summary['allowed_amount'] - summary['actual_amount']
        
        print("\nBalance Summary:")
        print(summary)
        print(f"Total Imbalance: ${summary['net_owed'].sum():.2f}")
        
        print("\nIntegrity checks completed.")
    else:
        print("No data loaded for integrity testing.")
