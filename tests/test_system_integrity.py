import os
import sys
import unittest

import pandas as pd

# Add src directory to path to import baseline_math
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))
from baseline_analyzer import baseline_math as bm


class TestSystemIntegrity(unittest.TestCase):
    def test_rent_allocation(self):
        """Test the 43/57 rent allocation rule."""
        rent_data = {
            "Month": ["Jan-25"],
            "Ryan's Rent (43%)": [1000 * 0.43],
            "Jordyn's Rent (57%)": [1000 * 0.57],
            "Gross Total": [1000],
        }
        rent_df = pd.DataFrame(rent_data)

        summary, audit = bm.build_baseline(pd.DataFrame(), pd.DataFrame(), rent_df)

        ryan_rent = audit[(audit["person"] == "Ryan") & (audit["merchant"] == "Rent")]
        jordyn_rent = audit[
            (audit["person"] == "Jordyn") & (audit["merchant"] == "Rent")
        ]

        self.assertAlmostEqual(ryan_rent["net_effect"].iloc[0], 430.00)
        self.assertAlmostEqual(jordyn_rent["net_effect"].iloc[0], -430.00)
        self.assertAlmostEqual(summary["net_owed"].sum(), 0.0)

    def test_standard_50_50_split(self):
        """Test a standard 50/50 expense split."""
        expense_data = {
            "person": ["Ryan"],
            "date": ["2025-01-15"],
            "merchant": ["Groceries"],
            "actual_amount": [100.00],
        }
        expense_df = pd.DataFrame(expense_data)

        summary, audit = bm.build_baseline(expense_df, pd.DataFrame(), pd.DataFrame())

        ryan_exp = audit[audit["person"] == "Ryan"]
        jordyn_exp = audit[audit["person"] == "Jordyn"]

        self.assertAlmostEqual(
            ryan_exp["net_effect"].iloc[0], -50.00
        )  # Paid 100, owed 50
        self.assertAlmostEqual(
            jordyn_exp["net_effect"].iloc[0], 50.00
        )  # Paid 0, owed 50
        self.assertAlmostEqual(summary["net_owed"].sum(), 0.0)

    def test_full_to_person_rule(self):
        """Test the 'full_to' allocation rule."""
        ledger_data = {
            "person": ["Jordyn"],
            "date": ["2025-01-16"],
            "merchant": ["Gift for Ryan (2x Ryan)"],
            "actual_amount": [75.00],
        }
        ledger_df = pd.DataFrame(ledger_data)

        summary, audit = bm.build_baseline(pd.DataFrame(), ledger_df, pd.DataFrame())

        ryan_ledger = audit[audit["person"] == "Ryan"]
        jordyn_ledger = audit[audit["person"] == "Jordyn"]

        self.assertAlmostEqual(
            ryan_ledger["net_effect"].iloc[0], 75.00
        )  # Owed full amount
        self.assertAlmostEqual(
            jordyn_ledger["net_effect"].iloc[0], -75.00
        )  # Paid full amount
        self.assertAlmostEqual(summary["net_owed"].sum(), 0.0)

    def test_cashback_rule(self):
        """Test that cashback transactions have zero net effect."""
        ledger_data = {
            "person": ["Ryan"],
            "date": ["2025-01-17"],
            "merchant": ["Discover Cashback"],
            "actual_amount": [25.00],
        }
        ledger_df = pd.DataFrame(ledger_data)

        summary, audit = bm.build_baseline(pd.DataFrame(), ledger_df, pd.DataFrame())

        self.assertAlmostEqual(audit["net_effect"].sum(), 0.0)
        self.assertAlmostEqual(summary["net_owed"].sum(), 0.0)

    def test_system_zeros_out(self):
        """Test a combination of transactions to ensure the grand total is zero."""
        expense_data = {
            "person": ["Ryan"],
            "date": ["2025-01-15"],
            "merchant": ["Groceries"],
            "actual_amount": [100.00],
        }
        ledger_data = {
            "person": ["Jordyn"],
            "date": ["2025-01-16"],
            "merchant": ["Movie Tickets (2x Jordyn)"],
            "actual_amount": [50.00],
        }
        rent_data = {
            "Month": ["Feb-25"],
            "Ryan's Rent (43%)": [860],
            "Jordyn's Rent (57%)": [1140],
            "Gross Total": [2000],
        }

        expense_df = pd.DataFrame(expense_data)
        ledger_df = pd.DataFrame(ledger_data)
        rent_df = pd.DataFrame(rent_data)

        summary, audit = bm.build_baseline(expense_df, ledger_df, rent_df)

        self.assertAlmostEqual(summary["net_owed"].sum(), 0.0, places=2)


if __name__ == "__main__":
    unittest.main()
