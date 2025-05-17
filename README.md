# BALANCE-pyexcel

[![Python CI](https://github.com/your-github-org-or-username/BALANCE-pyexcel/actions/workflows/ci.yml/badge.svg)](https://github.com/your-github-org-or-username/BALANCE-pyexcel/actions/workflows/ci.yml)

**An Excel-based shared expense tracker powered by Python. Uses a configurable YAML registry to automatically ingest, normalize, and owner-tag diverse bank/card CSV formats.**

## Overview

This project helps couples manage shared finances within a familiar Excel environment. Python running *inside* Excel, orchestrated via specific cells, handles the heavy lifting.

Its key feature is a schema-driven ingestion engine: using rules defined in `rules/schema_registry.yml`, it can automatically process different CSV layouts from various financial institutions, map columns, correct amount signs, and assign ownership based on folder structure. This normalized data is then presented in Excel for review, classification (shared/personal), and balance calculation.

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
    *   To process your CSVs and update the Parquet file (and optionally Excel, if not using `--dry-run`), run the following command from the project root directory (`BALANCE-pyexcel`):
        ```bash
        poetry run balance refresh "C:\MyCSVs" "C:\Path\To\MyWorkbook.xlsm"
        ```
        (Replace `"C:\MyCSVs"` with the path to your CSV inbox folder and `"C:\Path\To\MyWorkbook.xlsm"` with the path to your Excel workbook).
    *   This command will:
        *   Read CSVs from the specified inbox.
        *   Process them according to `rules/schema_registry.yml`.
        *   Create/update `balance_final.parquet` in the same directory as your workbook.
        *   If not a `--dry-run`, it will also attempt to update the 'Transactions' and 'Queue_Review' sheets in the Excel workbook.
    *   You can use various options like `--dry-run`, `--no-sync`, `--log <logfile>`, `--verbose`, `--exclude <pattern>`, `--only <pattern>`, etc. Run `poetry run balance refresh --help` for all options.
    *   The primary data output is `balance_final.parquet`, located alongside your Excel workbook.

### Using the Standalone Executable (Alternative)

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
    pyinstaller --onefile --name balance-pyexcel src/balance_pipeline/cli.py --add-data "rules/schema_registry.yml;rules"

    # On macOS/Linux (note the colon ':' in --add-data)
    # pyinstaller --onefile --name balance-pyexcel src/balance_pipeline/cli.py --add-data "rules/schema_registry.yml:rules"
    ```
4.  **Find the Executable:** PyInstaller will create a `dist` folder. Inside `dist`, you'll find `balance-pyexcel.exe`.
5.  **Run the Executable:** You can now run the pipeline from any terminal by providing the path to the executable, followed by the inbox path and workbook path:
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

## Project Structure

```
BALANCE-pyexcel/          (Repository Root)
│
├── .git/                 # Git internal data
├── .gitattributes        # Tells Git how to treat certain files (e.g., .xlsm)
├── .gitignore            # Files ignored by Git
├── architecture.md       # Architecture overview and diagrams
├── poetry.lock           # Exact dependency versions locked by Poetry
├── pyproject.toml        # Python project config (dependencies, metadata - managed by Poetry)
├── README.md             # This file
├── rules/                # Configuration rules for data processing
│   ├── schema_registry.yml # **IMPORTANT**: Defines how to parse different CSV formats
│   └── .gitkeep
├── sample_data_multi/    # Anonymized/fake sample CSV files for testing (tracked by Git)
│   ├── jordyn/           # Sample CSVs belonging to Jordyn
│   │   └── .gitkeep
│   └── ryan/             # Sample CSVs belonging to Ryan
│       └── .gitkeep
├── src/                  # Python source code directory
│   └── balance_pipeline/ # The core Python package
│       ├── __init__.py   # Makes it a package; contains main etl_main() entry point
│       ├── config.py     # Loads configuration (e.g., from .env - primarily for standalone use)
│       ├── ingest.py     # **Schema-aware** CSV loading, mapping, sign fixing, owner tagging
│       ├── normalize.py  # Description cleaning, TxnID generation, final column structuring
│       ├── utils.py      # Shared helper functions (text cleaning, hashing)
│       ├── classify.py   # (Future) Rule-based shared/personal classification
│       └── calculate.py  # (Future) Balance calculation logic
├── tests/                # Python unit tests directory
│   ├── __init__.py       # Makes tests discoverable as a package
│   ├── test_cross_schema.py # Tests ingestion across multiple schemas
│   ├── test_ingest.py    # (Likely remove/merge into cross_schema) Older test stub
│   └── test_normalize.py # Tests for normalization logic
└── workbook/             # Contains the main Excel file
    └── BALANCE-pyexcel.xlsm
```

## Contributing

(Add guidelines later if applicable)

* Run linters/formatters: `poetry run black . && poetry run ruff check . --fix`
* Run tests: `poetry run pytest`

## License

Personal use only.

## Version

0.1.x - Schema-Aware Ingestion Setup
