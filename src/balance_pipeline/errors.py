###############################################################################
# BALANCE-pyexcel – Error Definitions
#
# Description : Custom exception hierarchy for unified pipeline errors.
# Key Concepts: - Typed exceptions for failure scenarios
# Public API  : - BalancePipelineError
#               - FatalSchemaError
#               - RecoverableFileError
#               - DataConsistencyError
# -----------------------------------------------------------------------------
# Change Log
# Date        Author            Type        Note
# 2025-06-05  Codex             docs        Add standard header and docs.
# 2025-05-19  Ryan Zimmerman    feat        Initial creation of the module.
###############################################################################
"""Custom exception hierarchy for the BALANCE-pyexcel pipeline.

Enables consistent error handling across modules.
"""


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
