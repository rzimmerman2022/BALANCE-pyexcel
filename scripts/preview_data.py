#!/usr/bin/env python
"""
Quick-look preview of each CSV in ./data.
"""

from pathlib import Path
import sys
import pandas as pd

# -------- config --------
NROWS = int(sys.argv[1]) if len(sys.argv) > 1 else 20
DATA_DIR = Path(__file__).resolve().parent / "data"
OUT_DIR  = DATA_DIR / "_samples"
OUT_DIR.mkdir(exist_ok=True)

# -------- helpers --------
def preview_csv(csv_path: Path, nrows: int = 20) -> None:
    df = pd.read_csv(csv_path, nrows=nrows)
    #
    print(f"\n=== {csv_path.name} ===")
    print(f" • shape (preview): {df.shape}")
    print(f" • columns        : {list(df.columns)}")
    print(df.head(min(5, nrows)).to_markdown(index=False))  # quick peek
    #
    sample_path = OUT_DIR / csv_path.name
    df.to_csv(sample_path, index=False)
    print(f" → wrote preview to {sample_path.relative_to(Path.cwd())}")

# -------- main --------
if not DATA_DIR.exists():
    sys.exit(f"[!] Data directory not found: {DATA_DIR}")

csv_files = sorted(DATA_DIR.glob("*.csv"))
if not csv_files:
    sys.exit(f"[!] No CSVs in {DATA_DIR}")

print(f"Found {len(csv_files)} CSV file(s) in {DATA_DIR} (showing first {NROWS} rows each)")
for csv in csv_files:
    preview_csv(csv, NROWS)
