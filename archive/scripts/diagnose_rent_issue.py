#!/usr/bin/env python3
"""
Diagnostic script to analyze the 294 inconsistent rows and confirm
that rent allocation is the primary cause of the mismatches.
"""

import pathlib
import re

import numpy as np
import pandas as pd
from baseline_analyzer import baseline_math as bm

# Load data using the same logic as audit_run.py
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

def _to_money(val):
    """Strip $, commas, spaces; treat blanks/\"-\" as 0; always round to 2-dp."""
    if pd.isna(val) or val in {"", "-"}:
        return 0.0
    if isinstance(val, (int, float)):
        return round(float(val), 2)
    return round(float(re.sub(r"[^\d.\-]", "", str(val))), 2)

def _smart_read(path: pathlib.Path) -> pd.DataFrame:
    """Load CSV with smart header detection."""
    raw = pd.read_csv(path, header=None)
    hdr_rows = raw.index[
        raw.iloc[:, 0]
        .astype(str)
        .str.match(r"(Name|Month|Ryan|.*[Ee]xpenses)", na=False)
    ]
    df = (
        pd.read_csv(path, skiprows=int(hdr_rows[-1]))
        if len(hdr_rows)
        else pd.read_csv(path)
    )
    df = df.rename(columns=lambda c: c.strip()).rename(columns=COLUMN_MAP)
    if "person" not in df.columns and "name" in df.columns:
        df = df.rename(columns={"name": "person"})
    
    needed_cols = {"actual_amount", "actual", "allowed_amount", "allowed"}
    if needed_cols.isdisjoint(df.columns):
        try:
            df2 = (
                pd.read_csv(path, skiprows=1)
                .rename(columns=lambda c: c.strip())
                .rename(columns=COLUMN_MAP)
            )
            if not needed_cols.isdisjoint(df2.columns):
                df = df2
        except Exception:
            pass
    return df.assign(source_file=path.name)

def _cook_rent_alloc(path: pathlib.Path) -> pd.DataFrame:
    df = pd.read_csv(path).rename(columns=str.strip)
    rows = []
    for _, r in df.iterrows():
        rows += [
            {
                "person": "Ryan",
                "date": r["Month"],
                "merchant": "Rent",
                "actual_amount": _to_money(r["Ryan's Rent (43%)"]),
                "allowed_amount": _to_money(r["Ryan's Rent (43%)"]),
            },
            {
                "person": "Jordyn",
                "date": r["Month"],
                "merchant": "Rent",
                "actual_amount": _to_money(r["Jordyn's Rent (57%)"]),
                "allowed_amount": 0.0,
            },
        ]
    return pd.DataFrame(rows).assign(source_file=path.name)

def _cook_rent_hist(path: pathlib.Path) -> pd.DataFrame:
    return pd.DataFrame(
        [], columns=["person", "date", "merchant", "actual_amount", "allowed_amount", "source_file"]
    )

print("🔍 Loading data and running baseline analysis...")

# Load data
EXPENSE_PATHS = sorted(
    p for p in DATA_DIR.iterdir() if RE_EXPENSE.match(p.name) or RE_RENT.match(p.name)
)
LEDGER_PATH = next(p for p in DATA_DIR.iterdir() if RE_LEDGER.match(p.name))

frames = []
for p in EXPENSE_PATHS:
    if p.name.startswith("Rent_Allocation"):
        frames.append(_cook_rent_alloc(p))
    elif p.name.startswith("Rent_History"):
        frames.append(_cook_rent_hist(p))
    else:
        frames.append(_smart_read(p))

expense_df = pd.concat(frames, ignore_index=True)
ledger_df = _smart_read(LEDGER_PATH)

# Run baseline analysis
summary_df, audit_df = bm.build_baseline(expense_df, ledger_df)

print(f"📊 Total rows in audit: {len(audit_df)}")
print(f"💰 Net imbalance: ${summary_df['net_owed'].sum():.2f}")

# Find inconsistent rows
bad_rows = audit_df.loc[
    ~np.isclose(
        audit_df["allowed_amount"].fillna(0) + audit_df["net_effect"].fillna(0),
        audit_df["actual_amount"].fillna(0),
        atol=1e-6,
    )
]

print(f"❌ Total inconsistent rows: {len(bad_rows)}")

# Separate rent vs non-rent inconsistent rows
rent_inconsistent = bad_rows[
    bad_rows["merchant"].astype(str).str.contains("rent", case=False, na=False)
]
other_inconsistent = bad_rows[
    ~bad_rows["merchant"].astype(str).str.contains("rent", case=False, na=False)
]

print(f"\n🏠 Rent-related inconsistent rows: {len(rent_inconsistent)}")
print(f"🛒 Other inconsistent rows: {len(other_inconsistent)}")
print(f"📈 Rent percentage of total: {len(rent_inconsistent)/len(bad_rows)*100:.1f}%")

print("\n🔍 Sample rent inconsistent rows:")
print(rent_inconsistent[["person", "date", "merchant", "actual_amount", "allowed_amount", "net_effect"]].head(10).to_string(index=False))

print("\n🔍 Sample other inconsistent rows:")
if len(other_inconsistent) > 0:
    print(other_inconsistent[["person", "date", "merchant", "actual_amount", "allowed_amount", "net_effect"]].head(10).to_string(index=False))
else:
    print("No other inconsistent rows found!")

# Analyze rent patterns
if len(rent_inconsistent) > 0:
    print("\n📋 Rent inconsistency analysis:")
    rent_by_person = rent_inconsistent.groupby("person").agg({
        "actual_amount": ["count", "sum"],
        "allowed_amount": "sum",
        "net_effect": "sum"
    }).round(2)
    print(rent_by_person)
    
    print("\n💡 Expected rent allocation (43% Ryan, 57% Jordyn):")
    total_rent = rent_inconsistent["actual_amount"].sum() / 2  # Divide by 2 since each rent payment creates 2 rows
    expected_ryan = total_rent * 0.43
    expected_jordyn = total_rent * 0.57
    print(f"   Total rent amount: ${total_rent:.2f}")
    print(f"   Ryan should get: ${expected_ryan:.2f} (43%)")
    print(f"   Jordyn should get: ${expected_jordyn:.2f} (57%)")
