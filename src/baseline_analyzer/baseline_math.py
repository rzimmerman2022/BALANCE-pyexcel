"""
Core accounting logic for the balance analyzer.
"""
from __future__ import annotations

import re
from typing import Dict, List, Tuple
import pandas as pd
from ._settings import get_settings

_CFG = get_settings()
_PATTERNS: Dict[str, re.Pattern] = {k: re.compile(v, flags=re.I) for k, v in _CFG.patterns.items()}

def _detect_patterns(desc: str, payer: str) -> Tuple[List[str], Tuple[str, str | None]]:
    desc_l = desc or ""
    if "2x" in desc_l.lower():
        if m := re.search(r"\b2x\s+(Ryan|Jordyn)", desc_l, re.I) or re.search(r"(Ryan|Jordyn).*?\b2x\b", desc_l, re.I):
            return ["multiplier_2x"], ("full_to", m.group(1).title())
        if re.search(r"\$\s*\d+(?:\.\d{1,2})?\s*\(2x\)", desc_l, re.I):
            return ["multiplier_2x", "double_charge"], ("double_charge", None)
        return ["multiplier_2x", "ambiguous_2x"], ("full_to", payer)
    for key in ("xfer_to_ryan", "xfer_to_jordyn", "cashback", "gift"):
        if key in _PATTERNS and _PATTERNS[key].search(desc_l):
            if key.startswith("xfer_to_"):
                return [key], ("transfer", "Ryan" if key.endswith("ryan") else "Jordyn")
            if key == "cashback":
                return [key], ("zero_out", None)
            if key == "gift":
                return [key], ("full_to", "Jordyn" if payer.lower() == "ryan" else "Ryan")
    if m := re.search(r"100%\s+(Jordyn|Ryan)", desc_l, flags=re.I):
        return ["full_allocation_100_percent"], ("full_to", m.group(1).title())
    return [], ("standard", None)

def _apply_split_rules(actual: float, rule: Tuple[str, str | None], payer: str) -> Tuple[float, float, str]:
    kind, target = rule
    if kind == "standard": return actual / 2, actual / 2, "SR | Standard 50/50 split"
    if kind == "double_charge": return actual / 2, actual / 2, "DC | Double charge documented"
    if kind == "transfer":
        return (-actual, actual, "TR | Zelle to Ryan") if (target or "").title() == "Ryan" else (actual, -actual, "TR | Zelle to Jordyn")
    if kind == "zero_out": return 0.0, 0.0, "CB | Cash-back"
    who = (target or payer).title()
    return (actual, 0.0, f"FT | Full to Ryan") if who == "Ryan" else (0.0, actual, f"FT | Full to Jordyn")

def _clean_data(df: pd.DataFrame, file_type: str) -> pd.DataFrame:
    df = df.rename(columns={v: k for k, v in _CFG.column_map.items()})
    df.columns = [c.strip().lower() for c in df.columns]
    if "person" not in df.columns and "name" in df.columns:
        df = df.rename(columns={"name": "person"})
    if "person" not in df.columns: df["person"] = "Unknown"
    
    alias_map = {alias.lower(): canon for canon, aliases in _CFG.person_aliases.items() for alias in aliases}
    df["person"] = df["person"].str.strip().str.lower().map(alias_map).fillna(df["person"])
    
    money_cols = [col for col in df.columns if "amount" in col or "rent" in col or "total" in col]
    for col in money_cols:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(r"[^0-9.\-]", "", regex=True), errors='coerce').fillna(0).round(2)
        
    df["source_file"] = file_type
    return df

def build_baseline(expense_df: pd.DataFrame, ledger_df: pd.DataFrame, rent_alloc_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    exp = _clean_data(expense_df, "expense_history")
    led = _clean_data(ledger_df, "transaction_ledger")
    rent = _clean_data(rent_alloc_df, "rent_allocation")
    
    rows = []

    # Process standard expenses and ledger items
    for _, row in pd.concat([exp, led]).iterrows():
        payer = row["person"]
        actual_paid = float(row.get("actual_amount", 0.0))
        desc = f"{row.get('description', '')} {row.get('merchant', '')}"
        flags, rule = _detect_patterns(desc, payer)

        if rule[0] == 'zero_out':
            net_effect_ryan = 0.0
            net_effect_jordyn = 0.0
            allowed_ryan = 0.0
            allowed_jordyn = 0.0
            note = "CB | Cash-back"
        else:
            allowed_ryan, allowed_jordyn, note = _apply_split_rules(actual_paid, rule, payer)
            net_effect_ryan = round(allowed_ryan - (actual_paid if payer == "Ryan" else 0.0), 2)
            net_effect_jordyn = round(allowed_jordyn - (actual_paid if payer == "Jordyn" else 0.0), 2)

        rows.append({
            "person": "Ryan", "date": row["date"], "merchant": row.get("merchant", desc),
            "actual_amount": actual_paid if payer == "Ryan" else 0.0,
            "allowed_amount": allowed_ryan, "net_effect": net_effect_ryan,
            "pattern_flags": flags, "calculation_notes": note, "transaction_type": "standard"
        })
        rows.append({
            "person": "Jordyn", "date": row["date"], "merchant": row.get("merchant", desc),
            "actual_amount": actual_paid if payer == "Jordyn" else 0.0,
            "allowed_amount": allowed_jordyn, "net_effect": net_effect_jordyn,
            "pattern_flags": flags, "calculation_notes": note, "transaction_type": "standard"
        })

    # Process rent allocations
    for _, r in rent.iterrows():
        ryan_share = r.get("ryan's rent (43%)", 0)
        jordyn_share = r.get("jordyn's rent (57%)", 0)
        full_rent = ryan_share + jordyn_share
        
        # CORRECTED: Assume Ryan pays rent
        rows.append({
            "person": "Ryan", "date": r["month"], "merchant": "Rent",
            "actual_amount": full_rent, "allowed_amount": ryan_share,
            "net_effect": round(ryan_share - full_rent, 2),
            "pattern_flags": ["rent"], "calculation_notes": "Rent | 43/57 Split (Ryan Pays)", "transaction_type": "rent"
        })
        rows.append({
            "person": "Jordyn", "date": r["month"], "merchant": "Rent",
            "actual_amount": 0.0, "allowed_amount": jordyn_share,
            "net_effect": round(jordyn_share - 0.0, 2),
            "pattern_flags": ["rent"], "calculation_notes": "Rent | 43/57 Split (Ryan Pays)", "transaction_type": "rent"
        })

    audit_df = pd.DataFrame(rows)
    
    # Final summary
    summary_df = audit_df.groupby("person")["net_effect"].sum().reset_index().rename(columns={"net_effect": "net_owed"})
    imbalance = summary_df["net_owed"].sum()
    if abs(imbalance) > _CFG.rounding_tolerance:
        print(f"⚠️ Net imbalance {imbalance:,.2f} exceeds tolerance ({_CFG.rounding_tolerance}).")
        
    return summary_df, audit_df
