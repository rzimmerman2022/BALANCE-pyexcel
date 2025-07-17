```
###############################################################################
# BALANCE-pyexcel – AGENTS.MD (Rules & Playbook)
#
# Description : Development handbook for both human contributors and AI agents
#               working on BALANCE‑pyexcel. Covers environment setup, CI gates,
#               coding standards, commit conventions, and the forward roadmap.
# Key Concepts: - Poetry + Ruff + mypy + pytest strict CI pipeline
#               - Conventional Commits & ASCII file‑header enforcement
#               - UnifiedPipeline awareness & legacy‑compat layer
#               - Container‑agnostic setup script pattern (Codex compliant)
# Public API  : *Documentation file – no executable API*
# -----------------------------------------------------------------------------
# Change Log
# 2025‑06‑08  OpenAI o3       docs       Initial full rewrite with ASCII header,
#                                        strict CI rules, roadmap, env‑var notes.
###############################################################################
```

# AGENTS.MD – Rules & Playbook for Codex Agents

*(BALANCE‑pyexcel · last updated **2025‑06‑08**)*

> **Mission** — keep every contribution **type‑safe**, **well‑tested**, and **green on CI** while steering toward v1.0.

---

## 0 · Quick Project Overview 📚

`BALANCE‑pyexcel` converts messy CSV/PDF bank data into a normalised Parquet ledger and Excel workbook.

| Layer                | Path(s)                         | Role                                  |
| -------------------- | ------------------------------- | ------------------------------------- |
| **Unified ETL Core** | `src/balance_pipeline/`         | Ingest → normalise → dedupe → output. |
| **Excel UI**         | `workbook/BALANCE-pyexcel.xlsm` | Displays data via `=PY(etl_main())`.  |
| **CLI (new)**        | `src/balance_pipeline/main.py`  | `balance-pipe process …`              |
| **CLI (legacy)**     | `src/balance_pipeline/cli.py`   | `balance refresh` (wrapper)           |
| **Rules**            | `rules/schema_registry.yml`     | Declarative schema mapping.           |
| **CI**               | `.github/workflows/ci.yml`      | Ruff + mypy + pytest matrix.          |

Outputs → **Parquet** (`balance_final.parquet`) & **Excel workbook**.

---

## 1 · Environment Setup 🛠️

```bash
poetry install --no-root --with dev       # deps
pre-commit install -t pre-commit -t commit-msg
```

System libs (poppler, etc.) via apt/choco/brew inside the container.

---

## 2 · Mandatory Local Gates ✅

| Check  | Command                         | Pass/fail criteria |
| ------ | ------------------------------- | ------------------ |
| Lint   | `poetry run ruff check .`       | **0** errors       |
| Format | `poetry run ruff format .`      | no diff afterwards |
| Types  | `poetry run mypy src/ --strict` | 0 errors           |
| Tests  | `poetry run pytest -q`          | all green < 15 s   |
| Sanity | `poetry run snakeviz --version` | returns version    |

If any fails → **no PR**.

---

## 3 · Commit & PR Conventions 📝

* Stage → `git add .`
* Commit msg → `feat(pipeline): add flexible schema mode`
* Types: feat / fix / perf / refactor / docs / ci / test / chore
* Breaking? → add `BREAKING CHANGE:` paragraph.

---

## 4 · Coding Standards ✍️

* Black via `ruff format` (line 88)
* `from __future__ import annotations`; full type hints
* No bare `print()`; use `logging`
* All new files get the ASCII header block (80‑char width)

---

## 5 · Testing Strategy 🧪

* Unit tests < 1 s each; suite < 15 s.
* Coverage ≥ 90 % for changed modules.
* Integration tests may be slower; mark with `@pytest.mark.integration`.

---

## 6 · Cache Rules 💾

* Policy changes → clear `reportNameCache`.
* Modifying `ReportUtils.getReportName` → re‑run sync integration test.

---

## 7 · Helper Cheat‑Sheet 🔗

| Need             | Helper                                       |
| ---------------- | -------------------------------------------- |
| Load YAML        | `yaml.safe_load(Path(p).read_text('utf‑8'))` |
| Consolidate CSVs | `csv_consolidator.process_csv_files(...)`    |
| TxnID            | internal hash in `csv_consolidator`          |
| Merchant clean   | `normalize.clean_merchant(desc)`             |

---

## 8 · CI Details 🚦

* Matrix: Python 3.10 & 3.11 (3.12 pending).
* Poetry deps cached via `hashFiles('poetry.lock')`.

---

## 9 · Prohibited Actions 🚫

* No direct writes to `balance_final.parquet` outside ETL.
* No secrets/PII in repo.
* CSV inputs are immutable in tests.

---

## 10 · Manual Pipeline Invocation 🖥️

```bash
poetry run balance-pipe process "csv_inbox/**.csv" \
    --output-type powerbi \
    --output-path output/manual.parquet
```

Legacy wrapper still exists but is deprecated.

---

## 11 · Contact / Escalation 📣

* Slack `#balance-dev` → **@ryan.z** / **@jordyn**
* GitHub Issues → tag `[Bug]`, `[Feature]`, etc.

---

## 12 · Roadmap 🗺️

| Stage                     | Status | Key items                               |
| ------------------------- | ------ | --------------------------------------- |
| **S0 Bootstrap**          | ✅      | Repo, CI, first Parquet                 |
| **S1 Config ETL**         | ✅      | YAML registry, dedupe                   |
| **S2 Sync UX**            | ✅      | Merchant lookup, two‑way Excel sync     |
| **Patch 2.1**             | ✅      | Perf & resilience tweaks                |
| **S3 Polish & DX**        | 🚧     | Header enforcement, merchant CLI helper |
| **S4 Intelligent Ledger** | 🟡     | Rule‑based classifier, balance engine   |
| **S5 UX & Release**       | 🟢     | One‑file installer, PB Service refresh  |

*Backlog*: OCR PDF, mobile receipt snap, ML shared/personal, multi‑currency.

---

## v1.0 Acceptance Checklist 🎯

* CI green on 3.10/3.11/3.12
* Windows fresh install → docs run < 15 min
* Power BI template auto‑refresh via Azure Function
* Security audit OK, no secrets
* Every source file carries up‑to‑date ASCII header

---

Happy coding — keep it **strict‑typed**, **well‑tested**, and 🌱 **green on CI**!
