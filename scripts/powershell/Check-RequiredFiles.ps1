<#
.SYNOPSIS
    BALANCE-pyexcel - CSV presence verifier
    
.DESCRIPTION
    Checks for the presence of required CSV files in a specified directory.
    
.PARAMETER BaseDir
    The base directory to check for files. Defaults to "data" relative to script location.
    
.PARAMETER CI
    Switch to enable CI/pipeline mode (no interactive prompts).
    
.EXAMPLE
    PS> .\Check-RequiredFiles.ps1
    
.EXAMPLE
    PS> .\Check-RequiredFiles.ps1 -BaseDir "C:\Exports\2025-05-27"
    
.EXAMPLE
    PS> .\Check-RequiredFiles.ps1 -CI
#>

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$BaseDir = "data",
    
    [Parameter()]
    [switch]$CI
)

# Set strict mode for better error handling
Set-StrictMode -Version Latest

#--- Detect CI automatically if env var present ---------------------------------
if (-not $PSBoundParameters.ContainsKey('CI')) {
    $CI = [bool]$env:CI
}

#--- Resolve base directory (relative to this script) --------------------------
try {
    # If BaseDir is absolute, use as-is; otherwise, treat as relative to script
    if ([System.IO.Path]::IsPathRooted($BaseDir)) {
        $ResolvedBaseDir = Resolve-Path $BaseDir -ErrorAction Stop
    } else {
        $ResolvedBaseDir = Resolve-Path (Join-Path $PSScriptRoot $BaseDir) -ErrorAction Stop
    }
} catch {
    Write-Error "Base directory '$BaseDir' not found: $_"
    if ($CI) { 
        exit 1 
    } else { 
        Write-Host "`nPress ENTER to exit" -ForegroundColor Yellow
        [void]$Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        exit 1
    }
}

#--- Manifest ------------------------------------------------------------------
$RequiredFiles = @(
    'Expense_History_20250527.csv',
    'Transaction_Ledger_20250527.csv',
    'Rent_Allocation_20250527.csv',
    'Rent_History_20250527.csv'
)

#--- Check files ---------------------------------------------------------------
Write-Host "`nChecking for required files in: $ResolvedBaseDir" -ForegroundColor Cyan
Write-Host ("-" * 60) -ForegroundColor DarkGray

$Missing = [System.Collections.ArrayList]::new()
$Found = 0

foreach ($fileName in $RequiredFiles) {
    $filePath = Join-Path $ResolvedBaseDir $fileName
    
    if (Test-Path -Path $filePath -PathType Leaf) {
        Write-Host "  [OK] $fileName" -ForegroundColor Green
        $Found++
    } else {
        Write-Host "  [MISSING] $fileName" -ForegroundColor Red
        [void]$Missing.Add($fileName)
    }
}

Write-Host ("-" * 60) -ForegroundColor DarkGray

#--- Summary -------------------------------------------------------------------
$ExitCode = if ($Missing.Count -gt 0) { 1 } else { 0 }

if ($Missing.Count -gt 0) {
    Write-Warning "$($Missing.Count) file(s) missing:"
    foreach ($file in $Missing) {
        Write-Host "  - $file" -ForegroundColor Red
    }
} else {
    Write-Host "`nAll $Found required files are present." -ForegroundColor Green
}

#--- Exit ----------------------------------------------------------------------
if ($CI) {
    exit $ExitCode
} else {
    Write-Host "`nPress ENTER to exit" -ForegroundColor Yellow
    [void]$Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit $ExitCode
}