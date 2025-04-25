# CLI Usage Guide

## Overview

The BALANCE-pyexcel project now includes a command-line interface (CLI) that allows you to run the data pipeline outside of Excel. This is useful when Python-in-Excel is not available or when you want to automate data processing.

## Installation

To install the CLI, run the following command from the project root directory:

```bash
poetry install
```

This will create a command-line tool named `balance-pyexcel` that you can use to process your CSV files.

## Basic Usage

The basic usage of the CLI is:

```bash
poetry run balance-pyexcel <CSV_INBOX_FOLDER> <EXCEL_WORKBOOK_PATH>
```

For example:

```bash
poetry run balance-pyexcel "C:\CSVs" "C:\BALANCE\BALANCE-pyexcel.xlsm"
```

This will:
1. Load all CSVs from the specified inbox folder
2. Process them according to the schema registry
3. Read any existing decisions from the Queue_Review sheet in the Excel workbook
4. Apply those decisions to the transactions
5. Write the results back to the Transactions sheet in the workbook

## Command Line Options

The CLI supports the following options:

- `--no-sync`: Skip syncing decisions from Queue_Review sheet
- `--verbose` or `-v`: Enable verbose logging for more detailed output
- `--log PATH`: Write logs to the specified file (in addition to console output)
- `--dry-run`: Process data but don't write to Excel (saves to a .dry-run.csv file instead)
- `--queue-sheet NAME`: Specify a different name for the Queue_Review sheet (default: "Queue_Review")

Example with options:

```bash
poetry run balance-pyexcel "C:\CSVs" "C:\BALANCE\BALANCE-pyexcel.xlsm" --verbose --log process.log
```

For dry runs (test without modifying Excel):

```bash
poetry run balance-pyexcel "C:\CSVs" "C:\BALANCE\BALANCE-pyexcel.xlsm" --dry-run
```

## Integration with Excel

### Adding a Refresh Button in Excel

To add a Refresh button in Excel that triggers the Python script:

1. Open your workbook in Excel
2. Press Alt+F11 to open the VBA Editor
3. Insert a new Module (Insert > Module)
4. Paste the following code:

```vba
Sub RefreshData()
    ' Save and close the workbook to avoid file lock issues
    ThisWorkbook.Save
    
    ' Build the command to run the Python script
    Dim cmd As String
    cmd = "cmd /c cd ""C:\BALANCE\BALANCE-pyexcel-repository"" && poetry run balance-pyexcel ""C:\CSVs"" ""C:\BALANCE\BALANCE-pyexcel.xlsm"""
    
    ' Run the command (hide the command window)
    Shell cmd, vbHide
    
    ' Optionally, reopen the workbook to see the updated data
    ' Uncomment the following line if you want Excel to automatically reopen the file
    ' Application.Workbooks.Open "C:\BALANCE\BALANCE-pyexcel.xlsm"
End Sub
```

5. Adjust the paths in the code to match your environment:
   - Replace `C:\BALANCE\BALANCE-pyexcel-repository` with the path to your repository
   - Replace `C:\CSVs` with the path to your CSV inbox folder
   - Replace `C:\BALANCE\BALANCE-pyexcel.xlsm` with the path to your workbook

6. Insert a button on your worksheet (Developer tab > Insert > Button from Form Controls)
7. Assign the RefreshData macro to the button

Now, when you click the button, Excel will:
1. Save and close the workbook to avoid file lock issues
2. Run the Python script to process the CSVs and update the workbook
3. (Optionally) Reopen the workbook to show the updated data

### Automated Refresh with Task Scheduler

You can also set up a scheduled task to refresh the data automatically:

1. Create a batch file (e.g., `refresh_balance.bat`) with the following content:

```batch
@echo off
cd C:\BALANCE\BALANCE-pyexcel-repository
poetry run balance-pyexcel "C:\CSVs" "C:\BALANCE\BALANCE-pyexcel.xlsm"
```

2. Open Task Scheduler
3. Create a new task with the following settings:
   - General: Name the task and set it to run whether user is logged in or not
   - Triggers: Set a schedule (e.g., daily at 6:00 AM)
   - Actions: Start a program, with the path to your batch file
   - Conditions: Adjust as needed (e.g., only run when computer is on AC power)
   - Settings: Allow task to be run on demand

## Troubleshooting

### Working with Macro-Enabled Workbooks (.xlsm)

When working with macro-enabled workbooks (.xlsm files), the CLI uses a special approach to preserve VBA macros:

1. It creates a temporary .xlsx file containing the processed data
2. It preserves all existing sheets except for Transactions and Queue_Review
3. It provides instructions for importing the data into your macro workbook

#### Automatic Import with VBA Macro

For the easiest workflow, you can add the `ImportFromTemp.bas` module to your workbook:

1. Open your .xlsm workbook in Excel
2. Press Alt+F11 to open the VBA Editor
3. In the Project Explorer, right-click your project and select Import File
4. Browse to `ImportFromTemp.bas` and click Open
5. Close the VBA Editor

This adds two useful macros:
- `ImportFromTempFile`: Imports data from the .temp.xlsx file after running the CLI
- `RefreshData`: Runs the CLI and then prompts you to import the data

To use these macros:
1. Add buttons to your workbook (Developer tab > Insert > Button)
2. Assign `RefreshData` to one button and `ImportFromTempFile` to another

#### Manual Copying (Alternative)

If you prefer not to use the VBA macro, follow these steps when you see the CLI instructions:

```
IMPORTANT: To update your macro-enabled workbook:
1. Open your workbook: C:\BALANCE\BALANCE-pyexcel.xlsm
2. Open the temporary file: C:\BALANCE\BALANCE-pyexcel.temp.xlsx
3. Copy the 'Transactions' sheet from the temporary file to your workbook
4. Copy the 'Queue_Review' sheet if needed
5. Save your workbook
6. Delete the temporary file when done
```

### File Lock Files

The CLI creates a temporary `.lock` file next to your workbook to prevent multiple processes from modifying it simultaneously. This file is automatically removed when processing completes.

If the script crashes, the lock file might be left behind. If you're certain no other process is using the workbook, you can safely delete any `.lock` files manually.

### Missing Dependencies

If you get an error about missing dependencies, make sure you've installed all required packages:

```bash
poetry add openpyxl
poetry install
```

### Path Issues

If you get an error about a file or directory not being found, check that all paths in your commands are correct. Use absolute paths to avoid any confusion.

## Log Output

The CLI provides informative log output as it runs:

```
2025-04-22 23:30:15 - INFO - Loading CSVs from C:\CSVs
2025-04-22 23:30:15 - INFO - Successfully loaded rules/schema_registry.yml containing 5 schema(s).
2025-04-22 23:30:16 - INFO - Loaded 123 rows from CSVs
2025-04-22 23:30:16 - INFO - Normalizing data
2025-04-22 23:30:16 - INFO - Normalized data contains 120 rows
2025-04-22 23:30:16 - INFO - Reading Queue_Review sheet from C:\BALANCE\BALANCE-pyexcel.xlsm
2025-04-22 23:30:16 - INFO - Read 5 rows from Queue_Review
2025-04-22 23:30:16 - INFO - Syncing decisions from Queue_Review
2025-04-22 23:30:16 - INFO - Decisions synced
2025-04-22 23:30:16 - INFO - Writing 120 rows to Transactions sheet in C:\BALANCE\BALANCE-pyexcel.xlsm
2025-04-22 23:30:17 - INFO - ✅ Process completed successfully
