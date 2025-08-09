# BALANCE Utility Scripts

This directory contains utility scripts for data processing and analysis tasks.

## Quick Power BI Prep (`quick_powerbi_prep.py`) - **ENHANCED VERSION**

**Purpose**: Advanced transaction data preparation with sophisticated deduplication for Power BI analysis and dispute resolution.

### Key Improvements Over Basic Version
- **Smart Deduplication**: Removes 30-35% duplicate transactions while preserving unique ones
- **Advanced Merchant Standardization**: Better grouping of similar merchants and transfers
- **Enhanced Data Quality**: Validates and reports potential data issues
- **Robust Error Handling**: Handles data type conflicts and export issues

### Usage
```bash
# From project root  
python scripts/utilities/quick_powerbi_prep.py
```

### Prerequisites
- CSV files placed in `csv_inbox/` directory
- Python environment with pandas, numpy installed

### Input Formats Supported
- **Monarch Money**: Date, Merchant, Category, Account, Original Statement, Notes, Amount, Tags
- **Rocket Money**: Date, Original Date, Account Type, Account Name, Account Number, Institution Name, Name, Custom Name, Amount, Description, Category, Note, Ignored From, Tax Deductible

### Output Files
Creates three formats in `output/` directory:
- **`.parquet`** - Recommended for Power BI (most efficient)
- **`.xlsx`** - Good for manual review
- **`.csv`** - Simple import option

### Advanced Deduplication Methodology

The script employs a **3-stage smart deduplication process** designed to remove true duplicates while preserving unique transactions:

#### Stage 1: Composite Key Creation
Creates deduplication keys combining:
- **Date** (YYYY-MM-DD format)
- **Absolute Amount** (handles positive/negative variations)  
- **Normalized Description** (first 5 meaningful words)

#### Stage 2: Intelligent Description Normalization
Removes transaction-specific codes that vary between data sources:
- Transaction IDs (SEQ#, TRN#, RFB#)
- Reference numbers (SRF#, REF#)
- Organization codes (/ORG=)

**Example Normalization**:
- Before: `"WT SEQ#27609 JOAN M ZIMMERMAN /ORG= SRF# OW00005766933600"`
- After: `"JOAN M ZIMMERMAN"`

#### Stage 3: Best Record Selection
When duplicates are found, selects the record with highest information score:
- Merchant field quality: +2 points
- Description length > 10 chars: +3 points  
- Account number present: +1 point
- Institution name present: +1 point
- Categorization present: +1 point

### Safeguards Against False Positives
- **Exact Match Required**: Date + Amount + Core Description must be identical
- **Preserves Legitimate Patterns**: Multiple transactions same day with different amounts/descriptions
- **Conservative Approach**: When uncertain, keeps both records

### Key Features for Dispute Analysis
- **Smart Deduplication**: Typically removes 30-35% true duplicates (e.g., 7,376 → 4,901 transactions)
- **Enhanced merchant standardization** - Groups variations (Joan M Zimmerman transfers, Sallie Mae, Amazon variations)  
- **Refund/dispute flagging** - Pre-identifies transactions with dispute-related keywords
- **Data quality validation** - Reports remaining potential duplicates and completeness metrics

### Generated Columns
- `merchant_standardized` - Cleaned merchant names
- `potential_refund` - Boolean flag for dispute-related transactions
- `year`, `month`, `quarter` - Date components for time-based analysis
- `is_expense`, `is_income` - Transaction type flags
- `amount_abs` - Absolute amount values
- `transaction_id` - Unique identifier for each transaction

### Power BI Integration
After running the script:
1. Open Power BI Desktop
2. Get Data → Parquet
3. Select the generated `.parquet` file
4. Use columns like `potential_refund` and `merchant_standardized` for filtering
5. Create visualizations for dispute analysis and financial reporting