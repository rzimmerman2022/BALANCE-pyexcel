# Scripts Guide - Production Operations

**Status**: ✅ **PRODUCTION READY**  
**Version**: 0.3.2  
**Last Updated**: 2025-07-31

---

## Overview

This guide provides comprehensive documentation for all 40+ utility scripts in the BALANCE-pyexcel project. All scripts have been tested and validated for production use with real banking data.

### **Script Organization**
The scripts are organized into functional categories following industry best practices:
- **📊 Analysis Scripts**: Data analysis and investigation (8 scripts)
- **🔧 Correction Scripts**: Data repair and fixes (6 scripts)  
- **🔍 Investigation Scripts**: Issue debugging and diagnosis (3 scripts)
- **⚙️ Utility Scripts**: General processing and operations (20+ scripts)

## Script Categories

### 📁 scripts/analysis/
**Purpose**: Data analysis and transaction investigation

| Script | Description | Usage |
|--------|-------------|-------|
| `deep_analysis.py` | Comprehensive transaction analysis | Detailed financial pattern analysis |
| `transaction_count_analysis.py` | Transaction volume analysis | Volume and frequency metrics |
| `rent_logic_check.py` | Rent payment logic validation | Verify rent allocation logic |
| `simple_balance_check.py` | Basic balance verification | Quick balance sanity check |
| `careful_verification.py` | Detailed verification process | Thorough data verification |
| `understand_real_system.py` | System behavior analysis | Understand financial patterns |
| `imbalance_vs_settlement_explanation.py` | Imbalance analysis | Explain balance discrepancies |

### 📁 scripts/corrections/
**Purpose**: Data correction and repair utilities

| Script | Description | Usage |
|--------|-------------|-------|
| `rent_allocation_corrector.py` | Fix rent allocation issues | Correct rent payment allocations |
| `final_balance_correction.py` | Balance reconciliation | Fix balance discrepancies |
| `integrate_rent_corrections.py` | Apply rent corrections | Integrate rent fixes into main data |
| `rent_allocation_correction_analysis.py` | Analyze rent corrections | Review correction effectiveness |
| `create_final_correct_audit.py` | Generate corrected audit trail | Create final corrected records |
| `truly_correct_rent.py` | Ultimate rent correction | Final rent payment fixes |

### 📁 scripts/investigations/
**Purpose**: Issue investigation and debugging

| Script | Description | Usage |
|--------|-------------|-------|
| `critical_issue_investigator.py` | Critical issue detection | Find critical financial issues |
| `financial_issue_detector.py` | Financial anomaly detection | Detect financial anomalies |
| `investigate_imbalance.py` | Balance discrepancy investigation | Investigate balance problems |

**Report Files**:
- `financial_dashboard_report_*.txt` - Financial dashboard reports
- `financial_issues_report_*.txt` - Issue investigation reports

### 📁 scripts/utilities/
**Purpose**: General utility and processing scripts

#### Audit Trail Utilities
| Script | Description |
|--------|-------------|
| `comprehensive_audit_trail.py` | Complete audit trail generation |
| `enhanced_audit_trail.py` | Enhanced audit trail with metadata |
| `detailed_transaction_audit_generator.py` | Detailed transaction auditing |
| `comprehensive_transaction_audit.py` | Full transaction audit process |

#### Zelle Integration
| Script | Description |
|--------|-------------|
| `zelle_integration.py` | Main Zelle payment processing |
| `zelle_data_loader.py` | Load Zelle transaction data |
| `zelle_matcher.py` | Match Zelle transactions |
| `zelle_quick_start.py` | Quick Zelle setup |
| `zelle_summary_report.py` | Zelle transaction summaries |
| `comprehensive_zelle_integration.py` | Full Zelle integration |

#### Processing Utilities
| Script | Description |
|--------|-------------|
| `final_verification.py` | Final data verification |
| `final_reconciliation.py` | Final reconciliation process |
| `final_settlement.py` | Final settlement calculations |
| `final_balance_verification.py` | Final balance verification |
| `final_summary_report.py` | Final summary generation |

#### Power BI & Reporting
| Script | Description |
|--------|-------------|
| `powerbi_data_refresh.py` | Power BI data refresh utilities |
| `enhanced_financial_dashboard.py` | Enhanced dashboard generation |
| `transaction_reconciliation_report.py` | Transaction reconciliation reports |

#### Development & Testing
| Script | Description |
|--------|-------------|
| `test_cleaning.py` | Data cleaning tests |
| `test_rent_fix.py` | Rent fix validation tests |
| `debug_bad_rows.py` | Debug problematic data rows |
| `diagnose_reconciliation.py` | Diagnose reconciliation issues |
| `audit_run.py` | Run audit processes |
| `quick_check.py` | Quick system checks |
| `real_data_plan.py` | Real data processing plan |

## Root Scripts
Scripts remaining in the main scripts directory for general use:

| Script | Description |
|--------|-------------|
| `Run-ComprehensiveAnalyzer.py` | Main comprehensive analysis runner |
| `analyzer.py` | Core analyzer functionality |
| `comprehensive_balance_analyzer.py` | Comprehensive balance analysis |

## Usage Examples

### Running Analysis Scripts
```bash
# Basic balance check
python scripts/analysis/simple_balance_check.py

# Deep transaction analysis  
python scripts/analysis/deep_analysis.py

# Rent logic validation
python scripts/analysis/rent_logic_check.py
```

### Running Correction Scripts
```bash
# Fix rent allocations
python scripts/corrections/rent_allocation_corrector.py

# Apply balance corrections
python scripts/corrections/final_balance_correction.py

# Integrate rent corrections
python scripts/corrections/integrate_rent_corrections.py
```

### Running Investigation Scripts
```bash
# Investigate critical issues
python scripts/investigations/critical_issue_investigator.py

# Detect financial issues
python scripts/investigations/financial_issue_detector.py

# Investigate balance problems
python scripts/investigations/investigate_imbalance.py
```

### Running Utility Scripts
```bash
# Generate audit trail
python scripts/utilities/comprehensive_audit_trail.py

# Process Zelle transactions
python scripts/utilities/zelle_integration.py

# Refresh Power BI data
python scripts/utilities/powerbi_data_refresh.py
```

## PowerShell Scripts
Located in the root directory:

| Script | Description |
|--------|-------------|
| `Run-Analysis.ps1` | Main analysis runner |
| `Run-ComprehensiveAnalyzer.ps1` | Comprehensive analysis |
| `Clean-Repository.ps1` | Repository cleanup |
| `analyze_rent_payments.ps1` | Rent payment analysis |
| `consolidate_analysis_files.ps1` | Consolidate analysis outputs |

## Best Practices

1. **Always backup data** before running correction scripts
2. **Run analysis scripts first** to understand issues
3. **Use investigation scripts** to debug specific problems  
4. **Apply corrections incrementally** and verify results
5. **Generate audit trails** after major changes
6. **Use utility scripts** for routine processing tasks

## Output Locations

- **Analysis outputs**: `analysis_output/`
- **Reports**: `reports/`
- **Audit trails**: `audit_reports/`
- **Corrected data**: `data/_archive/` (timestamped)
- **Logs**: `logs/`

## Getting Help

For detailed help on any script, run:
```bash
python <script_name> --help
```

Or examine the script's docstring and comments for usage instructions.