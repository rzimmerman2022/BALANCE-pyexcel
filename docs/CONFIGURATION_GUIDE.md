# Configuration Guide

**Status**: ✅ **PRODUCTION READY**  
**Version**: 0.3.2  
**Last Updated**: 2025-07-31

---

## Overview

This guide provides comprehensive configuration information for BALANCE-pyexcel. All configurations have been validated and tested in production scenarios.

---

## 📁 **Configuration Files**

### **Core Configuration Files**
```
config/
├── balance_analyzer.yaml          # Balance analysis settings
├── canonical_schema_v2.yaml       # Data schema definitions  
├── comprehensive_balance_analysis.json  # Analysis parameters
└── generated_sharing_rules.json   # Automated sharing rules
```

### **Schema Registry**
```
rules/
├── schema_registry.yml            # Master schema registry
├── jordyn_chase_checking_v1.yaml  # Chase checking format
├── jordyn_discover_card_v1.yaml   # Discover card format
├── jordyn_wells_v1.yaml          # Wells Fargo format
├── ryan_monarch_v1.yaml          # Monarch Money format
├── ryan_rocket_v1.yaml           # Rocket Money format
└── merchant_lookup.csv           # Merchant normalization rules
```

---

## 🔧 **Environment Variables**

### **Primary Configuration**
```bash
# Data paths
export BALANCE_CSV_INBOX="csv_inbox"
export BALANCE_OUTPUT_DIR="output"
export BALANCE_SCHEMA_REGISTRY="rules/schema_registry.yml"
export BALANCE_MERCHANT_LOOKUP="rules/merchant_lookup.csv"

# Processing options
export BALANCE_SCHEMA_MODE="flexible"  # or "strict"
export BALANCE_LOG_LEVEL="INFO"       # DEBUG, INFO, WARNING, ERROR

# Performance settings
export BALANCE_MAX_MEMORY_MB="500"
export BALANCE_MAX_PROCESSING_TIME="150"
```

### **Advanced Configuration**
```bash
# Output formats
export BALANCE_DEFAULT_OUTPUT_FORMAT="parquet"
export BALANCE_SUPPORTED_FORMATS="excel,parquet,csv,powerbi"

# Analysis settings
export BALANCE_CONFIDENCE_LEVEL="0.95"
export BALANCE_OUTLIER_THRESHOLD="5000.0"
export BALANCE_RENT_BASELINE="2100.0"
```

---

## 💰 **Balance Analysis Configuration**

### **Shared Expense Rules**
Edit `config/balance_analyzer.yaml`:

```yaml
# Rent allocation (customize for your situation)
rent_allocation:
  ryan_percentage: 0.57
  jordyn_percentage: 0.43
  baseline_amount: 2100.0
  variance_threshold: 0.10

# Shared expense categories
shared_categories:
  - "Rent"
  - "Utilities"
  - "Groceries"
  - "Gas"
  - "Shared Dining"
  - "Home Expenses"

# Personal categories (not shared)
personal_categories:
  - "Personal Care"
  - "Individual Hobbies"
  - "Personal Shopping"
  - "Individual Entertainment"
  - "Medical Expenses"

# Split rules for specific merchants
merchant_split_rules:
  "Costco": 0.50          # 50/50 split
  "Target": 0.50          # 50/50 split
  "Whole Foods": 0.50     # 50/50 split
  "Safeway": 0.50         # 50/50 split
```

### **Analysis Thresholds**
```yaml
# Quality control thresholds
data_quality:
  minimum_threshold: 0.90
  outlier_threshold: 5000.0
  confidence_level: 0.95

# Performance limits
performance:
  max_memory_mb: 500
  max_processing_time_seconds: 150
  
# Balance reconciliation
reconciliation:
  liquidity_strain_threshold: 5000.0
  liquidity_strain_days: 60
  concentration_risk_threshold: 0.40
```

---

## 🏦 **Bank Schema Configuration**

### **Adding New Bank Formats**

1. **Create Schema File**: `rules/new_bank_v1.yaml`
```yaml
schema_name: "Your Bank Name"
id: "your_bank_v1"
notes: "Description of bank format"
file_pattern: 'Your Bank Export*.csv'

# Date format used by bank
date_format: "%m/%d/%Y"

# Headers that identify this bank format
header_signature:
  - "Date"
  - "Description"
  - "Amount"
  - "Account"

# Map bank columns to standard columns
column_map:
  Date: Date
  Description: OriginalDescription
  Amount: Amount
  Account: Account

# How to handle positive/negative amounts
sign_rule: "as_is"  # or "flip_if_positive", "flip_if_withdrawal"

# Static values to add
derived_columns:
  Owner:
    type: static_value
    value: "YourName"
  DataSourceName:
    type: static_value
    value: "YourBankName"
```

2. **Test New Schema**:
```bash
# Test with sample file
python -c "
import sys; sys.path.insert(0, 'src')
from balance_pipeline.main import main
sys.argv = ['main', 'process', 'path/to/sample_file.csv', '--debug']
main()
"
```

### **Existing Schema Modifications**

To modify existing schemas:
1. **Edit Schema File**: Update relevant `.yaml` file in `rules/`
2. **Test Changes**: Process sample data
3. **Validate Output**: Check transaction processing accuracy

---

## 🏪 **Merchant Normalization**

### **Merchant Lookup Configuration**
Edit `rules/merchant_lookup.csv`:

