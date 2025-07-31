# Production Operations Guide

**Status**: ✅ **PRODUCTION READY**  
**Version**: 0.3.2  
**Target Users**: Production operators, financial analysts

---

## Overview

This guide provides comprehensive operational procedures for running BALANCE-pyexcel in production with real banking data. All procedures have been validated and tested.

---

## 🚀 **Production Deployment**

### **Prerequisites Checklist**
- [ ] ✅ Python 3.11+ installed
- [ ] ✅ Poetry package manager installed
- [ ] ✅ All dependencies installed (`poetry install --with dev`)
- [ ] ✅ Banking data exported from all accounts
- [ ] ✅ Data organized in `csv_inbox/` structure

### **Environment Setup**
```bash
# Verify installation
poetry --version
python --version

# Install project dependencies
cd C:\Projects\BALANCE
poetry install --with dev

# Verify pipeline functionality
python test_all_data.py
```

---

## 📊 **Daily Operations**

### **Morning Data Processing**
```bash
# 1. Quick health check
python scripts/analysis/simple_balance_check.py

# 2. Process any new banking data
python -c "
import sys; sys.path.insert(0, 'src')
from balance_pipeline.main import main
sys.argv = ['main', 'process', 'csv_inbox/**.csv', '--output-type', 'powerbi']
main()
"

# 3. Generate daily status report
python scripts/utilities/comprehensive_audit_trail.py
```

### **Transaction Review Workflow**
1. **Open Excel Output**: `output/balance_data.xlsx`
2. **Review Queue_Review Sheet**: Categorize new transactions
3. **Mark Shared Expenses**: Y/N/S (Split) + percentage
4. **Re-run Processing**: Update with new categorizations

---

## 📅 **Weekly Operations**

### **Weekly Reconciliation**
```bash
# Comprehensive analysis
.\Run-ComprehensiveAnalyzer.ps1

# Balance verification
python scripts/analysis/careful_verification.py

# Generate weekly reports
python scripts/utilities/final_balance_verification.py
```

### **Data Quality Check**
```bash
# Investigate any issues
python scripts/investigations/financial_issue_detector.py

# Deep analysis if needed
python scripts/analysis/deep_analysis.py

# Check merchant normalization
python scripts/analysis/understand_real_system.py
```

---

## 🗓️ **Monthly Operations**

### **Month-End Reconciliation**
```bash
# Generate comprehensive monthly report
python scripts/utilities/comprehensive_transaction_audit.py

# Final balance settlement
python scripts/utilities/final_settlement.py

# Archive processed data
# (Manual step - move processed files to data/_archive/)
```

### **Performance Review**
```bash
# Check processing performance
python tools/diagnose_analyzer.py

# System health check
# Review logs in logs/ directory
# Check output files in output/ directory
```

---

## 🎛️ **Operational Commands Reference**

### **Core Processing**
```bash
# Test processing (safe)
python test_all_data.py

# Process real data (production)
python -c "
import sys; sys.path.insert(0, 'src')
from balance_pipeline.main import main
sys.argv = ['main', 'process', 'csv_inbox/**.csv', '--output-type', 'powerbi', '--output', 'output/monthly_data.parquet']
main()
"

# Process with debugging
python -c "
import sys; sys.path.insert(0, 'src')
from balance_pipeline.main import main
sys.argv = ['main', 'process', 'csv_inbox/**.csv', '--debug', '-vv']
main()
"
```

### **Analysis & Reporting**
```bash
# Quick balance check
python scripts/analysis/simple_balance_check.py

# Comprehensive analysis
python scripts/utilities/comprehensive_audit_trail.py

# Rent payment analysis
python scripts/analysis/rent_logic_check.py

# Transaction verification
python scripts/analysis/careful_verification.py
```

### **Troubleshooting**
```bash
# System diagnostics
python tools/diagnose_analyzer.py

# Debug data issues
python tools/debug_runner.py

# Investigate problems
python scripts/investigations/critical_issue_investigator.py

# Financial issue detection
python scripts/investigations/financial_issue_detector.py
```

---

## 📈 **Power BI Operations**

### **Data Refresh Process**
1. **Run Pipeline**: Generate latest Parquet files
2. **Open Power BI**: Connect to `output/unified_pipeline/*.parquet`
3. **Refresh Data**: Update dashboard with new transactions
4. **Publish**: Update online dashboard if configured

