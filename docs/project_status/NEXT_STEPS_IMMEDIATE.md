# IMMEDIATE NEXT STEPS - Start Here! 🚀

**Goal**: Get all your financial data flowing through the validated pipeline

---

## Phase 1: Data Collection (THIS WEEK)

### Step 1: Export Data from All Accounts 📊

**For Ryan:**
- [ ] **Monarch Money**: Export all historical data (already have schema ✅)
- [ ] **Rocket Money**: Export all historical data (already have schema ✅)
- [ ] **Individual Bank Accounts**: Export directly from banks for comparison
  - [ ] Primary checking account
  - [ ] Savings accounts  
  - [ ] Credit cards
  - [ ] Investment accounts

**For Jordyn:**
- [ ] **Chase Checking**: Export recent data (already have schema ✅)
- [ ] **Discover Card**: Export recent data (already have schema ✅)
- [ ] **Wells Fargo Card**: Export recent data (already have schema ✅)
- [ ] **Other Accounts**: Export any additional accounts
  - [ ] Other credit cards
  - [ ] Savings accounts
  - [ ] Investment accounts

### Step 2: Place Files in Organized Structure

Place downloaded files here:
```
csv_inbox/
├── Ryan/
│   ├── Checking/          # Direct bank exports
│   ├── CreditCard/        # Direct card exports
│   └── Aggregated/        # Monarch/Rocket exports (create this folder)
└── Jordyn/
    ├── Checking/          # Chase checking
    ├── CreditCard/        # Discover, Wells Fargo cards
    └── Savings/           # Any savings accounts
```

---

## Phase 2: First Import Test (TODAY) 🧪

### Quick Test Run
```bash
# Test with one file first
poetry run balance-pipe process "csv_inbox/Ryan/Aggregated/Monarch*.csv" --debug -vv

# Check what happened
ls output/
cat logs/pipeline_run.log
```

### If Test Succeeds - Run Full Import
```bash
# Process all data
poetry run balance-pipe process "csv_inbox/**.csv" \
    --output-type powerbi \
    --schema-mode flexible \
    --output-path output/complete_financial_data.parquet
```

### Validation Commands
```bash
# Generate comprehensive analysis
poetry run balance-analyze --config config/balance_analyzer.yaml

# Check for issues
python scripts/investigations/financial_issue_detector.py

# Simple balance check
python scripts/analysis/simple_balance_check.py
```

---

## Phase 3: Baseline Balance Calculation (THIS WEEK) 💰

### Define Your Shared Expense Rules

Edit `config/balance_analyzer.yaml`:
```yaml
# Add or update these sections:
shared_expense_rules:
  rent:
    total_amount: 2500  # Your actual rent
    ryan_share: 0.57
    jordyn_share: 0.43
  
  utilities:
    split_method: "50/50"
  
  groceries: 
    split_method: "50/50"
    
  dining:
    split_method: "50/50"

# Categories that are always shared
shared_categories:
  - "Rent"
  - "Utilities"
  - "Groceries" 
  - "Gas"
  - "Shared Dining"

# Categories that are always personal
personal_categories:
  - "Personal Care"
  - "Individual Hobbies"
  - "Personal Shopping"
```

### Run Balance Analysis
```bash
# Comprehensive balance calculation
python scripts/analysis/careful_verification.py

# Generate detailed breakdown
python scripts/utilities/final_balance_verification.py

# Check rent payments specifically
python scripts/analysis/rent_logic_check.py
```

---

## Phase 4: Review and Correct (END OF WEEK) 🔍

### Check the Results

Look at these output files:
- `analysis_output/comprehensive_analysis_results.json`
- `analysis_output/executive_summary_v2.3.csv`
- `audit_reports/complete_audit_trail_*.csv`

### Use Excel for Review
```bash
# Generate Excel workbook
poetry run balance-pipe process "csv_inbox/**.csv" --output-type excel

# Open output/balance_data.xlsx
# Review the Queue_Review sheet for uncategorized transactions
```

### Apply Corrections if Needed
```bash
# If you find data issues
python scripts/corrections/final_balance_correction.py

# If rent allocation needs fixing
python scripts/corrections/rent_allocation_corrector.py
```

---

## Immediate Commands to Run Now

### 1. Check What You Have
```bash
# See current data
ls sample_data_multi/

# Check existing schemas
ls rules/*.yaml
```

### 2. Test Current Pipeline
```bash
# Quick test with existing sample data
poetry run balance-pipe process "sample_data_multi/**.csv" --debug
```

### 3. Set Up for Production
```bash
# Create additional folders
mkdir csv_inbox/Ryan/Aggregated
mkdir csv_inbox/Jordyn/Savings

# Test full pipeline
poetry run balance-pipe process "csv_inbox/**.csv" --output-type powerbi
```

---

## Success Criteria for This Week

- [ ] ✅ All bank data exported and placed in csv_inbox/
- [ ] ✅ Pipeline processes all data without errors
- [ ] ✅ Baseline balance calculation shows who owes what
- [ ] ✅ Excel review queue set up for transaction categorization
- [ ] ✅ Power BI data file generated for advanced analytics

---

## If You Hit Issues

**Schema Problems:**
```bash
# Debug schema matching
poetry run balance-pipe process "csv_inbox/problematic_file.csv" --debug -vv
```

**Data Quality Issues:**
```bash
# Investigate problems
python scripts/investigations/financial_issue_detector.py

# Check data quality
python tools/diagnose_analyzer.py
```

**Balance Calculation Issues:**
```bash
# Deep dive analysis
python scripts/analysis/deep_analysis.py

# Understand transactions
python scripts/analysis/understand_real_system.py
```

---

**🎯 START HERE**: Export all your banking data and drop it into the csv_inbox folders, then run the first test command!