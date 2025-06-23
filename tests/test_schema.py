"""
Schema compliance tests for balance pipeline loaders.
Ensures all loaders return CTS-compliant DataFrames.
"""

import pytest
import pandas as pd
import pathlib
from src.balance_pipeline.loaders import LOADER_REGISTRY
from src.balance_pipeline.column_utils import CTS, CTS_MONEY_COLS, validate_cts_compliance
from src.balance_pipeline.data_loader import load_all_data


class TestSchemaCompliance:
    """Test that all loaders return CTS-compliant DataFrames."""
    
    @pytest.fixture
    def data_dir(self):
        """Return path to test data directory."""
        return pathlib.Path('data')
    
    def test_cts_constant_definition(self):
        """Test that CTS constant is properly defined."""
        expected_columns = [
            'date', 'person', 'merchant', 'description',
            'actual_amount', 'allowed_amount', 'source_file'
        ]
        assert CTS == expected_columns
        assert len(CTS) == 7
        assert len(set(CTS)) == 7  # No duplicates
    
    def test_money_columns_definition(self):
        """Test that money columns are properly defined."""
        expected_money_cols = {'actual_amount', 'allowed_amount'}
        assert CTS_MONEY_COLS == expected_money_cols
    
    @pytest.mark.parametrize("loader_func", LOADER_REGISTRY)
    def test_loader_returns_cts_columns(self, loader_func, data_dir):
        """Test that each loader returns exactly CTS columns."""
        df = loader_func(data_dir)
        
        if df.empty:
            # Empty DataFrames should still have CTS structure
            assert list(df.columns) == CTS
        else:
            # Non-empty DataFrames must have exactly CTS columns
            assert list(df.columns) == CTS, f"{loader_func.__name__} returned wrong columns: {list(df.columns)}"
    
    @pytest.mark.parametrize("loader_func", LOADER_REGISTRY)
    def test_loader_money_column_dtypes(self, loader_func, data_dir):
        """Test that money columns have numeric dtypes."""
        df = loader_func(data_dir)
        
        if not df.empty:
            for col in CTS_MONEY_COLS:
                assert pd.api.types.is_numeric_dtype(df[col]), f"{loader_func.__name__} column {col} is not numeric: {df[col].dtype}"
    
    @pytest.mark.parametrize("loader_func", LOADER_REGISTRY)
    def test_loader_date_column_dtype(self, loader_func, data_dir):
        """Test that date column has datetime dtype."""
        df = loader_func(data_dir)
        
        if not df.empty:
            assert pd.api.types.is_datetime64_any_dtype(df['date']), f"{loader_func.__name__} date column is not datetime: {df['date'].dtype}"
    
    @pytest.mark.parametrize("loader_func", LOADER_REGISTRY)
    def test_loader_cts_compliance(self, loader_func, data_dir):
        """Test that each loader passes CTS validation."""
        df = loader_func(data_dir)
        assert validate_cts_compliance(df), f"{loader_func.__name__} failed CTS compliance"
    
    @pytest.mark.parametrize("loader_func", LOADER_REGISTRY)
    def test_loader_source_file_populated(self, loader_func, data_dir):
        """Test that source_file column is populated."""
        df = loader_func(data_dir)
        
        if not df.empty:
            assert not df['source_file'].isna().any(), f"{loader_func.__name__} has null source_file values"
            assert (df['source_file'] != '').all(), f"{loader_func.__name__} has empty source_file values"
    
    def test_load_all_data_cts_compliance(self, data_dir):
        """Test that load_all_data returns CTS-compliant DataFrame."""
        df = load_all_data(data_dir)
        assert validate_cts_compliance(df), "load_all_data failed CTS compliance"
    
    def test_load_all_data_no_duplicate_columns(self, data_dir):
        """Test that concatenation doesn't create duplicate columns."""
        df = load_all_data(data_dir)
        assert len(df.columns) == len(set(df.columns)), "Duplicate columns found after concatenation"
    
    def test_money_values_are_rounded(self, data_dir):
        """Test that money values are properly rounded to 2 decimal places."""
        df = load_all_data(data_dir)
        
        if not df.empty:
            for col in CTS_MONEY_COLS:
                # Check that all values have at most 2 decimal places
                rounded_values = df[col].round(2)
                assert df[col].equals(rounded_values), f"Column {col} has values with more than 2 decimal places"


class TestEmptyDataHandling:
    """Test handling of empty or missing data."""
    
    def test_empty_directory_handling(self, tmp_path):
        """Test behavior with empty data directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        
        df = load_all_data(empty_dir)
        assert df.empty or validate_cts_compliance(df)
        assert list(df.columns) == CTS
    
    def test_missing_directory_handling(self, tmp_path):
        """Test behavior with missing data directory."""
        missing_dir = tmp_path / "missing"
        
        with pytest.raises(FileNotFoundError):
            load_all_data(missing_dir)


class TestRoundTripConsistency:
    """Test that data can be saved and reloaded consistently."""
    
    @pytest.fixture
    def data_dir(self):
        """Return path to test data directory."""
        return pathlib.Path('data')
    
    def test_csv_round_trip(self, data_dir, tmp_path):
        """Test that CTS DataFrame can be saved to CSV and reloaded identically."""
        # Load original data
        original_df = load_all_data(data_dir)
        
        if original_df.empty:
            pytest.skip("No data to test round-trip")
        
        # Save to CSV
        csv_path = tmp_path / "test_output.csv"
        original_df.to_csv(csv_path, index=False)
        
        # Reload from CSV
        reloaded_df = pd.read_csv(csv_path)
        
        # Parse date column back to datetime
        reloaded_df['date'] = pd.to_datetime(reloaded_df['date'])
        
        # Compare DataFrames
        pd.testing.assert_frame_equal(original_df, reloaded_df)
        
        # Ensure CTS compliance is maintained
        assert validate_cts_compliance(reloaded_df)
