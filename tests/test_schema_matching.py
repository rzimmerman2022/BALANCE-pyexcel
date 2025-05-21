from pathlib import Path

from balance_pipeline.schema_registry import load_registry, find_matching_schema

REGISTRY_PATH = Path("rules/schema_registry.yml")


def _load_registry():
    return load_registry(REGISTRY_PATH)


def test_exact_header_match():
    registry = _load_registry()
    headers = ["Account Name", "Institution Name", "Amount"]
    result = find_matching_schema(headers, "BALANCE - Rocket Money.csv", registry)
    assert result.schema["id"] == "rocket_money"
    assert result.missing == set()
    assert result.extra == set()


def test_alias_header_resolves():
    registry = _load_registry()
    headers = ["Date", "Description", "Amount"]
    result = find_matching_schema(headers, "generic_bank_2025.csv", registry)
    assert result.schema["id"] == "generic_checking"
    assert result.missing == set()


def test_optional_headers():
    registry = _load_registry()
    headers = ["Date", "Merchant", "Amount", "Running Balance", "Check Number"]
    result = find_matching_schema(headers, "generic_bank_1.csv", registry)
    assert result.schema["id"] == "generic_checking"
    assert result.missing == set()
    assert result.extra == set()


def test_fallback_with_unknown_extra():
    registry = _load_registry()
    headers = ["Date", "Merchant", "Amount", "Weird"]
    result = find_matching_schema(headers, "some_file.csv", registry)
    assert result.schema["id"] == "generic_checking"
    assert result.missing == set()
    assert result.extra == {"weird"}
