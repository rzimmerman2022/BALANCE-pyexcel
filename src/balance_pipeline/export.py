"""
Thin wrappers for exporting pipeline outputs.
Currently: Parquet via DuckDB (works on Py 3.13 without PyArrow wheels).
"""

from __future__ import annotations

import logging
import pathlib

import duckdb
import pandas as pd

log = logging.getLogger(__name__)


def write_parquet_duckdb(df: pd.DataFrame, out_path: pathlib.Path) -> None:
    """
    Write *df* to *out_path* in Parquet format using DuckDB’s COPY.
    Safe on Py 3.13 because duckdb wheels include Arrow libraries.
    """
    try:
        con = duckdb.connect()
        con.register("txns", df)
        con.execute(f"COPY txns TO '{out_path}' (FORMAT parquet);")
        con.close()
        log.info("✅ Parquet written via DuckDB → %s", out_path.name)
    except Exception as exc:
        log.warning("⚠️  DuckDB Parquet export skipped (%s)", exc)
