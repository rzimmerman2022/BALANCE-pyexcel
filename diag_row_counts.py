#!/usr/bin/env python3
"""
Diagnostic: print raw vs kept row counts for every CSV in data/.

• Uses the same _smart_read logic (header-skip + column cleanup) as audit_run.py.
• Summarises totals and estimates expected audit rows (double-entry).
"""

import pathlib
import re
import pandas as pd

DATA_DIR = pathlib.Path("data")

RE_EXPENSE = re.compile(r"Expense_History_.*\.csv", flags=re.I)
RE_LEDGER  = re.compile(r"Transaction_Ledger_.*\.csv", flags=re.I)
RE_RENT    = re.compile(r"Rent_Allocation_.*\.csv", flags=re.I)

# minimal column-map (matches baseline logic)
COLUMN_MAP = {
    "Date of Purchase": "date",
    " Actual Amount ":  "actual_amount",
    " Allowed Amount ": "allowed_amount",
    "Description":      "description",
    "Name":             "person",
}


def _smart_read(path: pathlib.Path) -> pd.DataFrame:
    """Reads a CSV, using the first detected banner as the header."""
    raw = pd.read_csv(path, header=None, low_memory=False)
    hdr_rows = raw.index[raw.iloc[:,0].astype(str).str.match(r"(Name|Month|Ryan|.*[Ee]xpenses)",na=False)]
    
    if not len(hdr_rows):
        # no header, return as is and let downstream handle it
        return pd.read_csv(path)

    # read with the first header found, and that's it.
    df = pd.read_csv(path, header=hdr_rows[0])
    df = df.rename(columns=lambda c: c.strip()).rename(columns=COLUMN_MAP)
    
    if "person" not in df.columns and "name" in df.columns:
        df = df.rename(columns={"name": "person"})
    return df


def report(pattern: re.Pattern, label: str) -> int:
    paths = sorted(p for p in DATA_DIR.iterdir() if pattern.match(p.name))
    total_raw = total_clean = 0
    print(f"\\n=== {label} ({len(paths)} files) ===")
    for p in paths:
        raw = pd.read_csv(p, engine="python")  # engine fallback for odd quoting
        clean = _smart_read(p)
        print(f"{p.name:<35} raw={len(raw):5d}  kept={len(clean):5d}")
        total_raw += len(raw)
        total_clean += len(clean)
    print(f"TOTAL {label:<28} raw={total_raw:5d}  kept={total_clean:5d}")
    return total_clean


def main():
    exp_clean = report(RE_EXPENSE, "EXPENSES")
    led_clean = report(RE_LEDGER,  "LEDGER")
    rent_clean = report(RE_RENT,   "RENT ALLOC")

    expected_rows = 2 * (exp_clean + led_clean + rent_clean)
    print("\\nExpected audit rows (double-entry):", expected_rows)


if __name__ == "__main__":
    main()
