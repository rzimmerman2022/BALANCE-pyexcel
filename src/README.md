# BALANCE Source Code Structure

**Last Updated:** 2025-08-10  
**Purpose:** Source code organization and navigation guide

---

## 📁 **Source Code Overview**

The `src/` directory contains the core Python packages that power the BALANCE-pyexcel financial analysis pipeline.

### **Main Entry Points**

#### **Primary Entry Point**
```bash
# Via the master pipeline script (RECOMMENDED)
.\pipeline.ps1 process

# Direct Python access (for development)
poetry run python -m balance_pipeline.main process --help
```

#### **Alternative CLI Entry Points**
```bash
# Legacy CLI interface
poetry run balance-legacy-cli --help

# Merchant-specific operations  
poetry run balance-merchant --help

# Analysis operations
poetry run balance-analyze --help

# Baseline analyzer
poetry run balance-baseline --help
```

---

## 🏗️ **Package Structure**

### **`balance_pipeline/` - Core Financial Pipeline**
**Main Module:** Primary financial data processing engine

**Key Files:**
- **`main.py`** - 🚀 **MAIN PYTHON ENTRY POINT** - CLI interface and argument parsing
- **`pipeline_v2.py`** - 🔧 **CORE ORCHESTRATOR** - UnifiedPipeline class that coordinates all processing
- **`csv_consolidator.py`** - 📊 **CSV PROCESSING ENGINE** - Handles multi-bank CSV file processing
- **`config.py`** - ⚙️ **CONFIGURATION MANAGEMENT** - Settings and parameter management
- **`schema_registry.py`** - 📋 **SCHEMA SYSTEM** - Bank format definitions and matching

**Processing Modules:**
- `ingest.py` - Data ingestion and validation
- `normalize.py` - Transaction normalization and standardization  
- `data_loader.py` - File loading and parsing
- `transaction_cleaner.py` - Data cleaning and deduplication
- `merchant.py` - Merchant name normalization
- `analytics.py` - Financial analysis and calculations

**I/O Modules:**
- `export.py` - Output format handling
- `outputs.py` - Report generation
- `viz.py` - Visualization and charts

**Utility Modules:**
- `errors.py` - Custom exception definitions
- `utils.py` - General utilities
- `constants.py` - Application constants
- `logging_config.py` - Logging setup

### **`baseline_analyzer/` - Balance Analysis Tools**
**Purpose:** Specialized balance reconciliation and analysis

**Key Files:**
- **`cli.py`** - Command-line interface for baseline analysis
- **`processing.py`** - Core balance calculation logic
- **`baseline_math.py`** - Mathematical operations for balance calculations
- **`config.py`** - Configuration management
- **`opening_balance.py`** - Opening balance calculations
- **`recon.py`** - Reconciliation logic

### **`utils/` - Shared Utilities**
**Purpose:** Shared utility functions (currently empty - reserved for future use)

---

## 🔄 **Data Flow Architecture**

### **Main Processing Flow**
```
1. Entry Point (main.py)
   ↓
2. Pipeline Orchestrator (pipeline_v2.py)
   ↓
3. CSV Consolidator (csv_consolidator.py)
   ↓
4. Schema Registry (schema_registry.py) → Bank Format Detection
   ↓
5. Data Processing Chain:
   - Ingestion (ingest.py)
   - Normalization (normalize.py)  
   - Cleaning (transaction_cleaner.py)
   - Merchant Processing (merchant.py)
   ↓
6. Analysis & Export:
   - Analytics (analytics.py)
   - Visualization (viz.py)
   - Export (export.py, outputs.py)
```

### **Configuration Flow**
```
config.py → schema_registry.py → Business Rules → Processing Modules
    ↓              ↓                    ↓              ↓
Settings      Bank Formats        External Rules    Runtime Config
```

---

## 🧭 **Navigation Guide**

### **For New Developers**
**Start Here:**
1. `main.py` - Understand the CLI interface
2. `pipeline_v2.py` - Learn the orchestration logic
3. `csv_consolidator.py` - Understand CSV processing
4. `config.py` - Learn configuration system

### **For Feature Development**
**Processing Features:** Add to appropriate modules in `balance_pipeline/`
**Analysis Features:** Consider `baseline_analyzer/` or `balance_pipeline/analytics.py`
**I/O Features:** Modify `export.py` or `outputs.py`
**Schema Changes:** Update `schema_registry.py` and related config files

### **For Debugging**
**Entry Points:** Start with `main.py` for CLI issues
**Data Processing:** Check `csv_consolidator.py` and `ingest.py`
**Business Logic:** Review `analytics.py` and `baseline_analyzer/`
**Configuration:** Verify `config.py` and external config files

---

## 🔧 **Development Workflows**

### **Running Components Directly**
```bash
# Main pipeline (development mode)
poetry run python src/balance_pipeline/main.py process --help

# Baseline analyzer (development mode)  
poetry run python -m baseline_analyzer.cli --help

# Individual modules (for testing)
poetry run python -c "from balance_pipeline.csv_consolidator import CSVConsolidator; print('OK')"
```

### **Testing Components**
```bash
# Run tests for specific packages
poetry run pytest tests/balance_analyzer/  # Balance analyzer tests
poetry run pytest tests/test_csv_consolidator.py  # CSV consolidator tests
poetry run pytest tests/test_unified_pipeline.py  # Main pipeline tests
```

### **Adding New Features**
1. **Identify the appropriate module** based on functionality
2. **Follow existing patterns** in the codebase
3. **Add comprehensive tests** in the `tests/` directory
4. **Update configuration** if needed
5. **Document the feature** in relevant docs

---

## 📚 **Module Dependencies**

### **Core Dependencies**
- **`main.py`** depends on `pipeline_v2.py`, `config.py`
- **`pipeline_v2.py`** depends on `csv_consolidator.py`, `schema_registry.py`
- **`csv_consolidator.py`** depends on most processing modules
- **All modules** depend on `config.py` and `errors.py`

### **External Dependencies**
- **Configuration Files:** `config/`, `rules/`
- **Schema Definitions:** `rules/schema_registry.yml`
- **Business Rules:** `config/business_rules.yml`

---

## ⚡ **Quick Reference**

### **Main Entry Points**
| Command | Module | Purpose |
|---------|--------|---------|
| `.\pipeline.ps1` | `main.py` | Primary interface (RECOMMENDED) |
| `balance-pipe` | `main.py` | Direct Python CLI |
| `balance-analyze` | `analyzer.py` | Analysis operations |
| `balance-baseline` | `baseline_analyzer/cli.py` | Balance analysis |

### **Key Classes**
| Class | Module | Purpose |
|-------|--------|---------|
| `UnifiedPipeline` | `pipeline_v2.py` | Main orchestrator |
| `CSVConsolidator` | `csv_consolidator.py` | CSV processing |
| `SchemaRegistry` | `schema_registry.py` | Bank format handling |

### **Configuration Files**
| File | Purpose | Location |
|------|---------|----------|
| Schema definitions | Bank CSV formats | `rules/schema_registry.yml` |
| Business rules | External configuration | `config/business_rules.yml` |
| Analysis settings | Analyzer parameters | `config/balance_analyzer.yaml` |

---

**Navigate with confidence!** 🧭  
This source code is designed for clarity and maintainability.