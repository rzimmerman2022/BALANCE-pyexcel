# Archive Directory

**Created**: 2025-08-09  
**Purpose**: Repository cleanup and standardization

This directory contains archived content from the BALANCE repository cleanup process. All files here are preserved for reference but are not part of the active codebase.

## Archive Structure

### `/legacy/`
Contains the original `_ARCHIVE_FOR_REVIEW_BEFORE_DELETION` directory with historical content.

### `/analysis/`
Historical analysis scripts that were part of `scripts/analysis/`:
- One-time analysis utilities
- Investigation scripts for specific issues
- Legacy calculation methods

### `/investigations/`
Investigation scripts from `scripts/investigations/`:
- Critical issue investigators
- Imbalance analysis tools
- Financial dashboard reports

### `/corrections/`
Data correction utilities from `scripts/corrections/`:
- Rent allocation corrections
- Balance correction scripts
- Transaction fixing utilities

### `/generated/`
Previously generated files and outputs:
- **artifacts/** - Old build artifacts
- **audit_reports/** - Historical audit reports  
- **data/** - Legacy data files
- **fixtures/** - Old test fixtures
- **logs/** - Historical log files
- **reports/** - Generated reports
- **sample_data_multi/** - Sample datasets
- **samples/** - Sample files
- **workflows/** - Old workflow definitions

### `/scripts/`
Archived scripts that were in the root `scripts/` directory:
- Legacy analysis utilities
- PowerShell helper scripts
- One-time processing scripts

### `/tools/`
Development tools that were archived:
- Debug utilities
- Profiling tools
- Verification scripts

### `/utilities/`
Utility scripts that were archived from `scripts/utilities/`:
- Legacy processing utilities
- One-time analysis tools
- Historical integration scripts

## Restoration

If any archived content needs to be restored:

1. Identify the required files in this archive
2. Copy (don't move) to appropriate location in active codebase
3. Update imports and dependencies as needed
4. Add tests if restoring to active use

## Cleanup Policy

This archive should be periodically reviewed and truly obsolete content can be permanently deleted after:
- 1 year for generated files and reports
- 2 years for utility scripts
- Permanent retention for significant analysis work

## Contact

For questions about archived content or restoration requests, refer to the git history or project documentation.