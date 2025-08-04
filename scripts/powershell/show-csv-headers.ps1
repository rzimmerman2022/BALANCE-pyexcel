<#
.SYNOPSIS
  Glimpse the structure of the four BALANCE CSV inputs
  by printing their headers and first 10 rows.

.NOTES
  • Adjust the paths if your directory layout differs.
  • If you don’t have Rent_History yet, comment that line out.
  • Uses Format-Table -AutoSize for clarity; widen your terminal if columns wrap.
#>

$csvFiles = @{
    Expenses   = "data\Expense_History_20250527.csv"
    Ledger     = "data\Transaction_Ledger_20250527.csv"
    Rent       = "data\Rent_Allocation_20250527.csv"
    RentHist   = "data\Rent_History_20250527.csv"   # comment/remove if absent
}

foreach ($label in $csvFiles.Keys) {
    $path = $csvFiles[$label]

    if (-not (Test-Path $path)) {
        Write-Warning "$label file NOT found → $path"
        continue
    }

    Write-Host "`n=== $label  ($path) ===" -ForegroundColor Cyan

    # 1️⃣ Raw header line (first line of file)
    $header = Get-Content -Path $path -TotalCount 1
    Write-Host "Header columns:"
    $header.Split(',') | ForEach-Object { "  $_" }

    # 2️⃣ First 10 data rows (as a table)
    Write-Host "`nFirst 10 rows:"
    Import-Csv -Path $path | Select-Object -First 10 | Format-Table -AutoSize

    Write-Host "----------------------------------------------"
}
