import sys
from pathlib import Path

import pandas as pd

# Ensure project root is on sys.path so "src" package resolves
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.baseline_analyzer.processing import _coerce_ledger_shape

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def test_vertical_ledger_coercion():
    raw_path = FIXTURE_DIR / "vertical_ledger.csv"
    # Load as plain text to avoid comma delimiter issues
    lines = raw_path.read_text().splitlines()
    raw_df = pd.DataFrame({"Col": lines})

    coerced = _coerce_ledger_shape(raw_df)

    # basic column checks
    assert {"Date", "Amount"}.issubset(coerced.columns)

    # should parse two transactions
    assert len(coerced) == 2

    # dates should be parsed
    assert pd.api.types.is_datetime64_any_dtype(coerced["Date"])
    assert coerced["Date"].notna().all()

    # amounts preserved
    amounts = coerced["Amount"].tolist()
    assert amounts == [-23.45, 1000.00]
    assert abs(sum(amounts) - 976.55) < 0.001
