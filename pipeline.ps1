#!/usr/bin/env pwsh
<#
.SYNOPSIS
    BALANCE-pyexcel Master Pipeline - Single Entry Point
    
.DESCRIPTION
    This is the main pipeline entry point for the BALANCE-pyexcel project.
    All operations should go through this script for consistency and clarity.
    
.PARAMETER Action
    The action to perform:
    - process: Process CSV files through the main pipeline
    - analyze: Run comprehensive analysis
    - baseline: Run baseline balance analysis
    - clean: Clean and organize repository
    - status: Show pipeline status
    - help: Show detailed help
    
.PARAMETER InputPath
    Path to CSV files or input directory (default: csv_inbox)
    
.PARAMETER OutputPath
    Path for output files (default: output)
    
.PARAMETER Format
    Output format: excel, parquet, csv, powerbi (default: powerbi)
    
.PARAMETER Debug
    Enable debug mode for detailed logging
    
.EXAMPLE
    .\pipeline.ps1 process
    # Process all CSV files in csv_inbox/ with default settings
    
.EXAMPLE
    .\pipeline.ps1 analyze -Debug
    # Run comprehensive analysis with debug output
    
.EXAMPLE
    .\pipeline.ps1 process -InputPath "data/*.csv" -Format excel
    # Process specific CSV files and output to Excel
    
.EXAMPLE
    .\pipeline.ps1 status
    # Show current pipeline status and health
#>

param(
    [Parameter(Mandatory=$true, Position=0)]
    [ValidateSet("process", "analyze", "baseline", "clean", "status", "help")]
    [string]$Action,
    
    [Parameter()]
    [string]$InputPath = "csv_inbox",
    
    [Parameter()]
    [string]$OutputPath = "output",
    
    [Parameter()]
    [ValidateSet("excel", "parquet", "csv", "powerbi")]
    [string]$Format = "powerbi",
    
    [Parameter()]
    [switch]$Debug
)

# Set error handling
$ErrorActionPreference = "Stop"

# Script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "🚀 BALANCE-pyexcel Master Pipeline" -ForegroundColor Green
Write-Host "Action: $Action" -ForegroundColor Cyan

try {
    switch ($Action) {
        "process" {
            Write-Host "📊 Processing CSV files..." -ForegroundColor Yellow
            
            $cmd = "poetry run balance-pipe process `"$InputPath/**/*.csv`""
            if ($Format -ne "powerbi") { $cmd += " --format $Format" }
            if ($OutputPath -ne "output") { $cmd += " --output $OutputPath" }
            if ($Debug) { $cmd += " --debug" }
            
            Write-Host "Executing: $cmd" -ForegroundColor Gray
            Invoke-Expression $cmd
            
            Write-Host "✅ Processing complete!" -ForegroundColor Green
        }
        
        "analyze" {
            Write-Host "🔍 Running comprehensive analysis..." -ForegroundColor Yellow
            
            if ($Debug) {
                poetry run balance-analyze --config config/balance_analyzer.yaml --verbose
            } else {
                poetry run balance-analyze --config config/balance_analyzer.yaml
            }
            
            Write-Host "✅ Analysis complete!" -ForegroundColor Green
        }
        
        "baseline" {
            Write-Host "⚖️  Running baseline balance analysis..." -ForegroundColor Yellow
            
            if ($Debug) {
                poetry run balance-baseline --debug
            } else {
                poetry run balance-baseline
            }
            
            Write-Host "✅ Baseline analysis complete!" -ForegroundColor Green
        }
        
        "clean" {
            Write-Host "🧹 Cleaning repository..." -ForegroundColor Yellow
            & "scripts/powershell/Clean-Repository.ps1"
            Write-Host "✅ Repository cleaned!" -ForegroundColor Green
        }
        
        "status" {
            Write-Host "📋 Pipeline Status:" -ForegroundColor Yellow
            Write-Host ""
            
            # Check Poetry environment
            try {
                $poetryStatus = poetry check 2>&1
                Write-Host "✅ Poetry: OK" -ForegroundColor Green
            } catch {
                Write-Host "❌ Poetry: Error" -ForegroundColor Red
            }
            
            # Check Python modules
            try {
                poetry run python -c "import balance_pipeline; print('✅ balance_pipeline: OK')"
                poetry run python -c "import baseline_analyzer; print('✅ baseline_analyzer: OK')"
            } catch {
                Write-Host "❌ Python modules: Error" -ForegroundColor Red
            }
            
            # Check input/output directories
            if (Test-Path $InputPath) {
                Write-Host "✅ Input directory ($InputPath): OK" -ForegroundColor Green
            } else {
                Write-Host "⚠️  Input directory ($InputPath): Not found" -ForegroundColor Yellow
            }
            
            if (Test-Path $OutputPath) {
                Write-Host "✅ Output directory ($OutputPath): OK" -ForegroundColor Green
            } else {
                Write-Host "⚠️  Output directory ($OutputPath): Not found" -ForegroundColor Yellow
            }
            
            # Show recent outputs
            if (Test-Path "output") {
                $recentFiles = Get-ChildItem "output" -Recurse -File | Sort-Object LastWriteTime -Descending | Select-Object -First 5
                if ($recentFiles) {
                    Write-Host ""
                    Write-Host "📁 Recent outputs:" -ForegroundColor Cyan
                    $recentFiles | ForEach-Object { 
                        Write-Host "   $($_.Name) ($($_.LastWriteTime.ToString('yyyy-MM-dd HH:mm')))" -ForegroundColor Gray 
                    }
                }
            }
        }
        
        "help" {
            Write-Host ""
            Write-Host "🔧 BALANCE-pyexcel Pipeline Commands:" -ForegroundColor Cyan
            Write-Host ""
            Write-Host "Main Operations:" -ForegroundColor White
            Write-Host "  .\pipeline.ps1 process              - Process CSV files (main pipeline)"
            Write-Host "  .\pipeline.ps1 analyze              - Run comprehensive analysis"
            Write-Host "  .\pipeline.ps1 baseline             - Run baseline balance analysis"
            Write-Host ""
            Write-Host "Utilities:" -ForegroundColor White
            Write-Host "  .\pipeline.ps1 status               - Show pipeline health status"
            Write-Host "  .\pipeline.ps1 clean                - Clean repository"
            Write-Host ""
            Write-Host "Options:" -ForegroundColor White
            Write-Host "  -InputPath <path>                   - Input CSV path (default: csv_inbox)"
            Write-Host "  -OutputPath <path>                  - Output directory (default: output)"
            Write-Host "  -Format <excel|parquet|csv|powerbi> - Output format (default: powerbi)"
            Write-Host "  -Debug                              - Enable debug logging"
            Write-Host ""
            Write-Host "Examples:" -ForegroundColor White
            Write-Host "  .\pipeline.ps1 process -Debug"
            Write-Host "  .\pipeline.ps1 process -InputPath 'data/*.csv' -Format excel"
            Write-Host "  .\pipeline.ps1 analyze -Debug"
            Write-Host ""
            Write-Host "Documentation: docs/PIPELINE_STATUS.md" -ForegroundColor Gray
        }
    }
} catch {
    Write-Host "❌ Error: $_" -ForegroundColor Red
    Write-Host "Run '.\pipeline.ps1 help' for usage information" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "🎯 Pipeline operation completed successfully!" -ForegroundColor Green