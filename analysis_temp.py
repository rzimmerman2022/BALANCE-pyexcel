import pandas as pd
import json
from pathlib import Path
import warnings
warnings.filterwarnings("ignore", category=pd.errors.DtypeWarning)

DATA_DIR = Path("data")

def _clean_money(series):
    """
    Strip $, commas, and spaces and convert to float. 
    Empty strings become 0.0.
    """
    cleaned = (
        series.astype(str)
        .str.replace(r"[^\d\-.]", "", regex=True)
        .replace({"": 0})
    )
    return pd.to_numeric(cleaned, errors="coerce").fillna(0.0)

# ──────────────────────────────────────────────────────────────
# Expense History
# ──────────────────────────────────────────────────────────────
def analyze_expense_history(path: Path):
    df = pd.read_csv(path, engine="python")
    df.columns = [c.strip() for c in df.columns]

    # Filter section-header rows (Name contains a year or literal "Name")
    mask_header = (
        df["Name"].astype(str).str.contains(r"\d{4}", regex=True)
        | (df["Name"] == "Name")
    )
    df = df.loc[~mask_header].copy()

    # Person counts
    counts = df["Name"].value_counts().to_dict()

    # Allowed vs Actual stats
    allowed_col = [c for c in df.columns if c.lower().startswith("allowed")][0]
    actual_col = [c for c in df.columns if c.lower().startswith("actual")][0]
    allowed = _clean_money(df[allowed_col])
    actual = _clean_money(df[actual_col])

    return {
        "total_rows": int(len(df)),
        "person_counts": {k: int(v) for k, v in counts.items()},
        "equal": int((allowed == actual).sum()),
        "zero": int((allowed == 0).sum()),
        "partial": int((allowed < actual).sum()),
        "greater": int((allowed > actual).sum()),
    }

# ──────────────────────────────────────────────────────────────
# Transaction Ledger
# ──────────────────────────────────────────────────────────────
def analyze_transaction_ledger(path: Path):
    # Skip first two non-data rows
    df = pd.read_csv(path, engine="python", skiprows=2)
    df.columns = [c.strip() for c in df.columns]

    counts = df["Name"].value_counts().to_dict()
    cat_counts = df["Category"].value_counts().to_dict()

    return {
        "total_rows": int(len(df)),
        "person_counts": {k: int(v) for k, v in counts.items()},
        "category_counts": {k: int(v) for k, v in cat_counts.items()},
    }

# ──────────────────────────────────────────────────────────────
# Rent Allocation
# ──────────────────────────────────────────────────────────────
def analyze_rent_allocation(path: Path):
    df = pd.read_csv(path)
    ryan_col = [c for c in df.columns if "Ryan" in c][0]
    jord_col = [c for c in df.columns if "Jordyn" in c][0]

    ryan_total = _clean_money(df[ryan_col]).sum()
    jord_total = _clean_money(df[jord_col]).sum()

    return {
        "months": int(len(df)),
        "ryan_total": float(round(ryan_total, 2)),
        "jordyn_total": float(round(jord_total, 2)),
    }

# ──────────────────────────────────────────────────────────────
# Rent History
# ──────────────────────────────────────────────────────────────
def analyze_rent_history(path: Path):
    df = pd.read_csv(path, engine="python")

    budget_cols = [c for c in df.columns if "Budgeted" in c]
    actual_cols = [c for c in df.columns if "Actual" in c]

    budget_total = _clean_money(df[budget_cols].stack()).sum()
    actual_total = _clean_money(df[actual_cols].stack()).sum()

    return {
        "months": int(len(budget_cols)),  # each month has Budgeted/Actual
        "budget_total": float(round(budget_total, 2)),
        "actual_total": float(round(actual_total, 2)),
    }

# ──────────────────────────────────────────────────────────────
# Run analyses and save JSON to stdout
# ──────────────────────────────────────────────────────────────
results = {
    "expense_history": analyze_expense_history(DATA_DIR / "Expense_History_20250527.csv"),
    "transaction_ledger": analyze_transaction_ledger(DATA_DIR / "Transaction_Ledger_20250527.csv"),
    "rent_allocation": analyze_rent_allocation(DATA_DIR / "Rent_Allocation_20250527.csv"),
    "rent_history": analyze_rent_history(DATA_DIR / "Rent_History_20250527.csv"),
}

print(json.dumps(results, indent=2))
