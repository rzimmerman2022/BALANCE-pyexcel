# BALANCE-pyexcel

[![Python CI](https://github.com/your-github-org-or-username/BALANCE-pyexcel/actions/workflows/ci.yml/badge.svg)](https://github.com/your-github-org-or-username/BALANCE-pyexcel/actions/workflows/ci.yml)

**A professional Excel-based shared-expense tracker powered by Python, with schema-driven CSV ingestion and a unified ETL pipeline.**

---

## Table of Contents

1. [Overview](#overview)
2. [Project Structure](#project-structure)
3. [Quick Start](#quick-start)
4. [Running the Pipeline](#running-the-pipeline)
5. [Scripts Organization](#scripts-organization)
6. [Configuration](#configuration)
7. [Development](#development)
8. [Contributing](#contributing)

---

## Overview

BALANCE-pyexcel lets parties manage shared finances in a familiar Excel environment. Python processes diverse bank/card CSV formats, normalizes them, and produces clean transaction ledgers for classification and balance calculation.

**Key Features:**
- Schema-driven CSV ingestion via `rules/schema_registry.yml`
- Automatic owner tagging (folder-name → `Owner` column)
- Data normalization & sign correction
- Stable `TxnID` generation (SHA-256)
- Excel review queue based on `FILTER`
- Comprehensive analysis and reporting tools

---

## Project Structure

```text
BALANCE-pyexcel/
├── 📁 config/                  # Configuration files (YAML, JSON)
├── 📁 data/                    # Data files and archives
│   ├── 📁 _archive/           # Historical and corrected data files
│   └── 📁 _samples/           # Sample data for testing
├── 📁 docs/                    # Documentation files
│   ├── ARCHITECTURE.md        # System architecture documentation
│   ├── CHANGELOG.md           # Version history
│   ├── quick_start.md         # Getting started guide
│   └── …
├── 📁 reports/                 # Generated reports and summaries
├── 📁 rules/                   # Schema registry & merchant lookup
├── 📁 scripts/                 # Utility and analysis scripts
│   ├── 📁 analysis/           # Data analysis scripts
│   ├── 📁 corrections/        # Data correction utilities
│   ├── 📁 investigations/     # Issue investigation tools
│   └── 📁 utilities/          # General utility scripts
├── 📁 src/                     # Main source code
│   ├── 📁 balance_pipeline/   # Core pipeline implementation
│   │   ├── pipeline_v2.py     # UnifiedPipeline orchestrator
│   │   ├── main.py            # CLI entry point (balance-pipe)
│   │   └── …
│   ├── 📁 baseline_analyzer/  # Balance analysis tools
│   └── 📁 utils/              # Shared utilities
├── 📁 tests/                   # Test suite
├── 📁 tools/                   # Development and debugging tools
├── 📁 workbook/                # Excel templates and outputs
│   └── template/              # Excel template files
├── pyproject.toml             # Python project configuration
└── README.md                  # This file
```

---

## Quick Start

```bash
# 1. Clone and enter
git clone <repo_url>
cd BALANCE-pyexcel

# 2. Install dependencies
poetry install --no-root --with dev

# 3. Create external CSV inbox
mkdir -p csv_inbox/Ryan csv_inbox/Jordyn

# 4. Run pipeline
poetry run balance-pipe process "csv_inbox/**.csv" --output-type powerbi
```

On success you'll see `output/unified_pipeline/<timestamp>.parquet`.

---

## Running the Pipeline

### Main CLI Command

```bash
poetry run balance-pipe process "csv_inbox/**.csv" \
    --schema-mode strict \
    --output-type excel \
    --output-path output/latest.xlsx
```

### PowerShell Scripts

- `Run-Analysis.ps1` - Main analysis runner
- `Run-ComprehensiveAnalyzer.ps1` - Full comprehensive analysis
- `Clean-Repository.ps1` - Repository cleanup utilities

---

## Scripts Organization

### 📁 scripts/analysis/
Data analysis and investigation scripts:
- `deep_analysis.py` - Comprehensive transaction analysis
- `transaction_count_analysis.py` - Transaction volume analysis
- `rent_logic_check.py` - Rent payment logic validation

### 📁 scripts/corrections/
Data correction and repair utilities:
- `rent_allocation_corrector.py` - Fix rent allocation issues
- `final_balance_correction.py` - Balance reconciliation
- `integrate_rent_corrections.py` - Apply rent corrections

### 📁 scripts/investigations/
Issue investigation and debugging tools:
- `critical_issue_investigator.py` - Critical issue detection
- `financial_issue_detector.py` - Financial anomaly detection
- `investigate_imbalance.py` - Balance discrepancy investigation

### 📁 scripts/utilities/
General utility and processing scripts:
- `comprehensive_audit_trail.py` - Complete audit trail generation
- `zelle_integration.py` - Zelle payment processing
- `powerbi_data_refresh.py` - Power BI data refresh utilities

---

## Configuration

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `BALANCE_CSV_INBOX` | `csv_inbox` | Root folder for CSVs |
| `BALANCE_OUTPUT_DIR` | `output` | Output directory |
| `BALANCE_SCHEMA_MODE` | `flexible` | Schema validation mode |
| `BALANCE_LOG_LEVEL` | `INFO` | Logging verbosity |

### Configuration Files

- `config/balance_analyzer.yaml` - Balance analyzer settings
- `rules/schema_registry.yml` - CSV schema definitions
- `rules/merchant_lookup.csv` - Merchant mapping rules

---

## Development

### Running Tests

```bash
poetry run pytest -v
```

### Code Quality

```bash
poetry run ruff check . && poetry run ruff format .
poetry run mypy src/ --strict
```

### Debug Tools

- `tools/debug_runner.py` - Development debugging utilities
- `tools/diagnose_analyzer.py` - Analyzer diagnostics

---

## Contributing

1. Run all CI gates before PR:
   ```bash
   poetry run ruff check . && poetry run ruff format .
   poetry run mypy src/ --strict  
   poetry run pytest -q
   ```

2. Follow Conventional Commits format
3. Update documentation for new features
4. Add tests for new functionality

---

## License & Version

Personal use only · Current version **0.1.x – Schema-Aware Ingestion Setup**