### **Dashboard Monitoring**
- **Daily**: Check transaction counts and balances
- **Weekly**: Review spending patterns and categories
- **Monthly**: Analyze trends and generate reports

---

## 🔧 **Configuration Management**

### **Schema Updates**
When adding new bank formats:
1. **Create Schema File**: `rules/new_bank_format_v1.yaml`
2. **Test Processing**: Use sample data first
3. **Validate Output**: Verify transaction processing
4. **Document Format**: Update schema documentation

### **Merchant Rules**
To improve merchant normalization:
1. **Edit Lookup**: `rules/merchant_lookup.csv`
2. **Add Mappings**: Raw merchant name → Clean name
3. **Test Changes**: Process sample transactions
4. **Validate Results**: Check merchant cleaning accuracy

---

## ⚠️ **Error Handling Procedures**

### **Common Issues & Solutions**

**Issue**: File not found errors
```bash
# Solution: Check file paths and permissions
ls csv_inbox/
python -c "import glob; print(glob.glob('csv_inbox/*/*.csv'))"
```

**Issue**: Schema matching failures
```bash
# Solution: Check schema registry and file formats
python tools/diagnose_analyzer.py
# Review logs in logs/ directory
```

**Issue**: Balance calculation discrepancies
```bash
# Solution: Run comprehensive verification
python scripts/analysis/careful_verification.py
python scripts/investigations/investigate_imbalance.py
```

### **Escalation Process**
1. **Self-Diagnosis**: Use diagnostic tools
2. **Check Documentation**: Review relevant guides
3. **Review Logs**: Examine error details in logs/
4. **Apply Corrections**: Use scripts in scripts/corrections/

---

## 📊 **Monitoring & Alerts**

### **Health Checks**
```bash
# Daily health check
python scripts/analysis/simple_balance_check.py

# System status
# Check: docs/PIPELINE_STATUS.md
# Review: GitHub Actions status
# Monitor: Processing logs in logs/
```

### **Key Metrics to Monitor**
- **Transaction Processing**: Success rates and error counts
- **Balance Accuracy**: Deviation from expected balances
- **Data Quality**: Missing or malformed transactions
- **Performance**: Processing times and resource usage

---

## 🔐 **Security & Compliance**

### **Data Protection**
- **Local Processing**: All data remains on local machine
- **No Transmission**: No data sent to external services
- **Audit Trails**: Complete transaction lineage tracking
- **Access Control**: File system permissions only

### **Backup Procedures**
```bash
# Backup processed data
cp -r output/ backups/output_$(date +%Y%m%d)/
cp -r csv_inbox/ backups/csv_inbox_$(date +%Y%m%d)/

# Backup configuration
cp -r config/ backups/config_$(date +%Y%m%d)/
cp -r rules/ backups/rules_$(date +%Y%m%d)/
```

---

## 📞 **Support Resources**

### **Documentation**
- **Quick Start**: `docs/quick_start.md`
- **Pipeline Status**: `docs/PIPELINE_STATUS.md`
- **Scripts Guide**: `docs/scripts_guide.md`
- **Troubleshooting**: `OUTSTANDING_ISSUES.md`

### **Tools & Utilities**
- **Diagnostic Tools**: `tools/` directory
- **Analysis Scripts**: `scripts/analysis/` directory
- **Correction Tools**: `scripts/corrections/` directory
- **Investigation Tools**: `scripts/investigations/` directory

---

## 🎯 **Success Criteria**

### **Daily Success**
- [ ] New transactions processed successfully
- [ ] Balance calculations accurate
- [ ] No critical errors in logs
- [ ] Power BI dashboard updated

### **Weekly Success**
- [ ] All accounts reconciled
- [ ] Transaction categorization complete
- [ ] Quality checks passed
- [ ] Reports generated successfully

### **Monthly Success**
- [ ] Comprehensive reconciliation complete
- [ ] Balance settlement accurate
- [ ] Performance within acceptable limits
- [ ] All data archived properly

---

**This guide ensures professional-grade operations of the BALANCE-pyexcel system with comprehensive procedures for daily, weekly, and monthly financial analysis workflows.**