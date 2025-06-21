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

    # Zelle transfers, cashback, and simple “gift” descriptors
    for key in ("xfer_to_ryan", "xfer_to_jordyn", "cashback", "gift"):
        if key in _PATTERNS and _PATTERNS[key].search(desc_l):
            flags.append(key)
            if key.startswith("xfer_to_"):
                target_person = "Ryan" if key.endswith("ryan") else "Jordyn"
                return flags, ("transfer", target_person)
            if key == "cashback":
                return flags, ("zero_out", None)
            if key == "gift":
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

    if kind == "transfer":
        # Money moves person-to-person; net zero overall
        if (target or "").title() == "Ryan":
            return -actual, actual, "TR\tZelle transfer to Ryan"
        else:
            return actual, -actual, "TR\tZelle transfer to Jordyn"

    if kind == "zero_out":
        return 0.0, 0.0, "CB\tCash-back; no net effect"

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
    # Bridge new canonical names produced by audit_run.py
    alias_bridge = {"actual_amount": "actual", "allowed_amount": "allowed"}
    df = df.rename(columns={k: v for k, v in alias_bridge.items() if k in df.columns})
    # Bridge legacy “Name” header → person
    if "person" not in df.columns and "name" in df.columns:
        df = df.rename(columns={"name": "person"})
    # Drop any duplicated columns that may have arisen
    df = df.loc[:, ~pd.Index(df.columns).duplicated()].copy()
    # Promote first column to 'date' if still missing
    if "date" not in df.columns and len(df.columns):
        df = df.rename(columns={df.columns[0]: "date"})
    # Ensure a person column exists — some raw files omit it entirely
    if "person" not in df.columns:
        df["person"] = "Unknown"
    # 2️⃣ normalise column names
    df.columns = [c.strip().lower() for c in df.columns]

    # 2b️⃣ fallback: alias → canonical if “date” still missing
    if "date" not in df.columns:
        alias_map_date = {"date of purchase": "date", "month": "date"}
        for alias, canon in alias_map_date.items():
            if alias in df.columns:
                df = df.rename(columns={alias: canon})
                break

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

    # 3b️⃣  normalise money strings → float
    for col in ("allowed", "actual"):
        if col in df.columns:
                df[col] = (
                    df[col]
                    .astype(str)
                    .str.replace(r"[^0-9.\-]", "", regex=True)
                    .replace({"": "0", "-": "0"})
                    .astype(float)
                    .round(2)
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
    """
    # Clean & label
    exp = (
        _clean_labels(expense_df, source_file="expense_history")
        if not expense_df.empty
        else pd.DataFrame()
    )
    led = (
        _clean_labels(ledger_df, source_file="transaction_ledger")
        if not ledger_df.empty
        else pd.DataFrame()
    )

    rows: list[dict[str, object]] = []

    # --- ① Process Expense & Synthetic Rent Rows ---
    if 'transaction_type' in exp.columns:
        rent_rows = exp[exp["transaction_type"] == "synthetic_rent"].copy()
        standard_exp_rows = exp[exp["transaction_type"] != "synthetic_rent"].copy()
        if not rent_rows.empty:
            rows.extend(rent_rows.to_dict("records"))
    else:
        standard_exp_rows = exp.copy()

    for _, row in standard_exp_rows.iterrows():
        payer = row["person"]
        total_to_split = float(row["allowed"])
        allowed_self = total_to_split
        allowed_other = 0.0
        for person_in_loop, allowed_for_loop in (
            ("Ryan", allowed_self if payer == "Ryan" else allowed_other),
            ("Jordyn", allowed_self if payer == "Jordyn" else allowed_other),
        ):
            fair_half = total_to_split / 2
            net_effect = round(fair_half - allowed_for_loop, 2)
            actual_for_person = row["actual"] if person_in_loop == payer else 0.0
            rows.append(
                {
                    "source_file": row["source_file"], "row_id": row["row_id"],
                    "person": person_in_loop, "date": row["date"], "merchant": row.get("merchant"),
                    "actual_amount": round(actual_for_person, 2),
                    "allowed_amount": round(allowed_for_loop, 2),
                    "net_effect": net_effect, "notes": row.get("notes", ""),
                    "pattern_flags": row.get("pattern_flags", []),
                    "calculation_notes": "EH|Standard 50/50 Split",
                    "transaction_type": "standard",
                }
            )

    # --- ② Process Transaction Ledger Rows ---
    for _, row in led.iterrows():
        payer = row["person"]
        desc_combined = f"{row.get('description', '')} {row.get('merchant', '')}"
        flags, rule = _detect_patterns(str(desc_combined), payer)
        actual_val = float(row.get("actual", row.get("actual_amount", 0.0)))
        allowed_ryan, allowed_jordyn, note = _apply_split_rules(actual_val, rule, payer)
        fair_share = actual_val / 2
        if payer == "Ryan":
            ryan_net_effect = fair_share - actual_val
            jordyn_net_effect = fair_share - 0
        else:
            ryan_net_effect = fair_share - 0
            jordyn_net_effect = fair_share - actual_val
        rows.append({
            "source_file": row["source_file"], "row_id": row["row_id"], "person": "Ryan",
            "date": row["date"], "merchant": row.get("merchant"),
            "actual_amount": round(actual_val, 2) if payer == "Ryan" else 0.0,
            "allowed_amount": round(allowed_ryan, 2), "net_effect": round(ryan_net_effect, 2),
            "notes": "", "pattern_flags": flags, "calculation_notes": note, "transaction_type": "ledger",
        })
        rows.append({
            "source_file": row["source_file"], "row_id": row["row_id"], "person": "Jordyn",
            "date": row["date"], "merchant": row.get("merchant"),
            "actual_amount": round(actual_val, 2) if payer == "Jordyn" else 0.0,
            "allowed_amount": round(allowed_jordyn, 2), "net_effect": round(jordyn_net_effect, 2),
            "notes": "", "pattern_flags": flags, "calculation_notes": note, "transaction_type": "ledger",
        })

    audit_df = pd.DataFrame(rows, columns=_CFG.audit_columns)

    # --- ③ Final Summary ---
    summary_df = (
        audit_df.groupby("person", as_index=False)["net_effect"]
        .sum()
        .rename(columns={"net_effect": "net_owed"})
    )
    imbalance = summary_df["net_owed"].sum()
    if abs(imbalance) > _CFG.rounding_tolerance:
        print(
            f"⚠️  Net imbalance {imbalance:,.2f} exceeds tolerance "
            f"({_CFG.rounding_tolerance}). Continuing for diagnostics."
        )

    return summary_df, audit_df
