# Phase 4: System Improvement Recommendations

This document outlines recommendations for improving the financial reconciliation system's codebase, features, and data pipeline.

## 4.1 Code Quality Assessment

The recent, intensive debugging and refactoring effort has significantly improved the core accounting logic in `src/baseline_analyzer/baseline_math.py`. The system is now robust and correct. However, further improvements can be made for clarity and long-term maintainability.

### Recommendations:

1.  **Consolidate Core Logic:** The `audit_run.py` script still contains some data loading and preparation logic. This should be moved into the `baseline_analyzer` package to create a single, authoritative source for all processing. `audit_run.py` should be simplified to a thin wrapper that calls the package.
    *   **Action:** Create a `data_loader.py` module within `src/baseline_analyzer` to house all file discovery and reading logic.
    *   **Action:** Refactor `baseline_math.py` to import from `data_loader.py`.
    *   **Action:** Update `audit_run.py` to simply call a main function from the `baseline_analyzer` package.

2.  **Configuration Management:** Key settings like file patterns and column maps are hardcoded in `baseline_math.py`. These should be managed via a dedicated configuration file (e.g., `config/balance_analyzer.yaml`) to make the system more flexible.
    *   **Action:** Move all regex patterns, column maps, and other settings into the existing `.yaml` configuration files.
    *   **Action:** Implement a configuration loading class or function within `baseline_analyzer` to provide settings to all modules.

3.  **Improve Docstrings and Comments:** While the logic is now correct, adding more detailed docstrings and inline comments, particularly in `_apply_split_rules` and `build_baseline`, would make the code easier to understand for future maintenance.

## 4.2 Feature Enhancement Proposals

### 1. Automated Monthly Reporting

**Objective:** Generate a monthly PDF or text report summarizing financial activity.

**Design:**
*   A new script, `generate_monthly_report.py`, will be created.
*   It will take a month and year as input (e.g., `python generate_monthly_report.py --month 5 --year 2025`).
*   The script will run the baseline analysis and then generate a summary report containing:
    *   **Total Expenses by Category:** A table showing spending grouped by merchant patterns (e.g., Groceries, Restaurants, Travel).
    *   **Net Balance Changes:** A summary of the starting and ending balance for Ryan and Jordyn.
    *   **Rent Allocation Summary:** A clear statement of the total rent paid and the 43%/57% split.
    *   **Flagged Anomalies:** A list of any transactions that required special handling (e.g., "Full to Jordyn").

### 2. Historical Trend Analysis

**Objective:** Create visualizations to track financial trends over time.

**Design:**
*   A new script, `generate_trend_visuals.py`, will be created.
*   It will use the `complete_audit_trail.csv` as its data source.
*   It will use libraries like `matplotlib` and `seaborn` to generate and save PNG images for:
    *   **Monthly Spending Patterns:** A bar chart showing total shared expenses per month.
    *   **Balance Trends Over Time:** A line chart showing the running `net_owed` for both Ryan and Jordyn over time.
    *   **Category Breakdowns:** A pie or bar chart showing the percentage of spending per category for a given period.

### 3. Reconciliation Dashboard

**Objective:** Provide a simple, at-a-glance web dashboard to view the current reconciliation status.

**Design:**
*   A simple web dashboard can be generated as a static HTML file using Python.
*   A script, `generate_dashboard.py`, will:
    *   Run the audit.
    *   Generate key metrics: Current net balance for each person, total expenses this month, number of transactions needing review.
    *   Use a templating engine like Jinja2 to inject these metrics into an HTML template.
    *   The HTML template will use a simple CSS framework (like Bootstrap) for clean presentation.
    *   The output will be a single `dashboard.html` file that can be opened in any browser.

## 4.3 Data Quality Improvements

### Recommendations:

1.  **Input Validation Schema:** Implement a validation step using a library like `pandera` or `pydantic` to check incoming CSVs against a defined schema. This would catch issues like missing columns, incorrect data types, or empty files before they enter the processing pipeline.
2.  **Automated Duplicate Detection:** Add a step in the data loading process to check for and flag potentially duplicate transactions based on date, amount, and merchant.
3.  **Formalize Edge Case Handling:** Instead of relying solely on regex in the code, move the patterns for edge cases (like "cashback" or "gift") into the configuration file. This makes it easier to add new rules without changing the Python code.
