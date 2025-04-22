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
            CONF_PY["src/balance_pipeline/config.py \n (+ .env optional)"]
            WBK_ConfigSheet[Excel: Config Sheet \n (Input Path, User Names)]
        end

        subgraph Python_Pipeline [src/balance_pipeline/]
            PY_INIT["__init__.py \n (etl_main orchestrator)"]
            PY_INGEST["ingest.py \n (YAML Reader, CSV Loader, \n Mapper, Sign Fixer, Owner Tag)"]
            PY_NORM["normalize.py \n (Clean Desc, TxnID Gen, \n Flagging, Final Cols/Sort)"]
            PY_UTILS["utils.py \n (Text Cleaning, Hashing)"]
            PY_CALC["calculate.py \n (Future: Balance Logic)"]
            PY_CLASS["classify.py \n (Future: Rule-based Tagging)"]

            CONF_YAML --> PY_INGEST
            CONF_PY --> PY_INGEST & PY_NORM & PY_UTILS #Potentially
            FS_CSVs_J & FS_CSVs_R --> PY_INGEST
            PY_UTILS --> PY_NORM
            PY_INGEST -- Raw+Owner DataFrame --> PY_NORM
            PY_INIT -- calls --> PY_INGEST & PY_NORM
            PY_NORM -- Final DataFrame --> PY_INIT
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
           WBK_PythonCell -- calls --> PY_INIT
           PY_INIT -- returns --> WBK_PythonCell
           WBK_PythonCell -- writes data --> WBK_Transactions # Or data read via formulas
           WBK_Transactions -- FILTER --> WBK_Queue
           WBK_Queue -- Manual Input --> WBK_PythonCell # For future Sync step
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
Orchestration	Python Cell (=PY(...) in Excel), __init__.py (etl_main)	Triggering Python ETL process (etl_main), Coordinating calls to ingest and normalize modules
ETL	Python package (src/balance_pipeline/), YAML Config	Schema-driven data ingestion (reading YAML, finding/reading CSVs, dynamic mapping, sign rules, deriving columns, owner tagging via ingest.py), Normalization (text cleaning, TxnID generation, default flagging, final column structuring via normalize.py), Shared Utilities (utils.py)
Configuration	Excel Sheet (Config), rules/schema_registry.yml, .env	Storing runtime paths (CSV Inbox), user names (Excel); Storing CSV parsing rules (YAML); Optional environment overrides (.env via config.py)
Storage	Excel Sheet (Transactions), File System (CSVs)	Persisting cleaned transaction data within the workbook; Original raw data source (external)
Testing	pytest framework, tests/ folder, sample_data_multi/	Unit testing Python ETL functions using anonymized sample data representing multiple schemas

Export to Sheets
---
2. Data Flow (ETL Round-Trip v0.1)
User places new bank/credit card CSV files into their respective sub-folders (e.g., /CSVs/Jordyn/, /CSVs/Ryan/) located outside the Git repository.
User opens BALANCE-pyexcel.xlsm in Excel.
User ensures the full path to the parent CSV folder (e.g., C:\...\CSVs) is correctly entered in the Config sheet (CsvInboxPath).
User triggers the main Python ETL cell (e.g., via Data > Refresh All, or cell execution).
The Excel Python cell calls etl_main from src/balance_pipeline/__init__.py, passing the CsvInboxPath.
etl_main orchestrates the process:
Calls ingest.load_folder, passing the inbox path.
ingest.load_folder:
Recursively scans the inbox path and its subdirectories (rglob) for *.csv files.
For each CSV found:
Determines the Owner from the parent directory name (e.g., 'Jordyn', 'Ryan').
Reads the first few rows to get headers.
Calls _find_schema, passing the file path and headers.
_find_schema:
Loads rules from rules/schema_registry.yml (if not already loaded).
Iterates through schemas in YAML, checking match_filename and header_signature against the current CSV.
Returns the matching schema dictionary or None.
If a schema is found:
Reads the full CSV file.
Applies the column_map from the schema to rename columns.
Applies derived_columns rules (if any) using regex.
Normalizes Date and Amount data types.
Applies the sign_rule from the schema to standardize Amount sign (outflow = negative).
Adds the Owner column.
Ensures all STANDARD_COLS exist, adding NA if needed.
Selects only STANDARD_COLS.
Appends the processed DataFrame for this file to a list.
After checking all files, concatenates all processed DataFrames in the list.
Returns the combined DataFrame to etl_main.
etl_main:
Receives the combined DataFrame from ingest.load_folder.
Calls normalize.normalize_df, passing the combined DataFrame.
normalize.normalize_df:
Takes the ingested data.
Cleans descriptions using utils.clean_whitespace, creating CleanDesc.
Generates TxnID using utils.sha256_hex based on hash of Owner, Date, Amount, Description, Account.
Adds default SharedFlag = '?'.
Ensures all FINAL_COLS are present and in the correct order.
Sorts the DataFrame by Date.
Returns the final, normalized DataFrame to etl_main.
etl_main:
Receives the final DataFrame from normalize.normalize_df.
Returns this DataFrame back to the Excel Python cell.
Excel: The Python cell receives the DataFrame. Depending on the exact formula/setup:
The data might spill into cells adjacent to the formula.
Or, if using direct write (less reliable initially), it attempts to write to the Transactions sheet/table. (Requires manual copy/paste from spill range as the robust starting point).
Excel (Queue_Review Sheet): A FILTER formula dynamically displays rows from the Transactions sheet where SharedFlag = '?', ready for user classification.
---
3. Key Design Decisions
Excel as Frontend: Leverage user familiarity with Excel for UI, configuration, data viewing, and manual classification.
Python for ETL & Logic: Use Python (Pandas) for reliable, flexible data manipulation, cleaning, rule application, and calculations, overcoming limitations of pure Excel/VBA, especially for varied inputs.
YAML Schema Registry: Centralize rules for parsing diverse CSV formats in an easy-to-edit rules/schema_registry.yml file. Makes the system highly maintainable and extensible without Python code changes for new formats. Configuration-over-code.
Configuration in Excel & Files: Store runtime settings (paths, user names) in Excel Config sheet for easy user access. Store complex parsing rules in YAML. Use optional .env for environment-specific overrides (config.py).
Owner Tagging via Folders: Use a simple convention (subfolders named after owners within the main CSV inbox) to automatically assign ownership during ingestion.
Deterministic Transaction ID (TxnID): Generate a unique and reproducible ID for each transaction based on hashing key, stable attributes including Owner, Date, Amount, Description, Account. Essential for tracking, updates, and preventing duplicates.
Modularity & Testing: Structure Python code into logical modules (ingest, normalize, utils, etc.) with clear functions. Use pytest for unit testing core logic using anonymized sample_data.
Version Control (Git): Track all code, YAML configuration, documentation, tests, sample data, and the Excel workbook for history, backup, and collaboration.
Dependency Management (Poetry): Ensure reproducible Python environments using pyproject.toml and poetry.lock.

**END REVISED CONTENT FOR `architecture.md`**