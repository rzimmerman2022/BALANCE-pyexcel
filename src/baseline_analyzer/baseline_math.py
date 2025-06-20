"""
Sprint-5 · baseline_math skeleton
Only _clean_labels + stub build_baseline.
"""
from __future__ import annotations

import re
from pathlib import Path
import pandas as pd

from ._settings import get_settings

# Cache settings once per session
_CFG = get_settings()


def _clean_labels(df: pd.DataFrame, *, source_file: str) -> pd.DataFrame:
    """Rename columns, drop header-noise rows, map person aliases."""
    cfg = _CFG

    # 1️⃣ rename columns according to config map
    df = df.rename(columns={v: k for k, v in cfg.column_map.items()})
    # 2️⃣ normalise column names
    df.columns = [c.strip().lower() for c in df.columns]

    # 3️⃣ drop header/noise rows that sometimes leak into CSV bodies
    noise_re = re.compile(cfg.header_noise_regex, flags=re.I)
    df = df.loc[~df["date"].astype(str).str.match(noise_re, na=False)].copy()

    # 4️⃣ canonicalise person aliases
    alias_map = {
        alias.lower(): canon
        for canon, aliases in cfg.person_aliases.items()
        for alias in aliases
    }
    df["person"] = (
        df["person"]
        .astype(str)
        .str.strip()
        .str.lower()
        .map(alias_map)
        .fillna(df["person"])
    )

    # 5️⃣ provenance columns
    df["source_file"] = source_file
    df["row_id"] = df.reset_index().index

    return df.reset_index(drop=True)


def build_baseline(
    expense_df: pd.DataFrame, ledger_df: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    TEMP stub: clean & concatenate expense / ledger frames.

    Returns:
        summary_df – per-person row counts
        audit_df   – concatenated & cleaned detail rows
    """
    exp = _clean_labels(expense_df, source_file="expense_history")
    led = _clean_labels(ledger_df, source_file="transaction_ledger")

    audit = pd.concat([exp, led], ignore_index=True)
    summary = (
        audit.groupby("person", as_index=False)
        .size()
        .rename(columns={"size": "row_count"})
    )
    return summary, audit
