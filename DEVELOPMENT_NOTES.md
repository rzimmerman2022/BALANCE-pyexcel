# Development Notes for BALANCE-pyexcel

This document provides guidance for developers (including AI assistants) working on the BALANCE-pyexcel project within this specific environment.

## Project Structure & Working Directory

*   **Repository Root (CWD):** `c:/BALANCE/BALANCE-pyexcel-repository`
*   **Main Python Project:** `BALANCE-pyexcel` (subdirectory within the repository root)
*   **Git Repository:** Located within the `BALANCE-pyexcel` subdirectory (`c:/BALANCE/BALANCE-pyexcel-repository/BALANCE-pyexcel/.git`)

## Important Command Patterns

Due to the current working directory being the repository root (`c:/BALANCE/BALANCE-pyexcel-repository`) and the project/git repo being in the `BALANCE-pyexcel` subdirectory, **you MUST use the `-C BALANCE-pyexcel` flag** for most `git` and `poetry` commands to target the correct directory.

**Shell Environment:** Windows (`cmd.exe`) - Avoid using `&&` for command chaining as it may not work reliably. Use separate commands or the `-C` flag.

### Poetry Commands

*   **Install/Update:** `poetry -C BALANCE-pyexcel install`
*   **Run Tests:** `poetry -C BALANCE-pyexcel run pytest`
*   **Run CLI:** `poetry -C BALANCE-pyexcel run balance-pyexcel [ARGS...]`
*   **Add Dependency:** `poetry -C BALANCE-pyexcel add [PACKAGE_NAME]`
*   **Remove Dependency:** `poetry -C BALANCE-pyexcel remove [PACKAGE_NAME]`
*   **Update Lockfile:** `poetry -C BALANCE-pyexcel lock --no-cache`

### Git Commands

*   **Check Status:** `git -C BALANCE-pyexcel status`
*   **Stage Changes:** `git -C BALANCE-pyexcel add .` or `git -C BALANCE-pyexcel add [FILE_PATH]`
*   **Commit Changes:** `git -C BALANCE-pyexcel commit -m "Your detailed commit message"`
*   **Push Changes:** `git -C BALANCE-pyexcel push origin [BRANCH_NAME]`
*   **Push Specific Local Branch to Specific Remote Branch:** `git -C BALANCE-pyexcel push origin [LOCAL_BRANCH]:[REMOTE_BRANCH]`
*   **Force Push:** `git -C BALANCE-pyexcel push --force origin [LOCAL_BRANCH]:[REMOTE_BRANCH]` (Use with caution!)

By consistently using the `-C BALANCE-pyexcel` flag, you ensure commands operate correctly within the project's context.
