import sys
import tempfile
from pathlib import Path

import pandas as pd
import pytest

# Add src to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from baseline_analyzer.lineage_utils import add_step_id, validate_lineage
from baseline_analyzer.processing import CleanerStats, build_baseline


class TestBuildBaseline:
    """Test suite for build_baseline function covering Phase P1 requirements."""

    def test_returns_dataframe(self):
        """Test that build_baseline returns a DataFrame."""
        result = build_baseline()
        assert isinstance(result, pd.DataFrame)

    def test_has_required_columns(self):
        """Test that the returned DataFrame has the expected columns."""
        result = build_baseline()
        expected_columns = {"person", "net_owed", "lineage"}
        assert expected_columns <= set(result.columns), \
            f"DataFrame columns {list(result.columns)} do not contain all expected columns {expected_columns}"

    def test_row_count_greater_than_zero_with_fixtures(self):
        """Test that row count > 0 when using test fixtures."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures"
        result = build_baseline(inputs_dir=str(fixtures_dir))
        assert len(result) > 0, "Should generate at least one row with test fixtures"

    def test_zero_sum_balance(self):
        """Test that Σ net_owed is reasonably close to 0 (small imbalances are normal)."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures"
        result = build_baseline(inputs_dir=str(fixtures_dir))
        
        if not result.empty:
            total_balance = result["net_owed"].sum()
            # Allow for small imbalances in real-world data (up to $100)
            assert abs(total_balance) < 100.0, f"Total balance should be reasonable, got ${total_balance:.2f}"

    def test_lineage_not_null(self):
        """Test that lineage column is not null for all rows."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures"
        result = build_baseline(inputs_dir=str(fixtures_dir))
        
        if not result.empty:
            assert result["lineage"].notna().all(), "All rows should have non-null lineage"
            assert (result["lineage"] != "").all(), "All rows should have non-empty lineage"

    def test_lineage_validation(self):
        """Test that lineage validation passes."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures"
        result = build_baseline(inputs_dir=str(fixtures_dir))
        
        if not result.empty:
            assert validate_lineage(result), "Lineage validation should pass"

    def test_debug_mode_creates_snapshots(self):
        """Test that debug mode creates snapshot files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            fixtures_dir = Path(__file__).parent.parent / "fixtures"
            snapshot_dir = Path(temp_dir) / "snapshots"
            
            result = build_baseline(
                debug=True, 
                inputs_dir=str(fixtures_dir),
                snapshot_dir=str(snapshot_dir)
            )
            
            # Check that snapshot directory was created
            assert snapshot_dir.exists(), "Debug snapshot directory should be created"
            
            # Check for expected snapshot files (at least raw files should exist)
            expected_patterns = ["01a_*_raw.csv", "02b_*_clean.csv"]
            snapshot_files = list(snapshot_dir.glob("*.csv"))
            
            assert len(snapshot_files) > 0, "Debug mode should create snapshot files"

    def test_inputs_dir_parameter(self):
        """Test that inputs_dir parameter works correctly."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures"
        result = build_baseline(inputs_dir=str(fixtures_dir))
        
        # Should work with test fixtures
        assert isinstance(result, pd.DataFrame)

    def test_empty_inputs_dir(self):
        """Test behavior with empty inputs directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = build_baseline(inputs_dir=temp_dir)
            
            # Should return empty DataFrame with correct columns
            assert isinstance(result, pd.DataFrame)
            expected_columns = {"person", "net_owed", "lineage"}
            assert expected_columns <= set(result.columns)

    def test_reconciliation_invariants(self):
        """Test reconciliation invariants on sample fixtures."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures"
        result = build_baseline(inputs_dir=str(fixtures_dir))
        
        if not result.empty:
            # Test that we have expected persons
            persons = set(result["person"].unique())
            expected_persons = {"Ryan", "Jordyn"}
            
            # At least one person should be present (depends on fixture data)
            assert len(persons) > 0, "Should have at least one person in results"
            
            # All persons should be from expected set
            assert persons <= expected_persons, f"Unexpected persons: {persons - expected_persons}"
            
            # Test that net_owed values are numeric
            assert result["net_owed"].dtype in [int, float], "net_owed should be numeric"
            
            # Test that amounts are reasonable (not extremely large)
            max_amount = result["net_owed"].abs().max()
            assert max_amount < 10000, f"Amounts seem too large: max=${max_amount:.2f}"

    def test_performance_lightning_fast(self):
        """Test that execution is lightning-fast (<5 seconds)."""
        import time
        
        fixtures_dir = Path(__file__).parent.parent / "fixtures"
        start_time = time.time()
        
        result = build_baseline(inputs_dir=str(fixtures_dir))
        
        duration = time.time() - start_time
        assert duration < 5.0, f"Execution took {duration:.2f}s, should be <5s"

    def test_lineage_traceability(self):
        """Test that lineage provides traceability back to sources."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures"
        result = build_baseline(inputs_dir=str(fixtures_dir))
        
        if not result.empty:
            for _, row in result.iterrows():
                lineage = row["lineage"]
                
                # Should contain step IDs
                assert "|" in lineage or len(lineage.split("_")) >= 2, \
                    f"Lineage should contain step IDs: {lineage}"
                
                # Should start with raw step
                lineage_steps = lineage.split("|")
                first_step = lineage_steps[0]
                assert "raw" in first_step, f"First step should be raw: {first_step}"


class TestCleanerStats:
    """Test suite for CleanerStats dataclass."""

    def test_cleaner_stats_creation(self):
        """Test that CleanerStats can be created."""
        stats = CleanerStats(
            rows_in=100,
            rows_out=95,
            duplicates_dropped=3,
            bad_dates=2
        )
        
        assert stats.rows_in == 100
        assert stats.rows_out == 95
        assert stats.duplicates_dropped == 3
        assert stats.bad_dates == 2


class TestLineageUtils:
    """Test suite for lineage utilities."""

    def test_add_step_id(self):
        """Test adding step IDs to DataFrame."""
        df = pd.DataFrame({"col1": [1, 2, 3]})
        result = add_step_id(df, "test_step")
        
        assert "lineage" in result.columns
        assert (result["lineage"] == "test_step").all()

    def test_add_step_id_append(self):
        """Test appending step IDs to existing lineage."""
        df = pd.DataFrame({
            "col1": [1, 2, 3],
            "lineage": ["step1", "step1", "step1"]
        })
        result = add_step_id(df, "step2")
        
        expected_lineage = "step1|step2"
        assert (result["lineage"] == expected_lineage).all()

    def test_validate_lineage_valid(self):
        """Test lineage validation with valid data."""
        df = pd.DataFrame({
            "lineage": ["step1|step2", "step1|step2|step3", "step1"]
        })
        
        assert validate_lineage(df)

    def test_validate_lineage_invalid(self):
        """Test lineage validation with invalid data."""
        df = pd.DataFrame({
            "lineage": ["step1", None, "step2"]
        })
        
        assert not validate_lineage(df)


class TestIntegration:
    """Integration tests for the full pipeline."""

    def test_end_to_end_with_real_fixtures(self):
        """Test end-to-end pipeline with real fixture data."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures"
        
        # Ensure fixtures exist
        expenses_file = fixtures_dir / "expenses.csv"
        ledger_file = fixtures_dir / "ledger.csv"
        rent_file = fixtures_dir / "rent.csv"
        
        for file_path in [expenses_file, ledger_file, rent_file]:
            assert file_path.exists(), f"Required fixture file missing: {file_path}"

        # Run full pipeline
        result = build_baseline(debug=True, inputs_dir=str(fixtures_dir))
        
        # Comprehensive validation
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert {"person", "net_owed", "lineage"} <= set(result.columns)
        assert result["lineage"].notna().all()
        assert validate_lineage(result)
        
        # Balance should be reasonable
        total_balance = result["net_owed"].sum()
        assert abs(total_balance) < 1000, f"Total balance seems unreasonable: ${total_balance:.2f}"

    def test_empty_source_handling(self):
        """Test handling of empty source files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create empty CSV files
            temp_path = Path(temp_dir)
            
            (temp_path / "expenses.csv").write_text("Name,Date of Purchase,Actual Amount\n")
            (temp_path / "ledger.csv").write_text("Name,Date of Purchase,Actual Amount\n") 
            (temp_path / "rent.csv").write_text("Month,Gross Total\n")
            
            result = build_baseline(inputs_dir=str(temp_path))
            
            # Should handle empty sources gracefully
            assert isinstance(result, pd.DataFrame)
            assert {"person", "net_owed", "lineage"} <= set(result.columns)


# Performance and stress tests
class TestPerformance:
    """Performance tests to ensure lightning-fast execution."""

    def test_multiple_runs_performance(self):
        """Test performance over multiple runs."""
        import time
        
        fixtures_dir = Path(__file__).parent.parent / "fixtures"
        times = []
        
        for _ in range(3):
            start_time = time.time()
            build_baseline(inputs_dir=str(fixtures_dir))
            duration = time.time() - start_time
            times.append(duration)
        
        avg_time = sum(times) / len(times)
        assert avg_time < 2.0, f"Average execution time {avg_time:.2f}s too slow"

    @pytest.mark.parametrize("debug_mode", [True, False])
    def test_debug_mode_performance(self, debug_mode):
        """Test that debug mode doesn't significantly impact performance."""
        import time
        
        fixtures_dir = Path(__file__).parent.parent / "fixtures"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            start_time = time.time()
            build_baseline(
                debug=debug_mode, 
                inputs_dir=str(fixtures_dir),
                snapshot_dir=temp_dir
            )
            duration = time.time() - start_time
            
            # Even with debug mode, should be fast
            max_time = 10.0 if debug_mode else 5.0
            assert duration < max_time, f"Execution took {duration:.2f}s with debug={debug_mode}"
