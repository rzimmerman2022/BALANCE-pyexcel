import pandas as pd
import pytest
from io import StringIO

from baseline_analyzer.baseline_math import build_baseline

# --------------------------------------------------------------------------- #
# Parametric scenarios exercising each rule branch.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "desc,expected",
    [
        ("Toll 15 (2x Ryan)", (50.0, 0.0)),           # full_to Ryan via '2x Ryan'
        ("Ryan 2x bridge toll", (50.0, 0.0)),         # full_to Ryan via 'Ryan … 2x'
        ("Service fee $40 (2x)", (25.0, 25.0)),       # double-charge -> 50/50
        ("Gift for Jordyn", (0.0, 50.0)),             # gift -> full_to Jordyn
        ("Lunch split", (25.0, 25.0)),                # standard 50/50
    ],
)
def test_ledger_math(desc: str, expected: tuple[float, float]) -> None:
    """Verify allowed_amount + net_effect maths for transaction-ledger rows."""
    csv_text = f"Name,Date,Actual Amount,Description\nRyan,2025-06-18,50,\"{desc}\""
    ledger_df = pd.read_csv(StringIO(csv_text))

    summary, audit = build_baseline(pd.DataFrame(), ledger_df)

    r_allow = audit.loc[audit.person == "Ryan", "allowed_amount"].iloc[-1]
    j_allow = audit.loc[audit.person == "Jordyn", "allowed_amount"].iloc[-1]

    assert (r_allow, j_allow) == expected
    # The two audit rows must balance to ≈0.
    assert abs(audit["net_effect"].sum()) < 0.02
