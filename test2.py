import pandas as pd
import numpy as np

# Load the parquet file
df = pd.read_parquet("output/balance_final.parquet")

print("Placeholder Value Analysis")
print("=" * 60)

# Define known placeholder values
placeholders = {
    'date_placeholders': ['NaT', 'nat', 'NAT'],
    'text_placeholders': ['<PA>', '<NA>', 'NA', 'N/A', '#N/A', 'nan', 'NaN', ''],
    'numeric_placeholders': [-999999, 999999, -1]  # Common numeric placeholders
}

# Analyze each column
results = []
for col in df.columns:
    col_type = str(df[col].dtype)
    total_rows = len(df)
    
    # Count different types of meaningless data
    if 'datetime' in col_type:
        # For datetime columns, check for NaT
        nat_count = df[col].isna().sum()  # pandas counts NaT as NA for datetime
        placeholder_count = nat_count
    elif 'object' in col_type:  # String columns
        # Check for text placeholders
        placeholder_mask = df[col].isin(placeholders['text_placeholders'])
        placeholder_count = placeholder_mask.sum()
        # Also check for empty strings separately
        empty_count = (df[col] == '').sum()
        placeholder_count += empty_count
    else:  # Numeric columns
        # Check for numeric placeholders
        placeholder_mask = df[col].isin(placeholders['numeric_placeholders'])
        placeholder_count = placeholder_mask.sum()
    
    # Calculate percentage of meaningful data
    meaningful_count = total_rows - placeholder_count - df[col].isna().sum()
    meaningful_pct = (meaningful_count / total_rows) * 100
    
    results.append({
        'Column': col,
        'Type': col_type,
        'Meaningful %': meaningful_pct,
        'Placeholder Count': placeholder_count
    })

# Sort by meaningful percentage (ascending) to see worst offenders first
results_df = pd.DataFrame(results).sort_values('Meaningful %')

print("\nColumns with High Placeholder Rates:")
print("-" * 60)
for _, row in results_df[results_df['Meaningful %'] < 100].iterrows():
    print(f"{row['Column']:25} {row['Meaningful %']:6.1f}% meaningful "
          f"({row['Placeholder Count']} placeholders)")

# Now let's see which sources contribute to which columns
print("\n\nSource-Specific Column Population:")
print("=" * 60)

for source in df['DataSourceName'].unique():
    source_df = df[df['DataSourceName'] == source]
    print(f"\n{source} ({len(source_df)} rows):")
    
    # Check a few key columns for this source
    check_columns = ['Institution', 'StatementStart', 'ReferenceNumber', 'AccountLast4']
    for col in check_columns:
        if col in source_df.columns:
            # Count meaningful values (not placeholders, not null)
            if 'datetime' in str(source_df[col].dtype):
                meaningful = source_df[col].notna()
            else:
                not_placeholder = ~source_df[col].isin(
                    placeholders.get('text_placeholders', []) + [''])
                meaningful = not_placeholder & source_df[col].notna()
            
            meaningful_pct = (meaningful.sum() / len(source_df)) * 100
            if meaningful_pct < 100:
                print(f"  {col}: {meaningful_pct:.1f}% meaningful")
                # Show what's actually in this column
                value_counts = source_df[col].value_counts().head(3)
                for value, count in value_counts.items():
                    print(f"    '{value}': {count} occurrences")