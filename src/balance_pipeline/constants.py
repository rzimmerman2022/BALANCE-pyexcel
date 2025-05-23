# src/balance_pipeline/constants.py

"""
Constants used throughout the BALANCE-pyexcel pipeline.

This module defines the canonical schema and other pipeline-wide constants.
Updated to implement Canonical Schema v2.0 based on evidence-based analysis.
"""

# Configuration constants
BALANCE_FINAL_PARQUET_FILENAME = "balance_final.parquet"

# Legacy 29-column schema (v1.0) - Preserved for reference
# Commented out on 2025-05-22 when implementing v2.0
"""
MASTER_SCHEMA_COLUMNS = [
    "TxnID", "Owner", "Date", "PostDate", "Merchant", "OriginalDescription",
    "Category", "Amount", "Tags", "Institution", "Account", "AccountLast4",
    "AccountType", "SharedFlag", "SplitPercent", "StatementStart", "StatementEnd",
    "StatementPeriodDesc", "DataSourceName", "DataSourceDate", "ReferenceNumber",
    "Note", "IgnoredFrom", "TaxDeductible", "CustomName", "Currency", "Extras",
    "Description", "Source"
]
"""

# Canonical Schema v2.0 - Evidence-based schema from data analysis
# Implemented 2025-05-22 based on audit of 5 source files
# See canonical_schema_v2.yaml for detailed documentation
MASTER_SCHEMA_COLUMNS = [
    # Core required fields (appear in all sources with >90% completeness)
    "TxnID",           # System-generated unique ID
    "Date",            # Transaction date (100% in all sources)
    "Amount",          # Transaction amount (100% in all sources)
    "Category",        # Transaction category (100% in all sources)
    "Description",     # Primary description (maps from various source fields)
    "Account",         # Account identifier (100% in all sources)
    
    # Common fields (high value, multiple sources)
    "PostDate",        # Posting date (banking sources only, 99.8%)
    "ReferenceNumber", # Bank reference (banking sources only, 96%)
    "Institution",     # Financial institution (consolidated field)
    
    # Source-specific optional fields
    "AccountLast4",    # Last 4 of account (derived for Jordyn sources)
    "StatementStart",  # Statement period start (Jordyn banking)
    "StatementEnd",    # Statement period end (Jordyn banking)
    "StatementPeriodDesc",  # Statement description (Jordyn sources)
    "OriginalDate",    # Original date from Rocket Money
    "AccountName",     # Full account name (Ryan aggregators)
    "AccountNumber",   # Account number (Ryan aggregators)
    "OriginalStatement",  # Original text (Monarch Money)
    "Merchant",        # Cleaned merchant name (all sources)
    
    # System metadata fields
    "Owner",           # Data owner (Jordyn/Ryan)
    "DataSourceName",  # Source system identifier
    "DataSourceDate",  # When data was extracted
    "AccountType",     # Type of account
    
    # User enrichment fields
    "SharedFlag",      # Shared expense indicator
    "SplitPercent",    # Percentage if shared
    "Currency",        # Transaction currency (default: USD)
    "Tags",            # User-defined tags (rarely used)
    
    # Preserve for compatibility but consider removing
    "Extras"           # JSON field for unmapped columns
]

# Fields removed in v2.0 (documented for migration purposes)
DEPRECATED_FIELDS = [
    "OriginalDescription",  # Merged into Description field
    "Note",                 # Duplicate of Notes, 0% usage
    "Notes",                # 0% usage across all sources
    "CustomName",           # 0% usage across all sources
    "IgnoredFrom",          # 0% usage across all sources
    "TaxDeductible",        # 0.1% usage, not meaningful
    "Source"                # Never populated in practice
]

# Column display order for final output (groups related fields)
COLUMN_DISPLAY_ORDER = [
    # Transaction core
    "Date", "PostDate", "Description", "Merchant", "Amount", "Category",
    
    # Account information
    "Account", "AccountName", "AccountType", "AccountLast4", "Institution",
    
    # Reference information
    "TxnID", "ReferenceNumber", "OriginalDate",
    
    # Statement information
    "StatementStart", "StatementEnd", "StatementPeriodDesc", "OriginalStatement",
    
    # Metadata
    "Owner", "DataSourceName", "DataSourceDate",
    
    # User fields
    "SharedFlag", "SplitPercent", "Tags", "Currency",
    
    # System fields
    "AccountNumber", "Extras"
]

# Data type specifications for each column
COLUMN_TYPES = {
    # Date columns
    "Date": "datetime64[ns]",
    "PostDate": "datetime64[ns]",
    "OriginalDate": "datetime64[ns]",
    "StatementStart": "datetime64[ns]",
    "StatementEnd": "datetime64[ns]",
    "DataSourceDate": "datetime64[ns]",
    
    # Numeric columns
    "Amount": "float64",
    "SplitPercent": "float64",
    
    # String columns (everything else)
    # Note: Power BI compatibility may require explicit string casting
}

# Required fields that must be non-null in final output
REQUIRED_FIELDS = ["Date", "Amount", "Category", "Description", "Account"]

# Fields that can be derived if missing
DERIVABLE_FIELDS = {
    "Description": "Can be derived from OriginalDescription, Merchant, or Name",
    "Institution": "Can be derived from InstitutionName or Account parsing",
    "Merchant": "Can be cleaned from Description or OriginalDescription",
    "AccountType": "Can be inferred from Account or DataSourceName"
}