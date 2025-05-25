import pandas as pd
from pathlib import Path

# ── 1. Load the parquet file ─────────────────────────────────────────────────────
df = pd.read_parquet(r"C:\BALANCE\BALANCE-pyexcel\artifacts\balance_final.parquet")

print("COMPREHENSIVE DATA ANALYSIS")
print("=" * 60)

# ── 2. Show every column name ────────────────────────────────────────────────────
print("\nALL COLUMNS IN YOUR FILE:")
for i, col in enumerate(df.columns, 1):
    print(f"{i:2d}. {col}")

# ── 3. Date-column diagnostics ───────────────────────────────────────────────────
print("\n\nDATE COLUMN ANALYSIS:")
print("-" * 40)
if "Date" in df.columns:
    print(f"Date column dtype: {df['Date'].dtype}")

    print("\nFirst 5 Date values (raw):")
    for i, val in enumerate(df['Date'].head()):
        print(f"  {i}: {repr(val)} (type: {type(val).__name__})")

    date_series   = pd.to_datetime(df["Date"], errors="coerce")
    valid_dates   = date_series.notna().sum()
    invalid_dates = date_series.isna().sum()

    print(f"\nDate parsing results:")
    print(f"  Valid dates:   {valid_dates}")
    print(f"  Invalid dates: {invalid_dates}")

    if valid_dates:
        print(f"  Date range:    {date_series.min()}  →  {date_series.max()}")

# ── 4. Scan for text columns that look like descriptions ─────────────────────────
print("\n\nSEARCHING FOR TRANSACTION DESCRIPTION DATA:")
print("-" * 40)
for col in df.columns:
    if df[col].dtype == "object":
        non_empty = df[col].notna()
        if non_empty.any():
            sample_val = df.loc[non_empty, col].iloc[0]
            if isinstance(sample_val, str) and len(sample_val) > 10:
                print(f"\n{col}:")
                print(f"  Non-empty values: {non_empty.sum()}")
                print(f"  Sample values:")
                for idx, val in enumerate(df.loc[non_empty, col].head(3)):
                    snippet = val[:80] + ("…" if len(val) > 80 else "")
                    print(f"    {idx+1}. {snippet}")

# ── 5. Dedicated check for a plain “Description” column ──────────────────────────
if "Description" in df.columns:
    print("\n\nDESCRIPTION COLUMN FOUND!")
    desc_non_empty = df["Description"].notna().sum()
    print(f"  Non-empty values: {desc_non_empty}")
    for i, desc in enumerate(df["Description"].dropna().head(5)):
        snippet = desc[:100] + ("…" if len(desc) > 100 else "")
        print(f"    {i+1}. {snippet}")

# ── 6. Peek into any “Extras” JSON-style column ──────────────────────────────────
if "Extras" in df.columns:
    print("\n\nEXTRAS COLUMN FOUND!")
    extras_non_empty = df["Extras"].notna().sum()
    print(f"  Non-empty values: {extras_non_empty}")
    if extras_non_empty:
        sample_extra = df["Extras"].dropna().iloc[0]
        print(f"  Sample (first 200 chars): {str(sample_extra)[:200]}…")
