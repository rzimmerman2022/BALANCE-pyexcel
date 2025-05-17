# CLI Usage Guide

## Why use the CLI?

`balance-pyexcel` lets you run the entire ETL pipeline **without** opening Excel.  
Typical reasons:

* Python-in-Excel isn’t available on your workstation.
* You want to automate nightly refreshes via Task Scheduler / cron.
* You prefer Git-tracked, headless runs for CI or ad-hoc scripts.

---

## Installation

```bash
poetry install                     # from the repo root
That adds a console entry-point called balance-pyexcel to your virtual-env.

Basic command
bash
Copy
Edit
poetry run balance-pyexcel <CSV_INBOX> <EXCEL_WORKBOOK>
Example:

bash
Copy
Edit
poetry run balance-pyexcel "C:\BALANCE\csv_inbox" "C:\BALANCE\BALANCE-pyexcel.xlsm"
What happens:

Load every CSV in <CSV_INBOX> (recursively).

Normalize via rules/schema_registry.yml.

Read existing decisions from the Queue_Review sheet.

Apply those decisions to the new data.

Write the result to the Transactions sheet (and refresh Queue_Review).

Options
Option	Purpose
--no-sync	Skip step 3 (ignore prior decisions).
-v, --verbose	Show debug-level logs. Repeat -vv for ultra-verbose.
--log PATH	Tee console logs to a file.
--dry-run	Do every step except writing to Excel; dumps run_YYYYMMDD_HHMMSS.csv.
--queue-sheet NAME	Use a sheet other than “Queue_Review”.

Example:

bash
Copy
Edit
poetry run balance-pyexcel "C:\csvs" "C:\BALANCE\BALANCE-pyexcel.xlsm" \
  -v --log process.log --dry-run
Excel integration
Add a Refresh button
Alt + F11 → Insert > Module → paste:

vba
Copy
Edit
Sub RefreshData()
    ThisWorkbook.Save
    Dim cmd As String
    cmd = "cmd /c cd ""C:\BALANCE\BALANCE-pyexcel-repository"" && " & _
          "poetry run balance-pyexcel ""C:\BALANCE\csv_inbox"" " & _
          """C:\BALANCE\BALANCE-pyexcel.xlsm"""
    Shell cmd, vbHide
End Sub
Drop a Form-Control button, assign RefreshData.

(Adjust paths to fit your install.)

Automate with Task Scheduler (Windows)
Create refresh_balance.bat:

batch
Copy
Edit
@echo off
cd C:\BALANCE\BALANCE-pyexcel-repository
poetry run balance-pyexcel "C:\BALANCE\csv_inbox" ^
                           "C:\BALANCE\BALANCE-pyexcel.xlsm"
In Task Scheduler → Create Task:

Triggers: Daily or hourly schedule.

Actions: Start a program → point to the batch file.

Settings: Check “Run whether user is logged on or not”.

Troubleshooting
.xlsm quirks
Macro-enabled files are updated via a temporary .temp.xlsx to keep your VBA code intact.
Either:

Add the supplied ImportFromTemp.bas to automate the copy, or

Manually copy the Transactions sheet from the temp file (CLI prints the path).

Lock files
A .lock next to the workbook prevents concurrent writes. If the script crashes, delete it manually once you’re sure no other process is running.

Missing packages
bash
Copy
Edit
poetry add openpyxl
poetry install
Path errors
Use absolute paths and wrap any that contain spaces in double quotes.

Sample log excerpt
pgsql
Copy
Edit
2025-05-17 09:42:01 INFO Loading CSVs from C:\BALANCE\csv_inbox
2025-05-17 09:42:02 INFO Loaded 148 rows
2025-05-17 09:42:02 INFO Normalizing data (5 schemas)
2025-05-17 09:42:03 INFO Removed 17 duplicates (via TxnID)
2025-05-17 09:42:03 INFO Reading Queue_Review (5 decisions)
2025-05-17 09:42:03 INFO Writing 131 rows → Transactions
2025-05-17 09:42:04 INFO ✅ Process completed