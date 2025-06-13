#!/usr/bin/env python3
###############################################################################
# BALANCE-pyexcel – Baseline Runner
#
# Description : Thin wrapper around analyzer.main to run the baseline
#                reconciliation with extra logging. Designed to execute once
#                and capture any exceptions without halting completely.
# Key Concepts: - Orchestration script
#               - Robust logging
# Public API  : - main()
# -----------------------------------------------------------------------------
# Change Log
# Date        Author      Type        Note
# 2025-06-08  Codex       add         Initial version
###############################################################################
from __future__ import annotations

import logging

from baseline_analyzer.cli import main as cli_main


logging.basicConfig(level=logging.INFO)
log = logging.getLogger("run_baseline")


def main() -> None:
    """Run the legacy analyzer with default arguments."""
    try:
        cli_main()
    except Exception as exc:  # pragma: no cover - best effort logging
        log.exception("Baseline calculation failed", exc_info=exc)
    else:
        log.info("Baseline run completed")


if __name__ == "__main__":
    main()
