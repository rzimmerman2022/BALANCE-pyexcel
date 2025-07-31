# CHANGELOG

## [0.3.2] – 2025-07-31 🏆 **GOLD STANDARD ACHIEVED**
### Added
* 🏆 **GOLD STANDARD DOCUMENTATION**: Comprehensive documentation suite with 25+ files
* 📊 **COMPREHENSIVE_PROJECT_STATUS.md**: 50+ section complete project status report
* 📋 **OUTSTANDING_ISSUES.md**: Organized action plan with priority-based tracking
* 📚 **docs/PROJECT_SUMMARY.md**: Executive-level achievement summary
* 📚 **docs/PRODUCTION_OPERATIONS.md**: Complete operational procedures guide
* 📚 **docs/DEPLOYMENT_STATUS.md**: Pipeline validation and health monitoring
* 🚀 **Production Quick Start**: Validated commands for real banking data processing
* 🧪 **Complete Pipeline Validation**: 5 bank formats tested end-to-end successfully

### Changed
* 📈 **README.md**: Enhanced with gold standard status badges and production readiness
* 🔧 **Pipeline Configuration**: Fixed all import dependencies and configuration paths
* 📊 **Status Reporting**: Updated all documentation to reflect production readiness
* 🎯 **User Experience**: Added production-ready command examples and workflows

### Validated
* ✅ **Pipeline Processing**: 5 bank formats (Chase, Discover, Wells Fargo, Monarch, Rocket)
* ✅ **End-to-End Testing**: Complete transaction processing with Excel/Parquet output
* ✅ **Schema Matching**: Automatic detection and processing of multiple bank formats
* ✅ **Data Integrity**: Transaction deduplication, merchant normalization, owner tagging
* ✅ **CI/CD Infrastructure**: Multi-platform testing, automated deployment, quality gates
* ✅ **Production Readiness**: All critical components operational and documented

### Technical Achievements
* 🔧 **Configuration Fixes**: Resolved SCHEMA_REGISTRY_PATH and MERCHANT_LOOKUP_PATH issues
* 🧪 **Validation Script**: Created `test_all_data.py` for comprehensive testing
* 📁 **CSV Inbox**: Organized directory structure for banking data import
* 🏗️ **Project Structure**: Industry-standard organization with comprehensive validation

## [0.3.1] – 2025-07-30
### Added
* Repository reorganization to industry best practices
* Professional folder structure for scripts and utilities
* Organized documentation and configuration directories

### Changed
* Moved 40+ scripts to categorized directories
* Centralized configuration files in `config/`
* Archived historical data in `data/_archive/`

## [0.3.0] – 2025-06-11
### Added
* Dual-mode ledger parser – supports standard `Date,Description,Amount` CSV _and_ single-column "vertical" export
* Header-normalisation map extended (`running_balance`, rent portion columns)
* Zero-sum invariant check now fails fast if Ryan + Jordyn ≠ 0 after reconciliation
* Fixture **vertical_ledger.csv** and unit test **test_ledger_parser** to guarantee vertical-format parsing remains green

### Fixed
* Rent 43 / 57 split now applied only to rent rows
* Leading/trailing-space headers in Expense CSV normalised

### Internal
* Version bumped to **0.3.0** in `pyproject.toml`
* All tests pass (23 total); baseline CLI yields Ryan + Jordyn = 0.00 with ≥ 90 % consistency
