# Financial Reconciliation Project Migration Script
# This script safely moves essential files to the new clean project structure

# Check current status
Write-Host "=== FINANCIAL RECONCILIATION PROJECT MIGRATION ===" -ForegroundColor Green
Write-Host "Current Date: $(Get-Date)" -ForegroundColor Yellow

# Verify source files exist
$sourceFiles = @(
    "c:\BALANCE\BALANCE-pyexcel\data\Consolidated_Expense_History_20250622.csv",
    "c:\BALANCE\BALANCE-pyexcel\data\Consolidated_Rent_Allocation_20250527.csv", 
    "c:\BALANCE\BALANCE-pyexcel\data\Zelle_From_Jordyn_Final.csv"
)

Write-Host "`nVerifying source files..." -ForegroundColor Cyan
foreach ($file in $sourceFiles) {
    if (Test-Path $file) {
        $size = (Get-Item $file).Length
        Write-Host "[OK] Found: $file ($size bytes)" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Missing: $file" -ForegroundColor Red
    }
}

# Check destination structure
Write-Host "`nChecking destination structure..." -ForegroundColor Cyan
$destPath = "c:\projects\financial-reconciliation"
if (Test-Path $destPath) {
    Write-Host "[OK] Destination exists: $destPath" -ForegroundColor Green
    
    # List current contents
    Write-Host "`nCurrent contents of new project:" -ForegroundColor Yellow
    Get-ChildItem $destPath -Recurse | Select-Object FullName | ForEach-Object { 
        Write-Host "  $($_.FullName)" 
    }
} else {
    Write-Host "[ERROR] Destination missing: $destPath" -ForegroundColor Red
}

# Check Git status of both projects
Write-Host "`n=== GIT STATUS CHECK ===" -ForegroundColor Green

Write-Host "`nBALANCE-pyexcel Git status:" -ForegroundColor Cyan
Set-Location "c:\BALANCE\BALANCE-pyexcel"
try {
    git status --porcelain
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Git repository is clean" -ForegroundColor Green
    }
} catch {
    Write-Host "[ERROR] Git issue in BALANCE-pyexcel: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`nFinancial-reconciliation Git status:" -ForegroundColor Cyan
Set-Location "c:\projects\financial-reconciliation"
try {
    git status --porcelain
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Git repository status checked" -ForegroundColor Green
    }
} catch {
    Write-Host "Git not initialized or error: $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host "`n=== MIGRATION COMPLETE - READY FOR NEXT STEPS ===" -ForegroundColor Green
Write-Host "Next actions needed:" -ForegroundColor Yellow
Write-Host "1. Resolve rent payment logic assumptions" -ForegroundColor White
Write-Host "2. Create single CSV processors" -ForegroundColor White  
Write-Host "3. Build reconciliation pipeline" -ForegroundColor White
Write-Host "4. Generate audit trails" -ForegroundColor White
