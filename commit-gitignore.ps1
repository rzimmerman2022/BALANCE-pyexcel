################################################################################
# Git Workflow: Committing and Pushing the Updated .gitignore File
# 
# This script demonstrates best practices for committing configuration changes
# to your repository. Each command is explained to help you understand the
# Git workflow and why each step matters.
################################################################################

# Step 1: Check Current Repository Status
# ========================================
# Always start by understanding what's changed in your repository.
# This command shows you which files are modified, staged, or untracked.

Write-Host "Checking repository status..." -ForegroundColor Cyan
git status

# Expected output:
# - You should see .gitignore listed as "modified" (if it existed before)
# - Or as "untracked" (if it's a new file)
# - This helps confirm you're committing the right changes

# Step 2: Review the Changes (Optional but Recommended)
# =====================================================
# Before staging, it's good practice to review what exactly changed.
# This prevents accidentally committing unwanted modifications.

Write-Host "`nReviewing changes to .gitignore..." -ForegroundColor Cyan
git diff .gitignore

# This shows:
# - Lines removed (in red with -)
# - Lines added (in green with +)
# - Press 'q' to exit the diff viewer

# Step 3: Stage the .gitignore File
# ==================================
# Staging tells Git which changes you want to include in your next commit.
# Think of it as preparing your changes for packaging.

Write-Host "`nStaging .gitignore for commit..." -ForegroundColor Green
git add .gitignore

# Alternative commands:
# - `git add -p .gitignore` - Interactive staging (choose specific changes)
# - `git add .` - Stage ALL changes (use cautiously)

# Step 4: Verify Staging
# ======================
# Always verify what you've staged before committing.
# This prevents accidental commits of unwanted files.

Write-Host "`nVerifying staged changes..." -ForegroundColor Cyan
git status

# You should now see .gitignore under "Changes to be committed" in green

# Step 5: Create a Detailed Commit
# =================================
# Good commit messages are crucial for project history and collaboration.
# They should explain WHAT changed and WHY.

Write-Host "`nCreating commit with detailed message..." -ForegroundColor Green

# Option A: Single-line commit (for simple changes)
# git commit -m "Update .gitignore with comprehensive patterns and documentation"

# Option B: Multi-line commit with detailed description (RECOMMENDED)
# This opens your default editor for a more detailed message
git commit -v

# If you prefer to do it all in PowerShell without opening an editor:
$commitMessage = @"
Update .gitignore with best practices and comprehensive patterns

WHAT Changed:
- Added ASCII header with project branding
- Implemented changelog section for tracking modifications
- Reorganized file into logical sections with clear headers
- Enhanced Python-specific ignore patterns (cache, testing, packaging)
- Expanded Excel temporary file patterns (~$*.xls*)
- Added comprehensive IDE support (VS Code, PyCharm, Vim, Emacs)
- Included OS-specific files for Windows, macOS, and Linux
- Added security section for sensitive files (*.key, *.pem, secrets.*)
- Created BALANCE-pyexcel specific section with critical workbook ignores

WHY These Changes Matter:
- Prevents accidental commits of the live BALANCE-pyexcel.xlsm workbook
- Ensures template folder remains in version control (!workbook/template/**)
- Protects sensitive data and credentials from being exposed
- Reduces repository clutter from temporary and cache files
- Improves developer experience across different environments
- Makes the .gitignore self-documenting for team members

BREAKING Changes: None
MIGRATION: No action needed - changes take effect immediately

Refs: #[ticket-number] (if applicable)
"@

# Execute the commit with the detailed message
git commit -m $commitMessage

# Step 6: Verify the Commit
# =========================
# Check that your commit was created successfully with the right information.

Write-Host "`nVerifying commit was created..." -ForegroundColor Cyan
git log -1 --stat

# This shows:
# - The commit hash (unique identifier)
# - Author and date
# - Commit message
# - Files changed with statistics

# Step 7: Check Remote Repository Status
# ======================================
# Before pushing, see if there are any upstream changes you need to pull.

Write-Host "`nChecking remote repository status..." -ForegroundColor Cyan
git fetch origin
git status

# If Git says "Your branch is ahead of 'origin/main' by 1 commit" - you're ready to push
# If it says "Your branch is behind" - you need to pull first

# Step 8: Push to Remote Repository
# ==================================
# Send your local commits to the remote repository (GitHub, GitLab, etc.)

Write-Host "`nPushing changes to remote repository..." -ForegroundColor Green

# Standard push to the current branch
git push

# Alternative push commands:
# - `git push origin main` - Explicitly specify remote and branch
# - `git push -u origin main` - Set upstream tracking (first push to new branch)
# - `git push --force` - DANGEROUS: Overwrites remote history (avoid unless necessary)

# Step 9: Verify Push Success
# ============================
# Confirm your changes are now on the remote repository.

Write-Host "`nVerifying push success..." -ForegroundColor Cyan
git log origin/main -1 --oneline

# This shows the latest commit on the remote branch
# It should match your local commit

# Step 10: Final Status Check
# ============================
# Ensure your local repository is clean and in sync.

Write-Host "`nFinal repository status check..." -ForegroundColor Green
git status

# Should show: "Your branch is up to date with 'origin/main'"
# and "nothing to commit, working tree clean"

################################################################################
# Troubleshooting Common Issues
################################################################################

# If you encounter merge conflicts:
# 1. Pull the latest changes: git pull origin main
# 2. Resolve conflicts in your editor
# 3. Stage resolved files: git add .gitignore
# 4. Complete the merge: git commit
# 5. Push the merged changes: git push

# If you need to undo the commit (before pushing):
# - Undo commit but keep changes: git reset --soft HEAD~1
# - Undo commit and changes: git reset --hard HEAD~1

# If you already pushed and need to undo:
# - Create a new commit that reverses changes: git revert HEAD
# - Then push the revert commit: git push

Write-Host "`n✅ Git workflow complete!" -ForegroundColor Green
Write-Host "Your .gitignore updates are now in the repository." -ForegroundColor Yellow

################################################################################
# Best Practices Reminder
################################################################################
# 1. Always review changes before committing (git diff)
# 2. Write meaningful commit messages that explain WHY, not just WHAT
# 3. Commit related changes together, but keep commits focused
# 4. Pull before pushing to avoid conflicts
# 5. Never force push to shared branches without team coordination
################################################################################