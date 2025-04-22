# BALANCE-pyexcel

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

## Usage Workflow

1.  **Download & Place CSVs:** Download new transaction CSV files from your banks/cards. Place each file into the correct owner's subfolder within your designated external CSV Inbox folder (e.g., put Jordyn's Chase CSV into `C:\MyCSVs\Jordyn\`).
2.  **Open Workbook:** Open `workbook/BALANCE-pyexcel.xlsm` in Excel.
3.  **Refresh Python ETL:** Trigger the main Python calculation. This is typically done by:
    * Finding the cell containing the `=PY(etl_main(...))` formula (likely on a sheet like `PythonRuntime`).
    * Recalculating that cell (e.g., selecting it, pressing F2, then Enter) or using Excel's `Data > Refresh All` (may require specific setup).
4.  **Check Results:** View the processed, normalized, and owner-tagged data on the `Transactions` sheet.
5.  **Review Queue:** Go to the `Queue_Review` sheet. Any transactions where `SharedFlag` is `?` (meaning not automatically classified yet) will appear here based on the `FILTER` formula.
6.  **Classify:** Manually enter `Y` (Shared), `N` (Personal), or `S` (Split) in the `Set Shared?` column on the `Queue_Review` sheet. Add split percentages if needed.
7.  **(Future)** Sync Decisions: Trigger a (currently unimplemented) Python cell/button to read the decisions from `Queue_Review` and update the `SharedFlag`/`SplitPercent` on the main `Transactions` sheet.
8.  **(Future)** View Dashboard: Check calculated balances and visualizations on the `Dashboard` sheet.

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