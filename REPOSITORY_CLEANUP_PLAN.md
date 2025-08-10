# Repository Cleanup and Standardization Plan

## File Analysis & Categorization

### KEEP - Core Production Files
**Main Entry Points:**
- `pipeline.ps1` - Master entry point
- `src/balance_pipeline/main.py` - Python CLI entry
- `src/balance_pipeline/pipeline_v2.py` - Core pipeline

**Source Code:**
- `src/balance_pipeline/` - Core Python package ✅
- `src/baseline_analyzer/` - Analysis tools ✅
- `tests/` - Test suite ✅

**Configuration:**
- `config/` - Configuration files ✅
- `rules/` - Schema definitions ✅
- `pyproject.toml`, `poetry.lock`, `pytest.ini` - Python project files ✅

**Documentation:**
- `README.md` - Main documentation ✅
- `docs/` - Comprehensive documentation ✅
- `LICENSE` - MIT License ✅
- `CHANGELOG.md` - Version history ✅
- `PIPELINE_COMMANDS.md` - Command reference ✅

**Essential Utilities:**
- `scripts/utilities/quick_powerbi_prep.py` - Data prep utility ✅
- `scripts/utilities/dispute_analyzer_gui.py` - Modern GUI ✅
- `scripts/utilities/dispute_analyzer.py` - CLI analyzer ✅

### ARCHIVE - Non-Essential Files
**Massive Archive Directory:**
- `_ARCHIVE_FOR_REVIEW_BEFORE_DELETION/` → Move to `/archive/legacy/`

**Analysis Scripts (Keep Core, Archive Rest):**
- `scripts/analysis/` - Most can be archived, keep key ones
- `scripts/corrections/` - Archive all (legacy correction scripts)
- `scripts/investigations/` - Archive all (one-time investigations)

**Generated Outputs:**
- `output/` - Keep structure, archive old files
- `audit_reports/` - Archive old reports
- `artifacts/` - Archive all

**Legacy Tools:**
- `tools/` - Archive most, keep essential debug tools

**Sample Data:**
- `sample_data_multi/`, `samples/` - Archive to reduce repo size

### NEW STRUCTURE - Post Cleanup
```
BALANCE/
├── 📄 README.md                    # Comprehensive guide
├── 📄 CHANGELOG.md                 # Version history
├── 📄 LICENSE                      # MIT License
├── 📄 pipeline.ps1                 # Master entry point
├── 📄 pyproject.toml              # Python project config
├── 📄 poetry.lock                 # Dependencies
├── 📄 pytest.ini                 # Test config
├── 📁 src/                        # Source code
│   ├── 📁 balance_pipeline/       # Core pipeline
│   └── 📁 baseline_analyzer/      # Analysis tools
├── 📁 docs/                       # Documentation
├── 📁 tests/                      # Test suite
├── 📁 config/                     # Configuration
├── 📁 rules/                      # Schema definitions
├── 📁 csv_inbox/                  # Input directory
├── 📁 output/                     # Output directory
├── 📁 scripts/                    # Essential utilities only
│   └── 📁 utilities/              # Key utility scripts
├── 📁 archive/                    # Archived content
│   ├── 📁 legacy/                 # Old archive content
│   ├── 📁 analysis/               # Old analysis scripts
│   ├── 📁 investigations/         # Investigation scripts
│   └── 📁 generated/              # Old generated files
└── 📁 workbook/                   # Excel templates
```

## Cleanup Actions

### Phase 1: Archive Operations
1. Create `/archive/` directory structure
2. Move `_ARCHIVE_FOR_REVIEW_BEFORE_DELETION/` → `archive/legacy/`
3. Move `scripts/analysis/` → `archive/analysis/`
4. Move `scripts/corrections/` → `archive/corrections/`
5. Move `scripts/investigations/` → `archive/investigations/`
6. Move old output files → `archive/generated/`

### Phase 2: Documentation Standardization
1. Update all `.md` files to consistent format
2. Add table of contents to longer documents
3. Ensure code examples are tested
4. Add timestamps and version numbers
5. Create comprehensive API documentation

### Phase 3: Directory Restructuring
1. Keep `src/` as main source directory
2. Streamline `scripts/` to essential utilities only
3. Organize `docs/` by category
4. Clean up `config/` and `rules/`
5. Preserve `tests/` structure

### Phase 4: Entry Point Validation
1. Ensure `pipeline.ps1` works correctly
2. Validate `src/balance_pipeline/main.py`
3. Test all documented commands
4. Update documentation with any changes

## File Retention Criteria

**KEEP IF:**
- Currently used in production
- Referenced in main documentation
- Part of core pipeline functionality
- Essential utility script
- Test file with current tests

**ARCHIVE IF:**
- Legacy/deprecated functionality
- One-time analysis or investigation
- Backup or temporary files
- Old generated outputs
- Experimental code not in use

**DELETE IF:**
- Clearly temporary files (`.tmp`, `.bak`)
- Duplicate files
- Empty or placeholder files
- Build artifacts that can be regenerated