# BALANCE Pipeline Commands Reference

**Last Updated**: 2025-08-09  
**Version**: 2.0 - Post-Cleanup  
**Single Entry Point**: `pipeline.ps1` - All operations go through this master script

## Table of Contents
- [Main Operations](#-main-operations)
- [Utility Operations](#-utility-operations)
- [Advanced Options](#-advanced-options)
- [Essential Utilities](#-essential-utilities)
- [Python CLI Alternative](#-python-cli-alternative)
- [Troubleshooting](#-troubleshooting)

---

## 🚀 Main Operations

> **Note**: All commands assume you're in the project root directory

### Process CSV Files (Main Pipeline)
```powershell
.\pipeline.ps1 process
```
- Processes all CSV files in `csv_inbox/`
- Outputs to Power BI format by default
- This is the **primary operation** most users need

### Comprehensive Analysis
```powershell
.\pipeline.ps1 analyze
```
- Runs detailed financial analysis
- Generates reports and visualizations
- Creates audit trails

### Baseline Balance Analysis
```powershell
.\pipeline.ps1 baseline
```
- Calculates baseline balances
- Reconciles who-owes-who amounts
- Generates balance reports

---

## 🔧 Utility Operations

### Pipeline Status Check
```powershell
.\pipeline.ps1 status
```
- Shows pipeline health
- Checks dependencies
- Lists recent outputs

### Repository Cleanup
```powershell
.\pipeline.ps1 clean
```
- Cleans temporary files
- Organizes repository structure
- Safe cleanup of generated files

### Help & Documentation
```powershell
.\pipeline.ps1 help
```
- Shows all available commands
- Usage examples
- Quick reference guide

---

## ⚙️ Advanced Options

### Debug Mode
```powershell
# Enable debug output for any command
.\pipeline.ps1 process -Debug
.\pipeline.ps1 analyze -Debug
.\pipeline.ps1 baseline -Debug
```

### Custom Paths
```powershell
# Custom input/output paths
.\pipeline.ps1 process -InputPath "data/*.csv" -OutputPath "reports"
```

### Output Formats
```powershell
# Different output formats
.\pipeline.ps1 process -Format powerbi    # Power BI optimized (default)
.\pipeline.ps1 process -Format excel      # Excel workbook
.\pipeline.ps1 process -Format parquet    # Parquet files
.\pipeline.ps1 process -Format csv        # CSV output
```

---

## 🛠️ Essential Utilities

### Modern GUI Dispute Analyzer (Recommended)
```powershell
python scripts/utilities/dispute_analyzer_gui.py
```
- Professional graphical interface
- Modern dark theme with enhanced visuals
- Interactive dashboard and analysis tools
- One-click Excel export

### CLI Dispute Analyzer
```powershell
python scripts/utilities/dispute_analyzer.py
```
- Command-line interface for dispute analysis
- Interactive menu system
- Search refunds by merchant
- Find duplicate charges

### Power BI Data Preparation
```powershell
python scripts/utilities/quick_powerbi_prep.py
```
- Advanced deduplication (removes 30-35% duplicates)
- Merchant standardization
- Power BI optimized output formats

### Baseline Analysis
```powershell
python scripts/run_baseline.py
```
- Calculate opening balances
- Run balance reconciliation
- Generate baseline reports

### Quick System Check
```powershell
python scripts/quick_check.py
```
- Verify pipeline health
- Check configuration files
- Validate data integrity

---

## 🐍 Python CLI Alternative

### Direct Python Usage
```powershell
# Process files directly with Python
poetry run python src/balance_pipeline/main.py process file1.csv file2.csv

# With custom schema and output
poetry run python src/balance_pipeline/main.py process *.csv \
  --schema-path custom_schema.yml \
  --output processed.parquet \
  --format parquet

# Enable debug mode
poetry run python src/balance_pipeline/main.py process *.csv --debug
```

### Python CLI Options
- `-s, --schema-path`: Custom schema registry YAML file
- `-m, --merchant-path`: Custom merchant lookup CSV file
- `-o, --output`: Output file path (default: stdout)
- `-f, --format`: Output format (csv, parquet, excel)
- `-d, --debug`: Enable debug mode
- `-v, --verbose`: Increase verbosity (can repeat: -v, -vv)

---

## 🔍 Troubleshooting

### Pipeline Won't Start
```powershell
# Check status first
.\pipeline.ps1 status

# Verify Poetry installation
poetry --version
poetry check

# Reinstall dependencies if needed
poetry install --no-root --with dev
```

### CSV Processing Errors
```powershell
# Run with debug output
.\pipeline.ps1 process -Debug

# Check schema registry
type rules\schema_registry.yml

# Validate specific CSV
python scripts/utilities/dispute_analyzer.py
```

### PowerShell Not Available
```powershell
# Use Python CLI directly
poetry run python src/balance_pipeline/main.py process *.csv

# Or run utilities directly
python scripts/utilities/quick_powerbi_prep.py
```

### Check Log Files
- Pipeline logs: `logs/pipeline_run.log`
- Analysis logs: `logs/financial_analysis_audit.log`
- Debug output: Console or log files in `logs/` directory

---

## 📁 File Locations

### Input
- **CSV Files**: Place in `csv_inbox/Ryan/` or `csv_inbox/Jordyn/`
- **Configuration**: `config/` directory
- **Schema Definitions**: `rules/` directory

### Output
- **Processed Data**: `output/` directory
- **Reports**: Various formats in output directory
- **Logs**: `logs/` directory (if exists)

---

## 🆘 Getting Help

```powershell
# Quick help
.\pipeline.ps1 help

# Python CLI help
poetry run python src/balance_pipeline/main.py --help

# Utility-specific help
python scripts/utilities/dispute_analyzer_gui.py  # GUI with built-in help
```

### Documentation
- **Main Guide**: `README.md`
- **Architecture**: `docs/ARCHITECTURE.md`
- **Utilities Guide**: `scripts/utilities/README.md`
- **Troubleshooting**: `docs/` directory

### Common Workflows

#### Daily Processing
```powershell
# 1. Add new CSV files to csv_inbox/
# 2. Run processing
.\pipeline.ps1 process

# 3. Check results
.\pipeline.ps1 status
```

#### Monthly Analysis
```powershell
# 1. Process all data
.\pipeline.ps1 process

# 2. Run comprehensive analysis
.\pipeline.ps1 analyze

# 3. Calculate balances
.\pipeline.ps1 baseline
```

#### Troubleshooting Workflow
```powershell
# 1. Check pipeline health
.\pipeline.ps1 status

# 2. Run with debug if issues
.\pipeline.ps1 process -Debug

# 3. Clean and retry if needed
.\pipeline.ps1 clean
.\pipeline.ps1 process
```

---

## 📊 Output Files

### Standard Outputs
- `output/transactions_cleaned_*.parquet` - Processed transactions
- `output/balance_final.parquet` - Final balance calculations
- `output/financial_analysis_report.xlsx` - Comprehensive reports

### Format Recommendations
- **Parquet**: Best for Power BI (recommended)
- **Excel**: Good for manual review
- **CSV**: Simple import format

---

**🏆 BALANCE Pipeline: Professional Financial Analysis Made Simple**