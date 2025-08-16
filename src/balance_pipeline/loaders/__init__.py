"""
Individual CSV loaders for the balance pipeline.
Each loader handles one specific CSV format and returns CTS-compliant DataFrames.
"""

from .expense_loader import load_expense_history
from .ledger_loader import load_transaction_ledger
from .rent_alloc_loader import load_rent_alloc
from .rent_history_loader import load_rent_history

# Registry of all available loaders
LOADER_REGISTRY = [
    load_expense_history,
    load_transaction_ledger,
    load_rent_alloc,
    load_rent_history,
]

__all__ = [
    "load_expense_history",
    "load_transaction_ledger",
    "load_rent_alloc",
    "load_rent_history",
    "LOADER_REGISTRY",
]
