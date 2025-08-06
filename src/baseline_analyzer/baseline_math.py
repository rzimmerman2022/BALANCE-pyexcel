"""
Core accounting logic for the balance analyzer.
"""
from __future__ import annotations

import logging
import re

import pandas as pd

from ._settings import get_settings

_CFG = get_settings()
_PATTERNS: dict[str, re.Pattern] = {k: re.compile(v, flags=re.I) for k, v in _CFG.patterns.items()}

log = logging.getLogger(__name__)

def _detect_patterns(desc: str, payer: str) -> tuple[list[str], tuple[str, str | None]]:
    desc_l = desc or ""
    if "2x" in desc_l.lower():
        if m := re.search(r"\b2x\s+(Ryan|Jordyn)", desc_l, re.I) or re.search(r"(Ryan|Jordyn).*?\b2x\b", desc_l, re.I):
            return ["multiplier_2x"], ("full_to", m.group(1).title())
        if re.search(r"\$\s*\d+(?:\.\d{1,2})?\s*\(2x\)", desc_l, re.I):
            return ["multiplier_2x", "double_charge"], ("double_charge", None)
        return ["multiplier_2x", "ambiguous_2x"], ("full_to", payer)
    for key in ("xfer_to_ryan", "xfer_to_jordyn", "cashback", "gift", "gift_or_present"):
        if key in _PATTERNS and _PATTERNS[key].search(desc_l):
            if key.startswith("xfer_to_"):
                return [key], ("transfer", "Ryan" if key.endswith("ryan") else "Jordyn")
            if key == "cashback":
                return [key], ("zero_out", None)
            if key in ("gift", "gift_or_present"):
                return [key], ("full_to", "Jordyn" if payer.lower() == "ryan" else "Ryan")
    if m := re.search(r"100%\s+(Jordyn|Ryan)", desc_l, flags=re.I):
        return ["full_allocation_100_percent"], ("full_to", m.group(1).title())
    return [], ("standard", None)

def _apply_split_rules(actual: float, rule: tuple[str, str | None], payer: str) -> tuple[float, float, str]:
    kind, target = rule
    if kind == "standard": return actual / 2, actual / 2, "SR | Standard 50/50 split"
    if kind == "double_charge": return actual / 2, actual / 2, "DC | Double charge documented"
    if kind == "transfer":
        return (-actual, actual, "TR | Zelle to Ryan") if (target or "").title() == "Ryan" else (actual, -actual, "TR | Zelle to Jordyn")
    if kind == "zero_out": return 0.0, 0.0, "CB | Cash-back"
    who = (target or payer).title()
    return (actual, 0.0, "FT | Full to Ryan") if who == "Ryan" else (0.0, actual, "FT | Full to Jordyn")

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

