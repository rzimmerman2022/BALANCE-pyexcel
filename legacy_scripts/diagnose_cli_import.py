import traceback
import sys

try:
    import balance_pipeline.cli as bpcli

    print("cli imported OK:", bpcli.__file__)
except Exception:
    print("cli import failed:")
    traceback.print_exc()
    print()
    print("Partial sys.modules entry:", sys.modules.get("balance_pipeline.cli"))
