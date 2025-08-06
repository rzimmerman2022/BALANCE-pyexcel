#!/usr/bin/env python3
###############################################################################
# BALANCE-pyexcel – Baseline Verification
#
# Description : Load the generated master ledger CSV from the analyzer output
#                and perform a quick sum check to validate the overall amount.
# Key Concepts: - Lightweight validation
#               - Pandas summarization
# Public API  : - main()
# -----------------------------------------------------------------------------
# Change Log
# Date        Author      Type        Note
# 2025-06-08  Codex       add         Initial version
###############################################################################
from __future__ import annotations

from pathlib import Path

import pandas as pd

LEDGER_PATH = Path("analysis_output/master_ledger.csv")


def main() -> None:
    """Print the total of the master ledger for a manual sanity check."""
    if not LEDGER_PATH.exists():
        print(f"Ledger file not found: {LEDGER_PATH}")
        return
    df = pd.read_csv(LEDGER_PATH)
    total = df["Amount"].sum()
    print(f"Ledger total: {total:.2f}")


if __name__ == "__main__":
    main()
