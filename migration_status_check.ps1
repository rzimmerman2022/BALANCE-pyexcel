# Financial Reconciliation Project Migration Script
# This script checks the status of moving projects to c:\projects structure

# Check current status
Write-Host "=== FINANCIAL RECONCILIATION PROJECT MIGRATION ===" -ForegroundColor Green
Write-Host "Current Date: $(Get-Date)" -ForegroundColor Yellow

# Check if projects are moved to c:\projects
Write-Host "`n=== CHECKING PROJECT LOCATIONS ===" -ForegroundColor Green

$balanceOld = "c:\BALANCE\BALANCE-pyexcel"
$balanceNew = "c:\projects\BALANCE"
$financialNew = "c:\projects\financial-reconciliation"

Write-Host "`nBALANCE-pyexcel migration status:" -ForegroundColor Cyan
if (Test-Path $balanceNew) {
    Write-Host "[OK] Found at: $balanceNew" -ForegroundColor Green
    if (Test-Path $balanceOld) {
        Write-Host "[WARNING] Original still exists at: $balanceOld" -ForegroundColor Yellow
        Write-Host "[INFO] Other projects in c:\BALANCE remain untouched (correct)" -ForegroundColor Green
    }
} else {
    Write-Host "[ERROR] Not found at: $balanceNew" -ForegroundColor Red
    if (Test-Path $balanceOld) {
        Write-Host "[INFO] Still at original location: $balanceOld" -ForegroundColor Yellow
    }
}

Write-Host "`nFinancial-reconciliation project:" -ForegroundColor Cyan
if (Test-Path $financialNew) {
    Write-Host "[OK] Found at: $financialNew" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Not found at: $financialNew" -ForegroundColor Red
}

# Show other projects in c:\BALANCE (should remain untouched)
Write-Host "`nOther projects in c:\BALANCE (should remain):" -ForegroundColor Cyan
Get-ChildItem "c:\BALANCE" | Where-Object {$_.Name -ne "BALANCE-pyexcel"} | ForEach-Object {
    Write-Host "[INFO] $($_.FullName)" -ForegroundColor White
}

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

if (Test-Path $balanceNew) {
    Write-Host "`nBALANCE project Git status:" -ForegroundColor Cyan
    Set-Location $balanceNew
    try {
        $gitStatus = git status --porcelain
        if ($LASTEXITCODE -eq 0) {
            if ([string]::IsNullOrEmpty($gitStatus)) {
                Write-Host "[OK] Git repository is clean" -ForegroundColor Green
            } else {
                Write-Host "[INFO] Git has uncommitted changes" -ForegroundColor Yellow
                Write-Host $gitStatus
            }
        }
    } catch {
        Write-Host "[ERROR] Git issue in balance project: $($_.Exception.Message)" -ForegroundColor Red
    }
}

if (Test-Path $financialNew) {
    Write-Host "`nFinancial-reconciliation Git status:" -ForegroundColor Cyan
    Set-Location $financialNew
    try {
        $gitStatus = git status --porcelain
        if ($LASTEXITCODE -eq 0) {
            if ([string]::IsNullOrEmpty($gitStatus)) {
                Write-Host "[OK] Git repository is clean" -ForegroundColor Green
            } else {
                Write-Host "[INFO] Git has uncommitted changes" -ForegroundColor Yellow
                Write-Host $gitStatus
            }
        }
    } catch {
        Write-Host "[ERROR] Git issue in financial-reconciliation: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "`n=== MIGRATION STATUS SUMMARY ===" -ForegroundColor Green
if ((Test-Path $balanceNew) -and (Test-Path $financialNew)) {
    Write-Host "[OK] Both projects are in c:\projects structure" -ForegroundColor Green
    if (Test-Path $balanceOld) {
        Write-Host "[TODO] Clean up original BALANCE-pyexcel after verification" -ForegroundColor Yellow
        Write-Host "[GOOD] Other c:\BALANCE projects preserved" -ForegroundColor Green
    }
    Write-Host "`nNext actions needed:" -ForegroundColor Yellow
    Write-Host "1. ✅ RESOLVED: Rent payment logic clarified!" -ForegroundColor Green
    Write-Host "   - Jordyn pays full rent to landlord" -ForegroundColor White
    Write-Host "   - Ryan owes ~47% back to Jordyn" -ForegroundColor White
    Write-Host "   - Zelle payments are for expenses, not rent" -ForegroundColor White
    Write-Host "2. Set up financial-reconciliation GitHub repository" -ForegroundColor White
    Write-Host "3. Create single CSV processors" -ForegroundColor White  
    Write-Host "4. Build reconciliation pipeline" -ForegroundColor White
    Write-Host "5. Generate audit trails" -ForegroundColor White
} else {
    Write-Host "[ERROR] Migration not complete - projects missing from c:\projects" -ForegroundColor Red
}
