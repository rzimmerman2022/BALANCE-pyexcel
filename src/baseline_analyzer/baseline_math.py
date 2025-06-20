"""
Sprint-5 · baseline_math skeleton
Only _clean_labels + stub build_baseline.
"""
from __future__ import annotations

import re
from typing import Dict, List, Tuple
from pathlib import Path

import pandas as pd

from ._settings import get_settings

# Cache settings once per session
_CFG = get_settings()

# ── Sprint-5 pattern cache ───────────────────────────────
_PATTERNS: Dict[str, re.Pattern] = {k: re.compile(v, flags=re.I) for k, v in _CFG.patterns.items()}

_RX_TWOX_NAMED = re.compile(r"\b2x\s+(Ryan|Jordyn)", re.I)
_RX_NAMED_TWOX = re.compile(r"(Ryan|Jordyn).*?\b2x\b", re.I)
_RX_DOUBLE_AMT = re.compile(r"\$\s*\d+(?:\.\d{1,2})?\s*\(2x\)", re.I)

def _detect_patterns(desc: str, payer: str) -> Tuple[List[str], Tuple[str, str | None]]:
    """Return (flags, rule).  rule examples: ('full_to','Ryan'), ('double_charge',None)."""
    desc_l: str = desc or ""
    flags: List[str] = []

    # 2× multiplier with named beneficiary
    if m := (_RX_TWOX_NAMED.search(desc_l) or _RX_NAMED_TWOX.search(desc_l)):
        return ["multiplier_2x"], ("full_to", m.group(1).title())

    # Explicit “$ xx.xx (2x)” double-charge
    if _RX_DOUBLE_AMT.search(desc_l):
        return ["multiplier_2x", "double_charge"], ("double_charge", None)

    # Ambiguous “2x” anywhere
    if "2x" in desc_l.lower():
        flags.extend(["multiplier_2x", "ambiguous_2x"])
        return flags, ("full_to", payer)

    # Gifts / freebies
    if any(rx.search(desc_l) for rx in [_PATTERNS["gift_or_present"], _PATTERNS["free_for_person"]]):
        flags.append("gift_or_present")
        if _PATTERNS["gift_or_present"].search(desc_l):
            flags.append("gift")
        if _PATTERNS["free_for_person"].search(desc_l):
            flags.append("free_for_person")
        other = "Jordyn" if payer.lower() == "ryan" else "Ryan"
        return flags, ("full_to", other)

    # 100 % allocation
    if m := re.search(r"100%\s+(Jordyn|Ryan)", desc_l, flags=re.I):
        return ["full_allocation_100_percent"], ("full_to", m.group(1).title())

    # Default rule
    return [], ("standard", None)

# ── Split-rule helper ────────────────────────────────────
def _apply_split_rules(
    actual: float,
    rule: Tuple[str, str | None],
    payer: str,
) -> Tuple[float, float, str]:
    """
    Return (allowed_ryan, allowed_jordyn, note).
    rule formats:
        ("standard", None)
        ("double_charge", None)
        ("full_to", "Ryan"|"Jordyn")
    """
    kind, target = rule

    if kind == "standard":
        return actual / 2, actual / 2, "SR\tStandard 50/50 split"

    if kind == "double_charge":
        note = "DC\tDouble charge documented; split stays 50/50"
        return actual / 2, actual / 2, note

    # full_to rule
    who = (target or payer).title()
    if who == "Ryan":
        return actual, 0.0, "FT\tFull reimbursement to Ryan"
    return 0.0, actual, "FT\tFull reimbursement to Jordyn"


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
    Phase-3B: compute ledger split rules + net_effect.
    Expense rows are passed through untouched (handled in 3-C).

    Returns
    -------
    summary_df : pd.DataFrame
        Per-person net owed totals (column: ``net_owed``).
    audit_df   : pd.DataFrame
        Detail rows in canonical order from ``_CFG.audit_columns``.
    """
    # Clean & label
    exp = (
        _clean_labels(expense_df, source_file="expense_history")
        if not expense_df.empty
        else pd.DataFrame()
    )
    led = _clean_labels(ledger_df, source_file="transaction_ledger")

    # ── Process ledger rows → two person-rows each ──────────────
    rows: list[dict[str, object]] = []
    for _, row in led.iterrows():
        flags, rule = _detect_patterns(str(row.get("description", "")), str(row["person"]))
        allowed_ryan, allowed_jordyn, note = _apply_split_rules(
            float(row["actual"]), rule, str(row["person"])
        )

        total_allowed = allowed_ryan + allowed_jordyn
        fair_half = total_allowed / 2

        for person, allowed in (("Ryan", allowed_ryan), ("Jordyn", allowed_jordyn)):
            net_eff = round(fair_half - allowed, 2)
            rows.append(
                {
                    "source_file": row["source_file"],
                    "row_id": row["row_id"],
                    "person": person,
                    "date": row["date"],
                    "merchant": row.get("merchant"),
                    "actual_amount": row["actual"],
                    "allowed_amount": allowed,
                    "net_effect": net_eff,
                    "notes": "",
                    "pattern_flags": flags,
                    "calculation_notes": note,
                }
            )

    audit_df = pd.DataFrame(rows, columns=_CFG.audit_columns)

    # ── Summary ────────────────────────────────────────────────
    summary_df = (
        audit_df.groupby("person", as_index=False)["net_effect"]
        .sum()
        .rename(columns={"net_effect": "net_owed"})
    )
    assert abs(summary_df["net_owed"].sum()) < _CFG.rounding_tolerance
    return summary_df, audit_df
