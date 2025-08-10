# API Reference

**Status**: ✅ **PRODUCTION READY**  
**Version**: 1.0.3  
**Last Updated**: 2025-08-10

---

## Overview

This document provides comprehensive API reference for the BALANCE-pyexcel pipeline components. All APIs have been validated and tested for production use.

---

## 🔧 **Core Pipeline API**

### **UnifiedPipeline Class**
**Location**: `src/balance_pipeline/pipeline_v2.py`

```python
from balance_pipeline.pipeline_v2 import UnifiedPipeline

# Initialize pipeline
pipeline = UnifiedPipeline(
    schema_mode="flexible",  # or "strict"
    debug_mode=False
)

# Process files
result_df = pipeline.process_files(
    file_paths=["path/to/file1.csv", "path/to/file2.csv"],
    schema_registry_override_path=None,
    merchant_lookup_override_path=None
)
```

**Parameters**:
- `schema_mode`: "strict" or "flexible" processing mode
- `debug_mode`: Enable detailed logging and intermediate outputs
- `file_paths`: List of file paths to process
- `schema_registry_override_path`: Custom schema registry file
- `merchant_lookup_override_path`: Custom merchant lookup file

**Returns**: pandas.DataFrame with processed transactions

---

## 📊 **Analysis API**

### **Balance Analysis Functions**
**Location**: `src/balance_pipeline/analyzer.py`

```python
from balance_pipeline.analyzer import analyze_balance, generate_reports

# Analyze balance between parties
balance_result = analyze_balance(
    transactions_df=df,
    ryan_percentage=0.57,
    jordyn_percentage=0.43,
    shared_categories=["Rent", "Utilities", "Groceries"]
)

# Generate comprehensive reports
reports = generate_reports(
    transactions_df=df,
    output_path="analysis_output/",
    include_charts=True
)
```

### **Transaction Analysis**
```python
from balance_pipeline.analytics import (
    calculate_monthly_summary,
    analyze_spending_patterns,
    detect_anomalies
)

# Monthly spending analysis
monthly_data = calculate_monthly_summary(df)

# Spending pattern analysis
patterns = analyze_spending_patterns(
    df, 
    groupby=["Owner", "Category"],
    time_period="monthly"
)

# Anomaly detection
anomalies = detect_anomalies(
    df,
    threshold=5000.0,
    method="statistical"
)
```

---

## 🏦 **Schema Registry API**

### **Schema Management**
**Location**: `src/balance_pipeline/schema_registry.py`

```python
from balance_pipeline.schema_registry import (
    load_schema_registry,
    match_schema,
    validate_schema
)

# Load all schemas
schemas = load_schema_registry("rules/schema_registry.yml")

# Match file to schema
matched_schema = match_schema(
    file_path="bank_export.csv",
    header_row=df.columns.tolist()
)

# Validate schema compliance
is_valid = validate_schema(df, schema_config)
```

### **Custom Schema Creation**
```python
from balance_pipeline.schema_registry import create_schema

# Create new schema
new_schema = create_schema(
    schema_name="New Bank Format",
    file_pattern="NewBank_*.csv",
    column_mappings={
        "Transaction Date": "Date",
        "Description": "OriginalDescription",
        "Amount": "Amount"
    },
    derived_columns={
        "Owner": {"type": "static_value", "value": "Ryan"}
    }
)
```

---

## 🏪 **Merchant Processing API**

### **Merchant Normalization**
**Location**: `src/balance_pipeline/merchant.py`

```python
from balance_pipeline.merchant import (
    normalize_merchant_name,
    load_merchant_rules,
    update_merchant_mapping
)

# Normalize single merchant name
clean_name = normalize_merchant_name(
    raw_merchant="WHOLEFDS CHR 10272",
    rules_dict=merchant_rules
)

# Load merchant rules
rules = load_merchant_rules("rules/merchant_lookup.csv")

# Update merchant mappings
update_merchant_mapping(
    raw_merchant="NEW MERCHANT NAME",
    clean_merchant="Clean Merchant Name",
    category="Groceries"
)
```

---

## 💾 **Data Export API**

### **Output Generation**
**Location**: `src/balance_pipeline/export.py`

```python
from balance_pipeline.export import (
    export_to_excel,
    export_to_parquet,
    export_to_powerbi
)

# Export to Excel with multiple sheets
export_to_excel(
    df=transactions_df,
    output_path="output/financial_data.xlsx",
    include_pivot_tables=True,
    create_review_queue=True
)

# Export to Parquet for analytics
export_to_parquet(
    df=transactions_df,
    output_path="output/analytics_data.parquet",
    optimize_for_powerbi=True
)

# Export Power BI optimized format
export_to_powerbi(
    df=transactions_df,
    output_directory="output/powerbi/",
    create_relationships=True
)
```

---

## 🔍 **Validation API**

### **Data Quality Checks**
**Location**: `src/balance_pipeline/errors.py`

```python
from balance_pipeline.errors import (
    validate_transaction_data,
    check_data_quality,
    generate_quality_report
)

# Validate transaction data
validation_result = validate_transaction_data(
    df=transactions_df,
    required_columns=["TxnID", "Owner", "Date", "Amount"],
    check_duplicates=True
)

# Comprehensive data quality check
quality_metrics = check_data_quality(
    df=transactions_df,
    quality_threshold=0.90
)

# Generate quality report
quality_report = generate_quality_report(
    df=transactions_df,
    output_path="reports/data_quality.html"
)
```

---

## ⚙️ **Configuration API**

### **Configuration Management**
**Location**: `src/balance_pipeline/config.py`

