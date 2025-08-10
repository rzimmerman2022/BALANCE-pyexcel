# CLEANUP MANIFEST - Repository Analysis and File Classification

**Created:** 2025-08-10  
**Version:** v1.0  
**Purpose:** Comprehensive analysis and classification of all files in the BALANCE repository for systematic cleanup

---

## 🎯 **Repository Overview**

**Project:** BALANCE-pyexcel - Gold Standard Financial Analysis Pipeline  
**Main Entry Point:** `pipeline.ps1` (Master entry point for all operations)  
**Core Engine:** `src/balance_pipeline/main.py` and `src/balance_pipeline/pipeline_v2.py`  
**Architecture:** Production-ready Python pipeline with comprehensive documentation and CI/CD

---

## 📊 **Classification Summary**

| Category | File Count | Description |
|----------|------------|-------------|
| **CORE** | ~85 files | Essential for operation - main pipeline, src code, configs |
| **DOCUMENTATION** | ~45 files | Important knowledge and guides |
| **DEPRECATED** | ~200+ files | Old/unused files in archive directories |
| **EXPERIMENTAL** | ~50+ files | Investigation tools and analysis scripts |
| **REDUNDANT** | ~30+ files | Duplicate functionality or legacy alternatives |

---

## 🔍 **FILE CLASSIFICATION AND ANALYSIS**

### **CORE FILES (Essential for Operation)**

#### **Primary Entry Points**
- `pipeline.ps1` - **MAIN ENTRY POINT** - Master pipeline script handling all operations
- `src/balance_pipeline/main.py` - Python CLI entry point
- `src/balance_pipeline/pipeline_v2.py` - UnifiedPipeline orchestrator

#### **Core Source Code**
- `src/balance_pipeline/` - **PRIMARY PACKAGE** (25+ modules)
  - `analyzer.py`, `config.py`, `csv_consolidator.py` - Core processing
  - `data_loader.py`, `ingest.py`, `normalize.py` - Data ingestion
  - `schema_registry.py`, `schema_types.py` - Schema management
  - `export.py`, `outputs.py` - Output generation
  - All other modules in this directory
- `src/baseline_analyzer/` - **SECONDARY PACKAGE** (8+ modules)
  - Balance analysis and reconciliation tools

#### **Configuration System**
- `pyproject.toml` - **CRITICAL** - Project configuration and dependencies
- `poetry.lock` - **CRITICAL** - Dependency lock file
- `config/` directory contents:
  - `balance_analyzer.yaml` - Analysis settings
  - `business_rules.yml` - External business rules
  - `canonical_schema_v2.yaml` - Schema definitions
- `rules/` directory contents:
  - `schema_registry.yml` - **CRITICAL** - Bank CSV format definitions
  - `merchant_lookup.csv` - Merchant normalization rules
  - All individual schema files (*.yaml)

#### **Testing Infrastructure**
- `pytest.ini` - **CRITICAL** - Test configuration
- `tests/` directory (30+ test files) - **ALL ESSENTIAL**
  - Core test suite ensuring pipeline reliability

#### **Essential Scripts**
- `scripts/powershell/` - PowerShell utility scripts
- `scripts/quick_check.py` - System validation
- `scripts/run_baseline.py` - Baseline analysis runner

### **DOCUMENTATION FILES (Keep - Important Knowledge)**

#### **Primary Documentation**
- `README.md` - **MAIN PROJECT DOCUMENTATION**
- `CHANGELOG.md` - Version history
- `LICENSE` - MIT license
- `PIPELINE_COMMANDS.md` - Command reference

#### **Comprehensive Guides**
- `docs/` directory (25+ documentation files):
  - `ARCHITECTURE.md` - System design
  - `DEPLOYMENT_STATUS.md` - Production status
  - `API_REFERENCE.md` - API documentation
  - `CONFIGURATION_GUIDE.md` - Setup instructions
  - `user_guide.md`, `quick_start.md` - User instructions
  - All other .md files in docs/ - **KEEP ALL**

### **DEPRECATED FILES (Archive - Old/Unused)**

#### **Legacy Archive Structure**
- `archive/legacy/` - **ENTIRE DIRECTORY IS DEPRECATED**
  - Contains old project versions and abandoned approaches
  - Multiple duplicate copies of old implementations
  - Virtual environment files (should never be in repo)
  - Old PowerBI files and temporary data

