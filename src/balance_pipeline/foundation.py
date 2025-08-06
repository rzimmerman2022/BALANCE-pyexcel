# src/balance_pipeline/foundation.py
"""
Defines the foundational schema for the BALANCE-pyexcel pipeline.
This includes the core set of columns that every processed transaction record
should aim to have, forming the basis for consistent analysis and reconciliation.
"""
from pandas import Float64Dtype, StringDtype  # For pandas dtypes

# The 8+1 Core Foundational Columns
# These columns represent the "gold standard" minimal viable transaction.
# 'Account' is included as the "+1" for essential bookkeeping.
CORE_FOUNDATION_COLUMNS = [
    "TxnID",               # Unique transaction identifier (string)
    "Owner",               # Owner of the transaction (Ryan/Jordyn) (string)
    "Date",                # Transaction date (datetime64[ns])
    "Amount",              # Transaction amount (float64)
    "Merchant",            # Cleaned merchant name (string)
    "Description",         # Cleaned, human-readable transaction description (string)
    "Category",            # Transaction category (string)
    "Account",             # Account identifier (string)
    "sharing_status",      # Sharing status ('individual', 'shared', 'split') (string/pd.StringDtype())
]

# Expected dtypes for the core foundational columns
# Using pandas ExtensionDtypes for nullable types where appropriate.
CORE_FOUNDATION_DTYPES = {
    "TxnID": StringDtype(),
    "Owner": StringDtype(),
    "Date": "datetime64[ns]", # Pandas handles this well
    "Amount": Float64Dtype(), # Ensures it's float, not object if all NA
    "Merchant": StringDtype(),
    "Description": StringDtype(),
    "Category": StringDtype(),
    "Account": StringDtype(),
    "sharing_status": StringDtype(),
}

# Relationship to MASTER_SCHEMA_COLUMNS:
# This foundation is a subset of the full MASTER_SCHEMA_COLUMNS (defined in constants.py).
# In "flexible" schema mode, these CORE_FOUNDATION_COLUMNS are guaranteed to exist if the
# pipeline can produce them.
# In "strict" schema mode, all MASTER_SCHEMA_COLUMNS are present, which includes these.

# For reference, other important related columns often generated:
# - OriginalDescription: Raw description from source, input to cleaner.
# - OriginalMerchant: Raw merchant from source/OriginalDescription, input to cleaner.
# - SharedFlag: Boolean indicating if shared (used to derive sharing_status).
# - SplitPercent: Float indicating split percentage (used to derive sharing_status).
# - DataSourceName: Identifier for the source schema/file type.
# - DataSourceDate: Date the source data was obtained/processed.
# - Extras: JSON blob of unmapped source columns.

# Note: While 'Currency' is in MASTER_SCHEMA_COLUMNS and often 'USD',
# it's not included in this minimal set as it's often implicitly USD for this project
# and can be added downstream if multiple currencies become a factor.
