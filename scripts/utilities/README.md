# BALANCE Utility Scripts

This directory contains utility scripts for data processing and analysis tasks.

## Quick Power BI Prep (`quick_powerbi_prep.py`)

**Purpose**: Prepares combined transaction data for Power BI analysis and dispute resolution.

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

### Key Features for Dispute Analysis
- **Automatic deduplication** - Removes duplicate transactions based on date, merchant, amount, and description
- **Merchant standardization** - Groups similar merchants (Amazon, AMZN Mktp → Amazon)
- **Refund/dispute flagging** - Pre-identifies transactions containing keywords like "refund", "dispute", "chargeback", "reversal"
- **Enhanced metadata** - Adds date components, expense/income flags, transaction IDs

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