```csv
raw_merchant,clean_merchant,category
"WHOLEFDS CHR 10272","Whole Foods","Groceries"
"FRYS-FOOD-DRG #051","Fry's Food and Drug","Groceries"
"DD *DOORDASH","DoorDash","Restaurants & Bars"
"ZELLE FROM ZIMMERMAN","Zelle Transfer","Transfer"
```

### **Advanced Merchant Rules**
```yaml
# In balance_analyzer.yaml
merchant_normalization:
  case_sensitive: false
  trim_whitespace: true
  remove_special_chars: true
  
  # Regex patterns for cleaning
  patterns:
    - pattern: '\s+#\d+'        # Remove store numbers
      replacement: ''
    - pattern: '\*+\s*'         # Remove asterisks
      replacement: ''
    - pattern: '\s+\w{2}\s*$'   # Remove state codes
      replacement: ''
```

---

## 🎛️ **Pipeline Configuration**

### **Processing Modes**

**Strict Mode** (Default):
```bash
export BALANCE_SCHEMA_MODE="strict"
```
- All 25 master schema columns present
- Ensures backward compatibility
- Consistent output structure

**Flexible Mode**:
```bash
export BALANCE_SCHEMA_MODE="flexible"
```
- Only core required columns guaranteed
- Source-specific columns included when available
- More efficient for large datasets

### **Output Configuration**

**Supported Output Types**:
- `excel`: Excel workbook with multiple sheets
- `parquet`: High-performance analytics format
- `csv`: Universal compatibility format
- `powerbi`: Optimized for Power BI dashboards

**Output Paths**:
```bash
# Default output locations
output/
├── balance_data.xlsx           # Excel output
├── unified_pipeline/          # Parquet files with timestamps
├── *.parquet                  # Direct parquet outputs
└── powerbi_*.parquet         # Power BI optimized files
```

---

## 🔧 **Advanced Configuration**

### **Performance Tuning**
```yaml
# In balance_analyzer.yaml
performance:
  chunk_size: 10000           # Rows per processing chunk
  parallel_processing: true   # Enable multiprocessing
  memory_limit_mb: 500       # Maximum memory usage
  cache_enabled: true        # Enable result caching
  
  # Optimization settings
  optimize_memory: true
  compress_outputs: true
  skip_duplicates: true
```

### **Logging Configuration**
```python
# Environment variables for logging
export BALANCE_LOG_LEVEL="INFO"
export BALANCE_LOG_FORMAT="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
export BALANCE_LOG_FILE="logs/balance_pipeline.log"
```

### **Debug Settings**
```bash
# Enable comprehensive debugging
export BALANCE_DEBUG_MODE="true"
export BALANCE_VERBOSE_LOGGING="true"
export BALANCE_SAVE_INTERMEDIATE="true"

# Debug output locations
debug_output/
├── 01a_*_raw.csv             # Raw input files
├── 02b_*_clean.csv           # Cleaned data
└── 03c_baseline_reconciled.csv  # Final reconciled data
```

---

## 🧪 **Testing Configuration**

### **Test Data Settings**
```yaml
# For development/testing
test_settings:
  use_sample_data: true
  sample_data_path: "sample_data_multi/"
  test_output_path: "test_output/"
  
  # Test-specific overrides
  max_rows: 1000
  skip_validation: false
  generate_reports: true
```

### **Validation Settings**
```yaml
validation:
  check_required_columns: true
  validate_date_formats: true
  verify_numeric_amounts: true
  check_schema_compliance: true
  
  # Error handling
  fail_on_schema_mismatch: false
  warn_on_missing_columns: true
  skip_malformed_rows: true
```

---

## 📊 **Monitoring Configuration**

### **Health Check Settings**
```yaml
monitoring:
  enable_health_checks: true
  check_interval_minutes: 60
  alert_on_failures: true
  
  # Metrics to track
  track_processing_time: true
  track_memory_usage: true
  track_error_rates: true
  track_data_quality: true
```

### **Alert Configuration**
```yaml
alerts:
  processing_time_threshold: 300  # seconds
  memory_usage_threshold: 80      # percentage
  error_rate_threshold: 5         # percentage
  
  # Notification settings
  log_alerts: true
  save_alert_history: true
```

---

## 🔐 **Security Configuration**

### **Data Protection**
```yaml
security:
  local_processing_only: true
  no_external_connections: true
  encrypt_sensitive_data: false  # Not needed for local processing
  
  # File permissions
  restrict_file_access: true
  secure_temp_files: true
  clean_temp_on_exit: true
```

### **Audit Configuration**
```yaml
auditing:
  enable_audit_trail: true
  track_all_changes: true
  log_data_access: true
  
  # Audit output
  audit_file_path: "audit_reports/"
  audit_retention_days: 365
```

---

## 📋 **Configuration Validation**

### **Validation Commands**
```bash
# Verify configuration
python -c "from balance_pipeline.config import *; print('Configuration valid')"

# Test schema registry
python -c "
import yaml
with open('rules/schema_registry.yml') as f:
    schemas = yaml.safe_load(f)
    print(f'Loaded {len(schemas)} schemas')
"

# Validate environment
python tools/diagnose_analyzer.py
```

### **Common Configuration Issues**

**Issue**: Schema not found
```bash
# Solution: Check file paths
ls rules/*.yaml
export BALANCE_SCHEMA_REGISTRY="$(pwd)/rules/schema_registry.yml"
```

**Issue**: Processing failures
```bash
# Solution: Validate configuration
python tools/debug_runner.py
# Check logs in logs/ directory
```

---

**This configuration guide provides comprehensive setup information for all aspects of the BALANCE-pyexcel system, enabling professional-grade financial analysis operations.**