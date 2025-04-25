# BALANCE-pyexcel Template Workbook

This directory contains the template Excel workbook with pre-loaded VBA macros for the BALANCE-pyexcel project.

## Files

- `BALANCE-template.xlsm`: Macro-enabled Excel workbook with ImportFromTemp VBA module
- `BALANCE-template-empty.xlsm`: Empty template with just the macros (no data)

## How to Use

1. Copy one of the template workbooks to your desired location
2. Run the CLI to process your CSVs:
   ```
   poetry run balance-pyexcel "C:\path\to\CSVs" "path\to\your-copy-of-BALANCE-template.xlsm"
   ```
3. Open your workbook
4. Click the "Import Data" button to import the processed data

## Included Macros

The workbook includes two main macros:

- **RefreshData**: Runs the CLI tool to process CSVs and generate the temporary Excel file
- **ImportFromTempFile**: Imports data from the temporary file into the workbook

## Customizing the Workbook

Feel free to add your own sheets, charts, and formulas. The macros will:

1. Preserve all sheets except Transactions and Queue_Review
2. Update Transactions with the latest data
3. Backup previous Transactions data as Transactions_Backup

## Loading the Macros Manually

If you need to add the macros to your own workbook:

1. Open your workbook in Excel
2. Press Alt+F11 to open the VBA Editor
3. Right-click your project in the Project Explorer
4. Select "Import File" and browse to `ImportFromTemp.bas`
5. Add buttons to your worksheet:
   - Developer tab > Insert > Button
   - Assign ImportFromTempFile and RefreshData to buttons
