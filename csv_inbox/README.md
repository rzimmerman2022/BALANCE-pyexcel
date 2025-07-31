# CSV Inbox Directory

This directory is organized for importing all your banking data into the BALANCE-pyexcel pipeline.

## Directory Structure

```
csv_inbox/
├── Ryan/
│   ├── Checking/          # Primary checking account CSVs
│   ├── Savings/           # Savings account CSVs  
│   ├── CreditCard/        # Credit card statement CSVs
│   └── Investment/        # Investment/brokerage CSVs
└── Jordyn/
    ├── Checking/          # Primary checking account CSVs
    ├── Savings/           # Savings account CSVs
    ├── CreditCard/        # Credit card statement CSVs
    └── Investment/        # Investment/brokerage CSVs
```

## How to Use

1. **Export Data from Banks**: Download CSV/Excel files from each account
2. **Place in Correct Folder**: Put files in the appropriate owner/account type folder
3. **Run Pipeline**: Use `poetry run balance-pipe process "csv_inbox/**.csv"`

## File Naming Convention

Use descriptive names that include:
- Bank name
- Account type  
- Date range
- Export date

Examples:
- `Chase_Checking_Jan2025_exported_20250131.csv`
- `Discover_Card_2024_Q4_exported_20250115.csv`
- `Fidelity_Investment_2024_full_year.csv`

## Supported Formats

- CSV files (preferred)
- Excel files (.xlsx)
- Tab-delimited files (.txt)

## Processing Commands

```bash
# Process all data
poetry run balance-pipe process "csv_inbox/**.csv" --output-type powerbi

# Process specific owner
poetry run balance-pipe process "csv_inbox/Ryan/**.csv" --debug

# Process specific account type
poetry run balance-pipe process "csv_inbox/*/Checking/*.csv"
```

## Notes

- The pipeline automatically detects owner from folder name
- Each file is deduplicated based on transaction ID
- Schema matching is automatic via `rules/schema_registry.yml`
- Failed imports are logged for troubleshooting