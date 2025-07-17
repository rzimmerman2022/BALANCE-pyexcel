# Development Notes

Guidance for anyone (humans *or* AI assistants) hacking on **BALANCE-pyexcel** in this repo layout.

---

## 1  Repository layout

| Path | Purpose |
|------|---------|
| `c:/BALANCE/BALANCE-pyexcel-repository` | **Repo root** – your default CWD in VS Code. |
| `BALANCE-pyexcel/` | Actual Python project & **Git repo** (`.git` lives here). |

Because your shell opens at the repo root while the Git project is *one level down*, you must prefix most `git` and `poetry` commands with:

```bash
-C BALANCE-pyexcel
This tells the tool, “run as if my CWD = BALANCE-pyexcel/”.

2 Shell notes
Environment: Windows / cmd.exe (inside VS Code).

Command chaining: Avoid && in cmd; run commands on separate lines.

3 Poetry cheat-sheet
Task	Command
Install / update deps	poetry -C BALANCE-pyexcel install
Run tests	poetry -C BALANCE-pyexcel run pytest
Run the CLI	poetry -C BALANCE-pyexcel run balance-pyexcel [args]
Add a dep	poetry -C BALANCE-pyexcel add <package>
Remove a dep	poetry -C BALANCE-pyexcel remove <package>
Refresh lockfile	poetry -C BALANCE-pyexcel lock --no-cache

Tip: In VS Code’s Run Task palette you can create shortcuts that already include the -C flag.

4 Git cheat-sheet
Task	Command
Status	git -C BALANCE-pyexcel status
Stage all	git -C BALANCE-pyexcel add .
Commit	git -C BALANCE-pyexcel commit -m "feat: message"
Push (current tracking)	git -C BALANCE-pyexcel push
Push to a specific branch	git -C BALANCE-pyexcel push origin <branch>
Force-push (use sparingly)	git -C BALANCE-pyexcel push --force origin <branch>

Stay consistent with the -C BALANCE-pyexcel prefix and you’ll never accidentally commit to the wrong repo or run Poetry in the wrong environment. Happy coding!

markdown
Copy
Edit

**Next steps**

1. Save as `docs/development_notes.md` (or `DEVELOPMENT_NOTES.md` at the repo root).  
2. Optionally add it to *mkdocs.yml* under **Developer Guide**:

```yaml
  - Developer Guide:
      - Environment Setup: developer_setup.md
      - Development Notes: development_notes.md
      - CLI Usage: cli_usage.md
      - Sync Review Sheet: sync_review.md