# Repository Cleanup Summary

**Date**: 2025-08-04
**Action**: Repository cleanup and reorganization

## Main Pipeline Identified

The main pipeline is located in `src/balance_pipeline/` with the following key components:

- **Entry Point**: `balance-pipe` command (via `main.py`)
- **Core Orchestrator**: `pipeline_v2.py` - UnifiedPipeline class
- **CSV Processing Engine**: `csv_consolidator.py`
- **Flow**: CSV Files → Schema Matching → Data Transformation → Consolidation → Output

## Documentation Status

✅ All documentation accurately reflects the current pipeline architecture and status.

## Folders Renamed for Deletion

The following folders have been renamed with "_OLD_TO_DELETE" suffix for easy identification and removal:

### 1. Backup and Legacy Folders
- `backups_OLD_TO_DELETE/` - Old backup from 2025-06-05
- `legacy_scripts_OLD_TO_DELETE/` - Legacy Python scripts

### 2. Debug and Test Output Folders
- `debug_fresh_OLD_TO_DELETE/` - Old debug outputs
- `debug_full_OLD_TO_DELETE/` - Old debug outputs
- `debug_output_OLD_TO_DELETE/` - Old debug outputs
- `demo_output_OLD_TO_DELETE/` - Old demo outputs
- `test_debug_output_OLD_TO_DELETE/` - Old test debug outputs

### 3. Old Reports
- `debug_reports_OLD_TO_DELETE/` - Debug reports from May 2025
- `audit_reports_OLD_TO_DELETE/` - Audit reports from June 2025

### 4. Empty/Temporary Folders
- `temp_scripts_OLD_TO_DELETE/` - Temporary scripts
- `sample_data_OLD_TO_DELETE/` - Empty folder

### 5. Old Analysis Output
- `analysis_output_v2.3_OLD_TO_DELETE/` - Old analysis results from v2.3

## Files Moved/Renamed

- `sample_data_multi/developer_setup.md` → `docs/developer_setup.md` (moved to proper location)

## Files in artifacts/ Renamed for Deletion

- `2025-05_audit_OLD_TO_DELETE.parquet`
- `2025-05_audit_full_OLD_TO_DELETE.csv`
- `2025-05_meta_rows_OLD_TO_DELETE.parquet`
- `complete_audit_trail_2025-06-21_OLD_TO_DELETE.csv`

## Next Steps

To complete the cleanup, run the following commands:

```bash
# Remove all folders marked for deletion
rm -rf *_OLD_TO_DELETE/

# Remove old files in artifacts
rm artifacts/*_OLD_TO_DELETE.*

# Optional: Remove the utils placeholder
rm src/utils/placeholder.txt
```

## Impact

This cleanup removes approximately:
- 11 unused folders
- Multiple old debug and analysis files
- Improves repository organization and clarity

The cleanup preserves all active code, documentation, and essential data while removing temporary and outdated files.