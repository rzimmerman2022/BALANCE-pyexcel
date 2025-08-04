# canonical_schema_v3.py
"""
The Lean Canonical Schema v3
============================
This is the true foundation - only fields that are:
1. Genuinely universal across all financial data sources
2. Essential for basic financial analysis
3. Actually populated with meaningful data

Everything else becomes source-specific extensions.
"""

# Core fields that EVERY transaction must have
REQUIRED_FIELDS = [
    'TxnID',        # Unique identifier (generated if needed)
    'Date',         # When it happened (THE critical field)
    'Amount',       # How much
    'Description',  # What it was (however the source describes it)
    'Owner'         # Whose transaction this is
]

# Fields that are common but not universal
COMMON_FIELDS = [
    'Account',      # Which account (might be inferred from filename)
    'Category',     # Transaction category (if source provides it)
    'PostDate',     # When it cleared (banks care, aggregators don't)
    'Institution',  # Which bank/card (might be inferred)
    'Merchant'      # Who you paid (aggregators have this, banks don't)
]

# Source-specific fields that should only appear when actually present
SOURCE_SPECIFIC_FIELDS = {
    'banking': [
        'ReferenceNumber',
        'StatementStart',
        'StatementEnd',
        'AccountNumber',
        'AccountLast4'
    ],
    'aggregator': [
        'OriginalStatement',
        'Tags',
        'Notes'
    ]
}

# System fields added by the pipeline
SYSTEM_FIELDS = [
    'DataSourceName',   # Which schema processed this
    'DataSourceDate',   # When it was processed
    'ImportID'          # Which import batch
]

# The complete canonical schema
CANONICAL_SCHEMA_V3 = REQUIRED_FIELDS + COMMON_FIELDS + SYSTEM_FIELDS

# Fields we're explicitly NOT including anymore
DEPRECATED_FIELDS = [
    'SharedFlag',       # Never used
    'SplitPercent',     # Never used
    'Currency',         # Always USD
    'AccountType',      # Inconsistently used
    'OriginalDate',     # Redundant with Date
    'StatementPeriodDesc', # Redundant with Start/End
    'OriginalStatement', # Folded into Description
    'Extras'            # Source of confusion
]

def validate_dataframe(df, source_type='unknown'):
    """
    Validate that a dataframe meets the canonical schema requirements.
    This is what clean data looks like.
    """
    issues = []
    
    # Check required fields exist and are populated
    for field in REQUIRED_FIELDS:
        if field not in df.columns:
            issues.append(f"Missing required field: {field}")
        elif df[field].isna().any():
            null_count = df[field].isna().sum()
            issues.append(f"Required field {field} has {null_count} null values")
    
    # Check Date is actually datetime
    if 'Date' in df.columns:
        if df['Date'].dtype != 'datetime64[ns]':
            issues.append(f"Date field is {df['Date'].dtype}, not datetime")
    
    # Check Amount is numeric
    if 'Amount' in df.columns:
        if not pd.api.types.is_numeric_dtype(df['Amount']):
            issues.append(f"Amount field is {df['Amount'].dtype}, not numeric")
    
    # Check for deprecated fields that shouldn't be there
    deprecated_present = [f for f in DEPRECATED_FIELDS if f in df.columns]
    if deprecated_present:
        issues.append(f"Deprecated fields present: {deprecated_present}")
    
    # Check that we don't have empty columns
    for col in df.columns:
        if df[col].isna().all():
            issues.append(f"Column {col} is entirely empty")
    
    return issues

def get_schema_for_source(source_name):
    """
    Return the appropriate field list for a given source type.
    This is how we avoid phantom columns.
    """
    # Detect source type from name
    if any(bank in source_name.lower() for bank in ['chase', 'wells', 'discover', 'bank']):
        source_type = 'banking'
    elif any(agg in source_name.lower() for agg in ['monarch', 'rocket', 'mint']):
        source_type = 'aggregator'
    else:
        source_type = 'unknown'
    
    # Build field list
    fields = REQUIRED_FIELDS + COMMON_FIELDS + SYSTEM_FIELDS
    
    # Add source-specific fields only if they exist
    if source_type in SOURCE_SPECIFIC_FIELDS:
        fields.extend(SOURCE_SPECIFIC_FIELDS[source_type])
    
    return fields, source_type