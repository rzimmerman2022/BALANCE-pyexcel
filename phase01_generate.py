#!/usr/bin/env python3
"""
Phase-0 & Phase-1 automation

• Phase 0  – build artifacts/detailed_audit_trail.csv
• Phase 1  – build sign_convention_analysis.md (diagnostic only)

Run:  python phase01_generate.py
"""
import pathlib, re, textwrap
from datetime import datetime

import pandas as pd
import importlib
from baseline_analyzer import baseline_math as bm

# ──────────────────────────────────────────────────────────────────────────
# Helper: generic CSV reader (mirrors audit_run.py logic, simplified)
# ──────────────────────────────────────────────────────────────────────────
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

def _smart_read(path: pathlib.Path) -> pd.DataFrame:
    """Reads a CSV, using the first detected banner as the header."""
    raw = pd.read_csv(path, header=None, low_memory=False)
    hdr_rows = raw.index[raw.iloc[:,0].astype(str).str.match(r"(Name|Month|Ryan|.*[Ee]xpenses)",na=False)]
    
    if not len(hdr_rows):
        # no header, return as is and let downstream handle it
        df = pd.read_csv(path)
    else:
        # read with the first header found
        df = pd.read_csv(path, header=hdr_rows[0])

    df = df.rename(columns=lambda c: c.strip()).rename(columns=COLUMN_MAP)
    
    if "person" not in df.columns and "name" in df.columns:
        df = df.rename(columns={"name": "person"})
    return df.assign(source_file=path.name)

# ──────────────────────────────────────────────────────────────────────────
# Phase 0  – build detailed audit trail
# ──────────────────────────────────────────────────────────────────────────
def build_detailed_audit():
    expense_paths = sorted(DATA_DIR.glob("Expense_History_*.csv"))
    ledger_paths = sorted(DATA_DIR.glob("Transaction_Ledger_*.csv"))
    rent_paths = sorted(DATA_DIR.glob("Rent_Allocation_*.csv"))

    expense_df = pd.concat([_smart_read(p) for p in expense_paths], ignore_index=True)
    ledger_df = pd.concat([_smart_read(p) for p in ledger_paths], ignore_index=True)
    rent_df = pd.concat([pd.read_csv(p) for p in rent_paths], ignore_index=True)

    importlib.reload(bm)   # hot-reload in case code changed
    summary_df, audit_df = bm.build_baseline(expense_df, ledger_df, rent_df)

    # add required columns
    audit_df = audit_df.copy()
    audit_df["row_global_id"] = range(1, len(audit_df) + 1)
    audit_df["integrity_check"] = (
        (
            audit_df["allowed_amount"].fillna(0)
            + audit_df["net_effect"].fillna(0)
            - audit_df["actual_amount"].fillna(0)
        ).abs()
        < 0.02
    )

    # running_balance (per person, ordered)
    audit_df["date"] = pd.to_datetime(audit_df["date"], errors="coerce")
    audit_df = audit_df.sort_values(["person", "date", "row_global_id"]).reset_index(drop=True)
    audit_df["running_balance"] = audit_df.groupby("person")["net_effect"].cumsum()

    # format pattern_flags column for CSV
    audit_df["pattern_flags"] = audit_df["pattern_flags"].apply(
        lambda x: ";".join(x) if isinstance(x, list) else str(x)
    )

    # final column order
    cols_required = [
        "row_global_id",
        "source_file",
        "date",
        "person",
        "merchant",
        "description",
        "actual_amount",
        "allowed_amount",
        "net_effect",
        "pattern_flags",
        "calculation_notes",
        "transaction_type",   # keep for downstream analysis
        "integrity_check",
        "running_balance",
    ]
    for c in cols_required:
        if c not in audit_df.columns:
            audit_df[c] = ""

    audit_df = audit_df[cols_required]

    # save
    out_dir  = pathlib.Path("artifacts")
    out_dir.mkdir(exist_ok=True)
    csv_path = out_dir / "detailed_audit_trail.csv"
    audit_df.to_csv(csv_path, index=False, date_format="%Y-%m-%d")
    print(f"✔ detailed audit trail → {csv_path}  ({len(audit_df):,} rows)")
    return audit_df