```python
from balance_pipeline.config import (
    SCHEMA_REGISTRY_PATH,
    MERCHANT_LOOKUP_PATH,
    CORE_REQUIRED_COLUMNS,
    AnalysisConfig
)

# Access configuration constants
schema_path = SCHEMA_REGISTRY_PATH
merchant_path = MERCHANT_LOOKUP_PATH
required_cols = CORE_REQUIRED_COLUMNS

# Use analysis configuration
config = AnalysisConfig(
    RYAN_PCT=0.57,
    JORDYN_PCT=0.43,
    RENT_BASELINE=2100.0,
    debug_mode=True
)
```

---

## 🧪 **CLI Integration API**

### **Command Line Interface**
**Location**: `src/balance_pipeline/main.py`

```python
from balance_pipeline.main import process_files_command

# Programmatic CLI execution
process_files_command(
    files=["csv_inbox/Ryan/*.csv", "csv_inbox/Jordyn/*.csv"],
    schema_path=None,  # Use default
    merchant_path=None,  # Use default
    output_path="output/processed_data.xlsx",
    output_format="excel",
    debug=False
)
```

### **Advanced CLI Usage**
```python
import sys
from balance_pipeline.main import main

# Simulate command line execution
sys.argv = [
    "balance-pipe",
    "process",
    "csv_inbox/**.csv",
    "--output-type", "powerbi",
    "--schema-mode", "flexible",
    "--debug"
]

main()
```

---

## 📈 **Analytics Extensions API**

### **Custom Analysis Functions**
```python
from balance_pipeline.analytics import BaseAnalyzer

class CustomAnalyzer(BaseAnalyzer):
    def __init__(self, config):
        super().__init__(config)
    
    def analyze_custom_metrics(self, df):
        """Custom analysis implementation"""
        return {
            "total_transactions": len(df),
            "total_amount": df["Amount"].sum(),
            "average_transaction": df["Amount"].mean()
        }
    
    def generate_custom_report(self, df, output_path):
        """Custom report generation"""
        metrics = self.analyze_custom_metrics(df)
        # Implementation here
        return metrics

# Use custom analyzer
analyzer = CustomAnalyzer(config)
results = analyzer.analyze_custom_metrics(transactions_df)
```

---

## 🛠️ **Utility Functions API**

### **Data Processing Utilities**
**Location**: `src/balance_pipeline/utils.py`

```python
from balance_pipeline.utils import (
    generate_transaction_id,
    clean_text,
    parse_date_string,
    validate_amount
)

# Generate unique transaction ID
txn_id = generate_transaction_id(
    date="2025-01-15",
    amount=-123.45,
    description="Grocery Store",
    account="Checking"
)

# Clean text data
clean_text = clean_text(
    text="  MESSY TEXT DATA  ",
    remove_extra_spaces=True,
    title_case=True
)

# Parse date from various formats
parsed_date = parse_date_string(
    date_string="01/15/2025",
    input_format="%m/%d/%Y"
)

# Validate monetary amounts
is_valid = validate_amount(
    amount_string="-$123.45",
    allow_negative=True
)
```

---

## 🔐 **Error Handling API**

### **Exception Classes**
```python
from balance_pipeline.errors import (
    BalancePipelineError,
    RecoverableFileError,
    FatalSchemaError
)

try:
    # Pipeline operations
    result = pipeline.process_files(files)
except RecoverableFileError as e:
    # Handle recoverable errors
    print(f"Warning: {e}")
    # Continue processing other files
except FatalSchemaError as e:
    # Handle fatal errors
    print(f"Fatal error: {e}")
    # Stop processing
except BalancePipelineError as e:
    # Handle general pipeline errors
    print(f"Pipeline error: {e}")
```

---

## 📊 **Example Usage Patterns**

### **Complete Processing Workflow**
```python
from balance_pipeline.pipeline_v2 import UnifiedPipeline
from balance_pipeline.analyzer import analyze_balance
from balance_pipeline.export import export_to_excel

# 1. Initialize pipeline
pipeline = UnifiedPipeline(schema_mode="flexible", debug_mode=True)

# 2. Process files
df = pipeline.process_files([
    "csv_inbox/Ryan/checking.csv",
    "csv_inbox/Jordyn/chase.csv"
])

# 3. Analyze balances
balance_result = analyze_balance(
    df, 
    ryan_percentage=0.57,
    jordyn_percentage=0.43
)

# 4. Export results
export_to_excel(
    df=df,
    output_path="output/monthly_analysis.xlsx",
    include_pivot_tables=True
)

print(f"Processed {len(df)} transactions")
print(f"Balance result: {balance_result}")
```

### **Custom Schema Processing**
```python
from balance_pipeline.schema_registry import load_schema_registry
from balance_pipeline.csv_consolidator import process_csv_files

# Load custom schema registry
schemas = load_schema_registry("custom_schemas.yml")

# Process with custom schemas
result_df = process_csv_files(
    file_paths=["new_bank_format.csv"],
    schema_registry_data=schemas,
    debug_mode=True
)
```

---

## 🔧 **Development Extensions**

### **Plugin Architecture**
```python
from balance_pipeline.foundation import CORE_FOUNDATION_COLUMNS

class CustomProcessor:
    def __init__(self):
        self.required_columns = CORE_FOUNDATION_COLUMNS
    
    def preprocess(self, df):
        """Custom preprocessing logic"""
        # Implementation here
        return df
    
    def postprocess(self, df):
        """Custom postprocessing logic"""
        # Implementation here
        return df

# Register custom processor
pipeline.register_processor(CustomProcessor())
```

---

**This API reference provides comprehensive integration points for all BALANCE-pyexcel components, enabling custom extensions and advanced usage patterns for production financial analysis systems.**