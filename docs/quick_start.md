# BALANCE Quick Start Guide

**Last Updated**: 2025-08-09  
**Version**: 2.0 - Post-Cleanup  
**Target Time**: 5-10 minutes to first results

Get BALANCE up and running with your financial data in minutes using the streamlined repository structure.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Installation](#1-clone--install)
- [Setup](#2-create-csv-inbox-structure)
- [First Run](#3-first-run)
- [Verification](#4-verify-results)
- [GUI Usage](#5-modern-gui-recommended)
- [Next Steps](#next-steps)

---

## Prerequisites

**Required:**
- **Python 3.11+** installed and in PATH
- **Poetry** package manager ([installation guide](https://python-poetry.org/docs/#installation))
- **Git** for version control

**Optional:**
- **PowerShell** (Windows) or **pwsh** (cross-platform) for `pipeline.ps1`
- **Excel** for viewing generated reports
- **Power BI Desktop** for advanced analytics

---

## 1. Clone & Install

```bash
# Clone the repository
git clone https://github.com/<your-github-handle>/BALANCE.git
cd BALANCE

# Install dependencies
poetry install --no-root --with dev

# Verify installation
poetry run python src/balance_pipeline/main.py --help
```

## 2. Create CSV Inbox Structure

The repository already includes the CSV inbox structure. Simply add your bank export files:

```text
csv_inbox/
   ├── Ryan/
   │   ├── Aggregated/     # Monarch Money, Rocket Money exports
   │   ├── Checking/       # Direct bank exports
   │   ├── CreditCard/
   │   └── Investment/
   └── Jordyn/
       ├── Checking/
       ├── CreditCard/
       └── Investment/
```

**Add your CSV files** to the appropriate subdirectories.

## 3. First Run

### Option A: Python CLI (Always Works)
```bash
# Process all CSV files in csv_inbox/
poetry run python scripts/utilities/quick_powerbi_prep.py
```

### Option B: PowerShell Pipeline (If Available)
```powershell
# Main pipeline command
.\pipeline.ps1 process

# Or with debug output
.\pipeline.ps1 process -Debug
```

### What Happens
- Automatically detects CSV formats
- Removes duplicates (typically 30-35% reduction)
- Standardizes merchant names
- Creates multiple output formats

## 4. Verify Results

Check the `output/` directory for generated files:

```text
output/
├── transactions_cleaned_YYYYMMDD_HHMMSS.csv     # Human-readable
├── transactions_cleaned_YYYYMMDD_HHMMSS.xlsx    # Excel format
└── transactions_cleaned_YYYYMMDD_HHMMSS.parquet # Power BI format
```

**Success indicators:**
- Files generated in `output/`
- Console shows processing statistics
- No error messages in output

## 5. Modern GUI (Recommended)

Launch the professional dispute analyzer interface:

```bash
python scripts/utilities/dispute_analyzer_gui.py
```

### GUI Features
- **Dashboard**: Real-time metrics and recent disputes
- **Find Refunds**: Search by merchant with date filtering
- **Duplicate Detection**: Identify potential double charges
- **Refund Verification**: Check if specific charges were refunded
- **Advanced Search**: Multi-filter capabilities
- **Excel Export**: One-click export for any view

## Next Steps

### For Basic Analysis
1. **Open Excel file** from `output/` directory
2. **Filter and sort** to find specific transactions
3. **Use pivot tables** for spending analysis

### For Advanced Analytics
1. **Open Power BI Desktop**
2. **Import parquet file** from `output/`
3. **Create visualizations** and dashboards

### For Ongoing Use
1. **Add new CSV files** to `csv_inbox/` as needed
2. **Re-run processing** to include new data
3. **Use GUI tools** for dispute investigation

---

## Troubleshooting

### Installation Issues
```bash
# Check Python version
python --version  # Should be 3.11+

# Check Poetry
poetry --version

# Reinstall dependencies
poetry install --no-root --with dev
```

### Processing Errors
```bash
# Run with debug output
poetry run python scripts/utilities/quick_powerbi_prep.py

# Check for error messages in console output
# Ensure CSV files are properly formatted
```

### GUI Won't Launch
```bash
# Install required package
pip install customtkinter

# Or try CLI version
python scripts/utilities/dispute_analyzer.py
```

---

## Supported Formats

### Bank CSV Formats
- **Chase Bank**: Checking accounts
- **Discover Card**: Credit card statements  
- **Wells Fargo**: Credit cards
- **Monarch Money**: Aggregated transaction exports
- **Rocket Money**: Aggregated transaction exports

### Adding New Formats
Edit `rules/schema_registry.yml` to add new bank CSV patterns and column mappings.

---

## Common Use Cases

### Monthly Review
1. Export new statements from banks
2. Add CSV files to appropriate folders
3. Run processing pipeline
4. Review results in Excel or Power BI

### Dispute Investigation
1. Launch GUI dispute analyzer
2. Search for merchant refunds
3. Check for duplicate charges
4. Export findings to Excel

### Power BI Dashboard
1. Process CSV files regularly
2. Import parquet files to Power BI
3. Create ongoing financial dashboards
4. Set up automated refresh

---

**🎉 You're ready to go! Your financial data is now processed and ready for analysis.**

For more advanced features, see:
- **[Pipeline Commands](../PIPELINE_COMMANDS.md)** - Full command reference
- **[Utilities Guide](../scripts/utilities/README.md)** - GUI and analysis tools
- **[Architecture](architecture.md)** - How the system works