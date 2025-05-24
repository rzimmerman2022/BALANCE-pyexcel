MASTER_SCHEMA_COLUMNS = [
    # Key Identifiers & Owner
    "TxnID",
    "Owner",

    # Core Date & Financial Info
    "Date",
    "PostDate",
    "Amount",
    "Currency",

    # Core Descriptive Info
    "Merchant",
    "Category",
    "OriginalDescription", # Rawest/longest description from source
    "Description",         # Primary/shorter description, or alias of OriginalDescription
    
    # Account Details
    "Account",
    "AccountLast4",
    "AccountType",
    "Institution",

    # Statement-related Info (primarily for bank/card direct exports)
    "StatementStart",
    "StatementEnd",
    "StatementPeriodDesc",

    # Optional & Source-Specific Data
    "Tags",
    "OriginalDate",      # e.g., from Rocket Money if different from main Date
    "AccountNumber",     # e.g., from Rocket Money
    "ReferenceNumber",   # Check numbers, etc.
    "Note",              # User notes

    # Metadata, Lineage & Uncategorized Extras
    "DataSourceName",
    "DataSourceDate",
    "Extras",            # JSON blob for other source-specific unmapped columns
]
