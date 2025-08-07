"""
errors.py

Defines custom exception hierarchy for the BALANCE-pyexcel pipeline,
enabling consistent error handling and classification.
"""
from __future__ import annotations


class BalancePipelineError(Exception):
    """Base class for all expected pipeline errors."""

    pass


class FatalSchemaError(BalancePipelineError):
    """Raised when a schema cannot be found or is invalid (YAML parse errors)."""

    pass


class RecoverableFileError(BalancePipelineError):
    """Raised when an individual file fails but processing can continue."""

    pass


class DataConsistencyError(BalancePipelineError):
    """Raised when data encountered is inconsistent (e.g., TxnID collision)."""

    pass