#### **Specific Deprecated Items**
- `archive/legacy/_ARCHIVE_FOR_REVIEW_BEFORE_DELETION/` - **READY FOR DELETION**
- `archive/legacy/_ARCHIVE_TO_DELETE_OLD/` - **READY FOR DELETION**
- Files in `archive/legacy/` with duplicate functionality
- Virtual environment directories in archive (venv/, .venv/)

### **EXPERIMENTAL FILES (Archive - Unfinished Features)**

#### **Investigation Tools**
- `archive/investigations/` - Analysis and debugging tools
  - `critical_issue_investigator.py`
  - `financial_issue_detector.py` 
  - `investigate_imbalance.py`

#### **Analysis Scripts**
- `archive/analysis/` - Historical analysis scripts
  - Various verification and checking scripts
  - Deep analysis tools for troubleshooting

#### **Generated Reports and Temporary Files**
- `archive/generated/` - Output from various analysis runs
  - `artifacts/`, `audit_reports/`, `data/` subdirectories
  - Large volumes of CSV files and temporary outputs

### **REDUNDANT FILES (Archive - Duplicate Functionality)**

#### **Duplicate Scripts**
- Multiple versions of similar analysis scripts in archive/
- Duplicate PowerShell scripts in archive vs scripts/
- Old configuration files superseded by current ones

#### **Output Files That Should Be Gitignored**
- `output/` directory contents (except maybe one sample)
- Various parquet and Excel files in root and archive
- Log files and temporary processing outputs

---

## 🔄 **DEPENDENCIES BETWEEN FILES**

### **Critical Dependencies**
1. **`pipeline.ps1`** → depends on `poetry` and `src/balance_pipeline/main.py`
2. **`src/balance_pipeline/main.py`** → depends on `pipeline_v2.py`
3. **`src/balance_pipeline/pipeline_v2.py`** → depends on all core modules
4. **Schema system** → `rules/schema_registry.yml` required by processing engine
5. **Configuration** → `config/` files loaded by various modules
6. **Tests** → depend on all source code modules

### **Safe to Archive/Delete**
- Everything in `archive/legacy/_ARCHIVE_FOR_REVIEW_BEFORE_DELETION/`
- Everything in `archive/legacy/_ARCHIVE_TO_DELETE_OLD/`
- Virtual environment directories in archive
- Most files in `archive/generated/` (keep some samples for reference)
- Duplicate documentation files in archive vs docs/

---

## 📁 **RECOMMENDED NEW STRUCTURE**

### **Keep in Root**
```
/
├── pipeline.ps1              # MAIN ENTRY POINT
├── README.md                 # Project documentation
├── pyproject.toml           # Project configuration
├── poetry.lock              # Dependencies
├── pytest.ini              # Test configuration
├── CHANGELOG.md             # Version history
├── LICENSE                  # MIT license
└── PIPELINE_COMMANDS.md     # Command reference
```

### **Organized Directories**
```
/src/                        # Source code
/docs/                       # All documentation
/config/                     # Configuration files
/rules/                      # Schema and mapping rules
/tests/                      # Test suite
/scripts/                    # Utility scripts
/csv_inbox/                  # Input directory
/output/                     # Generated outputs (mostly gitignored)
/workbook/                   # Excel templates
/archive/                    # Cleaned and organized archive
```

---

## ⚠️ **SPECIAL CONSIDERATIONS**

### **Files to Handle Carefully**
- `BALANCE-pyexcel.pbix` - Large PowerBI file, may need special handling
- Virtual environment directories - **NEVER commit these to git**
- Large data files - Consider LFS or gitignore
- Log files - Should be gitignored in future

### **Business Logic Dependencies**
- The pipeline processes financial data - ensure no real data is exposed
- Configuration files may contain business logic - validate before changes
- Schema definitions are critical for CSV processing - handle with care

### **Version Control Considerations**
- Large binary files should be evaluated for Git LFS
- Generated output should be gitignored
- Archive should be carefully curated, not just dumped

---

## 🎯 **CLEANUP STRATEGY RECOMMENDATIONS**

1. **Phase 1:** Move clearly deprecated items to archive/deprecated/
2. **Phase 2:** Consolidate duplicate documentation 
3. **Phase 3:** Clean up generated files and outputs
4. **Phase 4:** Optimize gitignore to prevent future clutter
5. **Phase 5:** Create standardized directory structure

---

**Analysis Complete - Ready for Phase 2**