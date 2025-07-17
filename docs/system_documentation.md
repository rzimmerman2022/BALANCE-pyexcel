# Phase 5.1: System Documentation

This document provides a comprehensive overview of the financial reconciliation system's architecture, data flow, and core logic.

## System Architecture Diagram

The system follows a simple, script-based architecture orchestrated by a main audit script.

```
[Raw Data CSVs] ----> [audit_run.py] ----> [baseline_analyzer Package] ----> [Audit Trail CSV]
      |                     |                        |                              |
      | (Expenses,          | (Loads raw data,       | (Core accounting logic,      | (Final detailed
      |  Ledger, Rent)      |  delegates to         |  rule processing)           |  output)
      |                     |  package)              |                              |
```

*   **Raw Data:** Source CSV files containing expense, ledger, and rent allocation data.
*   **`audit_run.py`:** The main entry point. It discovers and loads the raw data files and passes them to the `baseline_analyzer` package for processing.
*   **`baseline_analyzer` Package:** A Python package containing the core business logic.
    *   `baseline_math.py`: The heart of the system. It cleans the data, applies splitting rules, calculates the `net_effect` for every transaction, and generates the final, balanced audit trail.
*   **Audit Trail CSV:** The final output is a comprehensive CSV file containing a detailed, row-by-row breakdown of the entire reconciliation.

## Data Flow Explanation

1.  **Discovery:** `audit_run.py` scans the `data/` directory for CSV files matching predefined patterns for expenses, ledger, and rent.
2.  **Loading:** The script reads these files into pandas DataFrames.
3.  **Processing:** The raw DataFrames are passed to the `build_baseline` function in `src/baseline_analyzer/baseline_math.py`.
4.  **Cleaning:** Inside `build_baseline`, the `_clean_data` function standardizes column names, normalizes person names, and converts money columns to numeric types.
5.  **Rule Application:** The script iterates through each transaction:
    *   **Rent:** For rent transactions, it applies the 43%/57% split rule directly.
    *   **Standard/Ledger:** For all other transactions, it uses `_detect_patterns` to find keywords (like "2x" or "gift") and then `_apply_split_rules` to determine the `allowed_amount` for Ryan and Jordyn.
6.  **Net Effect Calculation:** For every transaction, the universal accounting formula is applied: `net_effect = allowed_amount - actual_amount`. This is calculated separately for both Ryan and Jordyn, creating a balanced, double-entry record.
7.  **Audit Trail Generation:** The resulting list of records is converted into the final audit DataFrame.
8.  **Output:** The final DataFrame is saved as the `complete_audit_trail.csv`.

## Pattern Matching Rules

The system uses regular expressions to detect special handling rules from transaction descriptions.

*   **`2x` (Full Allocation):** If a description contains "2x Ryan" or "2x Jordyn", the entire expense is allocated to that person.
*   **`2x` (Ambiguous):** If "2x" appears without a name, it defaults to allocating the full amount to the person who paid.
*   **`gift` / `present`:** Allocates the full expense to the person who did *not* pay.
*   **`cashback`:** Zeros out the transaction, as it has no net effect on the balance.
*   **`zelle` / `transfer`:** Treated as a direct transfer of funds, resulting in a negative `allowed_amount` for the sender and a positive one for the receiver.
*   **`100% [Name]`:** Explicitly allocates the full amount to the named person.
*   **Standard Rule:** If no other patterns are matched, the expense is split 50/50.

## Rent Handling Logic

The rent handling logic is now fully encapsulated within the `build_baseline` function in `baseline_math.py`.

1.  The `Rent_Allocation_...csv` file is loaded.
2.  For each row in the file, the system reads the `Ryan's Rent (43%)` and `Jordyn's Rent (57%)` columns to determine their respective shares (`allowed_amount`).
3.  The `Gross Total` is used as the `actual_amount` paid.
4.  It is assumed that **Jordyn pays the full rent amount**.
5.  Two balanced audit rows are created for each rent payment:
    *   **Jordyn's Row:**
        *   `actual_amount`: The full rent payment.
        *   `allowed_amount`: Her 57% share.
        *   `net_effect`: `allowed_amount - actual_amount` (a large negative number, as she is owed Ryan's share).
    *   **Ryan's Row:**
        *   `actual_amount`: 0.00.
        *   `allowed_amount`: His 43% share.
        *   `net_effect`: `allowed_amount - actual_amount` (a positive number, as he owes his share).

This model ensures that the rent transaction is internally balanced and correctly reflects the financial reality of the shared expense.
