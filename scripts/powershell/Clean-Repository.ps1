<#
.SYNOPSIS
    Cleans up a Python repository by quarantining orphan files and running quality checks.

.DESCRIPTION
    This script performs repository maintenance by:
    - Moving orphan *.py files into a legacy_scripts directory
    - Detecting PowerShell here-docs in Python files and renaming them to *.ps1
    - Updating pyproject.toml to exclude legacy_scripts from Ruff checks
    - Running quality gate checks (Ruff, MyPy, PyTest) with auto-fix capabilities

.PARAMETER RootPath
    The root directory of the repository. Defaults to current directory.

.PARAMETER LegacyDirectoryName
    Name of the directory to move orphan files to. Defaults to 'legacy_scripts'.

.PARAMETER SkipQualityGate
    Skip running the quality gate checks (Ruff, MyPy, PyTest).

.EXAMPLE
    .\Clean-Repository.ps1
    Runs the cleanup in the current directory with all quality checks.

.EXAMPLE
    .\Clean-Repository.ps1 -SkipQualityGate
    Runs the cleanup but skips the quality gate checks.

.NOTES
    Author: BALANCE Team
    Requires: Poetry, Ruff, MyPy, PyTest installed in the project
#>

[CmdletBinding()]
param(
    [Parameter()]
    [ValidateScript({
        if (-not (Test-Path $_)) {
            throw "Directory does not exist: $_"
        }
        $true
    })]
    [string]$RootPath = (Get-Location),

    [Parameter()]
    [ValidateNotNullOrEmpty()]
    [string]$LegacyDirectoryName = 'legacy_scripts',

    [Parameter()]
    [switch]$SkipQualityGate,

    [Parameter()]
    [switch]$SkipGitStaging
)

# Enable strict mode for better error detection
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

#region Helper Functions

function Write-InfoMessage {
    <#
    .SYNOPSIS
        Writes an informational message with consistent formatting.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$Message,
        
        [Parameter()]
        [ConsoleColor]$ForegroundColor = 'Cyan'
    )
    
    Write-Host $Message -ForegroundColor $ForegroundColor
}

function Write-SuccessMessage {
    <#
    .SYNOPSIS
        Writes a success message with consistent formatting.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$Message
    )
    
    Write-Host $Message -ForegroundColor Green
}

function Write-WarningMessage {
    <#
    .SYNOPSIS
        Writes a warning message with consistent formatting.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$Message
    )
    
    Write-Warning $Message
}

function Test-CommandAvailable {
    <#
    .SYNOPSIS
        Tests if a command is available in the current environment.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$CommandName
    )
    
    $null = Get-Command -Name $CommandName -ErrorAction SilentlyContinue
    return $?
}

function Get-UniqueFilePath {
    <#
    .SYNOPSIS
        Generates a unique file path by appending a GUID if the path already exists.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$Directory,
        
        [Parameter(Mandatory)]
        [string]$BaseName,
        
        [Parameter(Mandatory)]
        [string]$Extension
    )
    
    $proposedPath = Join-Path -Path $Directory -ChildPath "$BaseName$Extension"
    
    if (Test-Path -LiteralPath $proposedPath) {
        # Generate a short GUID suffix to ensure uniqueness
        $guidSuffix = [guid]::NewGuid().ToString('N').Substring(0, 8)
        $proposedPath = Join-Path -Path $Directory -ChildPath "${BaseName}_${guidSuffix}${Extension}"
    }
    
    return $proposedPath
}

function Test-PowerShellHereDoc {
    <#
    .SYNOPSIS
        Tests if a file contains PowerShell here-doc syntax.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$FilePath
    )
    
    try {
        $content = Get-Content -Path $FilePath -Raw -ErrorAction Stop
        # Look for PowerShell here-doc patterns: @" or <#
        return $content -match '(@"|<#)'
    }
    catch {
        Write-Verbose "Could not read file: $FilePath. Error: $_"
        return $false
    }
}

