import importlib
import pathlib
import re
import textwrap
import warnings

import numpy as np
import pandas as pd

# ------------------------------------------------------------------------------
# 0  CONFIG & GLOBALS
# ------------------------------------------------------------------------------
warnings.simplefilter("ignore", category=UserWarning)

DATA_DIR = pathlib.Path("data")

RE_EXPENSE = re.compile(r"Expense_History_\d+\.csv")
RE_LEDGER  = re.compile(r"Transaction_Ledger_\d+\.csv")
RE_RENT    = re.compile(r"Rent_(Allocation|History)_\d+\.csv")

# Canonical names expected by the downstream pipeline
COLUMN_MAP = {
    "Date of Purchase": "date",
    " Actual Amount ":  "actual_amount",
    " Allowed Amount ": "allowed_amount",
    "Description":      "description",
    "Name":             "person",
}

# ------------------------------------------------------------------------------
# 1  UNIVERSAL MONEY CLEANER
# ------------------------------------------------------------------------------
_MONEY_RE = re.compile(r"[^\d.\-]")      # keep digits, dot, minus


def _to_money(val):
    """Strip $, commas, spaces; treat blanks/\"-\" as 0; always round to 2-dp."""
    if pd.isna(val) or val in {"", "-"}:
        return 0.0
    if isinstance(val, (int, float)):
        return round(float(val), 2)
    return round(float(_MONEY_RE.sub("", str(val))), 2)


# ------------------------------------------------------------------------------
# 2  SMART CSV READER
# ------------------------------------------------------------------------------
def _smart_read(path: pathlib.Path) -> pd.DataFrame:
    """
    Load a CSV, skip banner rows (look for Name/Month/Ryan header markers),
    strip header whitespace, then apply COLUMN_MAP aliases.
    """
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
    # Fallback: if 'person' still missing but original column exists
    if "person" not in df.columns and "name" in df.columns:
        df = df.rename(columns={"name": "person"})
    # -------- Ledger-specific rescue -------------------------------------------------
    # If we still don't have core money columns, retry reading with skiprows=1 which
    # handles ledgers that embed a title line above the header row.
    needed_cols = {"actual_amount", "actual", "allowed_amount", "allowed"}
    if needed_cols.isdisjoint(df.columns):
        try:
            df2 = (
                pd.read_csv(path, skiprows=1)
                .rename(columns=lambda c: c.strip())
                .rename(columns=COLUMN_MAP)
            )
            # accept the retry only if it solved the problem
            if not needed_cols.isdisjoint(df2.columns):
                df = df2
        except Exception:
            pass
    return df.assign(source_file=path.name)


# ------------------------------------------------------------------------------
# 3  DISCOVER CSVs & PRINT HEADER PREVIEW
# ------------------------------------------------------------------------------
EXPENSE_PATHS = sorted(DATA_DIR.glob("Expense_History_*.csv"))
LEDGER_PATHS = sorted(DATA_DIR.glob("Transaction_Ledger_*.csv"))
RENT_ALLOC_PATHS = sorted(DATA_DIR.glob("Rent_Allocation_*.csv"))

print("── Column discovery ─────────────────────────────────────────────")
all_paths = EXPENSE_PATHS + LEDGER_PATHS + RENT_ALLOC_PATHS
for p in all_paths:
    cols = ", ".join(pd.read_csv(p, nrows=0).columns)
    print(f"{p.stem:<22} → {p.name}")
    print(textwrap.fill(cols, width=100, subsequent_indent="    "))
    print("-" * 80)

# ------------------------------------------------------------------------------
# 4  BUILD DATA FRAMES
# ------------------------------------------------------------------------------

from baseline_analyzer import baseline_math as bm

from src.balance_pipeline.data_loader import load_all_data

# Reload modules to pick up changes
importlib.reload(bm)
from src.balance_pipeline import data_loader

importlib.reload(data_loader)

df = load_all_data(DATA_DIR)

summary_df, audit_df = bm.build_baseline(df)

# ------------------------------------------------------------------------------
# 7  INTEGRITY CHECK  (allowed + net == actual)
# ------------------------------------------------------------------------------
print("\\n🧾 Net-owed summary")
print(summary_df.to_markdown(index=False))

# The universal accounting identity is: allowed_amount - actual_amount = net_effect
# Therefore, we check if (allowed_amount - actual_amount - net_effect) is close to zero.
# This check is now valid for ALL transaction types.
audit_df['integrity_calc'] = audit_df['allowed_amount'].fillna(0) - audit_df['actual_amount'].fillna(0) - audit_df['net_effect'].fillna(0)

bad_rows = audit_df[np.abs(audit_df['integrity_calc']) > 0.02]

if bad_rows.empty:
    print("✅ Per-row math is internally consistent.")
else:
    print(f"❌ Inconsistent rows detected: {len(bad_rows)}")
    print(bad_rows.head().to_markdown(index=False))

# ------------------------------------------------------------------------------
# 8  GRAND TOTAL IMBALANCE WARNING
# ------------------------------------------------------------------------------
grand_imbalance = round(summary_df["net_owed"].sum(), 2)
if abs(grand_imbalance) > 0.02:
    print(
        f"\\n⚠️  Net imbalance {grand_imbalance:,.2f} exceeds tolerance "
        "(0.02) — dig into audit table."
    )
else:
    print("\\n🎉 Grand totals zero out — reconciliation complete.")
