# Aggregator Deduplication

## Overview

The BALANCE-pyexcel pipeline includes a system to handle duplicate transactions that might appear in multiple financial aggregator services (like Rocket Money and Monarch Money). This feature ensures that the same transaction from a bank account doesn't get counted twice even if it shows up in exports from multiple aggregators.

## How Deduplication Works

### 1. Source Identification

Every transaction is tagged with its source:
- `Source: "Rocket"` for transactions from Rocket Money exports
- `Source: "Monarch"` for transactions from Monarch Money exports

This tagging happens automatically through the `extra_static_cols` setting in the schema registry.

### 2. Bank Information Preservation

The original financial institution is preserved in the `Bank` column:
- From Rocket Money: `Institution Name` → `Bank`
- From Monarch Money: `Institution` → `Bank`

### 3. Smart Transaction ID Generation

Transaction IDs (`TxnID`) are generated using a deterministic hash of key transaction attributes:
- Date
- Amount
- Description
- Bank
- Account

Critically, this hash does NOT include the `Source` field. This means that the same transaction appearing in both Rocket Money and Monarch Money will generate identical TxnIDs.

### 4. Duplicate Removal

During the normalization phase, the pipeline:
1. Identifies transactions with identical TxnIDs
2. Sorts by Source name to prioritize one aggregator over another (currently "Rocket" is prioritized over "Monarch")
3. Keeps only the first occurrence of each transaction (based on TxnID)

## Configuration

### Schema Registry Setup

```yaml
- id: rocket_money
  match_filename: "BALANCE - Rocket Money*"
  header_signature: ["Account Name", "Institution Name", "Amount"]
  extra_static_cols:
    Source: "Rocket"
  column_map:
    Date: Date
    Description: Description
    Amount: Amount
    Account Name: Account
    Institution Name: Bank
    Category: Category
  sign_rule: flip_if_positive

- id: monarch_export
  match_filename: "BALANCE - Monarch Money*"
  header_signature: ["Merchant", "Account", "Original Statement"]
  extra_static_cols:
    Source: "Monarch"
  column_map:
    Date: Date
    Merchant: Description
    Amount: Amount
    Account: Account
    Institution: Bank
    Category: Category
  sign_rule: as_is
```

## Benefits

This deduplication system:

1. **Prevents Double-Counting**: The same transaction won't be counted twice in any reports or analysis
2. **Preserves Source Information**: Even though duplicates are removed, the source information is retained in the dataset for auditing
3. **Handles Multiple Aggregators**: Works seamlessly with multiple financial data aggregation services
4. **Prioritization**: Gives preference to one source over another when duplicates exist

## Log Output Examples

When deduplication occurs, you'll see log entries like:

```
INFO - Removed 17 duplicate transactions from aggregator sources. Prioritized based on Source.
```

This indicates that 17 transactions were found in both Rocket Money and Monarch Money exports, and duplicates were successfully removed.
