# Pipeline Status & Health Check

**Last Updated**: 2025-07-31  
**Status**: ✅ **FULLY OPERATIONAL**

---

## Quick Health Check

| Component | Status | Details |
|-----------|--------|---------|
| **Core Pipeline** | ✅ | `src/balance_pipeline/` - All modules intact |
| **CLI Commands** | ✅ | 5 entry points active: balance-pipe, balance-analyze, etc. |
| **CI/CD** | ✅ | GitHub Actions with multi-platform testing |
| **Dependencies** | ✅ | Poetry lock file current, all deps resolved |
| **Tests** | ✅ | Test suite passing on Python 3.10, 3.11 |
| **Documentation** | ✅ | Comprehensive docs with deployment validation |

---

## Pipeline Components

### Core Modules (`src/balance_pipeline/`)
- ✅ `pipeline_v2.py` - UnifiedPipeline orchestrator
- ✅ `main.py` - CLI entry point
- ✅ `csv_consolidator.py` - CSV processing engine
- ✅ `config.py` - Configuration management
- ✅ `errors.py` - Custom error handling
- ✅ `schema_registry.py` - Schema validation
- ✅ `merchant.py` - Merchant normalization
- ✅ `analytics.py` - Analysis functions
- ✅ `export.py` - Output formatting

### Data Processing Flow
```
CSV Files → Schema Matching → Data Transformation → Consolidation → Output
     ↓             ↓                    ↓                 ↓            ↓
 Ingestion    Validation         Normalization      Deduplication   Export
```

### Output Formats Supported
- ✅ Excel (.xlsx)
- ✅ Parquet (.parquet)
- ✅ CSV (.csv)
- ✅ Power BI optimized

---

## Configuration

### Key Files
- `config/balance_analyzer.yaml` - Analysis settings
- `rules/schema_registry.yml` - CSV schema definitions
- `rules/merchant_lookup.csv` - Merchant mappings
- `pyproject.toml` - Project dependencies

### Environment Variables
```bash
BALANCE_CSV_INBOX     # Input directory (default: csv_inbox)
BALANCE_OUTPUT_DIR    # Output directory (default: output)
BALANCE_SCHEMA_MODE   # Schema mode (strict/flexible)
BALANCE_LOG_LEVEL     # Logging level (INFO/DEBUG)
```

---

## Common Operations

### Running the Pipeline
```bash
# Basic run
poetry run balance-pipe process "csv_inbox/**.csv"

# With options
poetry run balance-pipe process "csv_inbox/**.csv" \
    --output-type powerbi \
    --schema-mode flexible \
    --debug
```

### Analyzing Data
```bash
# Run balance analysis
poetry run balance-analyze --config config/balance_analyzer.yaml

# Run comprehensive analysis
.\Run-ComprehensiveAnalyzer.ps1
```

### Troubleshooting
```bash
# Verbose logging
poetry run balance-pipe process "csv_inbox/**.csv" -vv

# Debug tools
python tools/diagnose_analyzer.py
python tools/debug_runner.py
```

---

## Maintenance Tasks

### Regular Checks
1. **Schema Updates**: Review `rules/schema_registry.yml` for new bank formats
2. **Merchant Mappings**: Update `rules/merchant_lookup.csv` as needed
3. **Dependencies**: Run `poetry update` monthly
4. **Tests**: Run `poetry run pytest` before major changes

### Performance Monitoring
- Check log files in `logs/` directory
- Monitor output file sizes
- Review processing times for large datasets

---

## Support Resources

- **Documentation**: `docs/` directory
- **Scripts**: `scripts/` directory (organized by function)
- **Issues**: GitHub issue tracker
- **CI/CD**: GitHub Actions tab

---

## Recent Updates

- **v0.3.2**: Documentation update and pipeline validation
- **v0.3.1**: Repository reorganization to best practices
- **v0.3.0**: Enhanced ledger parsing and reconciliation

---

**Pipeline Validation**: All components verified operational on 2025-07-31