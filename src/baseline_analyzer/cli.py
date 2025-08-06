import argparse
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from baseline_analyzer.baseline_math import build_baseline
from rich.console import Console

console = Console()


def _load(globs: list[str]) -> pd.DataFrame:
    """Load all CSVs matching the supplied glob patterns and concatenate."""
    frames = [pd.read_csv(p) for g in globs for p in Path(".").glob(g)]
    if not frames:
        raise FileNotFoundError(globs)
    return pd.concat(frames, ignore_index=True)


def main() -> None:
    """Command-line entry-point for the BALANCE baseline analyzer."""
    ap = argparse.ArgumentParser(description="BALANCE baseline analyzer CLI")
    ap.add_argument("expense_csv", nargs="+", help="Glob(s) for expense CSV(s)")
    ap.add_argument("ledger_csv", nargs="+", help="Glob(s) for ledger CSV(s)")
    ap.add_argument(
        "--export-audit",
        metavar="FILE.parquet",
        help="Optional Parquet file to write the full audit dataframe",
    )
    args = ap.parse_args()

    summary, audit = build_baseline(_load(args.expense_csv), _load(args.ledger_csv))

    console.print(summary.to_markdown(index=False))

    if args.export_audit:
        pq.write_table(pa.Table.from_pandas(audit), args.export_audit)
        console.print(f"[green]✓[/green] Audit saved → {args.export_audit}")
