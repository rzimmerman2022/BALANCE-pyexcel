"""Tests for baseline_analyzer.config Settings loader (Sprint #1)."""

from baseline_analyzer import load_config


def test_yaml_default_loading():
    """Defaults in YAML should load unchanged."""
    cfg = load_config()
    assert cfg.opening_balance_col == "Opening Balance"
    assert cfg.baseline_date_format == "%Y-%m-%d"
    assert cfg.merchant_lookup_path == "config/merchant_lookup.csv"


def test_env_override(monkeypatch):
    """Environment variables with BA_ prefix should override YAML."""
    monkeypatch.setenv("BA_OPENING_BALANCE_COL", "OpeningBalEnv")
    cfg = load_config()
    assert cfg.opening_balance_col == "OpeningBalEnv"
