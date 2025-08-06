#!/usr/bin/env python3
"""
Generates a comprehensive audit trail CSV from the final, reconciled data.
This script loads the source data, runs the baseline analysis, and then
enriches the output with additional columns for deeper analysis as specified
in the project requirements.
"""

import os
import pathlib
import re
import sys
from datetime import datetime

import pandas as pd

# Add src directory to path to import baseline_math
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))
from baseline_analyzer import baseline_math as bm

# --- Data Loading Functions (mirrored from audit_run.py) ---
DATA_DIR = pathlib.Path("data")
RE_EXPENSE = re.compile(r"Expense_History_\d+\.csv")
RE_LEDGER  = re.compile(r"Transaction_Ledger_\d+\.csv")
RE_RENT    = re.compile(r"Rent_(Allocation|History)_\d+\.csv")

COLUMN_MAP = {
    "Date of Purchase": "date",
    " Actual Amount ":  "actual_amount",
    " Allowed Amount ": "allowed_amount",
    "Description":      "description",
    "Name":             "person",
}

_MONEY_RE = re.compile(r"[^\d.\-]")

def _to_money(val):
    if pd.isna(val) or val in {"", "-"}: return 0.0
    if isinstance(val, (int, float)): return round(float(val), 2)
    return round(float(_MONEY_RE.sub("", str(val))), 2)

def _smart_read(path: pathlib.Path) -> pd.DataFrame:
    raw = pd.read_csv(path, header=None)
    hdr_rows = raw.index[raw.iloc[:, 0].astype(str).str.match(r"(Name|Month|Ryan|.*[Ee]xpenses)", na=False)]
    df = pd.read_csv(path, skiprows=int(hdr_rows[-1])) if len(hdr_rows) else pd.read_csv(path)
    df = df.rename(columns=lambda c: c.strip()).rename(columns=COLUMN_MAP)
    if "person" not in df.columns and "name" in df.columns:
        df = df.rename(columns={"name": "person"})
    needed_cols = {"actual_amount", "actual", "allowed_amount", "allowed"}
    if needed_cols.isdisjoint(df.columns):
        try:
            df2 = pd.read_csv(path, skiprows=1).rename(columns=lambda c: c.strip()).rename(columns=COLUMN_MAP)
            if not needed_cols.isdisjoint(df2.columns): df = df2
        except Exception: pass
    return df.assign(source_file=path.name)

def _cook_rent_alloc(path: pathlib.Path) -> pd.DataFrame:
    df = pd.read_csv(path).rename(columns=str.strip)
    rows = []
    for _, r in df.iterrows():
        ryan_share = _to_money(r.get("Ryan's Rent (43%)", 0))
        jordyn_share = _to_money(r.get("Jordyn's Rent (57%)", 0))
        full_rent_amount = ryan_share + jordyn_share
        if full_rent_amount == 0: continue
        fair_share = full_rent_amount / 2
        jordyn_net_effect = fair_share - full_rent_amount
        ryan_net_effect = fair_share - 0
        pair_id = f"rent_{r['Month']}_{full_rent_amount:.0f}"
        rows.append({
            "person": "Jordyn", "date": r["Month"], "merchant": "Rent",
            "actual_amount": full_rent_amount, "allowed_amount": jordyn_share,
            "net_effect": jordyn_net_effect, "transaction_type": "synthetic_rent",
            "calculation_notes": "Rent: Pre-calculated", "double_entry_pair": pair_id,
        })
        rows.append({
            "person": "Ryan", "date": r["Month"], "merchant": "Rent",
            "actual_amount": 0.00, "allowed_amount": ryan_share,
            "net_effect": ryan_net_effect, "transaction_type": "synthetic_rent",
            "calculation_notes": "Rent: Pre-calculated", "double_entry_pair": pair_id,
        })
    final_cols = ["person", "date", "merchant", "actual_amount", "allowed_amount", "net_effect", "source_file", "transaction_type", "calculation_notes", "double_entry_pair"]
    if not rows: return pd.DataFrame(columns=final_cols)
    return pd.DataFrame(rows).assign(source_file=path.name)

def _cook_rent_hist(path: pathlib.Path) -> pd.DataFrame:
    return pd.DataFrame([], columns=["person", "date", "merchant", "actual_amount", "allowed_amount", "source_file"])

