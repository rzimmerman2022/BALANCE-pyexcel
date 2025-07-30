import pathlib, re, warnings
import numpy as np
import pandas as pd

# Silence noisy dtype warnings from wide CSVs
warnings.filterwarnings("ignore", category=pd.errors.DtypeWarning)

# ------------------------------------------------------------------------------
# Local helpers (mirrors audit_run.py logic in a few lines)
# ------------------------------------------------------------------------------
DATA_DIR = pathlib.Path("data")
RE_EXP   = re.compile(r"Expense_History_\d+\.csv")
RE_LED   = re.compile(r"Transaction_Ledger_\d+\.csv")

COLUMN_MAP = {
    "Date of Purchase": "date",
    " Actual Amount ":  "actual_amount",
    " Allowed Amount ": "allowed_amount",
    "Description":      "description",
    "Name":             "person",
}

_MONEY_RE = re.compile(r"[^\\d.\\-]")

def _to_money(val):
    """Cheap money cleaner (same as audit_run) – tolerates lone '.' or commas."""
    if pd.isna(val) or val in {"", "-", "."}:
        return 0.0
    try:
        return round(float(_MONEY_RE.sub("", str(val))), 2)
    except ValueError:
        # Any other weird token → treat as zero but leave breadcrumb for future analysis
        return 0.0

def _smart_read(path: pathlib.Path) -> pd.DataFrame:
    """Banner-row skip, header strip, alias, fallback person column."""
    raw = pd.read_csv(path, header=None)
    hdr = raw.index[raw.iloc[:, 0].astype(str).str.match(r"(Name|Month|Ryan)", na=False)]
    df  = pd.read_csv(path, skiprows=int(hdr[0])) if len(hdr) else pd.read_csv(path)
    df  = df.rename(columns=lambda c: c.strip()).rename(columns=COLUMN_MAP)
    if "person" not in df.columns and "name" in df.columns:
        df = df.rename(columns={"name": "person"})
    return df

# ------------------------------------------------------------------------------
# Load expense files (+ rent allocation cooker)
# ------------------------------------------------------------------------------
frames = []
for p in DATA_DIR.iterdir():
    if RE_EXP.match(p.name):
        frames.append(_smart_read(p))
    elif p.name.startswith("Rent_Allocation"):
        alloc = pd.read_csv(p).rename(columns=str.strip)
        rows = []
        for _, r in alloc.iterrows():
            rows.append({
                "person": "Ryan",
                "date": r["Month"],
                "merchant": "Rent",
                "actual_amount": _to_money(r["Ryan's Rent (43%)"]),
                "allowed_amount": _to_money(r["Ryan's Rent (43%)"]),
            })
            rows.append({
                "person": "Jordyn",
                "date": r["Month"],
                "merchant": "Rent",
                "actual_amount": _to_money(r["Jordyn's Rent (57%)"]),
                "allowed_amount": 0.0,
            })
        frames.append(pd.DataFrame(rows))

expense_df = pd.concat(frames, ignore_index=True)

try:
    ledger_path = next(p for p in DATA_DIR.iterdir() if RE_LED.match(p.name))
    ledger_df   = _smart_read(ledger_path)
except StopIteration:
    # No ledger present → create empty placeholder
    ledger_df = pd.DataFrame(columns=["person","date","merchant","actual","allowed","description"])

# Re-use the existing baseline builder
from baseline_analyzer import baseline_math as bm
import importlib; importlib.reload(bm)

_, audit = bm.build_baseline(expense_df, ledger_df)

bad = audit.loc[
    ~np.isclose(
        audit["allowed_amount"].fillna(0) + audit["net_effect"].fillna(0),
        audit["actual_amount"].fillna(0),
        atol=1e-6,
    )
]

sample = bad[["description", "merchant", "person", "actual_amount", "allowed_amount"]].head(250)

print("\\nBad-row sample (first 250 rows):\\n")
print(sample.to_markdown(index=False))

# Write full set for spreadsheet review
out_path = pathlib.Path("artifacts") / "bad_rows_full.csv"
out_path.parent.mkdir(parents=True, exist_ok=True)
bad.to_csv(out_path, index=False)
print(f"\\nFull inconsistent-row table written to {out_path}")
