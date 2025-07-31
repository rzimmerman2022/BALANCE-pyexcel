# BALANCE-pyexcel

[![Python CI](https://github.com/your-github-org-or-username/BALANCE-pyexcel/actions/workflows/ci.yml/badge.svg)](https://github.com/your-github-org-or-username/BALANCE-pyexcel/actions/workflows/ci.yml)

**A professional Excel-based shared-expense tracker powered by Python, with schema-driven CSV ingestion and a unified ETL pipeline.**

🔧 **Pipeline Status:** ✅ **PRODUCTION READY** - Gold standard achieved with full validation  
📊 **CI/CD Status:** ✅ **ACTIVE** - Multi-platform testing, automated deployment, executable building  
🏗️ **Architecture:** ✅ **GOLD STANDARD** - Industry best practices with comprehensive documentation  
🧪 **Validation:** ✅ **COMPLETE** - 5 bank formats tested, end-to-end processing verified  
📈 **Ready For:** ✅ **REAL DATA** - Banking data import and baseline balance calculation

---

## Table of Contents

1. [Overview](#overview)
2. [Project Structure](#project-structure)
3. [Quick Start](#quick-start)
4. [Running the Pipeline](#running-the-pipeline)
5. [Scripts Organization](#scripts-organization)
6. [Configuration](#configuration)
7. [Development](#development)
8. [CI/CD Pipeline](#cicd-pipeline)
9. [Contributing](#contributing)

---

## Overview

BALANCE-pyexcel lets parties manage shared finances in a familiar Excel environment. Python processes diverse bank/card CSV formats, normalizes them, and produces clean transaction ledgers for classification and balance calculation.

**Key Features:**
- ✨ Schema-driven CSV ingestion via `rules/schema_registry.yml`
- 🏷️ Automatic owner tagging (folder-name → `Owner` column)
- 🔄 Data normalization & sign correction
- 🆔 Stable `TxnID` generation (SHA-256)
- 📋 Excel review queue based on `FILTER`
- 📊 Comprehensive analysis and reporting tools
- 🚀 Professional CI/CD pipeline with automated testing
- 📈 Power BI integration for advanced analytics

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
- `Run-BalanceAnalysis.ps1` - Balance analysis workflows
- `Clean-Repository.ps1` - Repository cleanup utilities
- `Check-RequiredFiles.ps1` - Validate required files
- `Make-Previews.ps1` - Generate data previews

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

## 🚀 Production Quick Start

### **Ready for Your Banking Data** 
The pipeline has been validated with 5 bank formats and is production-ready.

```bash
# 1. Export data from all your bank accounts to csv_inbox/
# 2. Process all your data
python -c "
import sys; sys.path.insert(0, 'src')
from balance_pipeline.main import main
sys.argv = ['main', 'process', 'csv_inbox/**.csv', '--output-type', 'powerbi']
main()
"

# 3. Run balance analysis
python scripts/analysis/simple_balance_check.py
```

### **Validated Bank Formats**
- ✅ Chase Checking (`jordyn_chase_checking_v1`)
- ✅ Discover Card (`jordyn_discover_card_v1`)  
- ✅ Wells Fargo Card (`jordyn_wells_v1`)
- ✅ Monarch Money (`ryan_monarch_v1`)
- ✅ Rocket Money (`ryan_rocket_v1`)

### **Gold Standard Features**
- 🔄 **Auto Processing**: Schema detection and data transformation
- 👥 **Multi-Owner**: Ryan/Jordyn transaction separation
- 💰 **Balance Calc**: Automated who-owes-who analysis
- 📊 **Power BI Ready**: Optimized analytics data
- 📋 **Excel Review**: Transaction categorization workflow

---

## CI/CD Pipeline

### GitHub Actions Workflow

Our comprehensive CI/CD pipeline includes:

- 🧪 **Multi-platform Testing**: Ubuntu & Windows with Python 3.10, 3.11
- 🔍 **Code Quality**: Ruff linting, MyPy type checking
- 📚 **Documentation**: MkDocs build and GitHub Pages deployment
- 📦 **Executable Building**: PyInstaller Windows executable generation
- ⚡ **Fast Feedback**: Parallel job execution for optimal performance

### Workflow Structure

```yaml
test → build_docs → deploy_docs (main branch only)
  ↓
build_executable
```

### Available Commands

```bash
# Run full CI locally
poetry run pytest
poetry run ruff check .
poetry run mypy src/balance_pipeline

# Build documentation
poetry run mkdocs build

# Build executable (Windows)
pyinstaller --onefile --name balance-pyexcel src/balance_pipeline/cli.py
```

---

## Contributing

1. **Pre-commit Validation**: Run all CI gates before PR:
   ```bash
   poetry run ruff check . && poetry run ruff format .
   poetry run mypy src/ --strict  
   poetry run pytest -q
   ```

2. **Commit Standards**: Follow Conventional Commits format
3. **Documentation**: Update documentation for new features
4. **Testing**: Add comprehensive tests for new functionality
5. **Pipeline Validation**: Ensure all GitHub Actions pass

---

## License & Version

**Personal use only** · Current version **0.3.2 – Gold Standard Production Ready**

🏆 **Status**: Gold standard achieved - ready for real banking data  
🏗️ **Architecture**: Industry best practices with comprehensive validation  
📊 **Pipeline**: 5 bank formats tested, end-to-end processing verified  
🚀 **Next Step**: Import your banking data and establish baseline balance