def generate_audit_trail():
    """Main function to generate the enhanced audit trail."""
    print("─" * 80)
    print("🚀 Generating Comprehensive Audit Trail...")
    print("─" * 80)

    # 1. Load Data
    print("1. Loading source data...")
    try:
        EXPENSE_PATHS = sorted(p for p in DATA_DIR.iterdir() if RE_EXPENSE.match(p.name) or RE_RENT.match(p.name))
        LEDGER_PATH = next(p for p in DATA_DIR.iterdir() if RE_LEDGER.match(p.name))
        rent_alloc_path = next(p for p in DATA_DIR.iterdir() if p.name.startswith("Rent_Allocation"))

        expense_df = pd.concat([_smart_read(p) for p in EXPENSE_PATHS if not p.name.startswith("Rent_")], ignore_index=True)
        ledger_df = _smart_read(LEDGER_PATH)
        rent_alloc_df = pd.read_csv(rent_alloc_path)
        print("✅ Data loaded successfully.")
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return

    # 2. Run Baseline Analysis
    print("\n2. Running baseline reconciliation...")
    summary_df, audit_df = bm.build_baseline(expense_df, ledger_df, rent_alloc_df)
    print("✅ Reconciliation complete.")

    # 3. Enhance Audit Trail
    print("\n3. Enhancing audit trail with required columns...")
    
    # Rename columns to match prompt spec
    audit_df = audit_df.rename(columns={
        'date': 'original_date',
        'notes': 'reconciliation_notes',
        'pattern_flags': 'pattern_matched'
    })
    
    # Add new columns
    audit_df['transaction_id'] = audit_df.index.map(lambda x: f"txn_{x+1:04d}")
    audit_df['integrity_check'] = (audit_df['allowed_amount'].fillna(0) - audit_df['actual_amount'].fillna(0) - audit_df['net_effect'].fillna(0)).abs() < 0.02
    
    # Ensure 'original_description' exists - use merchant if not present
    if 'original_description' not in audit_df.columns:
        audit_df['original_description'] = audit_df['merchant']

    # Calculate running balances
    audit_df['original_date'] = pd.to_datetime(audit_df['original_date'], errors='coerce')
    audit_df = audit_df.sort_values(by=['original_date', 'transaction_id']).reset_index(drop=True)
    
    ryan_balance = audit_df[audit_df['person'] == 'Ryan']['net_effect'].cumsum()
    jordyn_balance = audit_df[audit_df['person'] == 'Jordyn']['net_effect'].cumsum()
    
    audit_df['running_balance_ryan'] = ryan_balance
    audit_df['running_balance_jordyn'] = jordyn_balance
    
    # Use forward fill to propagate the last valid balance to all rows for that person
    audit_df['running_balance_ryan'] = audit_df.groupby('person')['running_balance_ryan'].ffill()
    audit_df['running_balance_jordyn'] = audit_df.groupby('person')['running_balance_jordyn'].ffill()
    audit_df.fillna({'running_balance_ryan': 0, 'running_balance_jordyn': 0}, inplace=True)


    # Reorder columns to match the spec
    final_columns = [
        'transaction_id', 'source_file', 'original_date', 'person', 'merchant',
        'original_description', 'actual_amount', 'allowed_amount', 'net_effect',
        'pattern_matched', 'calculation_notes', 'transaction_type', 'integrity_check',
        'running_balance_ryan', 'running_balance_jordyn', 'reconciliation_notes'
    ]
    # Add any missing columns with default values
    for col in final_columns:
        if col not in audit_df.columns:
            audit_df[col] = ''
            
    audit_df = audit_df[final_columns]
    print("✅ Audit trail enhanced.")

    # 4. Save to CSV
    timestamp = datetime.now().strftime("%Y-%m-%d")
    output_dir = pathlib.Path("artifacts")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / f"complete_audit_trail_{timestamp}.csv"
    
    print(f"\n4. Saving final audit trail to '{output_path}'...")
    audit_df.to_csv(output_path, index=False, date_format='%Y-%m-%d')
    print("✅ Save complete.")
    print("─" * 80)
    print("🎉 Phase 2 Complete: Comprehensive audit trail generated.")
    print("─" * 80)

if __name__ == "__main__":
    generate_audit_trail()
