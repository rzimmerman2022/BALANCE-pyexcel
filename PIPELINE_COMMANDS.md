# BALANCE-pyexcel Pipeline Commands Reference

**Single Entry Point**: `pipeline.ps1` - All operations go through this master script

---

## 🚀 Main Operations

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

### Help & Documentation
```powershell
.\pipeline.ps1 help
```
- Shows all available commands
- Displays usage examples
- Lists all options

---

## ⚙️ Options & Customization

### Input/Output Options
```powershell
# Custom input path
.\pipeline.ps1 process -InputPath "data/*.csv"

# Custom output path
.\pipeline.ps1 process -OutputPath "reports"

# Different output formats
.\pipeline.ps1 process -Format excel      # Excel workbook
.\pipeline.ps1 process -Format parquet    # Parquet files
.\pipeline.ps1 process -Format csv        # CSV files
.\pipeline.ps1 process -Format powerbi    # Power BI optimized (default)
```

### Debug Mode
```powershell
# Enable detailed logging
.\pipeline.ps1 process -Debug
.\pipeline.ps1 analyze -Debug
.\pipeline.ps1 baseline -Debug
```

---

## 📁 File Organization

All utility scripts are now organized in `scripts/powershell/`:
- `Clean-Repository.ps1` - Repository cleanup
- `Run-Analysis.ps1` - Legacy analysis runner  
- `Check-RequiredFiles.ps1` - File validation
- `Make-Previews.ps1` - Data previews
- And more...

**But you should use the master `pipeline.ps1` instead of calling these directly.**

---

## 🎯 Common Workflows

### Daily Processing
```powershell
# 1. Add new CSV files to csv_inbox/Ryan/ or csv_inbox/Jordyn/
# 2. Run the pipeline
.\pipeline.ps1 process

# 3. Check results
.\pipeline.ps1 status
```

### Weekly Analysis
```powershell
# Process + analyze in sequence
.\pipeline.ps1 process
.\pipeline.ps1 analyze
.\pipeline.ps1 baseline
```

### Troubleshooting
```powershell
# Check pipeline health
.\pipeline.ps1 status

# Run with debug output
.\pipeline.ps1 process -Debug

# Clean and retry
.\pipeline.ps1 clean
.\pipeline.ps1 process
```

---

## 🏗️ Architecture

- **Entry Point**: `pipeline.ps1` (master script)
- **Core Engine**: `src/balance_pipeline/` (Python package)
- **CLI Commands**: `balance-pipe`, `balance-analyze`, `balance-baseline`
- **Configuration**: `config/`, `rules/`
- **Utilities**: `scripts/powershell/`

The master pipeline script provides a unified interface to all underlying Python CLI commands and utilities.