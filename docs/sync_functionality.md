# Sync Functionality

## Overview

The sync module is designed to bridge the gap between manual user decisions in Excel and the automated data pipeline. It allows users to review transactions in an Excel sheet called "Queue_Review" and make decisions about which transactions are shared expenses or split expenses, then synchronize these decisions back into the main dataset.

## Key Components

### 1. Queue_Review Excel Sheet

This Excel sheet has a standardized format with the following key columns:

- **TxnID**: A unique identifier for each transaction
- **Set Shared? (Y/N/S for Split)**: User decision about the transaction
  - `Y` = Yes, this is a shared expense
  - `N` = No, this is not a shared expense
  - `S` = Split this expense according to the specified percentage
- **Set Split % (0-100)**: Percentage of the expense to be assigned (only used when "S" is selected)

### 2. Decision Processing

The `sync_review_decisions()` function processes these decisions with robust error handling:

- **Invalid values** (anything other than Y/N/S) are ignored
- **Missing split percentages** default to 50%
- **Out-of-range percentages** are clamped (< 0 becomes 0, > 100 becomes 100)
- **Empty cells** are skipped (no change made to the transaction)

### 3. Data Flow

```
              ┌─────────────────┐
              │  Transaction    │
              │    Database     │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │ Queue_Review    │
              │    Excel Sheet  │
              └────────┬────────┘
                       │
                       ▼
┌─────────────────────────────────────────┐
│         sync_review_decisions()         │
├─────────────────────────────────────────┤
│ 1. Validate input data                  │
│ 2. Clean & standardize user decisions   │
│ 3. Merge decisions with transactions    │
│ 4. Apply updates to SharedFlag and      │
│    SplitPercent columns                 │
└────────────────────┬────────────────────┘
                     │
                     ▼
              ┌─────────────────┐
              │  Updated        │
              │  Transactions   │
              └─────────────────┘
```

## Using Sync Functionality

### In Python Code

```python
from balance_pipeline.sync import sync_review_decisions

# Load your data
transactions_df = pd.read_csv("transactions.csv")
queue_review_df = pd.read_excel("workbook.xlsx", sheet_name="Queue_Review")

# Apply decisions
updated_transactions = sync_review_decisions(transactions_df, queue_review_df)

# Now save or process the updated data
updated_transactions.to_csv("transactions_updated.csv", index=False)
```

### In Excel Workbook

1. Review transactions in the Queue_Review sheet
2. Make decisions by entering Y, N, or S in the "Set Shared?" column
3. For split expenses (S), specify the percentage in the "Set Split %" column
4. Run the refresh data cell/macro to apply the changes
5. View the updated transaction data with applied decisions

## Error Handling

The sync process is designed to be robust with extensive error handling:

- **Missing data**: If either DataFrame is empty, returns a copy of the transactions
- **Missing columns**: Checks for required columns before processing
- **Invalid decisions**: Logs warnings but continues processing valid entries
- **Data type issues**: Ensures proper conversion of numerical values

## Technical Details

- **TxnID matching**: Decisions are matched to transactions via the TxnID column
- **Updates are non-destructive**: Original transaction data is preserved, only SharedFlag and SplitPercent are updated
- **Logging**: Detailed logging for troubleshooting and auditing
