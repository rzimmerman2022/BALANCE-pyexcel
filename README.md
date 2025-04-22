# BALANCE-pyexcel

**An Excel-based shared expense tracker powered by Python. Imports bank CSVs, cleans transaction data, helps classify costs, and calculates who owes whom for personal budgeting.**

## Overview

This project helps couples manage shared finances within a familiar Excel environment. Python running *inside* Excel handles the heavy lifting of importing transaction CSVs from multiple banks, cleaning and standardizing the data, allowing users to classify expenses as shared or personal, and automatically calculating the net balance owed between partners.

## Features (Phase 1)

* **CSV Import:** Ingests `.csv` transaction files from a designated folder.
* **Data Normalization:** Cleans data (dates, amounts, descriptions), standardizes merchant names using configurable rules.
* **Unique Transaction ID:** Generates a stable ID for each transaction for reliable tracking.
* **Manual Classification Queue:** Presents transactions needing classification (Shared 'Y', Personal 'N', Split 'S') in a dedicated Excel sheet.
* **Balance Calculation:** Automatically calculates the net amount owed based on classified shared expenses and split percentages.
* **Basic Dashboard:** Displays the current balance and allows for embedding standard Excel charts.
* **Configurable:** User names, CSV input path, and processing rules managed within Excel sheets.

## Getting Started

### Prerequisites

* **Microsoft 365:** Subscription that includes Python in Excel (Business/Enterprise recommended, or relevant Personal/Family Insider Channel).
* **Windows:** Recommended OS for the most stable Python in Excel experience. (Can work on Mac via VM or potentially newer Mac preview builds).
* **Git:** For cloning the repository ([Download Git](https://git-scm.com/downloads)).
* **Python:** Version 3.11+ installed locally ([Download Python](https://www.python.org/downloads/)). Needed for development tools.
* **Poetry:** For Python package management ([Install Poetry](https://python-poetry.org/docs/#installation)).

### Installation & Setup

1.  **Clone the Repository:**
    ```bash
    # Example if cloning later:
    # git clone <your-repository-url>
    # cd BALANCE-pyexcel
    ```

2.  **Install Python Dependencies:** (Run from the project root directory)
    ```bash
    poetry install
    ```
    *(This creates a virtual environment and installs packages like Pandas based on `pyproject.toml` and `poetry.lock`)*

3.  **Configure Environment (Optional but Recommended):**
    * Copy `.env.example` to `.env` (if provided).
    * Edit `.env` to include local paths if needed (ensure `.env` is in `.gitignore`).

4.  **Open the Workbook:**
    * Open `BALANCE-pyexcel.xlsx` in Microsoft Excel.
    * **Enable Python:** If prompted, or ensure it's enabled via `File > Options > Formulas > Enable Python`.
    * **Enable Macros/Content:** If any security warnings appear related to external data or scripts, enable content cautiously (understand the source).

5.  **Initial Configuration (in Excel):**
    * Go to the `Config` sheet.
    * Enter the **full path** to the folder where you will drop your CSV files into the `CsvInboxPath` cell/field.
    * Enter the names for User 1 and User 2 in the respective fields.
    * Review/populate initial rules in `Rules_Merchants` and `Rules_Shared` sheets.

## Usage Workflow

1.  **Add Data:** Place new `.csv` transaction files into the folder specified by `CsvInboxPath`.
2.  **Refresh ETL:** Trigger the main Python ETL calculation in Excel. This might be:
    * Selecting the main Python calculation cell and pressing Ctrl+Enter.
    * Using Excel's `Data > Refresh All` (if connections are set up appropriately - might require advanced setup).
3.  **Update Transactions:** Manually copy the results from the Python spill range to the `Transactions` sheet (initial setup).
4.  **Review Queue:** Go to the `Queue_Review` sheet. Transactions needing classification (`SharedFlag = '?'`) will appear.
5.  **Classify:** Enter `Y`, `N`, or `S` (and split % if `S`) for each item in the queue.
6.  **Sync Decisions:** Trigger the "Sync Decisions" Python cell. Manually update the `Transactions` sheet with the synced results (initial setup).
7.  **View Dashboard:** Go to the `Dashboard` sheet. The balance calculation will update automatically (or via refresh). View charts and summaries.

## Project Structure

```
BALANCE-pyexcel/  (Or BALANCE-pyexcel-repository/BALANCE-pyexcel/ currently)
│
├── .git/                 # Git internal data
├── .gitignore            # Files ignored by Git
├── architecture.md       # Architecture overview
├── BALANCE-pyexcel.xlsx  # The main Excel workbook (UI, Config, Output)
├── poetry.lock           # Exact dependency versions
├── pyproject.toml        # Python project config (deps, metadata)
├── README.md             # This file
├── rules/                # (Optional) Folder for rule files if not in Excel
│   └── .gitkeep
├── sample_data/          # Anonymized sample CSV files for testing
│   └── .gitkeep
├── src/                  # Python source code directory
│   └── balance_pipeline/ # The core Python package
│       ├── __init__.py
│       ├── config.py     # Configuration loading
│       ├── ingest.py     # CSV ingestion logic
│       ├── normalize.py  # Data cleaning and normalization
│       ├── classify.py   # Shared/Personal classification (Future)
│       ├── calculate.py  # Balance calculation logic (Future)
│       └── utils.py      # Helper functions (e.g., TxnID generation)
└── tests/                # Python unit tests
    ├── __init__.py
    ├── test_ingest.py
    └── test_normalize.py
```

## Contributing

(Add guidelines later if applicable - e.g., feature branches, tests, code style)

* Run linters/formatters: `poetry run black . && poetry run ruff check . --fix`
* Run tests: `poetry run pytest`

## License

Personal use only.

## Version

0.1.0 - Initial Setup and Core ETL Structure