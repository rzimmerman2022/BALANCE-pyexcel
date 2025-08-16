import pandas as pd

from src.balance_pipeline.config import AnalysisConfig
from src.balance_pipeline.processing import expense_pipeline


def test_expense_pipeline_basic_shared_math():
    """
    Test expense pipeline with basic shared expense math validation.
    Uses a 3-row fixture: 2 shared expenses, 1 personal expense.
    Validates that RyanOwes + JordynOwes == AllowedAmount for shared rows.
    """
    # Create test fixture
    test_data = pd.DataFrame(
        {
            "Date": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "ActualAmount": [100.0, 50.0, 75.0],
            "AllowedAmount": [100.0, 50.0, 0.0],  # Third row is personal
            "Payer": ["Ryan", "Jordyn", "Ryan"],
            "Description": ["Shared groceries", "Shared utilities", "Personal coffee"],
            "Merchant": ["Grocery Store", "Electric Company", "Starbucks"],
        }
    )

    # Test configuration
    config = AnalysisConfig()
    config.RYAN_PCT = 0.43
    config.JORDYN_PCT = 0.57
    config.debug_mode = False

    # Test rules
    rules = {
        "settlement_keywords": ["venmo", "zelle", "cash app", "paypal"],
        "payer_split": {"ryan_pct": 0.43, "jordyn_pct": 0.57},
    }

    # Data quality issues list
    data_quality_issues = []

    # Run expense pipeline
    result_df = expense_pipeline(test_data, config, rules, data_quality_issues)

    # Validate results
    assert len(result_df) == 3, "Should return 3 rows"

    # Check shared rows (first two)
    shared_rows = result_df[result_df["IsShared"] == True]
    assert len(shared_rows) == 2, "Should have 2 shared rows"

    for idx, row in shared_rows.iterrows():
        ryan_owes = row["RyanOwes"]
        jordyn_owes = row["JordynOwes"]
        allowed_amount = row["AllowedAmount"]
        payer = row["Payer"]

        # For shared expenses, only the non-payer owes their portion to the payer
        if payer == "Ryan":
            # Ryan paid, so Jordyn owes her portion to Ryan
            assert ryan_owes == 0.0, f"Row {idx}: When Ryan pays, RyanOwes should be 0"
            expected_jordyn_owes = allowed_amount * config.JORDYN_PCT
            assert (
                abs(jordyn_owes - expected_jordyn_owes) < 0.01
            ), f"Row {idx}: JordynOwes ({jordyn_owes}) != expected ({expected_jordyn_owes})"
        else:
            # Jordyn paid, so Ryan owes his portion to Jordyn
            assert (
                jordyn_owes == 0.0
            ), f"Row {idx}: When Jordyn pays, JordynOwes should be 0"
            expected_ryan_owes = allowed_amount * config.RYAN_PCT
            assert (
                abs(ryan_owes - expected_ryan_owes) < 0.01
            ), f"Row {idx}: RyanOwes ({ryan_owes}) != expected ({expected_ryan_owes})"

    # Check personal row (third)
    personal_rows = result_df[result_df["IsShared"] == False]
    assert len(personal_rows) == 1, "Should have 1 personal row"

    personal_row = personal_rows.iloc[0]
    assert personal_row["RyanOwes"] == 0.0, "Personal expense should have RyanOwes = 0"
    assert (
        personal_row["JordynOwes"] == 0.0
    ), "Personal expense should have JordynOwes = 0"

    # Validate specific calculations for Ryan paying shared expense
    ryan_shared_row = result_df[
        (result_df["Payer"] == "Ryan") & (result_df["IsShared"] == True)
    ].iloc[0]
    expected_jordyn_owes = ryan_shared_row["AllowedAmount"] * config.JORDYN_PCT
    assert (
        abs(ryan_shared_row["JordynOwes"] - expected_jordyn_owes) < 0.01
    ), "Ryan paid shared: JordynOwes calculation incorrect"

    # Validate specific calculations for Jordyn paying shared expense
    jordyn_shared_row = result_df[
        (result_df["Payer"] == "Jordyn") & (result_df["IsShared"] == True)
    ].iloc[0]
    expected_ryan_owes = jordyn_shared_row["AllowedAmount"] * config.RYAN_PCT
    assert (
        abs(jordyn_shared_row["RyanOwes"] - expected_ryan_owes) < 0.01
    ), "Jordyn paid shared: RyanOwes calculation incorrect"

    # Check required columns exist
    required_columns = [
        "Date",
        "ActualAmount",
        "AllowedAmount",
        "Payer",
        "Description",
        "Merchant",
        "TransactionType",
        "DataQualityFlag",
        "IsShared",
        "RyanOwes",
        "JordynOwes",
        "BalanceImpact",
        "AuditNote",
    ]
    for col in required_columns:
        assert col in result_df.columns, f"Missing required column: {col}"

    print("✓ All expense pipeline tests passed!")


if __name__ == "__main__":
    test_expense_pipeline_basic_shared_math()
