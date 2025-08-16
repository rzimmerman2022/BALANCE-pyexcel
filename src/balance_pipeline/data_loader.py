"""
Main data loader for balance pipeline.
Uses modular loaders to ensure all DataFrames conform to Canonical Transaction Schema (CTS).
"""

import logging
import pathlib

import pandas as pd

from .column_utils import CTS, validate_cts_compliance
from .loaders import LOADER_REGISTRY

logger = logging.getLogger(__name__)


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
                    logger.warning(
                        f"{loader_func.__name__} returned non-CTS compliant DataFrame"
                    )
                    continue

                all_frames.append(df)
                logger.info(f"Loaded {len(df)} rows from {loader_func.__name__}")
            else:
                logger.debug(f"No data loaded from {loader_func.__name__}")

        except Exception as e:
            logger.error(f"Error in {loader_func.__name__}: {e}")
            continue

    if not all_frames:
        logger.warning("No data loaded from any source")
        # Return empty DataFrame with CTS structure
        empty_df = pd.DataFrame(columns=CTS)
        return empty_df

    # Concatenate all frames - guaranteed to work since all are CTS-compliant
    combined_df = pd.concat(all_frames, ignore_index=True)

    logger.info(f"Total combined rows: {len(combined_df)}")
    logger.info(
        f"Date range: {combined_df['date'].min()} to {combined_df['date'].max()}"
    )
    logger.info(f"Sources: {combined_df['source_file'].value_counts().to_dict()}")

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
        stacklevel=2,
    )
    return load_all_data(data_dir)


if __name__ == "__main__":
    # Test the loader
    data_dir = pathlib.Path("data")
    df = load_all_data(data_dir)

    if not df.empty:
        logger.info("\nDataFrame Info:")
        logger.info(df.info())
        logger.info("\nSample rows:")
        logger.info(df.head(10))
        logger.info("\nCTS Compliance: %s", validate_cts_compliance(df))
    else:
        logger.info("No data loaded")
