# -*- coding: utf-8 -*-
import pytest
import pandas as pd
import csv
from pathlib import Path
# import importlib  # No longer needed for reloading
import logging

# Module to test
from balance_pipeline import normalize
from balance_pipeline.config import MERCHANT_LOOKUP_PATH as REAL_MERCHANT_LOOKUP_PATH
from balance_pipeline.utils import _clean_desc_single  # For fallback comparison

# Store the original module state for _merchant_lookup_data if needed for reset
# ORIGINAL_MERCHANT_LOOKUP_DATA = normalize._merchant_lookup_data


# def _reload_normalize_module(monkeypatch, temp_csv_path: Path): # Replaced by reset_merchant_lookup_cache
#     """
#     Helper to monkeypatch MERCHANT_LOOKUP_PATH, reset internal cache,
#     and reload the normalize module.
#     """
#     # monkeypatch.setattr(normalize, "_merchant_lookup_data", None)  # Reset cache
#     # monkeypatch.setattr(
#     #     normalize, "MERCHANT_LOOKUP_PATH", temp_csv_path
#     # )  # Patch where it's used
#     # # The import-time load in normalize.py will use the new path
#     # importlib.reload(normalize)
#     normalize.reset_merchant_lookup_cache(new_path=temp_csv_path)


def create_lookup_csv(file_path: Path, content: list[list[str]]):
    """Helper to create a merchant_lookup.csv file."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(content)


@pytest.fixture(autouse=True)
def reset_normalize_module_state(monkeypatch):
    """
    Fixture to automatically reset the normalize module's merchant lookup path
    and data cache before and after each test that might modify it.
    This ensures that tests don't interfere with each other due to the module-level cache
    and import-time loading.
    """
    original_path = REAL_MERCHANT_LOOKUP_PATH
    # original_data_cache_existed = hasattr(normalize, "_merchant_lookup_data") # No longer needed
    # original_data_cache = getattr(normalize, "_merchant_lookup_data", None) # No longer needed

    yield  # Test runs here

    # Teardown: Restore original path and cache state using the new function
    normalize.reset_merchant_lookup_cache(new_path=original_path)


def test_clean_merchant_with_csv_rule(tmp_path): # Removed monkeypatch
    """Test that clean_merchant uses a rule from the CSV."""
    lookup_file = tmp_path / "merchant_lookup.csv"
    rules = [
        ["pattern", "canonical"],
        ["SUPER.*MART", "SuperMart"],
        ["COFFEE SHOP", "Generic Coffee Place"],
    ]
    create_lookup_csv(lookup_file, rules)

    normalize.reset_merchant_lookup_cache(new_path=lookup_file) # Use new reset function

    assert normalize.clean_merchant("TRANSACTION AT SUPER MART 123") == "SuperMart"
    assert normalize.clean_merchant("My Favorite COFFEE SHOP") == "Generic Coffee Place"


def test_clean_merchant_fallback_behavior(tmp_path): # Removed monkeypatch
    """Test clean_merchant falls back to default cleaning if no rule matches."""
    lookup_file = tmp_path / "merchant_lookup.csv"
    rules = [["pattern", "canonical"], ["KNOWN PLACE", "Known Place Canonical"]]
    create_lookup_csv(lookup_file, rules)
    normalize.reset_merchant_lookup_cache(new_path=lookup_file) # Use new reset function

    description = "An Unknown Place Ltd."
    expected_fallback = _clean_desc_single(description).title()
    assert normalize.clean_merchant(description) == expected_fallback


def test_clean_merchant_empty_lookup_file(tmp_path): # Removed monkeypatch
    """Test fallback with an empty (but valid header) lookup file."""
    lookup_file = tmp_path / "merchant_lookup.csv"
    rules = [["pattern", "canonical"]]  # Only header
    create_lookup_csv(lookup_file, rules)
    normalize.reset_merchant_lookup_cache(new_path=lookup_file) # Use new reset function

    description = "Another Unknown Place"
    expected_fallback = _clean_desc_single(description).title()
    assert normalize.clean_merchant(description) == expected_fallback


def test_load_merchant_lookup_invalid_regex_raises_valueerror( # Removed monkeypatch
    tmp_path, caplog
):
    """Test that an invalid regex in the CSV raises ValueError during module load."""
    lookup_file = tmp_path / "merchant_lookup.csv"
    rules = [
        ["pattern", "canonical"],
        ["VALID PATTERN", "Valid"],
        ["[INVALID REGEX", "Invalid Rule Attempt"],  # Unclosed bracket
    ]
    create_lookup_csv(lookup_file, rules)

    # monkeypatch.setattr(normalize, "_merchant_lookup_data", None)  # Reset cache # No longer needed
    # monkeypatch.setattr(
    #     normalize, "MERCHANT_LOOKUP_PATH", lookup_file
    # )  # Patch where it's used # No longer needed

    with caplog.at_level(logging.ERROR, logger="balance_pipeline.normalize"):
        with pytest.raises(ValueError) as excinfo:
            normalize.reset_merchant_lookup_cache(new_path=lookup_file) # This should trigger the load and the error

    assert "Invalid regex pattern" in str(excinfo.value)
    assert "[INVALID REGEX" in str(excinfo.value)
    assert "at row 3" in str(
        excinfo.value
    )  # 1-based index, row 1 is header, row 2 is valid, row 3 is bad
    # Check logs
    assert "invalid regex pattern found" in caplog.text.lower() # This log is from normalize.py
    assert "[invalid regex" in caplog.text.lower() # This log is from normalize.py


def test_load_merchant_lookup_file_not_found_uses_fallback( # Removed monkeypatch
    tmp_path, caplog
):
    """Test that if lookup file is not found, it logs error and uses fallback."""
    non_existent_file = tmp_path / "does_not_exist.csv"

    caplog.set_level(
        logging.ERROR, logger="balance_pipeline.normalize"
    )  # Ensure level is set
    with caplog.at_level(logging.ERROR, logger="balance_pipeline.normalize"):
        normalize.reset_merchant_lookup_cache(new_path=non_existent_file) # Use new reset function

    assert f"merchant lookup file not found: {non_existent_file}".lower() in caplog.text.lower() # This log is from normalize.py
    assert normalize._merchant_lookup_data == []  # Should be empty list

    # Test clean_merchant uses fallback
    description = "Any Description"
    expected_fallback = _clean_desc_single(description).title()
    assert normalize.clean_merchant(description) == expected_fallback


def test_load_merchant_lookup_invalid_header(tmp_path, caplog): # Removed monkeypatch
    """Test that an invalid header in CSV raises ValueError."""
    lookup_file = tmp_path / "merchant_lookup.csv"
    rules = [
        ["pattrn", "canonical_name"],  # Misspelled header
        ["SOME PATTERN", "Some Canonical"],
    ]
    create_lookup_csv(lookup_file, rules)

    # monkeypatch.setattr(normalize, "_merchant_lookup_data", None) # No longer needed
    # monkeypatch.setattr(
    #     normalize, "MERCHANT_LOOKUP_PATH", lookup_file
    # )  # Patch where it's used # No longer needed

    with caplog.at_level(logging.ERROR, logger="balance_pipeline.normalize"):
        with pytest.raises(normalize.FatalSchemaError) as excinfo: # Expect FatalSchemaError directly
            normalize.reset_merchant_lookup_cache(new_path=lookup_file) # Use new reset function

    assert "Invalid header" in str(excinfo.value) # This is from FatalSchemaError
    assert (
        f"invalid header in merchant lookup file: {lookup_file}".lower() in caplog.text.lower() # This log is from normalize.py
    )


def test_load_merchant_lookup_malformed_row_is_skipped(tmp_path, caplog): # Removed monkeypatch
    """Test that malformed rows (wrong number of columns) are skipped."""
    lookup_file = tmp_path / "merchant_lookup.csv"
    rules = [
        ["pattern", "canonical"],
        ["VALID PATTERN", "Valid Canonical"],
        ["MALFORMED ROW ONLY ONE COLUMN"],  # Malformed
        ["ANOTHER VALID", "Another One"],
    ]
    create_lookup_csv(lookup_file, rules)

    caplog.set_level(
        logging.WARNING, logger="balance_pipeline.normalize"
    )  # Ensure level is set
    with caplog.at_level(logging.WARNING, logger="balance_pipeline.normalize"):
        normalize.reset_merchant_lookup_cache(new_path=lookup_file) # Use new reset function

    assert "skipping malformed row 3" in caplog.text.lower()  # Row 3 is malformed

    # Check that valid rules were loaded
    assert len(normalize._merchant_lookup_data) == 2
    assert normalize.clean_merchant("TEST VALID PATTERN XYZ") == "Valid Canonical"
    assert normalize.clean_merchant("TEST ANOTHER VALID ABC") == "Another One"
    # Check that malformed rule isn't accidentally matched or causing issues
    assert (
        normalize.clean_merchant("MALFORMED ROW ONLY ONE COLUMN")
        == _clean_desc_single("MALFORMED ROW ONLY ONE COLUMN").title()
    )


def test_clean_merchant_handles_non_string_input(tmp_path): # Removed monkeypatch
    """Test clean_merchant handles non-string input gracefully."""
    lookup_file = tmp_path / "merchant_lookup.csv"
    rules = [["pattern", "canonical"]]  # Empty rules
    create_lookup_csv(lookup_file, rules)
    normalize.reset_merchant_lookup_cache(new_path=lookup_file) # Use new reset function

    with pytest.raises(normalize.DataConsistencyError):
        normalize.clean_merchant(123)
    with pytest.raises(normalize.DataConsistencyError):
        normalize.clean_merchant(None)
    with pytest.raises(normalize.DataConsistencyError):
        normalize.clean_merchant(float("nan"))


# Example of a basic DataFrame test (though normalize_df is more complex)
def test_normalize_df_minimal_smoke_test():
    """A very basic smoke test for normalize_df, not covering all features."""
    # This test doesn't involve merchant lookup specifics but ensures normalize_df runs.
    # More detailed tests for normalize_df would be in a separate context.
    data = {
        "Date": ["2023-01-01"],
        "Description": ["Test Merchant"],
        "Amount": [10.00],
        "Owner": ["TestOwner"],
        "Account": ["TestAccount"],
        "Bank": ["TestBank"],  # Added Bank
        "PostDate": ["2023-01-01"],  # Added PostDate
    }
    input_df = pd.DataFrame(data)
    # Ensure 'Date' and 'PostDate' are datetime
    input_df["Date"] = pd.to_datetime(input_df["Date"])
    input_df["PostDate"] = pd.to_datetime(input_df["PostDate"])

    # Since normalize_df calls clean_merchant, which tries to load the real CSV,
    # we might need to mock MERCHANT_LOOKUP_PATH for this test too if it's not covered by autouse.
    # For now, assume autouse fixture handles resetting to real path, or it uses an empty default.

    # To be safe, let's ensure _merchant_lookup_data is at least an empty list if file not found
    # This would mimic the behavior of _load_merchant_lookup if the real file is missing
    # or if we want to isolate this test from the CSV loading.
    # However, the autouse fixture should handle reloading with the real path.

    normalized_output_df = normalize.normalize_df(input_df.copy())  # Pass a copy

    assert not normalized_output_df.empty
    assert "TxnID" in normalized_output_df.columns
    assert "CleanDesc" in normalized_output_df.columns
    assert "CanonMerchant" in normalized_output_df.columns
    # Based on current normalize.py, CanonMerchant will be "Test Merchant" (title cased from _clean_desc)
    # if no rules match "Test Merchant" in the actual merchant_lookup.csv
    # For a truly isolated unit test of normalize_df, clean_merchant might be mocked.
    # Here, we rely on the fallback if the real CSV doesn't match.
    assert normalized_output_df["CanonMerchant"].iloc[0] == "Test Merchant"
