# Quick Analysis of Rent vs Zelle Payments
# This script examines the rent allocation CSV and Zelle payments to understand the financial flow

Write-Host "=== RENT ALLOCATION ANALYSIS ===" -ForegroundColor Green

# Import rent data 
$rentData = Import-Csv "c:\projects\financial-reconciliation\data\raw\Consolidated_Rent_Allocation_20250527.csv"

Write-Host "`nRent allocation structure:" -ForegroundColor Cyan
$rentData | Select-Object Month, "Gross Total", "Ryan's Rent (43%)", "Jordyn's Rent (57%)" | Format-Table

# Calculate some totals
Write-Host "`nRent allocation analysis:" -ForegroundColor Yellow
foreach ($row in $rentData) {
    $grossTotal = [decimal]($row."Gross Total" -replace '[\$,]', '')
    $ryanRent = [decimal]($row."Ryan's Rent (43%)" -replace '[\$,]', '')
    $jordynRent = [decimal]($row."Jordyn's Rent (57%)" -replace '[\$,]', '')
    
    $total = $ryanRent + $jordynRent
    $difference = $grossTotal - $total
    
    Write-Host "$($row.Month): Gross=$grossTotal, Ryan+Jordyn=$total, Diff=$difference"
}

Write-Host "`n=== ZELLE PAYMENTS ANALYSIS ===" -ForegroundColor Green

# Import Zelle data
$zelleData = Import-Csv "c:\projects\financial-reconciliation\data\raw\Zelle_From_Jordyn_Final.csv"

Write-Host "`nZelle payments from Jordyn:" -ForegroundColor Cyan
$zelleData | Select-Object Date, Amount, Notes | Format-Table

# Calculate monthly totals
Write-Host "`nMonthly Zelle totals:" -ForegroundColor Yellow
$zelleByMonth = $zelleData | Group-Object {([DateTime]$_.Date).ToString("MMM-yy")} | 
    ForEach-Object {
        $monthTotal = ($_.Group | ForEach-Object {[decimal]$_.Amount} | Measure-Object -Sum).Sum
        [PSCustomObject]@{
            Month = $_.Name
            Total = $monthTotal
            Count = $_.Count
        }
    }

$zelleByMonth | Format-Table

Write-Host "`n=== CRITICAL INSIGHTS ===" -ForegroundColor Red
Write-Host "1. Rent allocation shows Ryan pays 43%, Jordyn pays 57%" -ForegroundColor White
Write-Host "2. Zelle payments appear to be monthly reimbursements" -ForegroundColor White
Write-Host "3. Need to compare Jordyn's allocated rent vs her Zelle payments" -ForegroundColor White
Write-Host "4. Some Zelle payments have specific notes (bills, loans, etc.)" -ForegroundColor White
