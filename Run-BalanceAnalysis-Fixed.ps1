# BALANCE Project - Automated Analysis Pipeline
# This script runs the complete analysis pipeline for Power BI and reporting

param(
    [switch]$QuickRun,
    [switch]$FullAnalysis,
    [switch]$PowerBIOnly
)

Write-Host "🏦 BALANCE Project - Automated Analysis Pipeline" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan

$ErrorActionPreference = "Continue"
$OriginalLocation = Get-Location
$ProjectRoot = "c:\Projects\BALANCE"

try {
    # Change to project directory
    Set-Location $ProjectRoot
    Write-Host "📁 Working in: $ProjectRoot" -ForegroundColor Green

    if ($PowerBIOnly -or $QuickRun -or $FullAnalysis) {
        Write-Host "`n🔄 Running Power BI Data Refresh..." -ForegroundColor Yellow
        python powerbi_data_refresh.py
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Power BI datasets updated successfully" -ForegroundColor Green
        } else {
            Write-Host "❌ Power BI refresh failed with exit code $LASTEXITCODE" -ForegroundColor Red
        }
    }

    if (-not $PowerBIOnly) {
        Write-Host "`n📊 Running Enhanced Financial Dashboard..." -ForegroundColor Yellow
        python enhanced_financial_dashboard.py
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Financial dashboard generated successfully" -ForegroundColor Green
        } else {
            Write-Host "❌ Dashboard generation failed with exit code $LASTEXITCODE" -ForegroundColor Red
        }
    }

    if ($FullAnalysis) {
        Write-Host "`n🔍 Running Comprehensive Audit Trail..." -ForegroundColor Yellow
        python comprehensive_audit_trail.py
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Comprehensive audit trail updated" -ForegroundColor Green
        } else {
            Write-Host "❌ Audit trail generation failed with exit code $LASTEXITCODE" -ForegroundColor Red
        }
        
        Write-Host "`n📋 Running Transaction Audit..." -ForegroundColor Yellow
        python comprehensive_transaction_audit.py
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Transaction audit completed" -ForegroundColor Green
        } else {
            Write-Host "❌ Transaction audit failed with exit code $LASTEXITCODE" -ForegroundColor Red
        }
    }

    # Show recent outputs
    Write-Host "`n📁 Recent Analysis Files:" -ForegroundColor Cyan
    Get-ChildItem -Filter "powerbi_*" | Where-Object {$_.LastWriteTime -gt (Get-Date).AddDays(-1)} | 
        Select-Object Name, Length, LastWriteTime | Format-Table -AutoSize

    Get-ChildItem -Filter "financial_dashboard_*" | Where-Object {$_.LastWriteTime -gt (Get-Date).AddDays(-1)} | 
        Select-Object Name, Length, LastWriteTime | Format-Table -AutoSize

    Write-Host "`n📊 Current Balance Status:" -ForegroundColor Cyan
    if (Test-Path "powerbi_current_status.csv") {
        $status = Import-Csv "powerbi_current_status.csv"
        foreach ($row in $status) {
            if ($row.Person -ne "SUMMARY") {
                $balance = [math]::Abs([decimal]$row.Running_Balance)
                $status_text = if ([decimal]$row.Running_Balance -lt 0) { "owes" } elseif ([decimal]$row.Running_Balance -gt 0) { "is owed" } else { "even" }
                Write-Host "  • $($row.Person): $($balance.ToString('C')) ($status_text)" -ForegroundColor White
            }
        }
    }

    Write-Host "`n🎉 Analysis Pipeline Complete!" -ForegroundColor Green
    Write-Host "=" * 60 -ForegroundColor Cyan

} catch {
    Write-Host "❌ Error occurred: $_" -ForegroundColor Red
} finally {
    Set-Location $OriginalLocation
}

Write-Host "`nUsage Examples:" -ForegroundColor Yellow
Write-Host "  .\Run-BalanceAnalysis.ps1 -QuickRun      # Power BI + Dashboard only" -ForegroundColor Gray
Write-Host "  .\Run-BalanceAnalysis.ps1 -PowerBIOnly   # Power BI datasets only" -ForegroundColor Gray
Write-Host "  .\Run-BalanceAnalysis.ps1 -FullAnalysis  # Complete analysis pipeline" -ForegroundColor Gray