def build_baseline(df: pd.DataFrame, output_dir: str = "audit_reports") -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Build baseline analysis with audit trail.
    
    Args:
        df: Input DataFrame with CTS schema
        output_dir: Directory to save audit files (default: "audit_reports")
    
    Returns:
        tuple: (summary_df, audit_df)
    """
    import pathlib
    
    # Ensure output directory exists
    pathlib.Path(output_dir).mkdir(exist_ok=True)
    
    # Clean the input data
    df = _clean_data(df, "test_data")
    
    rows = []

    # Process standard expenses and ledger items
    for _, row in df.iterrows():
        payer = row["person"]
        actual_paid = float(row.get("actual", 0.0))
        allowed_amount = float(row.get("allowed", 0.0))
        
        # Handle expense history records (have allowed but no actual)
        if allowed_amount > 0 and actual_paid == 0:
            # For expense history, the payer gets the allowed amount, other person gets 0
            if payer == "Ryan":
                allowed_ryan = allowed_amount
                allowed_jordyn = 0.0
                net_effect_ryan = allowed_amount  # Ryan gets positive allowed amount
                net_effect_jordyn = -allowed_amount  # Jordyn owes this amount
            else:
                allowed_ryan = 0.0
                allowed_jordyn = allowed_amount
                net_effect_ryan = -allowed_amount  # Ryan owes this amount
                net_effect_jordyn = allowed_amount  # Jordyn gets positive allowed amount
            note = "EH | Expense History"
            flags = ["expense_history"]
        else:
            # Standard transaction processing
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

        # Preserve full original description for context
        full_description = f"{row.get('description', '')} | {row.get('merchant', '')}".strip(' |')
        
        rows.append({
            "person": "Ryan", "date": row["date"], "merchant": row.get("merchant", ""),
            "full_description": full_description,
            "actual_amount": actual_paid if payer == "Ryan" else 0.0,
            "allowed_amount": allowed_ryan, "net_effect": net_effect_ryan,
            "pattern_flags": flags, "calculation_notes": note, "transaction_type": "standard",
            "source_file": row["source_file"]
        })
        rows.append({
            "person": "Jordyn", "date": row["date"], "merchant": row.get("merchant", ""),
            "full_description": full_description,
            "actual_amount": actual_paid if payer == "Jordyn" else 0.0,
            "allowed_amount": allowed_jordyn, "net_effect": net_effect_jordyn,
            "pattern_flags": flags, "calculation_notes": note, "transaction_type": "standard",
            "source_file": row["source_file"]
        })

    # Process rent allocations
    rent_df = df[df['source_file'].isin(['Rent_Allocation', 'Rent_History'])].copy()
    for _, r in rent_df.iterrows():
        if r['source_file'] == 'Rent_Allocation':
            ryan_share = r.get("allowed_amount", 0)
            jordyn_share = r.get("actual_amount", 0) - ryan_share
            full_rent = r.get("actual_amount", 0)
        
            # CORRECTED: Assume Ryan pays rent
            rent_description = f"{r.get('description', '')} | Rent Allocation".strip(' |')
            
            rows.append({
                "person": "Ryan", "date": r["date"], "merchant": "Rent",
                "full_description": rent_description,
                "actual_amount": full_rent, "allowed_amount": ryan_share,
                "net_effect": round(ryan_share - full_rent, 2),
                "pattern_flags": ["rent"], "calculation_notes": "Rent | 43/57 Split (Ryan Pays)", "transaction_type": "rent",
                "source_file": "Rent_Allocation"
            })
            rows.append({
                "person": "Jordyn", "date": r["date"], "merchant": "Rent",
                "full_description": rent_description,
                "actual_amount": 0.0, "allowed_amount": jordyn_share,
                "net_effect": round(jordyn_share - 0.0, 2),
                "pattern_flags": ["rent"], "calculation_notes": "Rent | 43/57 Split (Ryan Pays)", "transaction_type": "rent",
                "source_file": "Rent_Allocation"
            })
        elif r['source_file'] == 'Rent_History':
            # For Rent_History, the actual_amount is the full rent paid by Ryan
            # and allowed_amount is his share.
            rent_hist_description = f"{r.get('description', '')} | {r.get('merchant', '')} | Rent History".strip(' |')
            
            rows.append({
                "person": "Ryan", "date": r["date"], "merchant": r['merchant'],
                "full_description": rent_hist_description,
                "actual_amount": r['actual_amount'], "allowed_amount": r['allowed_amount'],
                "net_effect": round(r['allowed_amount'] - r['actual_amount'], 2),
                "pattern_flags": ["rent"], "calculation_notes": "Rent | History", "transaction_type": "rent",
                "source_file": "Rent_History"
            })
            rows.append({
                "person": "Jordyn", "date": r["date"], "merchant": r['merchant'],
                "full_description": rent_hist_description,
                "actual_amount": 0, "allowed_amount": r['actual_amount'] - r['allowed_amount'],
                "net_effect": round(r['actual_amount'] - r['allowed_amount'], 2),
                "pattern_flags": ["rent"], "calculation_notes": "Rent | History", "transaction_type": "rent",
                "source_file": "Rent_History"
            })

    audit_df = pd.DataFrame(rows)
    
    # Add running balance calculation
    # Sort by date to ensure chronological order
    audit_df = audit_df.sort_values(['date', 'source_file', 'person']).reset_index(drop=True)
    
    # Add transaction sequence number
    audit_df['transaction_id'] = range(1, len(audit_df) + 1)
    
    # Calculate running balances for each person
    ryan_balance = 0.0
    jordyn_balance = 0.0
    running_balances_ryan = []
    running_balances_jordyn = []
    
    for _, row in audit_df.iterrows():
        if row['person'] == 'Ryan':
            ryan_balance += row['net_effect']
        elif row['person'] == 'Jordyn':
            jordyn_balance += row['net_effect']
        
        running_balances_ryan.append(round(ryan_balance, 2))
        running_balances_jordyn.append(round(jordyn_balance, 2))
    
    audit_df['running_balance_ryan'] = running_balances_ryan
    audit_df['running_balance_jordyn'] = running_balances_jordyn
    
    # Final summary
    summary_df = audit_df.groupby("person")["net_effect"].sum().reset_index().rename(columns={"net_effect": "net_owed"})
    imbalance = summary_df["net_owed"].sum()
    if abs(imbalance) > _CFG.rounding_tolerance:
        log.warning(f"Net imbalance {imbalance:,.2f} exceeds tolerance ({_CFG.rounding_tolerance}).")
    
    # Auto-save audit files to output directory
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    audit_file = f"{output_dir}/complete_audit_trail_{timestamp}.csv"
    summary_file = f"{output_dir}/balance_summary_{timestamp}.csv"
    
    audit_df.to_csv(audit_file, index=False)
    summary_df.to_csv(summary_file, index=False)
    
    log.info(f"Saved audit trail: {audit_file}")
    log.info(f"Saved summary: {summary_file}")
        
    return summary_df, audit_df
