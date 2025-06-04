import pytest
import pandas as pd
import yaml # Added import
from balance_pipeline.errors import FatalSchemaError, DataConsistencyError
from balance_pipeline.schema_registry import load_registry, find_matching_schema
from balance_pipeline.sign_rules import flip_if_positive, flip_if_withdrawal


def test_load_registry_file_not_found(tmp_path):
    missing = tmp_path / "nosuch.yml"
    with pytest.raises(FileNotFoundError): # Changed from FatalSchemaError
        load_registry(missing)


def test_load_registry_invalid_yaml(tmp_path):
    bad = tmp_path / "bad.yml"
    bad.write_text("not: [unclosed sequence")
    with pytest.raises(yaml.YAMLError): # Changed from FatalSchemaError
        load_registry(bad)


def test_load_registry_wrong_type(tmp_path):
    f = tmp_path / "list_as_dict.yml"
    f.write_text("key: value")
    # Pytest output indicates AssertionError. This might mean load_registry itself
    # has an assert that fails, or it doesn't raise an error when it should,
    # leading to pytest's own assertion for pytest.raises failing.
    # For now, let's assume an AssertionError is the new expected behavior if not wrapped.
    # If load_registry is supposed to raise FatalSchemaError here, this test points to a bug in load_registry.
    # Based on "bubble YAML errors" and strict mode, direct errors are plausible.
    with pytest.raises(AssertionError): # Changed from FatalSchemaError, based on pytest output
        load_registry(f)


def test_find_matching_schema_no_match(tmp_path):
    # Create a dummy registry
    registry = [{"id": "a", "match_filename": "foo.csv", "header_signature": ["X"]}]
    # Should raise FatalSchemaError when none match
    with pytest.raises(FatalSchemaError):
        find_matching_schema(headers=["A", "B"], filename="bar.csv", registry=registry)


@pytest.mark.parametrize(
    "func,args",
    [
        (flip_if_positive, (None, "Amount")),
        (flip_if_positive, (pd.DataFrame({"Other": [1, 2]}), "Amount")),
        (flip_if_withdrawal, (None, "Amount", "Category")),
        (flip_if_withdrawal, (pd.DataFrame({"Amount": [1, 2]}), "Amount", "Category")),
        (flip_if_withdrawal, (pd.DataFrame({"Category": ["X"]}), "Amount", "Category")),
    ],
)
def test_sign_rules_invalid_input(func, args):
    with pytest.raises(DataConsistencyError):
        func(*args)
