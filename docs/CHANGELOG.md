# CHANGELOG

## [0.3.2] – 2025-07-31
### Added
* Comprehensive pipeline validation and deployment status report
* Enhanced documentation structure with status indicators
* CI/CD pipeline documentation in README
* New `docs/DEPLOYMENT_STATUS.md` with validation results
* Complete rewrite of `docs/quick_start.md` with CLI-first approach

### Changed
* Updated README with operational status badges
* Enhanced quick start guide with troubleshooting section
* Version bump to 0.3.2 for documentation updates

### Validated
* All critical pipeline components confirmed intact
* CI/CD infrastructure fully operational
* Repository reorganization verified as file moves, not deletions

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
