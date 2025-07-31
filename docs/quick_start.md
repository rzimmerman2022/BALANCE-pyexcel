# Quick Start Guide

Get BALANCE-pyexcel up and running with your financial data in minutes.

---

## Prerequisites

- Python 3.11+ installed
- Poetry package manager
- Git for version control

---

## 1. Clone & Install

```bash
git clone https://github.com/<your-github-handle>/BALANCE-pyexcel.git
cd BALANCE-pyexcel
poetry install --with dev         # installs main + dev/test dependencies
```

## 2. Create CSV Inbox Structure

Create organized folders for your bank export files:

```text
csv_inbox/
   ├── Jordyn/          # Owner 1's bank exports
   └── Ryan/            # Owner 2's bank exports
```

Drop your raw bank CSV files into the matching owner folder.

## 3. Run the Pipeline

### Option A: CLI Command (Recommended)

```bash
# Process all CSV files and generate output
poetry run balance-pipe process "csv_inbox/**.csv" \
    --output-type powerbi \
    --schema-mode flexible
```

### Option B: PowerShell Scripts

```powershell
# Run comprehensive analysis
.\Run-ComprehensiveAnalyzer.ps1

# Or run basic analysis
.\Run-Analysis.ps1
```

## 4. Review Output

The pipeline generates:

- **Parquet files**: `output/unified_pipeline/<timestamp>.parquet`
- **Excel workbooks**: `output/balance_data.xlsx`
- **Analysis reports**: `analysis_output/` directory
- **Audit trails**: `audit_reports/` directory

## 5. Power BI Integration

1. Open Power BI Desktop
2. Connect to the generated `.parquet` file
3. Use the pre-built data model for instant analytics

## 6. Excel Integration

Open the Excel template from `workbook/template/BALANCE-template.xlsm`:

1. Configure data sources in the **Config** sheet
2. Run the ETL process
3. Review transactions in **Queue_Review** sheet
4. Check balances in **Dashboard** sheet

---

## Command Reference

### Main Commands

```bash
# Core pipeline processing
poetry run balance-pipe process <pattern> [options]

# Balance analysis
poetry run balance-analyze --config config/balance_analyzer.yaml

# Legacy CLI (backwards compatibility)
poetry run balance-legacy-cli [options]

# Merchant operations
poetry run balance-merchant [options]
```

### Development Commands

```bash
# Run tests
poetry run pytest

# Code quality checks
poetry run ruff check .
poetry run mypy src/balance_pipeline

# Build documentation
poetry run mkdocs build
```

---

## Configuration

### Environment Variables

```bash
export BALANCE_CSV_INBOX="csv_inbox"
export BALANCE_OUTPUT_DIR="output"  
export BALANCE_SCHEMA_MODE="flexible"
export BALANCE_LOG_LEVEL="INFO"
```

### Key Configuration Files

- `config/balance_analyzer.yaml` - Analysis settings
- `rules/schema_registry.yml` - CSV schema definitions
- `rules/merchant_lookup.csv` - Merchant mapping rules

---

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure you're in the project directory and poetry shell is active
2. **Schema validation failures**: Check your CSV files match expected formats in `rules/schema_registry.yml`
3. **Permission errors**: Ensure write access to output directories

### Debug Tools

```bash
# Run with verbose logging
poetry run balance-pipe process "csv_inbox/**.csv" -vv

# Use diagnostic tools
python tools/diagnose_analyzer.py
python tools/debug_runner.py
```

---

## Next Steps

1. **Customize schemas**: Edit `rules/schema_registry.yml` for your bank formats
2. **Automated workflows**: Set up CI/CD with GitHub Actions
3. **Advanced analytics**: Explore Power BI integration
4. **Custom scripts**: Use utilities in `scripts/` directory

---

## Getting Help

- 📚 **Documentation**: See `docs/` directory
- 🔧 **Scripts Guide**: `docs/scripts_guide.md`
- 🏗️ **Architecture**: `docs/ARCHITECTURE.md`
- 🐛 **Issues**: Check GitHub issues or create new ones

Happy balancing! 🎯