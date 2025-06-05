###############################################################################
# BALANCE-pyexcel – PDF Processing Stub
#
# Description : Minimal stub to satisfy tests expecting process_pdfs module.
# Key Concepts: - Command-line interface placeholder
#               - No-op append_to_master helper
# Public API  : - append_to_master(df_input: pd.DataFrame, owner_name: str)
#               - main() -> None
# -----------------------------------------------------------------------------
# Change Log
# Date        Author            Type        Note
# 2025-06-05  Codex             feat        Provide stub for test execution.
###############################################################################
from __future__ import annotations
import argparse
import logging
import pandas as pd

log = logging.getLogger(__name__)


def append_to_master(df_input: pd.DataFrame, owner_name: str) -> None:
    """Log call without writing to disk."""
    log.info(
        "append_to_master stub called for owner %s with %d rows",
        owner_name,
        len(df_input),
    )


def main() -> None:
    """Entry point for the PDF processing stub."""
    parser = argparse.ArgumentParser()
    parser.add_argument("input_dir")
    parser.add_argument("output_dir")
    parser.add_argument("owner_name")
    parser.add_argument("-v", action="store_true")
    parser.parse_args()
    print("process_pdfs stub executed")


if __name__ == "__main__":  # pragma: no cover
    main()
