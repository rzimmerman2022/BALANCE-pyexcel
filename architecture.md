# BALANCE-pyexcel - High-Level Architecture

## Overview

This document outlines the architecture of the `BALANCE-pyexcel` project, an Excel-based personal finance tracker for couples, powered by a Python backend running within Excel.

```mermaid
flowchart TD
    subgraph User_Interaction
        direction LR
        UI_CSV[Drop CSV Files] --> FS_Inbox
        UI_Excel[Open BALANCE-pyexcel.xlsx] --> WBK_Config
        UI_Excel --> WBK_QueueReview
        UI_Excel --> WBK_Dashboard
    end

    subgraph File_System
        direction TB
        FS_Inbox[/csv_inbox/]
        FS_Rules[/rules/ or Excel Tables]
    end

    subgraph Excel_Workbook [BALANCE-pyexcel.xlsx]
        direction TB
        WBK_Config[Config Sheet\n(CSV Path, User Names)] --> PY_Orchestrator
        WBK_RulesMerchants[Rules_Merchants Sheet/Table] --> PY_Orchestrator
        WBK_RulesShared[Rules_Shared Sheet/Table] --> PY_Orchestrator
        PY_Orchestrator(Python Cell(s)\nETL Trigger, Sync Trigger, Calc Trigger)
        PY_Orchestrator --> WBK_Transactions[Transactions Sheet\n(Cleaned Data Output)]
        WBK_Transactions -- Filtered --> WBK_QueueReview[Queue_Review Sheet\n(Manual Classification Y/N/S)]
        WBK_QueueReview -- User Input --> PY_Orchestrator
        PY_Orchestrator --> WBK_Dashboard[Dashboard Sheet\n(Balance, Charts)]
    end

    subgraph Python_Pipeline [src/balance_pipeline/]
        direction TB
        PY_Config[config.py\nLoad Settings] --> PY_Ingest
        FS_Inbox --> PY_Ingest[ingest.py\nLoad & Combine CSVs]
        PY_Ingest -- Raw DataFrame --> PY_Normalize[normalize.py\nClean, Standardize, Add TxnID]
        FS_Rules --> PY_Normalize
        WBK_RulesMerchants --> PY_Normalize
        PY_Normalize -- Normalized DataFrame --> PY_Classify[classify.py (Phase 2)\nApply Shared Rules]
        WBK_RulesShared --> PY_Classify
        PY_Classify -- Classified DataFrame --> PY_OutputHandler
        PY_OutputHandler[Output Handler\n(Formats for Excel Sheet)] --> PY_Orchestrator
        PY_Test[tests/] -- Validates --> Python_Pipeline
    end

    User_Interaction --> File_System
    User_Interaction --> Excel_Workbook
    Python_Pipeline --> Excel_Workbook

    1. Layers
Layer	Technology	Responsibility
UI/Input	Excel Sheets, File System Folder	Data Input (CSVs), Settings Configuration, Manual Transaction Classification
View	Excel Sheets (Dashboard, Queue_Review)	Displaying Balances, Charts, Insights, Items needing Review
Orchestration	Python Cells (=PY(...) in Excel)	Triggering ETL Refresh, Syncing User Decisions, Triggering Balance Calculation
ETL	Python package (src/balance_pipeline)	Data Ingestion, Cleaning, Normalization, Classification, TxnID Generation
Configuration	Excel Sheets (Config, Rules_*), .env file	Storing Paths, User Names, Processing Rules (Merchants, Shared Expenses)
Storage	Excel Sheet (Transactions), File System (CSVs)	Persisting cleaned transaction data within the workbook, Raw data source
Testing	pytest framework (tests/ folder)	Unit testing Python ETL functions

Export to Sheets
2. Data Flow (High Level)
User places new bank/credit card CSV files into the configured csv_inbox folder.
User opens BALANCE-pyexcel.xlsx.
User triggers the main Python ETL cell (e.g., via Data > Refresh All, or cell execution).
Python (ingest.py): Reads CSVs from the inbox, combines them.
Python (normalize.py): Cleans data types, standardizes text, generates a unique TxnID for each row, applies merchant rules (from Excel/files). Adds SharedFlag = '?'.
Python (classify.py - Future): Applies shared expense rules (from Excel/files) to automatically set SharedFlag to Y or N where possible.
Python (Orchestrator Cell): Returns the processed DataFrame.
Excel: The DataFrame populates the Transactions sheet (manually copied from spill range initially).
Excel (Queue_Review Sheet): FILTER formula displays rows from Transactions where SharedFlag = '?'.
User reviews items in Queue_Review and enters classification (Y/N/S, SplitPercent).
User triggers the Python "Sync Decisions" cell.
Python (Sync Cell): Reads Transactions and Queue_Review, merges decisions based on TxnID, updates SharedFlag and SplitPercent in the Transactions data. Returns the updated DataFrame (user manually updates Transactions sheet).
Python (Balance Calc Cell): Reads updated Transactions, calculates who owes whom based on 'Y' flagged items and split percentages. Returns summary.
Excel (Dashboard Sheet): Displays the calculated balance and charts based on Transactions data.
3. Key Design Decisions
Excel as Frontend: Leverage user familiarity with Excel for UI, configuration, and data viewing. Python enhances it with robust processing.
Python for ETL & Logic: Use Python (Pandas) for reliable data manipulation, cleaning, rule application, and calculations, overcoming limitations of pure Excel/VBA.
Configuration in Excel/Files: Store user settings (paths, names) and processing rules (merchant mapping, shared rules) in accessible Excel tables or external files (.env, rules/), not hardcoded in Python.
Deterministic Transaction ID (TxnID): Generate a unique and reproducible ID for each transaction based on its core attributes (Date, Amount, Description, Account) using hashing. Essential for tracking and merging updates.
Idempotent ETL (Goal): Design the Python pipeline so that running it multiple times on the same input CSVs produces the same output in the Transactions sheet (assuming no new user classifications).
Modularity & Testing: Structure Python code into logical modules (ingest, normalize, etc.) with clear functions. Write unit tests (pytest) for core logic to ensure correctness and facilitate refactoring.
Version Control (Git): Track all code, configuration files (rules), and the Excel workbook itself (though diffing .xlsx is limited) for history and collaboration.
Dependency Management (Poetry): Ensure reproducible Python environments.