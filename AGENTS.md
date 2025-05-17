You are absolutely right! I focused on the immediate operational guidelines for an AI agent in the AGENTS.MD and did not include the detailed project roadmap and future vision that was provided. My apologies for that oversight.

A verbose AGENTS.MD should indeed include such context if it helps the AI agent understand the project's trajectory and how current tasks fit into the larger picture.

I will now amend the AGENTS.MD to include this important information as a new section.

Here is the updated AGENTS.MD with the Project Roadmap section added:

Markdown

# AGENTS.MD – Rules & Playbook for Codex Agents (BALANCE-pyexcel · Updated May 2025)

This document provides comprehensive guidelines for AI agents (such as OpenAI Codex) and human collaborators on how to contribute to the `BALANCE-pyexcel` repository. Adherence to these rules is mandatory for all development tasks, including environment setup, coding standards, testing procedures, and commit conventions. If any rule herein conflicts with an explicit user prompt for a specific task, the user's prompt takes precedence for that instance only.

--------------------------------------------------------------------------------

## 0 · Quick Overview of the Project 📚

`BALANCE-pyexcel` is a personal-finance ETL (Extract, Transform, Load) tool. It's designed for individuals or partners who download financial statements (CSV, PDF) and require a unified, clean ledger for analysis, primarily within Excel and Power BI. The core concept is to simplify financial tracking: "Drag CSVs in → click Refresh → get a normalized Parquet file + live Excel workbook."

| Layer             | Path(s)                                               | Description                                                                    |
|-------------------|-------------------------------------------------------|--------------------------------------------------------------------------------|
| **ETL Core** | `src/balance_pipeline/`                             | Ingests CSV/PDF data, normalizes it, and writes to `balance_final.parquet`. Key modules include `csv_consolidator.py` for CSV processing and `cli.py` for orchestration. |
| **Excel Front-end** | `workbook/BALANCE-pyexcel.xlsm`                     | Utilizes Python in Excel via `=PY(etl_main(...))` to display processed data.   |
| **CLI** | `src/balance_pipeline/cli.py` (invoked as `balance refresh`) | Enables headless data refresh and merges Parquet data with Excel flags.        |
| **Rules** | `rules/schema_registry.yml`, `rules/merchant_lookup.csv` | Defines declarative schema mappings and rules for cleaning merchant names.     |
| **Tests** | `tests/` (includes unit & integration tests)          | Must execute quickly (target <15 seconds on typical laptop hardware) and remain green. |
| **CI** | `.github/workflows/ci.yml`                          | Automates checks using **ruff + mypy + pytest** across Python 3.10 & 3.11.     |

**Primary Outputs:**
* An Excel workbook (`BALANCE-pyexcel.xlsm`) with live transaction data and dashboard stubs.
* A Parquet file (`balance_final.parquet`) serving as the authoritative, analysis-ready dataset with columns like `TxnID`, `Owner`, `Date`, `Amount`, `SharedFlag`, etc.

**Workflow:** Python ETL handles schema mapping, data deduplication, and Parquet generation. Users in Excel perform final tagging (e.g., Shared/Personal). Power BI is used for visualizations.

--------------------------------------------------------------------------------

## 1 · Environment Setup 🛠️

The development sandbox container typically starts empty. The following steps MUST be executed in order to prepare the development environment:

