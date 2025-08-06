import sys
import sys as _sys_module  # Alias for sys, used in stubbing logic below
import types as _types_module
from pathlib import Path

from balance_pipeline.schema_registry import find_matching_schema

# Ensure src directory is on sys.path for direct import when package not installed
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Stub missing yaml module for tests and balance_pipeline package to avoid side-effects
# _types_module and _sys_module are already imported above

# Stub balance_pipeline package to prevent __init__.py side-effects
_pkg = _types_module.ModuleType("balance_pipeline")
_pkg.__path__ = []
_sys_module.modules["balance_pipeline"] = _pkg

# Stub errors submodule with FatalSchemaError
_errors = _types_module.ModuleType("balance_pipeline.errors")
_errors.FatalSchemaError = Exception
_errors.RecoverableFileError = Exception
_sys_module.modules["balance_pipeline.errors"] = _errors

# Stub missing yaml dependency
_sys_module.modules["yaml"] = _types_module.SimpleNamespace(
    safe_load=lambda x: None, YAMLError=Exception
)

# Import schema_registry directly from file to avoid pulling full package
SCHEMA_PY = SRC / "balance_pipeline" / "schema_registry.py"

# Commented out problematic direct import logic
# # Import schema_registry directly from file to avoid pulling full package
# # This direct import method is causing issues with pytest collection and module state.
# # Rely on PYTHONPATH and standard import mechanisms.
# # SCHEMA_PY = SRC / "balance_pipeline" / "schema_registry.py"
# # import importlib.util as _import_util

# # _spec = _import_util.spec_from_file_location("schema_registry", SCHEMA_PY)
# # schema_mod = _import_util.module_from_spec(_spec)  # type: ignore[arg-type]
# # assert _spec and _spec.loader
# # _spec.loader.exec_module(schema_mod)  # type: ignore[attr-defined]

# # find_matching_schema = schema_mod.find_matching_schema  # type: ignore[attr-defined]

# --------------------------------------------------------------------------- #
# Synthetic registry for isolated tests
# --------------------------------------------------------------------------- #
REGISTRY = [
    {
        "id": "generic_checking",
        "header_signature": ["date", "merchant", "amount"],  # canonical names
    }
]


def test_alias_matching_description():
    headers = ["Date", "Description", "Amount"]
    schema = find_matching_schema(headers, "dummy.csv", REGISTRY)
    assert schema["id"] == "generic_checking"


# import sys # This was causing E402, sys is already imported at the top
sys.modules.pop("balance_pipeline", None)
sys.modules.pop("balance_pipeline.errors", None)
sys.modules.pop("yaml", None)


def test_alias_matching_account_optional():
    headers = ["Date", "Merchant", "Amount", "Acct Name"]
    schema = find_matching_schema(headers, "dummy.csv", REGISTRY)
    assert schema["id"] == "generic_checking"
