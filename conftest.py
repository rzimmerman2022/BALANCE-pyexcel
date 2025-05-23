import sys
import os

# Ensure the src directory is on PYTHONPATH so tests can import balance_pipeline
ROOT = os.path.dirname(__file__)
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)


def pytest_sessionstart(session):
    """
    Clear any stub modules injected by test_schema_alias to ensure real modules load.
    """
    import sys
    import importlib

    # Remove any stubbed modules
    for mod in ("balance_pipeline", "balance_pipeline.errors", "yaml"):
        sys.modules.pop(mod, None)
    # Force import of real modules from src
    try:
        importlib.import_module("balance_pipeline.errors")
        importlib.import_module("balance_pipeline.csv_consolidator")
    except ImportError:
        pass
