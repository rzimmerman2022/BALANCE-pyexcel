# Phase 5.2: User Guide

This guide explains how to use the financial reconciliation system.

## How to Run the Audit

The primary way to run a full reconciliation is by using the `audit_run.py` script.

1.  **Prepare Your Data:**
    *   Ensure your source CSV files are located in the `data/` directory.
    *   The system expects files that follow these naming conventions:
        *   `Expense_History_[date].csv`
        *   `Transaction_Ledger_[date].csv`
        *   `Rent_Allocation_[date].csv`

2.  **Run the Script:**
    *   Open your terminal or command prompt.
    *   Navigate to the root directory of the project.
    *   Execute the following command:
        ```bash
        python audit_run.py
        ```

3.  **Check the Output:**
    *   The script will print a summary to the console.
    *   Look for the following messages to confirm a successful run:
        *   `✅ Per-row math is internally consistent.`
        *   `🎉 Grand totals zero out — reconciliation complete.`

## How to Interpret the Results

The main output of the system is the **Comprehensive Audit Trail CSV**. After a successful run, you can find this file in the `artifacts/` directory, named `complete_audit_trail_[YYYY-MM-DD].csv`.

This file contains a detailed breakdown of every transaction. Key columns to check are:

*   `person`: The person involved (Ryan or Jordyn).
*   `actual_amount`: The actual cash that was spent by that person for the transaction.
*   `allowed_amount`: The amount that person was *responsible* for.
*   `net_effect`: The crucial balancing number. It is calculated as `allowed_amount - actual_amount`.
    *   A **positive** `net_effect` means the person owes money.
    *   A **negative** `net_effect` means the person is owed money.
*   `calculation_notes`: Explains *why* a transaction was split a certain way (e.g., "Standard 50/50 split", "Full to Ryan", "Rent | 43/57 Split").

The console output from `audit_run.py` also provides a high-level summary of the `net_owed` balance for each person.

## Common Issues and Solutions

*   **Issue:** The script reports a `Net imbalance`.
    *   **Solution:** This indicates a fundamental error in the accounting logic. The `net_effect` amounts do not sum to zero across all transactions. This should not happen with the current version of the code, but if it does, it requires a code-level investigation.

*   **Issue:** The script reports `Inconsistent rows detected`.
    *   **Solution:** This means that for one or more rows, the integrity check (`allowed_amount - actual_amount - net_effect`) failed. This also points to a bug in the core logic and requires a developer to investigate.

*   **Issue:** A transaction was split 50/50 but should have been allocated differently.
    *   **Solution:** The system relies on pattern matching. To change how a transaction is handled, you need to add a keyword to its description in the source CSV file. For example, to allocate an entire expense to Ryan, add `(2x Ryan)` to the description.

## When and How to Add New Pattern Rules

If you frequently encounter transactions that need special handling, you can add a new pattern rule instead of manually editing the CSV every time.

1.  **Identify the Pattern:** Find a unique, consistent keyword or phrase in the description of the transactions you want to target.
2.  **Edit the Configuration:** Open the `src/baseline_analyzer/_settings.py` file (or the `.yaml` config file if the system is upgraded as per recommendations).
3.  **Add the Regex:** Add a new entry to the `patterns` dictionary. The key should be a descriptive name (e.g., `new_rule_name`), and the value should be the regular expression to match.
4.  **Update the Logic:** In `src/baseline_analyzer/baseline_math.py`, add logic to `_detect_patterns` to check for your new pattern and return a corresponding rule. You may also need to add a new rule handler in `_apply_split_rules`.

**Note:** Modifying rules requires knowledge of Python and regular expressions. It is recommended to follow the code quality improvement proposal to move these rules to a more user-friendly configuration file.
