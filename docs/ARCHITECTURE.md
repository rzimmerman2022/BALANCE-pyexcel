# BALANCE-pyexcel - High-Level Architecture

# ---
## Overview

This document outlines the architecture of the `BALANCE-pyexcel` project, an Excel-based personal finance tracker for couples, powered by a Python backend running within Excel. It leverages a configuration-driven approach using YAML to handle multiple, diverse CSV input formats from various financial institutions.

# ---
## System Components & Flow Diagram

```mermaid
flowchart TD
    subgraph User_Input
        direction LR
        UI_DropCSV[User Drops CSVs into Folders] --> FS_CSVs
        UI_Excel[User Opens/Interacts with Excel] --> WBK[BALANCE-pyexcel.xlsm]
        UI_Excel --> PY_Trigger[User Triggers Python Refresh in Excel]
    end

    subgraph External_FileSystem
        direction TB
        FS_CSVs["CSV Input Folder (e.g., C:/.../CSVs/)"]
        subgraph Owner_Subfolders [Owner Subfolders]
           FS_CSVs_J["Jordyn/*.csv"]
           FS_CSVs_R["Ryan/*.csv"]
        end
        FS_CSVs --> FS_CSVs_J & FS_CSVs_R
    end

    subgraph Git_Repository [Project Root: BALANCE-pyexcel]
        direction TB

        subgraph Configuration
            CONF_YAML["rules/schema_registry.yml"]
            CONF_MERCHANT_CSV["rules/merchant_lookup.csv"]
            CONF_PY["src/balance_pipeline/config.py \n (+ .env optional)"]
            WBK_ConfigSheet[Excel: Config Sheet \n (Input Path, User Names)]
        end

        subgraph Python_Pipeline [src/balance_pipeline/]
            PY_CLI["cli.py \n (etl_main orchestrator, \n File Scanner, Deduplication)"]
            PY_CONSOLIDATOR["csv_consolidator.py \n (Schema Matching, Transformations, \n Merchant Cleaning, TxnID Gen)"]
            PY_SYNC["sync.py \n (Excel Queue_Review Sync)"]
            PY_UTILS["utils.py \n (Shared Text Cleaning, etc.)"]
            PY_NORM_HELPERS["normalize.py \n (Original Merchant Cleaner, \n TxnID Hashing components - referenced)"]
            PY_CALC["calculate.py \n (Future: Balance Logic)"]
            PY_CLASS["classify.py \n (Future: Rule-based Tagging)"]

            CONF_YAML --> PY_CONSOLIDATOR
            CONF_MERCHANT_CSV --> PY_CONSOLIDATOR
            CONF_PY --> PY_CLI & PY_CONSOLIDATOR & PY_UTILS 
            FS_CSVs_J & FS_CSVs_R -.-> PY_CLI # CLI scans these paths

            PY_UTILS --> PY_CONSOLIDATOR & PY_NORM_HELPERS
            PY_NORM_HELPERS --> PY_CONSOLIDATOR # Consolidator uses clean_merchant

            PY_CLI -- CSV File Paths --> PY_CONSOLIDATOR
            PY_CONSOLIDATOR -- Consolidated DataFrame --> PY_CLI
            PY_CLI -- DataFrame for Sync --> PY_SYNC
            PY_SYNC -- Synced DataFrame --> PY_CLI
            PY_CLI -- Final DataFrame for Output --> WBK_PythonCell # and Parquet writing
        end

        subgraph Excel_Interface [workbook/BALANCE-pyexcel.xlsm]
           WBK_PythonCell["Excel: Python Cell \n (=PY(etl_main(...)))"]
           WBK_Transactions["Excel: Transactions Sheet"]
           WBK_Queue["Excel: Queue_Review Sheet"]
           WBK_Dashboard["Excel: Dashboard Sheet"]
           WBK_RulesM["Excel: Rules_Merchants Table"]
           WBK_RulesS["Excel: Rules_Shared Table"]

           WBK_ConfigSheet -- Input Path --> WBK_PythonCell
           PY_Trigger --> WBK_PythonCell
           WBK_PythonCell -- calls --> PY_CLI # Or a wrapper in __init__ that calls CLI's etl_main
           PY_CLI -- returns --> WBK_PythonCell
           WBK_PythonCell -- writes data --> WBK_Transactions # Or data read via formulas
           WBK_Transactions -- FILTER --> WBK_Queue
           WBK_Queue -- Manual Input --> PY_SYNC # Sync logic reads from Excel
           WBK_Transactions -- data source --> WBK_Dashboard # For charts/calcs
           WBK_RulesM & WBK_RulesS # Used for reference/manual input, maybe read by Python later
        end

        subgraph Testing
            TESTS["tests/ \n (pytest files)"]
            SAMPLE_DATA["sample_data_multi/ \n (Anonymized CSVs)"]
            SAMPLE_DATA --> TESTS
            PY_Pipeline --> TESTS # Tests import code from src
        end
    end

    User_Input --> Git_Repository # User interacts via Excel file in repo
---
1. Layers
Layer	Technology	Responsibility
UI/Input	Excel Sheets, File System Folders	Data Input (CSVs via folders), Settings Config (Excel), Manual Transaction Classification (Excel Queue_Review)
View	Excel Sheets (Dashboard, Transactions, Queue_Review)	Displaying Balances, Charts, Processed Transactions, Items needing Review
Orchestration	Python Cell (=PY(...) in Excel), cli.py (etl_main)	Triggering Python ETL process (etl_main), Coordinating calls to CSV consolidator and sync modules.
ETL	Python package (src/balance_pipeline/), YAML Config	Schema-driven CSV processing (via csv_consolidator.py: reading YAML, finding/reading CSVs, dynamic mapping, date/amount/derived/static column transformations, merchant cleaning, TxnID generation, master schema conformance), Deduplication (in cli.py), Shared Utilities (utils.py).
Configuration	Excel Sheet (Config), rules/schema_registry.yml, rules/merchant_lookup.csv, .env	Storing runtime paths (CSV Inbox), user names (Excel); Storing CSV parsing rules (YAML); Merchant cleaning rules (CSV); Optional environment overrides (.env via config.py)
Storage	File System (balance_final.parquet, CSVs), Excel Sheet (Transactions)	Primary data store (Parquet); Original raw data source (CSVs); View/Interaction layer (Excel).
Testing	pytest framework, tests/ folder (including fixtures/), sample_data_multi/	Unit testing Python ETL functions using anonymized sample data representing multiple schemas.

Export to Sheets
---
2. Data Flow (ETL Round-Trip v0.1)
User places new bank/credit card CSV files into their respective sub-folders (e.g., /CSVs/Jordyn/, /CSVs/Ryan/) located outside the Git repository.
User opens BALANCE-pyexcel.xlsm in Excel.
User ensures the full path to the parent CSV folder (e.g., C:\...\CSVs) is correctly entered in the Config sheet (CsvInboxPath).
User triggers the main Python ETL cell (e.g., via Data > Refresh All, or cell execution), or runs the CLI command (`poetry run balance refresh ...`).
The Excel Python cell (if used) calls `etl_main` (likely from `src/balance_pipeline/__init__.py` which in turn might call the CLI's `etl_main` or a similar function). The CLI directly calls `etl_main` in `cli.py`.
`etl_main` (in `cli.py`) orchestrates the process:
  a. Scans the `inbox_path` for CSV files, respecting `exclude_patterns` and `only_patterns`, creating a list of file paths.
  b. Calls `csv_consolidator.process_csv_files`, passing the list of CSV paths, and paths to `schema_registry.yml` and `merchant_lookup.csv`.
  c. `csv_consolidator.process_csv_files`:
     i. Loads schema registry and merchant lookup rules.
     ii. For each CSV file in the list:
        1. Reads the raw CSV into a DataFrame.
        2. Infers `Owner` from the CSV's parent directory name.
        3. Gets `DataSourceDate` from the CSV's file modification time.
        4. Calls `find_matching_schema` (using CSV headers and filename) to get the appropriate schema from the registry.
        5. If a schema is matched, calls `apply_schema_transformations` with the DataFrame and schema rules.
        6. `apply_schema_transformations`:
           - Applies `column_map` to rename/select columns.
           - Collects unmapped columns into an `Extras` JSON field.
           - Parses date columns (e.g., `Date`, `PostDate`) using `date_format` from the schema.
           - Standardizes `Amount` (numeric conversion, applies `amount_regex`, `sign_rule` including simple and complex types like `flip_if_column_value_matches`).
           - Generates derived columns (e.g., `Account`, `AccountLast4`, `AccountType`) based on `derived_columns` rules in the schema.
           - Populates `DataSourceName` from the schema ID.
           - Adds static columns defined in `extra_static_cols`.
        7. Populates `Owner` and `DataSourceDate` into the processed DataFrame.
        8. Performs final merchant cleaning on the appropriate description column (populating the master `Merchant` column) using loaded merchant lookup rules and `balance_pipeline.normalize.clean_merchant` as a fallback.
        9. Generates `TxnID` using a hash of key transaction attributes.
        10. Sets default values for `Currency`, `SharedFlag`, `SplitPercent`, etc.
        11. Ensures all master schema columns exist and coerces them to their defined data types (including robust boolean parsing via `coerce_bool`).
        12. Orders columns according to the master schema.
        13. Appends the processed DataFrame for this file to a list.
     iii. After processing all CSVs, concatenates all resulting DataFrames.
     iv. Sorts the combined DataFrame.
     v. Returns the consolidated DataFrame to `etl_main`.
  d. `etl_main` (in `cli.py`):
     i. Receives the consolidated DataFrame from `process_csv_files`.
     ii. Performs deduplication based on `TxnID` and the `prefer_source` argument, keeping the record from the preferred data source if duplicates exist.
     iii. Returns this final DataFrame.
The main script (`cli.py` `main()` function) then:
  a. Loads existing canonical data from `balance_final.parquet` (if any).
  b. Merges these existing classifications (SharedFlag, SplitPercent) into the newly processed data based on `TxnID`.
  c. Reads `Queue_Review` sheet from the Excel workbook (if not `--no-sync`).
  d. Calls `sync.sync_review_decisions` to update `SharedFlag` and `SplitPercent` in the DataFrame based on `Queue_Review` input.
  e. Writes the final, updated DataFrame to `balance_final.parquet`.
  f. Writes the data to the 'Transactions' sheet and a template to the 'Queue_Review' sheet in the Excel workbook (unless `--dry-run`).
Excel (if not run headlessly): The Python cell receives the DataFrame from `etl_main`. Data is updated on the 'Transactions' sheet. The 'Queue_Review' sheet dynamically updates via its `FILTER` formula.
---
3. Key Design Decisions
Excel as Frontend: Leverage user familiarity with Excel for UI, configuration, data viewing, and manual classification.
Python for ETL & Logic: Use Python (Pandas) for reliable, flexible data manipulation, cleaning, rule application, and calculations.
YAML Schema Registry & CSV Merchant Rules: Centralize rules for parsing diverse CSV formats (`rules/schema_registry.yml`) and for cleaning merchant names (`rules/merchant_lookup.csv`). Makes the system highly maintainable and extensible. Configuration-over-code.
Modular Python Backend: `csv_consolidator.py` handles comprehensive CSV processing. `cli.py` orchestrates the overall flow including deduplication and Excel interaction. `sync.py` handles Excel data synchronization.
Owner Tagging via Folders: Use a simple convention (subfolders named after owners within the main CSV inbox) to automatically assign ownership.
Deterministic Transaction ID (TxnID): Generate a unique and reproducible ID for each transaction. Essential for tracking, updates, and preventing duplicates.
Comprehensive Master Schema: A well-defined target schema ensures data consistency.
Unit Testing: `pytest` framework with fixtures and parametrized tests for core logic.
CLI for Headless Operation: `cli.py` enables running the full ETL pipeline, including Parquet and Excel updates, from the command line, suitable for automation or users not directly interacting with Python in Excel.
Dependency Management (Poetry): Ensure reproducible Python environments.

**END REVISED CONTENT FOR `architecture.md`**
