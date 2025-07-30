```
###############################################################################
# BALANCE-pyexcel – README
#
# Description : End‑to‑end guide for installing, configuring, and contributing
#               to BALANCE‑pyexcel – an Excel‑fronted ETL pipeline that turns
#               messy CSV/PDF bank data into a normalised Parquet ledger.
# Key Concepts: - UnifiedPipeline architecture (v2)
#               - Poetry‑based dependency management & strict CI gates
#               - Environment‑variable driven configuration
#               - Debug runner & dev‑experience helpers
# Public API  : *Documentation file – no executable API*
# -----------------------------------------------------------------------------
# Change Log
# 2025‑06‑08  OpenAI o3       docs       Added ASCII header, env‑var section,
#                                        re‑organised content & ToC.
###############################################################################
```

# BALANCE‑pyexcel

[![Python CI](https://github.com/your-github-org-or-username/BALANCE-pyexcel/actions/workflows/ci.yml/badge.svg)](https://github.com/your-github-org-or-username/BALANCE-pyexcel/actions/workflows/ci.yml)

**An Excel‑based shared‑expense tracker powered by Python, with schema‑driven CSV ingestion and a unified ETL pipeline.**

---

## Table of Contents

1. [Overview](#overview)
2. [Unified Pipeline Architecture (v2)](#unified-pipeline-architecture-v2)
3. [Features](#features)
4. [Environment Variables](#environment-variables)
5. [Quick Start](#quick-start)
6. [Running the Pipeline](#running-the-pipeline)
7. [Development & Debugging Tools](#development--debugging-tools)
8. [Standalone Executable](#standalone-executable)
9. [Advanced Analysis with DuckDB](#advanced-analysis-with-duckdb)
10. [Usage Workflow](#usage-workflow)
11. [Project Structure](#project-structure)
12. [Migration Guide (pre‑v2 → v2)](#migration-guide-pre-v2--v2)
13. [Troubleshooting](#troubleshooting)
14. [Contributing](#contributing)
15. [License & Version](#license--version)

---

## Overview

BALANCE‑pyexcel lets any two parties manage shared finances in a familiar Excel environment. Python (running *inside* Excel or headless via CLI) ingests diverse bank/card CSV formats, normalises them, and produces a clean transaction ledger for classification and balance calculation.

> **v2 Notice** – From **v2.0.0** onward, all data processing flows through the **UnifiedPipeline**. Legacy CLI calls are now thin wrappers around the new engine.

---

## Unified Pipeline Architecture (v2)

| Module           | Path                                  | Purpose                                                     |
| ---------------- | ------------------------------------- | ----------------------------------------------------------- |
| **Engine**       | `src/balance_pipeline/pipeline_v2.py` | `UnifiedPipeline` orchestrates ingest → transform → output. |
| **Config**       | `src/balance_pipeline/config_v2.py`   | `PipelineConfig` dataclass + env‑var overrides.             |
| **Outputs**      | `src/balance_pipeline/outputs.py`     | Parquet / Excel / future adapters.                          |
| **CLI (new)**    | `src/balance_pipeline/main.py`        | `balance-pipe process …` command.                           |
| **CLI (legacy)** | `src/balance_pipeline/cli.py`         | `balance refresh` → forwards into v2.                       |

Strict vs flexible schema modes, deduplication, and owner‑tagging all live here. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for a full diagram.

---

## Features

* **Schema‑Driven CSV Ingestion** via `rules/schema_registry.yml`.
* **Automatic Owner Tagging** (folder‑name → `Owner` column).
* **Data Normalisation & Sign Correction**.
* **Stable `TxnID` Generation** (SHA‑256).
* **Excel Review Queue** based on `FILTER`.
* **Planned** automatic shared/personal classification & balance engine.

---

## Environment Variables

These vars are *optional* but recommended for flexibility:

| Var                        | Default     | Purpose                                               |
| -------------------------- | ----------- | ----------------------------------------------------- |
| `BALANCE_CSV_INBOX`        | `csv_inbox` | Root folder containing owner sub‑dirs & CSVs.         |
| `BALANCE_OUTPUT_DIR`       | `output`    | Where Parquet/Excel outputs are written.              |
| `BALANCE_SCHEMA_MODE`      | `flexible`  | `strict` enforces all 25 canonical columns.           |
| `BALANCE_LOG_LEVEL`        | `INFO`      | Set `DEBUG` for verbose tracing.                      |
| `BALANCE_ENABLE_PROFILING` | `false`     | `true` wraps ETL in `cProfile`; used with `snakeviz`. |
| `BALANCE_MAX_ROWS`         | `0`         | Non‑zero limits rows (handy for smoke‑tests).         |

Create a `.env` or set them in Codespaces → *Environment variables* panel.

---

## Quick Start

```bash
# 1 Clone & enter
$ git clone <repo_url>
$ cd BALANCE-pyexcel

# 2 Install deps (Codex container has Poetry pre‑installed)
$ poetry install --no-root --with dev

# 3 Create external CSV inbox
$ mkdir -p csv_inbox/Ryan csv_inbox/Jordyn

# 4 Run pipeline once
$ poetry run balance-pipe process "csv_inbox/**.csv" --output-type powerbi
```

On success you’ll see `output/unified_pipeline/<timestamp>.parquet`.

---

## Running the Pipeline

### New CLI

```bash
poetry run balance-pipe process "csv_inbox/**.csv" \
    --schema-mode strict \
    --output-type excel \
    --output-path output/latest.xlsx
```

### Legacy CLI (deprecated)

`poetry run balance refresh csv_inbox workbook/BALANCE-pyexcel.xlsm`

---

## Development & Debugging Tools

* **CI gates**: `ruff check`, `ruff format`, `mypy --strict`, `pytest -q`, `snakeviz --version`.
* **Debug runner**: `tools/debug_runner.py` lets you step through stubbed data. Provide `core_calculations.py` and `data_loader_temp.py` in `src/balance_pipeline/`.

---

## Standalone Executable

```bash
pyinstaller --onefile --name balance-pipe \
  src/balance_pipeline/main.py --add-data "rules;rules"
```

Grab `dist/balance-pipe.exe` and run like any CLI example.

---

## Advanced Analysis with DuckDB

```sql
-- simple query
SELECT COUNT(*)
FROM read_parquet('output/unified_pipeline/latest.parquet');
```

Full ODBC instructions are in the old README’s DuckDB section.

---

## Usage Workflow

1. Drop new CSVs into the correct owner folder.
2. Run `balance-pipe …` or refresh in Excel.
3. Classify shared vs personal on **Queue\_Review**.
4. (Planned) sync → calculate balances.

---

## Project Structure

<details><summary>Expand tree</summary>

```text
BALANCE-pyexcel/
├── rules/ …                # schema registry & merchant lookup
├── src/balance_pipeline/   # UnifiedPipeline + helpers
│   ├── pipeline_v2.py
│   ├── main.py (balance‑pipe)
│   └── …
├── tools/debug_runner.py
├── workbook/BALANCE-pyexcel.xlsm
└── tests/ …
```

</details>

---

## Migration Guide (pre‑v2 → v2)

Switch your scripts from `balance refresh` → `balance-pipe`. Excel `etl_main()` already forwards to v2.

---

## Troubleshooting

* **Schema not found** → check `rules/schema_registry.yml` patterns.
* **Excel PY error** → confirm `CsvInboxPath` in workbook.
* **snakeviz check fails** → ensure `python3-tk` & PATH fix (see setup script in AGENTS.MD).

---

## Contributing

Run all CI gates before PR:

```bash
poetry run ruff check . && poetry run ruff format .
poetry run mypy src/ --strict
poetry run pytest -q
```

Follow Conventional Commits.

---

## License & Version

Personal use only · Current version **0.1.x – Schema‑Aware Ingestion Setup**
