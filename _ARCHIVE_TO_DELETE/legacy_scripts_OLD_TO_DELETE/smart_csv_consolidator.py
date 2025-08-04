# smart_csv_consolidator.py
"""
Smart CSV Consolidator
======================
This is the foundational fix that prevents phantom columns.
Instead of creating 27 columns regardless of data availability,
it only includes columns that actually contain meaningful data.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import logging
from canonical_schema_v3 import (
    REQUIRED_FIELDS, 
    COMMON_FIELDS, 
    SYSTEM_FIELDS,
    get_schema_for_source,
    validate_dataframe
)

class SmartConsolidator:
    """
    A consolidator that respects the reality of your data sources
    instead of forcing them into an impossible mold.
    """
    
    def __init__(self, schema_dir='rules'):
        self.schema_dir = Path(schema_dir)
        self.logger = logging.getLogger(__name__)
        
    def process_source_file(self, csv_path, schema):
        """
        Process a single CSV file according to its schema.
        Key difference: we only create columns that have data.
        """
        # Read the CSV
        df = pd.read_csv(csv_path)
        self.logger.info(f"Read {len(df)} rows from {csv_path.name}")
        
        # Apply column mappings
        mapped_df = pd.DataFrame()
        
        for target_col, source_col in schema.get('column_map', {}).items():
            if source_col in df.columns:
                mapped_df[target_col] = df[source_col]
                self.logger.debug(f"Mapped {source_col} -> {target_col}")
            else:
                self.logger.warning(f"Source column '{source_col}' not found, skipping {target_col}")
        
        # CRITICAL FIX #1: Parse dates immediately after mapping
        date_columns = schema.get('date_columns', [])
        for date_config in date_columns:
            col = date_config['column']
            if col in mapped_df.columns:
                # Try to parse with specified format first
                date_format = date_config.get('format')
                if date_format:
                    try:
                        mapped_df[col] = pd.to_datetime(mapped_df[col], format=date_format)
                        self.logger.info(f"Parsed {col} with format {date_format}")
                    except:
                        # Fall back to intelligent parsing
                        mapped_df[col] = pd.to_datetime(mapped_df[col], 
                                                       errors='coerce',
                                                       infer_datetime_format=True)
                        self.logger.warning(f"Used inferred parsing for {col}")
                else:
                    # No format specified, use intelligent parsing
                    mapped_df[col] = pd.to_datetime(mapped_df[col], 
                                                   errors='coerce',
                                                   infer_datetime_format=True)
                
                # Validate parsed dates
                nat_count = mapped_df[col].isna().sum()
                if nat_count > 0:
                    self.logger.error(f"Failed to parse {nat_count} dates in {col}")
        
        # CRITICAL FIX #2: Ensure Date column exists and is valid
        if 'Date' not in mapped_df.columns and 'OriginalDate' in mapped_df.columns:
            mapped_df['Date'] = mapped_df['OriginalDate']
            self.logger.info("Used OriginalDate as Date fallback")
        
        # Apply derived columns
        for col_name, rule in schema.get('derived_columns', {}).items():
            if rule['type'] == 'constant':
                mapped_df[col_name] = rule['value']
            elif rule['type'] == 'extract_from_account' and 'Account' in mapped_df.columns:
                # Extract pattern from account field
                pattern = rule.get('pattern', '')
                if col_name == 'Institution':
                    mapped_df[col_name] = mapped_df['Account'].str.extract(pattern)[0]
                elif col_name == 'AccountLast4':
                    mapped_df[col_name] = mapped_df['Account'].str.extract(pattern)[0]
        
        # Add system fields
        mapped_df['DataSourceName'] = schema.get('name', csv_path.stem)
        mapped_df['DataSourceDate'] = datetime.now()
        
        # Generate transaction IDs if not present
        if 'TxnID' not in mapped_df.columns:
            # Create deterministic IDs based on content
            id_components = mapped_df[['Date', 'Amount', 'Description']].fillna('').astype(str)
            mapped_df['TxnID'] = pd.util.hash_pandas_object(id_components).astype(str)
        
        return mapped_df
    
    def consolidate_sources(self, source_files, output_path):
        """
        Consolidate multiple source files into a single parquet file.
        Key innovation: only include columns that actually have data.
        """
        all_frames = []
        
        for csv_path, schema in source_files:
            try:
                df = self.process_source_file(csv_path, schema)
                all_frames.append(df)
                self.logger.info(f"Processed {csv_path.name}: {len(df)} rows, {len(df.columns)} columns")
            except Exception as e:
                self.logger.error(f"Failed to process {csv_path.name}: {e}")
                continue
        
        if not all_frames:
            raise ValueError("No files successfully processed")
        
        # CRITICAL FIX #3: Smart concatenation that doesn't create phantom columns
        # Instead of forcing all dataframes to have the same columns, we:
        # 1. Identify which columns actually have data
        # 2. Only include those in the final output
        
        # Find all columns that have at least SOME data
        columns_with_data = set()
        for df in all_frames:
            for col in df.columns:
                if not df[col].isna().all():  # Column has at least one non-null value
                    columns_with_data.add(col)
        
        # Determine final column set based on canonical schema
        expected_columns, _ = get_schema_for_source('consolidated')
        final_columns = [col for col in expected_columns if col in columns_with_data]
        
        # Add any unexpected columns that have data (for debugging)
        unexpected_columns = columns_with_data - set(expected_columns)
        if unexpected_columns:
            self.logger.warning(f"Unexpected columns with data: {unexpected_columns}")
            final_columns.extend(sorted(unexpected_columns))
        
        # Standardize all dataframes to have the same columns
        standardized_frames = []
        for df in all_frames:
            standardized = pd.DataFrame(index=df.index)
            for col in final_columns:
                if col in df.columns:
                    standardized[col] = df[col]
                else:
                    # Only create null column if it's a required field
                    if col in REQUIRED_FIELDS:
                        standardized[col] = np.nan
                        self.logger.warning(f"Required field {col} missing from {df['DataSourceName'].iloc[0]}")
            standardized_frames.append(standardized)
        
        # Combine all frames
        combined_df = pd.concat(standardized_frames, ignore_index=True)
        
        # CRITICAL FIX #4: Final cleanup - remove any columns that ended up all null
        columns_to_drop = []
        for col in combined_df.columns:
            if combined_df[col].isna().all():
                columns_to_drop.append(col)
        
        if columns_to_drop:
            self.logger.info(f"Dropping empty columns: {columns_to_drop}")
            combined_df = combined_df.drop(columns=columns_to_drop)
        
        # Validate the final dataframe
        issues = validate_dataframe(combined_df)
        if issues:
            self.logger.warning(f"Validation issues: {issues}")
        
        # Sort by date for better organization
        if 'Date' in combined_df.columns:
            combined_df = combined_df.sort_values('Date', ascending=False)
        
        # Write to parquet
        combined_df.to_parquet(output_path, index=False)
        self.logger.info(f"Wrote {len(combined_df)} rows, {len(combined_df.columns)} columns to {output_path}")
        
        # Log column summary
        self.logger.info("Final columns: " + ", ".join(combined_df.columns))
        
        return combined_df

# Example usage showing how to process files
def process_all_sources():
    """
    Example of processing all sources with proper schema loading
    """
    consolidator = SmartConsolidator()
    
    # Define source files and their schemas
    source_configs = [
        ('data/ryan_monarch.csv', 'ryan_monarch_v2.yaml'),
        ('data/ryan_rocket.csv', 'ryan_rocket_v2.yaml'),
        ('data/jordyn_chase.csv', 'jordyn_chase_v2.yaml'),
        ('data/jordyn_wells.csv', 'jordyn_wells_v2.yaml'),
        ('data/jordyn_discover.csv', 'jordyn_discover_v2.yaml')
    ]
    
    # Load schemas and pair with files
    source_files = []
    for csv_path, schema_name in source_configs:
        schema = load_schema(f'rules/{schema_name}')  # You'd implement schema loading
        source_files.append((Path(csv_path), schema))
    
    # Process everything
    output_df = consolidator.consolidate_sources(
        source_files,
        'output/balance_final_v3.parquet'
    )
    
    return output_df