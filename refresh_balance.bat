@echo off
rem ============================================================================
rem BALANCE-pyexcel ETL Pipeline Runner
rem 
rem This batch file runs the BALANCE-pyexcel pipeline to process CSV files 
rem and update the Excel workbook.
rem
rem Usage: 
rem   - Double-click this file to run with default paths
rem   - Or customize the paths below to match your environment
rem ============================================================================

rem Set the path to the repository (current directory by default)
set REPO_PATH=%~dp0
cd %REPO_PATH%

rem Set the path to the CSV inbox folder (change if needed)
set CSV_INBOX=C:\CSVs

rem Set the path to the Excel workbook (change if needed)
set WORKBOOK=%REPO_PATH%workbook\BALANCE-pyexcel.xlsm

echo ============================================================================
echo BALANCE-pyexcel ETL Pipeline
echo ============================================================================
echo Repository: %REPO_PATH%
echo CSV Inbox:  %CSV_INBOX%
echo Workbook:   %WORKBOOK%
echo ============================================================================

rem Run the pipeline
echo Running ETL pipeline...

rem Use fully qualified path to Python in the Poetry venv
if exist "%REPO_PATH%\.venv\Scripts\python.exe" (
    "%REPO_PATH%\.venv\Scripts\python.exe" -m balance_pipeline.cli "%CSV_INBOX%" "%WORKBOOK%"
) else (
    rem Fall back to poetry run if venv not found in standard location
    poetry run balance-pyexcel "%CSV_INBOX%" "%WORKBOOK%"
)

echo.
echo Process complete. Press any key to exit.
pause > nul
