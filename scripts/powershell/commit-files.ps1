commit-files.ps1################################################################################
# Universal Git Commit Workflow Script
# 
# This flexible script can be used to commit any file(s) to your repository
# with proper verification and best practices.
#
# Usage: .\commit-files.ps1 -Files "filename1,filename2" -Message "Your message"
# Or run without parameters for interactive mode
################################################################################

param(
    [string]$Files = "",
    [string]$Message = "",
    [switch]$QuickMode = $false,
    [switch]$SkipDiff = $false
)

# Function to display section headers nicely
function Write-Section {
    param([string]$Title)
    Write-Host "`n=== $Title ===" -ForegroundColor Cyan
}

# If no files specified, ask the user
if ($Files -eq "") {
    Write-Section "File Selection"
    Write-Host "Current modified files:" -ForegroundColor Yellow
    git status --short
    
    $Files = Read-Host "`nEnter file(s) to commit (comma-separated, or '.' for all)"
}

# Convert comma-separated list to array
$FileList = if ($Files -eq ".") { @(".") } else { $Files -Split "," | ForEach-Object { $_.Trim() } }

Write-Section "Repository Status Check"
git status

# Review changes for each file (unless in quick mode)
if (-not $SkipDiff -and -not $QuickMode) {
    foreach ($file in $FileList) {
        if ($file -ne ".") {
            Write-Section "Reviewing changes to: $file"
            git diff $file
            
            Write-Host "`nPress Enter to continue or Ctrl+C to abort..." -ForegroundColor Yellow
            Read-Host
        }
    }
}

# Stage the files
Write-Section "Staging Files"
foreach ($file in $FileList) {
    Write-Host "Staging: $file" -ForegroundColor Green
    git add $file
}

# Verify what's been staged
Write-Section "Verification of Staged Changes"
git status

# Create commit message
Write-Section "Commit Message Creation"

if ($Message -eq "") {
    if ($QuickMode) {
        # In quick mode, use a simple prompt
        $Message = Read-Host "Enter commit message"
    } else {
        # In interactive mode, help build a good commit message
        Write-Host "Let's build a comprehensive commit message!" -ForegroundColor Green
        Write-Host "Follow the prompts to create a well-structured message.`n" -ForegroundColor Yellow
        
        $summary = Read-Host "Brief summary (50 chars or less)"
        
        Write-Host "`nNow, let's add details. Press Enter twice when done." -ForegroundColor Yellow
        Write-Host "What changed:" -ForegroundColor Cyan
        $whatChanged = @()
        while ($true) {
            $line = Read-Host "- "
            if ($line -eq "") { break }
            $whatChanged += "- $line"
        }
        
        Write-Host "`nWhy these changes matter:" -ForegroundColor Cyan
        $whyChanged = @()
        while ($true) {
            $line = Read-Host "- "
            if ($line -eq "") { break }
            $whyChanged += "- $line"
        }
        
        $breakingChanges = Read-Host "`nAny breaking changes? (leave empty if none)"
        $ticketRef = Read-Host "Ticket/Issue reference? (leave empty if none)"
        
        # Build the complete message
        $Message = @"
$summary

What changed:
$($whatChanged -join "`n")

Why these changes matter:
$($whyChanged -join "`n")
"@
        
        if ($breakingChanges -ne "") {
            $Message += "`n`nBREAKING CHANGES: $breakingChanges"
        }
        
        if ($ticketRef -ne "") {
            $Message += "`n`nRefs: $ticketRef"
        }
    }
}

# Commit with the message
Write-Host "`nCreating commit..." -ForegroundColor Green
git commit -m $Message

# Verify the commit
Write-Section "Commit Verification"
git log -1 --stat

# Check if we need to push
Write-Section "Remote Status Check"
git fetch origin
$status = git status -uno
if ($status -match "Your branch is ahead") {
    Write-Host "Ready to push changes!" -ForegroundColor Green
    
    if ($QuickMode) {
        git push
    } else {
        $pushConfirm = Read-Host "`nPush to remote? (y/n)"
        if ($pushConfirm -eq 'y') {
            git push
            
            Write-Section "Push Verification"
            git log origin/$(git branch --show-current) -1 --oneline
        }
    }
} elseif ($status -match "Your branch is behind") {
    Write-Host "Warning: Remote has changes you don't have locally!" -ForegroundColor Yellow
    Write-Host "Run 'git pull' first to avoid conflicts." -ForegroundColor Yellow
}

Write-Section "Final Status"
git status

Write-Host "`n✅ Workflow complete!" -ForegroundColor Green

# Usage examples
if (-not $QuickMode -and -not $Files) {
    Write-Host "`nPro tip: You can run this script in different ways:" -ForegroundColor Magenta
    Write-Host "  .\commit-files.ps1 -Files 'file1.py,file2.py' -Message 'Fix calculation bug'" -ForegroundColor DarkGray
    Write-Host "  .\commit-files.ps1 -QuickMode  # For faster commits" -ForegroundColor DarkGray
    Write-Host "  .\commit-files.ps1 -SkipDiff   # Skip the diff review" -ForegroundColor DarkGray
}