```bash
# 1. Install Poetry-managed dependencies (including all runtime and development packages).
#    The sandbox is expected to have Poetry pre-installed.
poetry install --no-root --with dev

# 2. Activate pre-commit hooks for automated checks (e.g., Black, Ruff) before committing.
#    This applies to any new files created or existing files modified.
pre-commit install -t pre-commit -t commit-msg
Important Notes:

Avoid using global pip install ... unless a package is absolutely not manageable via Poetry.
If additional system libraries are required (e.g., poppler for PDF processing tests), they MUST be installed via the appropriate package manager (e.g., apt-get for Debian/Ubuntu, choco for Windows) within the sandbox before running tests or application code that depends on them.
2 · Commands That MUST Pass ✅
Before any Pull Request (PR) is created or any task is considered complete, all of the following commands MUST be executed and pass without errors. The agent should refuse to create a PR or mark a task as complete if any of these checks fail.

Purpose	Command	Notes
Static Linting	poetry run ruff check .	Must report zero errors. Warnings are permissible but should be reviewed.
Code Formatting	poetry run ruff format .	Ensures adherence to Black-compatible formatting (via ruff format).
Type Checking	poetry run mypy src/ --strict	Must pass with --strict mode enabled. No new Any types should be introduced without explicit justification.
Unit & Integration Tests	poetry run pytest -q	All tests must pass. Target execution time is under 15 seconds. For tests potentially exceeding 1 minute, use appropriate pytest markers.
Import Graph (Sanity Check)	poetry run snakeviz --version	This is a sanity check to ensure profiling tools like snakeviz can be imported, indicating a healthy environment for deeper performance analysis if needed.

Export to Sheets
Failure to meet these conditions requires the agent to abort the PR creation and report the failures.

3 · Commit, Push, and Pull Request (PR) Conventions 📝
All Git commits and pushes MUST follow this precise process:

Stage Changes: All modified and new files relevant to the task MUST be staged using:

Bash

git add .
Commit Message Formatting: Commit messages MUST adhere to the Conventional Commits specification. This is critical for changelog generation and versioning.

Header Format:
<type>(<scope>): <subject>
Example: fix(normalize): ensure TxnID remains stable across runs
Valid <type> tokens: feat (new feature), fix (bug fix), perf (performance improvement), refactor (code restructuring without behavior change), docs (documentation changes), ci (CI/CD changes), test (adding or correcting tests), chore (routine tasks, build process).
<scope> (optional): Indicates the section of the codebase affected (e.g., parser, cli, etl_core).
<subject>: A concise description of the change, written in the imperative mood (e.g., "add logging for X" not "added logging for X").
Body (Optional):
Provide a more detailed explanation of the changes. Explain the WHY, not just the WHAT.
Wrap lines at 72 characters.
Link to relevant issue numbers if applicable.
Breaking Changes (Optional):
If the commit introduces a breaking change, it MUST be indicated at the beginning of the footer or body, prefixed with BREAKING CHANGE:.
Example for schema/rule changes:
BREAKING CHANGE: Re-run `balance refresh` to regenerate Parquet files due to schema updates.
Create Commit: The conventionally formatted commit message (as described above) MUST be written to a temporary file (e.g., commit_message.txt). The commit is then created using:

Bash

git commit -F commit_message.txt
(Replace commit_message.txt with the actual temporary filename used).

Push Commit: After a successful commit, push the changes to the remote repository:

Bash

git push
4 · Coding Style & Conventions ✍️
Adherence to a consistent coding style is crucial for readability and maintainability.

Aspect	Rule
Formatting	Strictly follow Black formatting (line length = 88 characters). ruff format will enforce this.
Imports	Import order is enforced by ruff-isort. Use from pathlib import Path preferred over os.path.
Strings	Use f-strings for string interpolation. Prefer single quotes (') unless the string contains a single quote, in which case use double quotes (").
Logging	Use logging.getLogger(__name__) for module-specific loggers. Default logging level should be INFO or above. No bare print() calls are allowed.
Paths in Config	Centralize new path definitions in src/balance_pipeline/config.py. Expose them with environment variable fallbacks where appropriate.
DataFrame Ops	Prioritize vectorized operations for performance. Avoid using .apply() in performance-sensitive code paths (hot paths, typically >4ms execution time).
Type Hints	Mandatory for all new code. Use from __future__ import annotations at the beginning of Python files. Annotate all function signatures and variables where type clarity is beneficial.

Export to Sheets
Most of these style aspects are automatically enforced by Ruff and Black. Annotate any edge cases or complex logic with clear comments.

4.1 · File-Header & In-File Documentation Standard 📄
Every new source file (e.g., *.py, *.ts, *.jsx, .yml, but not typically test files unless very complex) MUST begin with an ASCII comment header block. This header is vital for understanding the file's role and history.

###############################################################################
# BALANCE-pyexcel – <Module / Component Name>
#
# Description : <A concise, one-sentence summary of the file’s purpose and
#                its primary responsibility within the application.>
# Key Concepts: <A bulleted list of essential domain-specific or algorithmic
#                concepts that this file implements. Examples:
#                - CSV schema mapping strategies
#                - Merchant name canonicalization using regex cache
#                - Idempotent transaction ID generation>
# Public API  : <List key functions, classes, or variables intended for import
#                and use by other modules. Specify if a class is a dataclass,
#                an enum, etc.
#                - `function_name(arg1: type) -> return_type`
#                - `ClassName.method_name()`>
# -----------------------------------------------------------------------------
# Change Log
# Date        Author            Type        Note
# YYYY-MM-DD  <Agent/Dev Name>  <feat|fix>  Initial creation of the module.
# YYYY-MM-DD  <Agent/Dev Name>  <type>      <Short, descriptive summary of the change made.>
# ... (add new entries at the top)
###############################################################################
Rules for File Headers and Documentation:

Header Presence: All new source files must include this ASCII header.
Type Column in Change Log: This MUST use Conventional Commit type tokens (e.g., feat, fix, refactor, perf, docs, test, chore).
Header Up-to-Date: The header, especially the "Change Log" section, MUST be kept current. Every Pull Request that modifies a file significantly (more than trivial typo fixes) must add a new entry to its "Change Log".
Width: Keep the header content within an 80-character width to ensure it renders clearly in side-by-side diff views and standard terminals.
Docstrings: Below the header, use Google-style docstrings for all public classes and functions. Docstrings should include:
A concise summary line.
A more detailed explanation if necessary.
Args: section detailing each parameter, its type, and description.
Returns: section detailing the return type and what is returned.
Raises: section detailing any exceptions that can be raised.
Internal Helpers: Functions or methods intended for internal use within the module should be prefixed with an underscore (e.g., _internal_helper()). These require at least a one-liner docstring explaining their purpose.
Generated Code: If a file contains auto-generated code, add the comment # AUTO-GENERATED – DO NOT EDIT MANUALLY prominently inside the ASCII header block. Codex MUST refuse to make manual edits to such files unless explicitly instructed to regenerate them.
Codex Action on Non-Compliance: Codex MUST refuse to commit a file if:

The ASCII header is missing from a new source file.
The "Change Log" entry for the current modification is absent or incomplete.
Lines within the ASCII header exceed the 80-character width limit.
Required docstrings are missing or inadequately detailed for public APIs.
4.2 · General Engineering Best-Practice Checklist ✔️
Before marking any task as complete or submitting a PR, Codex should verify the changes against these general engineering best practices:

Area	Guideline
Design	Adhere to SOLID principles (Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion) and DRY (Don't Repeat Yourself). Prefer composition over inheritance in new Python code unless inheritance offers a clear, compelling advantage.
Error Handling	Avoid bare except: blocks. Always catch specific exceptions (e.g., except ValueError:, except FileNotFoundError:). Handle exceptions gracefully and provide meaningful error messages or logging.
Logging	Implement structured logging for key events. Messages should be informative (e.g., "event='csv_ingest_successful' file_name='%s' rows_processed=%d"). Avoid logging sensitive PII.
Testing	Every bug fix MUST be accompanied by a regression test that fails without the fix and passes with it. Every new feature MUST include comprehensive unit tests and at least one integration test demonstrating its end-to-end functionality. Strive for high test coverage (target ≥ 90% lines for new modules).
Performance	Avoid O(n²) loops or highly inefficient operations, especially when dealing with DataFrame rows or large datasets. Profile and optimize critical code paths. Use vectorization with Pandas/NumPy where possible.
Security	Never commit real credentials, API keys, or other secrets directly into the source code or tests. Use environment variables, configuration files (ignored by Git), or secure vault solutions. Use placeholder strings (e.g., PLACEHOLDER_API_KEY) in tests and examples.
Accessibility (UI)	For any user interface code (even if not the primary focus of this project), ensure new elements include appropriate ARIA labels and are keyboard navigable to maintain accessibility standards.
Documentation	If public behavior, API contracts, or system architecture changes, update the relevant README files, module documentation, or architectural diagrams accordingly.

Export to Sheets
Codex Action on Non-Compliance: Codex agents should refuse to finalize a PR if any checklist item is clearly violated, unless the user explicitly overrides the guideline for a specific, justifiable reason.

5 · Testing Strategy & Shortcuts 🧪
Comprehensive testing is non-negotiable.

Location: Unit tests are located in the tests/ directory. Integration tests may also reside here, typically marked with @pytest.mark.integration.
Speed: Individual unit tests in tests/ should ideally complete in under 1 second each. The entire test suite (pytest -q) should aim to finish in under 15 seconds.
Fixtures: Utilize pytest fixtures, especially those defined in tests/conftest.py, for setting up test conditions, managing temporary resources (like tmp_path for file I/O), and stubbing external dependencies.
Test Placement: When adding new tests:
If an existing test file logically covers the module or functionality you're testing, add your new test cases to that file.
Otherwise, create a new test file named tests/test_<module_name>.py.
Coverage: New features or significant refactors require test coverage of ≥ 90% lines for the newly added or modified module(s). Use pytest --cov to measure coverage.
Mocking: Mock external resources (e.g., network requests via requests, direct file system I/O beyond tmp_path, database interactions) using pytest-mock (the mocker fixture).
Integration Tests: Integration tests, marked with @pytest.mark.integration, are allowed to be slower. They may be skipped in certain CI environments (e.g., Windows, if they test Linux-specific features) to speed up the build, but must pass in the primary CI environment.
6 · Cache Invalidation Rules 💾
Proper cache management is essential for data consistency.

Policy Cache: When policies are fetched or modified (identified by ONYXKEYS.COLLECTION.POLICY), the reportNameCache MUST be cleared to prevent stale LHN (Left-Hand Navigation) titles. Refer to ReportUtils for implementation details.
Report Name Logic: If you modify ReportUtils.getReportName or related logic that affects how report names are generated or cached, you MUST re-run (and ensure passes) the integration test tests/test_cli_sync_flow_with_parquet_and_queue.py to verify end-to-end consistency.
7 · Frequently-Used Helper Functions 🔗
To maintain consistency and avoid code duplication, reuse these existing helper functions where appropriate. Codex should prioritize using these helpers over reimplementing similar logic.

Need / Purpose	How to Call / Function Location
Load YAML configuration safely	`yaml.safe_load(Path(path_to_yaml_file).read_text('utf-8'))`
Process list of CSV files into a consolidated, normalized DataFrame	`balance_pipeline.csv_consolidator.process_csv_files(csv_paths: list, schema_registry_path: Path, merchant_lookup_path: Path)` (Main ETL entry for CSVs)
Generate a unique Transaction ID (TxnID)	Logic is internal to `csv_consolidator.py` (based on `normalize._hash_txn` principles).
Clean/Canonicalize merchant description	`balance_pipeline.normalize.clean_merchant(description_string)` (Used as a fallback by `csv_consolidator.py` after checking `merchant_lookup.csv`)

Export to Sheets
(This list may be expanded. Check relevant utility modules before implementing common tasks.)

8 · CI Specifics 🚦
The Continuous Integration (CI) pipeline is managed via GitHub Actions.

Workflow File: .github/workflows/ci.yml
Python Versions: The CI pipeline runs tests and linters across a matrix of Python versions, typically Python 3.10 and 3.11. Support for Python 3.12 will be added once all core dependencies have stable wheels.
Cache Keys: Poetry dependencies are cached using a key structure like: poetry-cache-${{ runner.os }}-${{ hashFiles('poetry.lock') }}.
Job Parallelization: Linting, type-checking, and testing jobs generally run in parallel to speed up feedback.
Deployment: Deployment (if configured) typically only occurs from the main branch after all checks pass.
9 · Prohibited Actions & Safety Footnotes 🚫🔒
To maintain system integrity, data security, and code quality, the following actions are strictly prohibited:

No Direct Writes to balance_final.parquet: The balance_final.parquet file is the source of truth and should only be written by the main ETL process (etl_main). Do not write to it directly from other parts of the application or tests, except through designated ETL pipeline functions.
No Secrets in Repository: Never commit real credentials, API keys, passwords, or any personally identifiable information (PII) into the source code, configuration files, or tests.
Use environment variables for sensitive data.
Use placeholder strings like PLACEHOLDER_SECRET or TEST_API_KEY in tests and example configurations.
No print() Calls: All diagnostic output and application messages MUST use the logging module. Bare print() statements are forbidden in the application codebase.
No Mutation of Input CSVs: During ingest tests or processing, the original input CSV files MUST NOT be modified. Treat input data as immutable. If transformations are needed, create copies or process data in memory.
Temporary Files: If you need to generate temporary files during tests or runtime, use the tmp_path fixture provided by pytest for tests, or standard library modules like tempfile for application code, ensuring they are properly cleaned up.
10 · How to Run the Full Manual Pipeline 🖥️
To execute the full ETL pipeline manually from the command line (e.g., for end-to-end testing or a manual data refresh):

Bash

poetry run balance refresh \
  --csv-inbox  /path/to/your/CSVs/folder \
  --workbook   /path/to/your/BALANCE-pyexcel.xlsm
Replace /path/to/your/CSVs/folder with the actual path to the directory containing your input CSV files (organized into owner-named subfolders if applicable).
Replace /path/to/your/BALANCE-pyexcel.xlsm with the actual path to your Excel workbook.
A successful run should conclude with a log message similar to: “Successfully wrote … balance_final.parquet”.

11 · Contact / Escalation 📣
If you encounter ambiguities in tasks, require clarification on these guidelines, or need to discuss design decisions:

Primary Channel (Slack): #balance-dev (mention @ryan.z or @jordyn for urgent queries).
Secondary Channel (GitHub Issues): For bugs, feature requests, or detailed technical discussions, create an issue in the project's GitHub repository. Please prefix issue titles appropriately, e.g., [Bug], [Feature], [Refactor], [Question].
12 · Project Roadmap & Future Vision 🗺️
This section outlines the decomposed roadmap for BALANCE-pyexcel, detailing its progression from initial stages to a production-ready v1.0 and beyond. Understanding this roadmap helps contextualize current development efforts.

Stage 0 · Bootstrap (✅ DONE)
Item	Detail
Repo init	Poetry project, Ruff + Black, GitHub Actions skeleton, Excel .xlsm template.
MVP ETL	Hard-coded ingest of single bank CSV → DataFrame → Excel spill.
Output file	balance_final.parquet first created.
Acceptance	Manual run writes Parquet & displays in Excel.

Export to Sheets
Stage 1 · Config-driven ETL (✅ DONE & Enhanced)
Item	Detail
1.1 Schema Registry	`rules/schema_registry.yml` defines comprehensive CSV parsing rules: `id`, `match_filename`, `header_signature`, `column_map`, `sign_rule` (supporting simple string rules and complex `type: flip_if_column_value_matches`), `date_format`, `derived_columns` (supporting `static_value`, `from_column`, `regex_extract`, `concatenate`), `amount_regex`, `extra_static_cols`. `rules/merchant_lookup.csv` for merchant cleaning.
1.2 CSV Processing Engine	`src/balance_pipeline/csv_consolidator.py::process_csv_files()` is the core engine. It takes a list of CSV paths, loads schema and merchant rules. For each CSV: matches schema, applies all transformations (column mapping, date parsing, amount standardization, derived columns, extras), infers Owner & DataSourceDate, performs merchant cleaning, generates TxnID, and ensures master schema conformance including data types (with robust boolean parsing).
1.3 Deduplication & Orchestration	`src/balance_pipeline/cli.py::etl_main()` scans for CSV files (respecting include/exclude patterns), calls `process_csv_files`, then performs deduplication of transactions based on `TxnID` and `prefer_source` logic.
1.4 CLI + Excel hook	`balance refresh` command (`cli.py`) orchestrates the full ETL. `etl_main()` remains callable from Python-in-Excel (`=PY(...)`).
Deliverables	- `docs/architecture.md` updated with new flow.<br>- Unit tests for `csv_consolidator.py` covering multiple sample CSVs (`tests/test_csv_consolidator.py`).<br>- CI: Ruff + PyTest on Python 3.11 (and 3.10).
Exit criteria	- `pytest -q` → 0 failures.<br>- Sample run logs “Successfully wrote balance_final.parquet”.<br>- Key features like derived columns, complex sign rules, and boolean parsing are functional.

Export to Sheets
Stage 2 · User-friendly data & sync (✅ DONE)
Item	Detail
2.0 Merchant lookup CSV	rules/merchant_lookup.csv loaded on-demand; fallback to _clean_desc.title().
2.1 Two-way classification sync	Excel Queue_Review sheet → CLI merges SharedFlag/SplitPercent back into Parquet.
2.2 Docs + tests	- power_bi_workflow.md (Parquet via DuckDB ODBC)<br>- Tests for merchant rules, sync merge<br>- CI badge in README
2.3 Patch 2.1 (perf & resilience)	- Selective Parquet read (TxnID, SharedFlag, SplitPercent)<br>- Retry loop on to_parquet w/ exponential back-off.

Export to Sheets
Stage 3 · Polish & Dev-Experience (🚧 In Progress)
(Current development focus is likely within this stage or transitioning from it)

Sub-task	Detail	Acceptance
3.1 Merchant-rule CLI helper	balance merchant add "<regex>" "<canonical>". Validates regex, refuses commas, appends row, clears cache.	tests/test_merchant_cli.py green
3.2 CI matrix	GitHub Actions on 3.10 & 3.11; pin ruff==0.4.*.	Workflow passes on both versions
3.3 ASCII file headers	Enforce header + change-log via pre-commit hook; documented in AGENTS.MD.	Ruff custom rule / pre-commit fails on missing header
3.4 Docs touch-ups	Screenshots placeholders in Power BI doc, README quick-start inc. new CLI.	Docs build passes markdown-lint

Export to Sheets
Stage 4 · Intelligent Ledger (🟡 Planned)
Item	Detail
4.1 Rule-based auto-classification	classify.py loads YAML/JSON rules (pattern → SharedFlag/SplitPercent, Category). Confidence score column for ML fallback.
4.2 Balance calculation engine	calculate.py computes owed/owing per person, running balance graph, split reimbursements.
4.3 Incremental ingest	Track last processed file hash / modified-time → skip unchanged. Optional --since YYYY-MM-DD to re-process delta.
4.4 Tests + visual smoke	Golden dataset in tests/data/golden.parquet → expected balances. Power BI template (.pbit) checked into /templates.
Exit criteria	- balance refresh --dry-run finishes < 5 s on 10k-txn sample<br>- pytest coverage ≥ 90 %<br>- Power BI template refreshes without user edits

Export to Sheets
Stage 5 · UX & Release hardening (🟢 Future)
Item	Detail
5.1 Installer / Packaging	PyInstaller one-file exe for non-Python users. Excel workbook updated by exe, not Poetry.
5.2 Performance hardening	Profile with 200k rows → vectorise any stragglers. Memory peak ≤ 500 MB.
5.3 Power BI Service deployment	Azure Function / GitHub Action nightly runs balance refresh, commits Parquet to Blob → PBIX dataset auto-refresh.
5.4 End-user docs & video	Step-by-step GIF / Loom. FAQ on schema troubleshooting.
5.5 Version 1.0 tag & changelog	SemVer tag, release notes, brew/scoop/winget manifest.

Export to Sheets
Future Ideas (Backlog)
OCR PDF ingestion with Tesseract for image-only statements.
Mobile app to snap receipts, auto-tag personal vs shared.
ML model to predict Shared vs Personal with feedback loop.
Multi-currency support with daily FX rates.
Visual Timeline (Indicative - as of May 2025)
S0  S1    S2     Patch2.1   S3 (current)   S4           S5
│───│─────│──────│──────────│──────────────│────────────│────────▶
... Apr   May    May-wk3    Jun   Jul-Aug    Sep-Oct      Nov-Dec
(Note: "You’re currently between the Patch 2.1 arrow and the S3 bar" indicates project status at the time this roadmap was formulated.)

Acceptance Checklist Before v1.0 Release
All CI jobs green on Python 3.10, 3.11, (and eventually 3.12).
“Getting Started” documentation enables a user to install & refresh on a clean Windows machine in < 15 minutes.
Power BI template publishes to Power BI Service and successfully refreshes via an Azure Function or similar automated mechanism.
Manual regression test: delete cache, refresh data, verify that room names (or equivalent critical dynamic data) update correctly (addresses historical bugs like Stage 2 bug).
Thorough security review completed: no secrets committed to the repository, logging is scrubbed of PII.
License headers and ASCII comment blocks (as defined in this AGENTS.MD) are present on every source file.
Achieving all items on this checklist is a prerequisite for tagging v1.0.0.

Happy coding — strive for clarity, robustness, and ensure every test passes!

End of AGENTS.MD
