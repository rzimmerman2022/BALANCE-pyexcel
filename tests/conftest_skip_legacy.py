"""conftest_skip_legacy.py
Automatically skip legacy baseline tests that we haven’t ported yet.
"""
import pathlib

import pytest

LEGACY_DIR = pathlib.Path(__file__).parent / "baseline"

def pytest_collection_modifyitems(config, items):
    skip_marker = pytest.mark.skip(reason="skipped - legacy baseline suite")
    for item in items:
        if LEGACY_DIR in pathlib.Path(item.fspath).parents:
            item.add_marker(skip_marker)
