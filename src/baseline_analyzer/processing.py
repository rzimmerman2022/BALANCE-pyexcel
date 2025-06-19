"""baseline_analyzer.processing
Tiny config helpers + legacy-compat stubs
----------------------------------------
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, date
import pandas as pd

from ._settings import load_config, Settings

# ── New helpers (Sprint 3) ─────────────────────────────────────────────
def _cfg(cfg: Settings | None = None) -> Settings:
    return cfg or load_config()

def amount_col(cfg: Settings | None = None) -> str:
    return _cfg(cfg).amount_col

def date_col(cfg: Settings | None = None) -> str:
    return _cfg(cfg).date_col

def baseline_floor_date(cfg: Settings | None = None) -> date:
    return datetime.strptime(_cfg(cfg).baseline_floor_date, "%Y-%m-%d").date()

# ── Legacy-test stubs (keep until real rewrite) ───────────────────────
def _coerce_ledger_shape(df: pd.DataFrame, *_, **__) -> pd.DataFrame:
    """NO-OP stub — returns df unchanged."""
    return df.copy()

def _parse_tabular_ledger(df: pd.DataFrame, *_, **__) -> pd.DataFrame:
    """NO-OP stub — legacy parser placeholder."""
    return df.copy()

def build_baseline(df: pd.DataFrame, *_, **__) -> pd.DataFrame:
    """NO-OP stub — legacy baseline builder placeholder."""
    return df.copy()

@dataclass
class CleanerStats:
    """Placeholder dataclass — tracks nothing."""
    rows_in: int = 0
    rows_out: int = 0