function Move-OrphanFile {
    <#
    .SYNOPSIS
        Moves an orphan file to the legacy directory with appropriate renaming.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [System.IO.FileInfo]$File,
        
        [Parameter(Mandatory)]
        [string]$TargetDirectory
    )
    
    # Determine if file should be renamed based on content
    $targetExtension = if (Test-PowerShellHereDoc -FilePath $File.FullName) {
        '.ps1'
    } else {
        $File.Extension
    }
    
    # Generate unique destination path
    $destinationPath = Get-UniqueFilePath `
        -Directory $TargetDirectory `
        -BaseName $File.BaseName `
        -Extension $targetExtension
    
    # Display the move operation
    Write-InfoMessage "  -> $($File.FullName)" -ForegroundColor Yellow
    Write-InfoMessage "    |-> $destinationPath" -ForegroundColor DarkYellow
    
    # Perform the move
    Move-Item -LiteralPath $File.FullName -Destination $destinationPath -Force
    
    return $destinationPath
}

function Update-PyProjectToml {
    <#
    .SYNOPSIS
        Updates pyproject.toml to exclude the legacy directory from Ruff checks.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$PyProjectPath,
        
        [Parameter(Mandatory)]
        [string]$ExcludePattern
    )
    
    $content = Get-Content -Path $PyProjectPath -Raw
    
    # Check if the pattern is already excluded
    if ($content -match [regex]::Escape($ExcludePattern)) {
        Write-Verbose "Pattern '$ExcludePattern' already exists in pyproject.toml"
        return $false
    }
    
    # Check for existing [tool.ruff] section
    if ($content -notmatch '\[tool\.ruff\]') {
        # No [tool.ruff] section exists - append one
        $newContent = $content.TrimEnd() + "`n`n[tool.ruff]`nexclude = [`"$ExcludePattern`"]`n"
        Set-Content -Path $PyProjectPath -Value $newContent -NoNewline
    }
    elseif ($content -match '(?ms)(\[tool\.ruff\].*?)(^\s*exclude\s*=\s*\[)([^\]]*)\]') {
        # Exclude list exists - append to it
        $updatedContent = $content -replace `
            '(?ms)(\[tool\.ruff\].*?)(^\s*exclude\s*=\s*\[)([^\]]*)\]', `
            "`$1`$2`$3, `"$ExcludePattern`"]"
        Set-Content -Path $PyProjectPath -Value $updatedContent -NoNewline
    }
    else {
        # [tool.ruff] exists but no exclude line - add one
        $updatedContent = $content -replace `
            '(\[tool\.ruff\])', `
            "`$1`nexclude = [`"$ExcludePattern`"]"
        Set-Content -Path $PyProjectPath -Value $updatedContent -NoNewline
    }
    
    return $true
}

function Invoke-QualityCheck {
    <#
    .SYNOPSIS
        Runs a quality check command and handles the result.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$CheckName,
        
        [Parameter(Mandatory)]
        [scriptblock]$Command,
        
        [Parameter()]
        [string]$WorkingDirectory = (Get-Location)
    )
    
    Write-InfoMessage "`n-- Running $CheckName" -ForegroundColor Magenta
    
    # Save current location and change to working directory
    $originalLocation = Get-Location
    try {
        Set-Location -Path $WorkingDirectory
        
        # Execute the command
        & $Command
        
        if ($LASTEXITCODE -ne 0) {
            throw "$CheckName check failed with exit code: $LASTEXITCODE"
        }
        
        Write-SuccessMessage "   (OK) $CheckName passed"
    }
    finally {
        # Always restore original location
        Set-Location -Path $originalLocation
    }
}

#endregion

#region Main Script Logic

