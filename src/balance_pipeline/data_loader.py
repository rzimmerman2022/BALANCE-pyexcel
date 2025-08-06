"""
Main data loader for balance pipeline.
Uses modular loaders to ensure all DataFrames conform to Canonical Transaction Schema (CTS).
"""

import pathlib

import pandas as pd

from .column_utils import CTS, validate_cts_compliance
from .loaders import LOADER_REGISTRY


def load_all_data(data_dir: pathlib.Path) -> pd.DataFrame:
    """
    Load all CSV data using modular loaders and return CTS-compliant DataFrame.
    
    Args:
        data_dir: Directory containing CSV files
        
    Returns:
        Combined DataFrame with Canonical Transaction Schema
    """
    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")
    
    all_frames = []
    
    # Execute each loader
    for loader_func in LOADER_REGISTRY:
        try:
            df = loader_func(data_dir)
            
            if not df.empty:
                # Validate CTS compliance
                if not validate_cts_compliance(df):
                    print(f"Warning: {loader_func.__name__} returned non-CTS compliant DataFrame")
                    continue
                
                all_frames.append(df)
                print(f"Loaded {len(df)} rows from {loader_func.__name__}")
            else:
                print(f"No data loaded from {loader_func.__name__}")
                
        except Exception as e:
            print(f"Error in {loader_func.__name__}: {e}")
            continue
    
    if not all_frames:
        print("Warning: No data loaded from any source")
        # Return empty DataFrame with CTS structure
        empty_df = pd.DataFrame(columns=CTS)
        return empty_df
    
    # Concatenate all frames - guaranteed to work since all are CTS-compliant
    combined_df = pd.concat(all_frames, ignore_index=True)
    
    print(f"Total combined rows: {len(combined_df)}")
    print(f"Date range: {combined_df['date'].min()} to {combined_df['date'].max()}")
    print(f"Sources: {combined_df['source_file'].value_counts().to_dict()}")
    
    return combined_df


# Legacy compatibility function
def legacy_load_all_data(data_dir: pathlib.Path) -> pd.DataFrame:
    """
    Legacy compatibility wrapper for existing scripts.
    Deprecated: Use load_all_data() instead.
    """
    import warnings
    warnings.warn(
        "legacy_load_all_data is deprecated. Use load_all_data() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return load_all_data(data_dir)


if __name__ == '__main__':
    # Test the loader
    data_dir = pathlib.Path('data')
    df = load_all_data(data_dir)
    
    if not df.empty:
        print("\nDataFrame Info:")
        print(df.info())
        print("\nSample rows:")
        print(df.head(10))
        print("\nCTS Compliance:", validate_cts_compliance(df))
    else:
        print("No data loaded")