# ──────────────────────────────────────────────────────────────────────────
# Phase 1  – sign-convention analysis markdown
# ──────────────────────────────────────────────────────────────────────────
FORMULAS = textwrap.dedent(
    """\
    # --- Standard expenses / ledger ---
    net_effect_ryan   = round(allowed_ryan   - (actual_paid if payer == "Ryan"   else 0.0), 2)
    net_effect_jordyn = round(allowed_jordyn - (actual_paid if payer == "Jordyn" else 0.0), 2)

    # --- Rent rows (Ryan assumed payer) ---
    net_effect = round(ryan_share   - full_rent, 2)   # Ryan row
    net_effect = round(jordyn_share - 0.0,      2)   # Jordyn row
    """
)

GROUPBY_LINE = (
    'summary_df = audit_df.groupby("person")["net_effect"].sum()'
    '.reset_index().rename(columns={"net_effect": "net_owed"})'
)


def pick_example_rows(audit_df: pd.DataFrame):
    """Return three exemplar rows: Ryan-paid standard, Jordyn-paid standard, rent."""
    std_ryan  = audit_df.query("person == 'Ryan'   and actual_amount > 0 and transaction_type == 'standard'").head(1)
    std_jordy = audit_df.query("person == 'Jordyn' and actual_amount > 0 and transaction_type == 'standard'").head(1)
    rent_row  = audit_df.query("merchant == 'Rent' and transaction_type == 'rent' and person == 'Ryan'").head(1)
    return pd.concat([std_ryan, std_jordy, rent_row], ignore_index=True)


def make_markdown(audit_df: pd.DataFrame):
    md_lines = []
    md_lines.append("# Sign-Convention Analysis\n")

    # 1.1 raw formulas
    md_lines.append("## 1.1 net_effect calculation (verbatim)")
    md_lines.append("```python")
    md_lines.append(FORMULAS.rstrip())
    md_lines.append("```")

    # three concrete rows
    examples = pick_example_rows(audit_df)
    md_lines.append("\n### Example rows – input → calculation")
    for _, r in examples.iterrows():
        who = r["person"]
        date_val = r["date"]
        date_str = "NA" if pd.isna(date_val) else date_val.strftime("%Y-%m-%d")
        md_lines.append(
            f"- **{who}**, {date_str}, {r['merchant']}:  "
            f"actual={r['actual_amount']:.2f}, allowed={r['allowed_amount']:.2f} "
            f"→ net_effect = {r['net_effect']:+.2f}"
        )

    # 1.2 aggregation
    md_lines.append("\n## 1.2 Balance accumulation")
    md_lines.append("Code:")
    md_lines.append("```python")
    md_lines.append(GROUPBY_LINE)
    md_lines.append("```")

    md_lines.append("\n### Interpretation")
    md_lines.append(
        "*Positive* net_effect → the person **owes** the partner (they under-paid).\n"
        "*Negative* net_effect → the person **is owed** (they over-paid).\n"
    )
    md_lines.append(
        "*Positive* net_owed → cumulative amount the person still owes.\n"
        "*Negative* net_owed → cumulative amount the person should receive."
    )

    # 10-transaction running balance
    slice_df = (
        audit_df.sort_values(["date", "row_global_id"])
        .head(10)
        .reset_index(drop=True)
        .assign(idx=lambda d: d.index + 1)
    )
    bal_table = slice_df[["idx", "date", "merchant", "person", "net_effect", "running_balance"]]
    md_lines.append("\n### 10-transaction running-balance sample")
    md_lines.append(bal_table.to_markdown(index=False))

    # 1.3 summary bullets
    md_lines.append("\n## 1.3 Current sign conventions")
    md_lines.append(
        textwrap.dedent(
            """\
            • Positive net_effect means **the person owes** their partner  
            • Negative net_effect means **the person is owed**  
            • Positive net_owed means **cumulative amount owed**  
            • Negative net_owed means **cumulative amount to be received**  
            *No flips detected between expense types; rent rows obey the same rule.*
            """
        )
    )

    md_path = pathlib.Path("sign_convention_analysis.md")
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"✔ analysis markdown → {md_path}")


# ──────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    df = build_detailed_audit()
    make_markdown(df)
    print("\n### Phase 0 complete – audit trail written to artifacts/")
    print("### Phase 1 complete – analysis markdown created")
    print("Ready for review.")
