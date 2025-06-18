"""Unit tests for processing configuration integration (Sprint 3 – Phase A)."""

import importlib
import os
from types import ModuleType

import pytest

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def reload_processing() -> ModuleType:
    """Reload baseline_analyzer.processing fresh after env mutations."""
    from importlib import reload

    import baseline_analyzer.processing as proc  # type: ignore
    return reload(proc)


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #
def test_yaml_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure YAML default values are picked up when no env-vars are set."""
    # Clear potential overrides
    monkeypatch.delenv("BA_AMOUNT_COL", raising=False)
    monkeypatch.delenv("BA_DATE_COL", raising=False)
    monkeypatch.delenv("BA_BASELINE_FLOOR_DATE", raising=False)

    proc = reload_processing()

    assert proc.amount_col() == "Amount"
    assert proc.date_col() == "Date"
    assert str(proc.baseline_floor_date()) == "2000-01-01"


def test_environment_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    """BA_ prefix env vars must override YAML defaults."""
    monkeypatch.setenv("BA_AMOUNT_COL", "AmtEnv")
    monkeypatch.setenv("BA_DATE_COL", "DtEnv")
    monkeypatch.setenv("BA_BASELINE_FLOOR_DATE", "1999-12-31")

    proc = reload_processing()

    assert proc.amount_col() == "AmtEnv"
    assert proc.date_col() == "DtEnv"
    assert str(proc.baseline_floor_date()) == "1999-12-31"
