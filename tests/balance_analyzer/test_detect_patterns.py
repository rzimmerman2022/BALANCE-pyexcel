from baseline_analyzer.baseline_math import _detect_patterns
import pytest


@pytest.mark.parametrize(
    "desc,payer,rule",
    [
        ("Toll $15 (2x Ryan)", "Ryan", ("full_to", "Ryan")),
        ("Ryan 2x bridge", "Ryan", ("full_to", "Ryan")),
        ("Fee $40 (2x)", "Ryan", ("double_charge", None)),
        ("Gift for Jordyn", "Ryan", ("full_to", "Jordyn")),
        ("Lunch split", "Ryan", ("standard", None)),
    ],
)
def test_detect(desc: str, payer: str, rule):
    flags, got = _detect_patterns(desc, payer)
    assert got == rule
