# BALANCE-pyexcel

[![Python CI](https://github.com/your-github-org-or-username/BALANCE-pyexcel/actions/workflows/ci.yml/badge.svg)](https://github.com/your-github-org-or-username/BALANCE-pyexcel/actions/workflows/ci.yml)

**An Excel-based shared expense tracker powered by Python. Uses a configurable YAML registry to automatically ingest, normalize, and owner-tag diverse bank/card CSV formats.**

## Overview

This project helps couples manage shared finances within a familiar Excel environment. Python running *inside* Excel, orchestrated via specific cells, handles the heavy lifting.

Its key feature is a schema-driven ingestion engine: using rules defined in `rules/schema_registry.yml`, it can automatically process different CSV layouts from various financial institutions, map columns, correct amount signs, and assign ownership based on folder structure. This normalized data is then presented in Excel for review, classification (shared/personal), and balance calculation.

**As of version 2.0.0, the backend data processing has been refactored into a Unified Pipeline Architecture. See the "Unified Pipeline Architecture (v2)" section below for details.**

## Unified Pipeline Architecture (v2)

The data processing backend of BALANCE-pyexcel has been significantly refactored to improve maintainability, consistency, and flexibility. This new architecture (v2) introduces a unified pipeline that centralizes data ingestion, transformation, and output.

Key components of the new architecture include:

*   **`UnifiedPipeline` (`src/balance_pipeline/pipeline_v2.py`):** The central engine orchestrating data processing. It wraps the core logic of `csv_consolidator.py` and supports different schema modes ("strict" and "flexible").
*   **Output Adapters (`src/balance_pipeline/outputs.py`):** Modules for formatting and writing processed data to various targets (e.g., Parquet for Power BI, Excel).
*   **Centralized Configuration (`src/balance_pipeline/config_v2.py`):** A `PipelineConfig` dataclass manages all pipeline settings, supporting defaults, environment variables, and CLI overrides.
*   **New Main CLI (`src/balance_pipeline/main.py`):** A new command-line interface, `balance-pipe`, built with Click for user-friendly interaction with the unified pipeline.

This refactoring aims to:
*   Consolidate all data processing through one consistent path.
*   Maintain backward compatibility with existing functionality (legacy CLI and Excel `etl_main` calls are routed through the new pipeline).
*   Separate processing logic from output formatting.
*   Provide clear configuration and entry points.
*   Support both strict (all 25 canonical columns) and flexible (only columns with data) schema modes.

For a detailed explanation of the new architecture, please refer to [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Features

* **Schema-Driven CSV Ingestion:** Parses multiple bank/card CSV formats automatically based on rules defined in `rules/schema_registry.yml`. Easily extensible for new formats by editing the YAML file.
* **Automatic Owner Tagging:** Assigns an 'Owner' (e.g., 'Ryan', 'Jordyn') to transactions based on the subfolder the CSV file is placed in.
* **Data Normalization:** Cleans data (dates, amounts, descriptions), standardizes amount signs (outflows are negative).
* **Unique Transaction ID:** Generates a stable SHA-256 based `TxnID` for each transaction for reliable tracking and updates.
* **Manual Classification Queue:** Presents transactions needing classification (Shared 'Y', Personal 'N', Split 'S') in a dedicated Excel sheet (`Queue_Review`) using an Excel `FILTER` formula.
* **(Planned)** Rule-based Classification: Automatically tag transactions as shared/personal based on merchant rules.
* **(Planned)** Balance Calculation: Automatically calculate the net amount owed based on classified shared expenses.
* **Excel Interface:** Uses standard Excel features for configuration, data display, review queue, and dashboards.
* **Configurable:** Key settings like the CSV input path, user names (in Excel `Config`), and all CSV parsing rules (in YAML) are user-configurable.

## Getting Started

### Prerequisites

* **Microsoft 365:** Subscription that includes Python in Excel (Business/Enterprise recommended, or relevant Personal/Family Insider Channel).
* **Windows:** Recommended OS for the most stable Python in Excel experience.
* **Git:** For cloning/managing the repository ([Download Git](https://git-scm.com/downloads)).
* **Python:** Version 3.11+ installed locally ([Download Python](https://www.python.org/downloads/)). Needed for development tools (Poetry, pytest).
* **Poetry:** For Python package management ([Install Poetry](https://python-poetry.org/docs/#installation)).
* **Ghostscript:** Required by `camelot-py` for PDF processing. Download and install from [ghostscript.com](https://www.ghostscript.com/releases/gsdnld.html) and ensure the executable (`gs` or `gswin64c`/`gswin32c`) is in your system's PATH.

### Installation & Setup

1.  **Clone Repository:** Obtain the project files (e.g., via `git clone <repo_url>`).
2.  **Navigate to Project Root:** Open PowerShell or your terminal in the project's root directory (e.g., `cd C:\BALANCE\BALANCE-pyexcel-repository\BALANCE-pyexcel`).
3.  **Install Dependencies:** Run `poetry install`. This creates a virtual environment and installs required Python packages (`pandas`, `PyYAML`, `python-dotenv`, etc.) based on `pyproject.toml`.
4.  **Configure CSV Input:**
    * **Create External Folders:** Create a main folder *outside* this Git repository to store your actual bank CSVs (e.g., `C:\MyCSVs`). Inside that folder, create subfolders named after each owner (e.g., `C:\MyCSVs\Jordyn`, `C:\MyCSVs\Ryan`). **Do NOT commit real CSVs to Git.**
    * **Set Path in Excel:** Open `workbook/BALANCE-pyexcel.xlsm`. Go to the `Config` sheet. In the cell designated for `CsvInboxPath` (e.g., B1), enter the **full path** to the *parent* CSV folder you created (e.g., `C:\MyCSVs`).
    * **Set User Names:** On the `Config` sheet, enter the names for `User1_Name` and `User2_Name`.
5.  **Configure Parsing Rules:**
    * Open `rules/schema_registry.yml` in VS Code or a text editor.
    * Review the existing schemas. **Crucially, check the `wells_fargo_card` entry** and adjust the `derived_columns` or `column_map` based on how Amount is represented in your *actual* WF files.
    * Add or modify schemas as needed for *all* your different CSV formats, following the comments in the file. Ensure `match_filename` and `header_signature` correctly identify each file type.
6.  **Prepare Sample Data (for Testing):**
    * Create anonymized or fake sample CSV files representing *each* format defined in your YAML.
    * Place these sample files inside the corresponding subfolders within the `sample_data_multi/` directory (e.g., `sample_data_multi/jordyn/chase_sample.csv`, `sample_data_multi/ryan/monarch_sample.csv`). This folder *is* tracked by Git.
7.  **Enable Python in Excel:** Ensure Python is enabled (`File > Options > Formulas > Enable Python`) and trust prompts if necessary when running Python code for the first time.

8.  **Running the ETL Pipeline (Command Line for Development/Testing):**
    *   **Recommended (New Unified Pipeline CLI):**
        The new `balance-pipe` CLI provides a more streamlined interface to the unified pipeline.
        ```bash
        # Example: Process CSVs and output to Parquet (default for Power BI)
        poetry run balance-pipe process "C:\MyCSVs\Ryan\somefile.csv" "C:\MyCSVs\Jordyn\anotherfile.csv" --output-type powerbi --output-path "output\my_transactions.parquet"

        # Example: Process CSVs from a directory and output to Excel, using flexible schema mode
        poetry run balance-pipe process "C:\MyCSVs\*" --schema-mode flexible --output-type excel --output-path "output\my_transactions.xlsx"
        
        # Example: Process all CSVs in a directory recursively and its subdirectories
        poetry run balance-pipe process "C:\MyCSVs\**\*.csv" --output-type powerbi

        # Show current configuration and exit
        poetry run balance-pipe process --explain-config 
        ```
        Run `poetry run balance-pipe process --help` for all available options.
        This new CLI uses the `UnifiedPipeline` and offers more granular control over schema modes and output formats. The output path is also more explicit, defaulting to a subfolder in `output/unified_pipeline/` if not specified.

    *   **Legacy CLI (for backward compatibility):**
        The old `balance refresh` (or `python -m balance_pipeline.cli`) command is still available but is now a compatibility layer over the new pipeline.
        ```bash
        # Legacy command
        poetry run balance refresh "C:\MyCSVs" "C:\Path\To\MyWorkbook.xlsm"
        ```
        **Note:** This legacy CLI will show a deprecation warning. It's recommended to migrate to `balance-pipe`.
        It internally uses the `UnifiedPipeline` with `schema_mode="flexible"` by default for its main ETL path. The primary data output (`balance_final.parquet`) behavior remains similar (output alongside the workbook).

### Using the Standalone Executable (Alternative)

**Note:** The standalone executable build process should ideally be updated to point to the new `src/balance_pipeline/main.py` if you want it to use the `balance-pipe` CLI. The instructions below primarily cover building the legacy CLI.

For users who don't need the full development environment (Poetry, Git), a standalone executable can be built or downloaded. This packages the Python script and its dependencies into a single `.exe` file (on Windows).

**Download Pre-built Executable:**

You can download the latest Windows executable directly from the GitHub Actions build artifacts:

1.  Go to the [latest successful CI run on the main branch](https://github.com/your-github-org-or-username/BALANCE-pyexcel/actions/workflows/ci.yml/runs?query=branch%3Amain+status%3Asuccess).
2.  Click on the latest run listed.
3.  Scroll down to the "Artifacts" section.
4.  Download the `balance-pyexcel-windows-...` artifact (it will be a zip file containing the `.exe`).
5.  Extract the `.exe` file to a location of your choice.

**Build Manually:**

1.  **Install PyInstaller:** If you don't have it, open a terminal/PowerShell and run:
    ```bash
    pip install pyinstaller
    ```
2.  **Navigate to Project Root:** Open your terminal in the `BALANCE-pyexcel` directory (where `pyproject.toml` is located).
3.  **Build the Executable:** Run the following command. This tells PyInstaller to create a single executable file named `balance-pyexcel.exe`, find the main script (`cli.py`), and importantly, include the necessary `schema_registry.yml` file in the package.
    ```bash
    # On Windows (note the semicolon ';' in --add-data)
    # To build the new 'balance-pipe' CLI (recommended):
    # pyinstaller --onefile --name balance-pipe src/balance_pipeline/main.py --add-data "rules;rules"
    # To build the legacy 'balance-pyexcel' CLI:
    pyinstaller --onefile --name balance-pyexcel src/balance_pipeline/cli.py --add-data "rules;rules"

    # On macOS/Linux (note the colon ':' in --add-data)
    # To build the new 'balance-pipe' CLI (recommended):
    # pyinstaller --onefile --name balance-pipe src/balance_pipeline/main.py --add-data "rules:rules"
    # To build the legacy 'balance-pyexcel' CLI:
    # pyinstaller --onefile --name balance-pyexcel src/balance_pipeline/cli.py --add-data "rules:rules"
    ```
    **Important:** The `--add-data "rules;rules"` (or `"rules:rules"`) part is crucial to include the entire `rules` directory (containing `schema_registry.yml`, `merchant_lookup.csv`, and individual schema YAMLs) in the executable.

4.  **Find the Executable:** PyInstaller will create a `dist` folder. Inside `dist`, you'll find `balance-pyexcel.exe` (or `balance-pipe.exe` if you build the new one).
5.  **Run the Executable:** You can now run the pipeline from any terminal:
    ```bash
    # Example from the 'dist' folder
    .\balance-pyexcel.exe "C:\MyCSVs" "C:\Path\To\MyWorkbook.xlsx"

    # Example from elsewhere (using full path to executable)
    C:\path\to\BALANCE-pyexcel\dist\balance-pyexcel.exe "C:\MyCSVs" "C:\Path\To\MyWorkbook.xlsx"
    ```
    *   Remember to replace `"C:\MyCSVs"` and `"C:\Path\To\MyWorkbook.xlsx"` with your actual paths.
    *   You can add other command-line options like `--log`, `--no-sync`, etc., just like with the `poetry run` command.
    *   **Note on `--dry-run`:** If you use the `--dry-run` flag, the output CSV (`<workbook_name>.dry-run.csv`) will be created in the same directory as the specified *workbook*, not in the CSV inbox directory.
    *   **Note on Windows Shells:** When running commands, be mindful of your shell. `cmd.exe` typically uses `&&` to chain commands (e.g., `cd C:\Project && poetry run ...`). PowerShell uses `;` or separate lines (e.g., `cd C:\Project; poetry run ...`).

### Using DuckDB for Analysis (Optional)

After running the pipeline (either via `poetry run balance refresh ...` or the standalone executable), a file named `balance_final.parquet` (the name is configurable via `BALANCE_FINAL_PARQUET_FILENAME` in `.env` or `src/balance_pipeline/config.py`) will be created in the same directory as your Excel workbook. This file contains the complete, processed transaction data in the efficient Parquet format.

You can use DuckDB to query this data directly for more advanced analysis or connect it to tools like Power Query:

1.  **Install DuckDB CLI:** Follow instructions at [duckdb.org/docs/installation](https://duckdb.org/docs/installation/).
2.  **Query the Parquet File:** Open the DuckDB CLI and run SQL queries directly against the Parquet file:
    ```sql
    -- Example: Load and view the first 10 rows
    SELECT * FROM read_parquet('C:/Path/To/Your/Workbook/Directory/balance_final.parquet') LIMIT 10;

    -- Example: Create a persistent DuckDB database file and import the data
    CREATE DATABASE 'my_finance_db.duckdb';
    USE 'my_finance_db.duckdb';
    CREATE TABLE transactions AS SELECT * FROM read_parquet('C:/Path/To/Your/Workbook/Directory/balance_final.parquet');
    SELECT COUNT(*) FROM transactions;
    ```
    (Replace the path with the actual location of your `balance_final.parquet` file).
3.  **Connect via Power Query/ODBC:**
    *   **Install Driver:** First, download and install the **DuckDB ODBC driver** from [duckdb.org/docs/api/odbc](https://duckdb.org/docs/api/odbc). The MSI installer is recommended for Windows.
    *   **Excel Connection:**
        *   You can use the sample `.odc` file provided in the `samples/` directory (`Connect_DuckDB_Parquet.odc`). You may need to edit it to point to `balance_final.parquet`. Place it next to your `balance_final.parquet` file and try opening it via `Data > Existing Connections` in Excel.
        *   Alternatively, configure an ODBC Data Source (DSN) using the "ODBC Data Sources (x64)" administrator tool in Windows. Point the DSN to your `.parquet` file (e.g., `Database=C:\Path\To\balance_final.parquet`). Then, in Excel, use `Data > Get Data > From Other Sources > From ODBC` and select your DSN.
    *   **Power BI Connection:**
        *   Use the `ODBC` connector (`Get data > ODBC`).
        *   Select `None` for the Data Source Name (DSN) if you haven't configured one.
        *   Expand "Advanced options". In the "Connection string" field, enter the following (replace the path):
            ```
            Driver={DuckDB Driver};Database=C:\Path\To\Your\Workbook\Directory\balance_final.parquet;
            ```
        *   Click OK. You should be able to connect and see the data. You can leave the SQL statement blank initially to browse.

## Usage Workflow

1.  **(Optional) Process PDFs to CSVs:** If you have bank statements as PDFs (e.g., for Jordyn):
    *   Create a temporary folder to hold the PDFs (e.g., `C:\PDF_Inbox`).
    *   Create a temporary folder for the output CSVs (e.g., `C:\PDF_Output`).
    *   Open your terminal in the `BALANCE-pyexcel` project directory.
    *   Run the PDF processing script:
        ```bash
        poetry run python scripts/process_pdfs.py "C:\PDF_Inbox" "C:\PDF_Output"
        ```
        (Replace paths with your actual temporary folders).
    *   Move the generated CSV files (e.g., `jordyn_pdf_*.csv`) from `C:\PDF_Output` into the *main* CSV inbox folder under the correct owner (e.g., `C:\MyCSVs\Jordyn\`).
2.  **Download & Place CSVs:** Download any *direct* transaction CSV files from your banks/cards. Place each file into the correct owner's subfolder within your designated external CSV Inbox folder (e.g., put Ryan's Monarch CSV into `C:\MyCSVs\Ryan\`).
3.  **(Optional) Add Merchant Rules:** If you know certain transaction descriptions should always map to a specific merchant name, you can add rules via the command line:
    ```bash
    poetry run balance-merchant add "<regex_pattern_for_description>" "<Canonical Merchant Name>"
    # Example: poetry run balance-merchant add "^AMAZON MKTP US\\*AB123" "Amazon Marketplace"
    ```
    This appends the rule to `rules/merchant_lookup.csv`.
4.  **Open Workbook:** Open `workbook/BALANCE-pyexcel.xlsm` in Excel.
5.  **Refresh Python ETL:** Trigger the main Python calculation. This is typically done by:
    * Finding the cell containing the `=PY(etl_main(...))` formula (likely on a sheet like `PythonRuntime`).
    * Recalculating that cell (e.g., selecting it, pressing F2, then Enter) or using Excel's `Data > Refresh All` (may require specific setup).
6.  **Check Results:** View the processed, normalized, and owner-tagged data on the `Transactions` sheet.
7.  **Review Queue:** Go to the `Queue_Review` sheet. Any transactions where `SharedFlag` is `?` (meaning not automatically classified yet) will appear here based on the `FILTER` formula.
8.  **Classify:** Manually enter `Y` (Shared), `N` (Personal), or `S` (Split) in the `Set Shared?` column on the `Queue_Review` sheet. Add split percentages if needed.
9.  **(Future)** Sync Decisions: Trigger a (currently unimplemented) Python cell/button to read the decisions from `Queue_Review` and update the `SharedFlag`/`SplitPercent` on the main `Transactions` sheet.
10. **(Future)** View Dashboard: Check calculated balances and visualizations on the `Dashboard` sheet.

### Analyzer Utility

For detailed reconciliation outside of Excel, run `analyzer.py` directly. The
script accepts CSV paths via command-line options:

```bash
poetry run python analyzer.py \
  --expense data/Expense_History_20250527.csv \
  --ledger data/Transaction_Ledger_20250527.csv \
  --rent data/Rent_Allocation_20250527.csv \
  --rent-hist data/Rent_History_20250527.csv
```

The `--ledger` option is required when you want to merge a running balance CSV
with your expense history.

## Project Structure

```
BALANCE-pyexcel/              (Repository Root)
│
├── .git/                     # Git internal data
├── .gitattributes            # Tells Git how to treat certain files (e.g., .xlsm)
├── .gitignore                # Files ignored by Git
├── docs/                     # Documentation files
│   └── ARCHITECTURE.md       # Detailed explanation of the v2 pipeline architecture
├── poetry.lock               # Exact dependency versions locked by Poetry
├── pyproject.toml            # Python project config (dependencies, metadata - managed by Poetry)
├── README.md                 # This file
├── rules/                    # Configuration rules for data processing
│   ├── schema_registry.yml   # **IMPORTANT**: Defines how to parse different CSV formats
│   ├── merchant_lookup.csv   # Rules for cleaning merchant names
│   └── *.yaml                # Individual schema definition files (referenced by schema_registry.yml)
├── sample_data_multi/        # Anonymized/fake sample CSV files for testing (tracked by Git)
│   ├── jordyn/               # Sample CSVs belonging to Jordyn
│   └── ryan/                 # Sample CSVs belonging to Ryan
├── scripts/                  # Utility and validation scripts
│   └── validate_migration.py # Script to compare legacy and new pipeline outputs
├── src/                      # Python source code directory
│   └── balance_pipeline/     # The core Python package
│       ├── __init__.py       # Makes it a package; legacy etl_main() for Excel (uses UnifiedPipeline)
│       ├── cli.py            # Legacy CLI (balance refresh), now uses UnifiedPipeline
│       ├── config.py         # Legacy configuration (still used for some constants like PARQUET_FILENAME by legacy CLI)
│       ├── csv_consolidator.py # Core CSV processing and transformation logic (used by UnifiedPipeline)
│       ├── ingest.py         # Legacy ingestion logic (no longer primary path)
│       ├── normalize.py      # Legacy normalization logic (no longer primary path)
│       ├── errors.py         # Custom error classes
│       ├── constants.py      # Project-wide constants (e.g., master schema columns)
│       ├── schema_registry.py # Handles loading and matching schemas from YAML files
│       ├── schema_types.py   # Type definitions related to schemas
│       ├── utils.py          # Shared helper functions
│       ├── merchant.py       # Merchant cleaning specific logic (if separated)
│       │
│       ├── main.py           # New primary CLI entry point (balance-pipe)
│       ├── pipeline_v2.py    # UnifiedPipeline class - new core processing engine
│       ├── config_v2.py      # New centralized PipelineConfig dataclass
│       └── outputs.py        # Output adapters (PowerBIOutput, ExcelOutput)
│
├── tests/                    # Python unit tests directory
│   ├── __init__.py           # Makes tests discoverable as a package
│   ├── test_unified_pipeline.py # Tests for the new UnifiedPipeline and components
│   ├── test_csv_consolidator.py # Existing tests for csv_consolidator
│   └── ...                   # Other existing test files
└── workbook/                 # Contains the main Excel file
    └── BALANCE-pyexcel.xlsm
```

## Migration Guide (from pre-v2)

If you were previously using this project, here's how to adapt to the v2 architecture:

*   **Primary CLI Change:**
    *   The old command `poetry run balance refresh ...` (or `python -m balance_pipeline.cli ...`) is now considered legacy. While it still works (it routes through the new pipeline with default flexible schema mode), it will show a deprecation warning.
    *   **Switch to the new `balance-pipe` CLI:**
        ```bash
        poetry run balance-pipe process [YOUR_FILES_OR_PATTERNS] [OPTIONS]
        ```
        Example: `poetry run balance-pipe process "C:\MyCSVs\**\*.csv" --output-type powerbi`
        Refer to the "Running the ETL Pipeline" section for more examples or run `poetry run balance-pipe process --help`.
*   **Excel Integration (`=PY(etl_main(...))`):**
    *   This should continue to work as before. The `etl_main` function in `src/balance_pipeline/__init__.py` now uses the `UnifiedPipeline` internally (with `schema_mode="flexible"`).
*   **Configuration:**
    *   The new pipeline uses `src/balance_pipeline/config_v2.py` for its primary configuration. Default paths for `schema_registry.yml` and `merchant_lookup.csv` are defined there and point to the `rules/` directory.
    *   Environment variables (e.g., `BALANCE_SCHEMA_MODE`, `BALANCE_SCHEMA_REGISTRY_PATH`) can be used to override these defaults for the new pipeline.
    *   The old `src/balance_pipeline/config.py` is still partially used by the legacy CLI for some specific constants like the Parquet output filename when used with the legacy CLI.
*   **Output Files:**
    *   The new `balance-pipe` CLI provides more explicit control over output paths and types. If no `--output-path` is specified, it defaults to creating timestamped files in `output/unified_pipeline/`.
    *   The legacy `balance refresh` CLI continues to place `balance_final.parquet` alongside the workbook.
*   **Schema Mode:** The new pipeline explicitly supports `"strict"` and `"flexible"` schema modes. The legacy interfaces default to a behavior similar to "flexible". Use the `--schema-mode` option with `balance-pipe` for explicit control.

## Troubleshooting

*   **"Schema not found" errors:**
    *   Ensure your `rules/schema_registry.yml` is correctly configured and points to valid individual schema YAML files.
    *   Verify that `filename_patterns` or `header_patterns` in your schema definitions accurately match your input CSV files.
    *   Check that the `balance-pipe process --schema-registry <path>` (if used) points to the correct registry file.
*   **Incorrect data mapping or parsing:**
    *   Review the `column_map`, `date_format`, `sign_rule`, and `derived_columns` in the specific schema YAML file for the problematic CSV type.
    *   Use the `--log-level DEBUG` option with `balance-pipe process` to get detailed logs, which can show how schemas are matched and transformations are applied.
*   **Legacy CLI (`balance refresh`) issues:**
    *   Remember it's deprecated. Try using the new `balance-pipe process` command.
    *   If you must use the legacy CLI, ensure that `src/balance_pipeline/config.py` still has relevant default paths if they are not overridden by `config_v2.py` in the execution flow.
*   **Executable (`.exe`) problems:**
    *   Ensure you built the executable with the correct `--add-data "rules;rules"` (or `rules:rules`) flag to bundle the entire `rules` directory.
    *   Run the executable from a terminal to see any error messages.
*   **Excel `=PY` errors:**
    *   Check the Python runtime pane in Excel for error messages.
    *   Ensure the `CsvInboxPath` in the Excel `Config` sheet is correct and accessible.
    *   The `etl_main` function called by Excel now logs to the standard Python logging system. You might need to configure a file handler (see `src/balance_pipeline/cli.py setup_logging` for an example, though Excel's Python environment might have its own logging quirks) or check where Python in Excel outputs logs.
*   **Differences between old and new pipeline outputs:**
    *   Use the `scripts/validate_migration.py` script. It processes data through both pipelines and can help pinpoint discrepancies.
    *   Pay attention to the `schema_mode`. The legacy pipeline behaved more like the "flexible" mode. If comparing, ensure you run the new pipeline in "flexible" mode for a closer match.

For more detailed architectural information, see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Contributing

(Add guidelines later if applicable)

* Run linters/formatters: `poetry run black . && poetry run ruff check . --fix`
* Run tests: `poetry run pytest`

### Standalone Analyzer

The repository also ships with a legacy `analyzer.py` script for ad-hoc
experiments. It accepts CSV files for expenses, rent, and now an optional
transaction ledger:

```bash
poetry run python analyzer.py \
  --expense Expense_History_20250527.csv \
  --ledger Transaction_Ledger_20250527.csv \
  --rent Rent_Allocation_20250527.csv \
  --rent-hist Rent_History_20250527.csv
```

Providing `--ledger` merges ledger rows with the expense history to build the
master ledger and improves balance accuracy.

## License

Personal use only.

## Version

0.1.x - Schema-Aware Ingestion Setup
