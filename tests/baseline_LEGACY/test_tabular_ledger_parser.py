import pandas as pd
import sys
from pathlib import Path

# Add project root so src imports resolve
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.baseline_analyzer.processing import _parse_tabular_ledger

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def test_tabular_ledger_parser_sign_and_clean():
    """
    • Row-0: DEBIT → amount should be ‑50.00
    • Row-1: CREDIT → +100.00
    • Row-2: no Transaction Type but “Payment to Ryan” in Description → +200.00
    """
    raw_lines = (FIXTURE_DIR / "tabular_ledger.csv").read_text().splitlines()
    df = _parse_tabular_ledger(raw_lines)

    # Expected columns
    assert list(df.columns)[:2] == ["Date", "Amount"]
    assert len(df) == 3

    # Dates parsed
    assert pd.api.types.is_datetime64_any_dtype(df["Date"])
    assert df["Date"].min().year == 2024

    # Amount signs
    amounts = df["Amount"].tolist()
    assert amounts == [-50.00, 100.00, 200.00]

    # Net sum should be +250
    assert abs(sum(amounts) - 250.0) < 0.001
