# Setup script for the new Financial Reconciliation project
# This creates all the essential files and documentation

$projectPath = "c:\projects\financial-reconciliation"

Write-Host "Setting up Financial Reconciliation project..." -ForegroundColor Green

# Create README.md
$readmeContent = @"
# Financial Reconciliation System

A clean, focused financial reconciliation system built from lessons learned in BALANCE-pyexcel.

## Architecture

This project follows a clean, modular approach:

```
├── data/
│   ├── raw/           # Original CSV files
│   └── processed/     # Cleaned data
├── src/
│   ├── loaders/       # CSV loading modules
│   ├── processors/    # Data cleaning/validation  
│   └── reconcilers/   # Reconciliation logic
├── docs/
│   ├── assumptions.md    # Business logic assumptions
│   ├── data_sources.md   # CSV specifications
│   └── audit_trail.md    # Audit requirements
├── tests/             # Unit tests
├── output/            # Generated reports
└── scripts/           # Utility scripts
```

## Key Principles

1. **One CSV at a time**: Process each data source independently first
2. **Clear assumptions**: Document all business logic upfront
3. **Full audit trails**: Every transaction must be traceable
4. **Clean separation**: Keep old experimental work separate

## Data Sources

### Current Files in data/raw/:
- ``Consolidated_Expense_History_20250622.csv`` - Shared expenses
- ``Consolidated_Rent_Allocation_20250527.csv`` - Rent payments and allocations
- ``Zelle_From_Jordyn_Final.csv`` - Zelle payments from Jordyn

## Critical Questions to Resolve

### Rent Payment Logic (HIGHEST PRIORITY):
1. Does Ryan pay the full rent each month?
2. Does Jordyn pay the full rent each month? 
3. What do the CSV columns "Ryan's Rent (43%)" and "Jordyn's Rent (57%)" actually represent?

## Implementation Plan

### Phase 1: Data Understanding
- [ ] Analyze each CSV structure individually
- [ ] Document field meanings and assumptions
- [ ] Resolve rent payment logic questions

### Phase 2: Single CSV Processors  
- [ ] Build expense CSV processor (simplest)
- [ ] Build rent CSV processor (once assumptions clear)
- [ ] Build Zelle CSV processor

### Phase 3: Integration
- [ ] Combine processors with reconciliation logic
- [ ] Generate comprehensive audit trails
- [ ] Create final reports

## Development Notes

This project was created by migrating essential files from the original BALANCE-pyexcel experiment. The old project remains at ``c:\BALANCE\BALANCE-pyexcel`` for reference.

Created: July 16, 2025
"@

$readmeContent | Out-File -FilePath "$projectPath\README.md" -Encoding UTF8

# Create assumptions.md
$assumptionsContent = @"
# Business Logic Assumptions

## CRITICAL: Rent Payment Logic

**STATUS: UNRESOLVED - MUST CLARIFY BEFORE PROCEEDING**

### Questions needing answers:
1. **Who pays the actual rent?**
   - Does Ryan pay the full rent amount to the landlord each month?
   - Does Jordyn pay the full rent amount to the landlord each month?
   - Or do they split the payment to the landlord?

2. **What do the percentage columns mean?**
   - In ``Consolidated_Rent_Allocation_20250527.csv``:
     - "Ryan's Rent (43%)" = ?
     - "Jordyn's Rent (57%)" = ?
   - Are these:
     - a) Reimbursement amounts owed between roommates?
     - b) Actual amounts paid to landlord?
     - c) Calculated allocations for tracking purposes?

3. **Reconciliation expectations**
   - Should the sum of Ryan's % + Jordyn's % = 100% of actual rent?
   - How do Zelle payments from Jordyn relate to these percentages?

### Working Hypothesis (TO BE CONFIRMED):
- Ryan pays full rent to landlord
- Rent is allocated 43% Ryan / 57% Jordyn based on some agreement
- Jordyn reimburses Ryan for her portion via Zelle
- CSV tracks this allocation and reimbursement flow

**THIS MUST BE RESOLVED BEFORE BUILDING RECONCILIATION LOGIC**

## Expense Assumptions

### Shared Expenses
- Expenses in ``Consolidated_Expense_History_20250622.csv`` are shared expenses
- Need to determine split methodology (50/50? Based on usage? Other?)

### Zelle Payments
- Zelle payments from Jordyn to Ryan are reimbursements
- Could be for rent, expenses, or both
- Need clear mapping of what each payment covers

## Data Quality Assumptions

1. **Date formats**: Assume consistent date formatting within each CSV
2. **Currency**: All amounts in USD
3. **Completeness**: CSVs contain all relevant transactions for their respective periods
4. **Uniqueness**: Each row represents a unique transaction/allocation

## Audit Trail Requirements

1. **Every dollar must be traceable** from source CSV to final reconciliation
2. **No black box calculations** - all logic must be documented and verifiable
3. **Immutable source data** - original CSVs never modified, only processed copies
4. **Version control** - All processing steps and logic changes tracked in Git

---
*This document must be updated as assumptions are clarified and confirmed.*
"@

$assumptionsContent | Out-File -FilePath "$projectPath\docs\assumptions.md" -Encoding UTF8

Write-Host "Created project documentation files" -ForegroundColor Green
Write-Host "Ready to begin development phase" -ForegroundColor Yellow