try {
    # Display script header
    Write-InfoMessage @"

----------------------------------------------------------------
 BALANCE - Repository Clean-Up & Quality Gate (PowerShell)
----------------------------------------------------------------
"@ -ForegroundColor Cyan

    # Validate environment
    if (-not (Test-CommandAvailable -CommandName 'poetry')) {
        throw "Poetry is not installed or not in PATH. Please install Poetry first."
    }

    # Set up paths
    $legacyDirectory = Join-Path -Path $RootPath -ChildPath $LegacyDirectoryName
    $pyProjectPath = Join-Path -Path $RootPath -ChildPath 'pyproject.toml'
    
    # Validate pyproject.toml exists
    if (-not (Test-Path -Path $pyProjectPath)) {
        throw "pyproject.toml not found in $RootPath. Is this a Python project?"
    }

    # Create legacy directory if it doesn't exist
    if (-not (Test-Path -Path $legacyDirectory)) {
        New-Item -Path $legacyDirectory -ItemType Directory | Out-Null
        Write-Verbose "Created directory: $legacyDirectory"
    }

    # Define directories to skip during scanning
    $skipPatterns = @(
        'src',
        'tests',
        'tools',  # Don't move development tools!
        $LegacyDirectoryName,
        '.venv',
        '.git',
        'dist',
        'build',
        'node_modules',
        '__pycache__',
        '.pytest_cache',
        '.mypy_cache',
        '.ruff_cache'
    )
    
    # Build regex pattern for directories to skip
    $skipRegex = '[\\/](' + ($skipPatterns -join '|') + ')[\\/]'
    
    Write-InfoMessage "`n-- Scanning for orphan *.py files..."
    
    # Find all Python files not in standard directories
    $orphanFiles = Get-ChildItem -Path $RootPath -Recurse -File -Filter '*.py' |
        Where-Object { $_.FullName -notmatch $skipRegex }
    
    $movedFiles = @()
    
    # Process each orphan file
    foreach ($file in $orphanFiles) {
        $movedPath = Move-OrphanFile -File $file -TargetDirectory $legacyDirectory
        $movedFiles += $movedPath
    }
    
    # Handle results
    if ($movedFiles.Count -eq 0) {
        Write-SuccessMessage "`n(OK) No orphan files found - repository is clean!"
    }
    else {
        # Update pyproject.toml
        $excludePattern = "$LegacyDirectoryName/*"
        $tomlUpdated = Update-PyProjectToml `
            -PyProjectPath $pyProjectPath `
            -ExcludePattern $excludePattern
        
        # Stage changes in git if available
        if (-not $SkipGitStaging -and (Test-CommandAvailable -CommandName 'git')) {
            # Check if we're in a git repository
            $savedErrorPref = $ErrorActionPreference
            $ErrorActionPreference = 'Continue'
            
            $gitRoot = & git rev-parse --show-toplevel 2>$null
            if ($LASTEXITCODE -eq 0) {
                if ($tomlUpdated) {
                    # Capture Git output to prevent warnings from stopping the script
                    $gitOutput = & git add $pyProjectPath 2>&1
                    if ($gitOutput -match "warning:") {
                        Write-Verbose "Git warning: $gitOutput"
                    }
                }
                # Add the legacy directory
                $gitOutput = & git add $legacyDirectory 2>&1
                if ($gitOutput -match "warning:") {
                    Write-Verbose "Git warning: $gitOutput"
                }
            }
            
            $ErrorActionPreference = $savedErrorPref
        }
        
        Write-SuccessMessage "`n(OK) Quarantined $($movedFiles.Count) file(s) into $LegacyDirectoryName/"
    }
    
    # Run quality gate checks unless skipped
    if (-not $SkipQualityGate) {
        Write-InfoMessage "`n================================================================"
        Write-InfoMessage " Running Quality Gate Checks"
        Write-InfoMessage "================================================================"
        
        # Run Ruff first with auto-fix capability
        try {
            Write-InfoMessage "`n-- Running Ruff Linter with auto-fix" -ForegroundColor Magenta
            $originalLocation = Get-Location
            Set-Location -Path $RootPath
            
            # Run Ruff with --fix flag to auto-fix issues
            & poetry run ruff check src tests --fix
            
            if ($LASTEXITCODE -eq 0) {
                Write-SuccessMessage "   (OK) Ruff passed (auto-fixed issues if any)"
            }
            else {
                # Run again without --fix to show remaining issues
                & poetry run ruff check src tests
                throw "Ruff check failed with remaining issues"
            }
        }
        finally {
            Set-Location -Path $originalLocation
        }
        
        # Check if MyPy auto-fixer exists and offer to run it
        $mypyFixerPath = Join-Path -Path $RootPath -ChildPath "tools\fix_mypy_errors.py"
        if (Test-Path -Path $mypyFixerPath) {
            Write-InfoMessage "`n-- MyPy Auto-Fixer Available" -ForegroundColor Magenta
            Write-InfoMessage "   This tool can automatically fix common type annotation issues."
            
            try {
                $originalLocation = Get-Location
                Set-Location -Path $RootPath
                
                # First, do a dry run to show what will be fixed
                Write-InfoMessage "`n   Running analysis to identify fixable issues..."
                & poetry run python $mypyFixerPath --verbose
                
                # Ask user if they want to apply the fixes
                $response = Read-Host "`n   Apply these fixes? (Y/N)"
                if ($response -eq 'Y' -or $response -eq 'y') {
                    & poetry run python $mypyFixerPath --apply --verbose
                    Write-SuccessMessage "   (OK) MyPy auto-fixes applied"
                }
                else {
                    Write-InfoMessage "   Skipped MyPy auto-fixes"
                }
            }
            catch {
                Write-WarningMessage "   MyPy auto-fixer encountered an error: $_"
            }
            finally {
                Set-Location -Path $originalLocation
            }
        }
        else {
            Write-InfoMessage "`n   (INFO) MyPy auto-fixer not found. Consider adding fix_mypy_errors.py to your project."
            Write-InfoMessage "      This tool can automatically fix common type annotation issues."
        }
        
        # Now run the remaining quality checks
        $qualityChecks = [ordered]@{
            'MyPy Type Checker' = { poetry run mypy src --strict }
            'PyTest Suite' = { poetry run pytest -q }
        }
        
        # Run each remaining quality check
        foreach ($check in $qualityChecks.GetEnumerator()) {
            Invoke-QualityCheck `
                -CheckName $check.Key `
                -Command $check.Value `
                -WorkingDirectory $RootPath
        }
        
        Write-SuccessMessage "`n(OK) All quality checks passed! Your repository is clean and compliant."
    }
    else {
        Write-WarningMessage "`nQuality gate checks were skipped. Run without -SkipQualityGate to verify code quality."
    }
}
catch {
    Write-Host "Script failed: $_" -ForegroundColor Red
    exit 1
}

#endregion