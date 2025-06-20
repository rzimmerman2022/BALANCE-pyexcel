"""
Baseline Analyzer - One-time ledger baseline finder for Balance

This package contains the refactored analyzer functionality for determining
the baseline "who owes whom" calculations from expense and rent data.

Core modules:
- cli: Command-line interface for running the baseline analysis
- config: Configuration management and data quality flags
- loaders: Data loading and merging functionality
- processing: Expense and rent processing pipelines
- ledger: Master ledger creation
- recon: Triple reconciliation calculations
- analytics: Advanced analytics and risk assessment
- viz: Visualization generation
- outputs: Report generation
"""

__version__ = "0.1.0"
__author__ = "Ryan Zimmerman"
__description__ = "Single-run ledger baseline finder for Balance"

# Public re-exports (BA Sprint 1)
from ._settings import load_config, get_settings, Settings  # noqa: F401
from .opening_balance import inject_opening_balance  # noqa: F401

__all__ = ["load_config", "get_settings", "Settings", "inject_opening_balance"]
