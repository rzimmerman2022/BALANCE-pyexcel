"""
CSV streaming utilities for handling large files efficiently.

This module provides functions to read and process CSV files in chunks,
preventing memory exhaustion when dealing with large datasets.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterator, Optional, Any

import pandas as pd

logger = logging.getLogger(__name__)


def read_csv_chunked(
    filepath: str | Path,
    chunk_size: int = 10000,
    encoding: str = 'utf-8',
    **kwargs: Any
) -> Iterator[pd.DataFrame]:
    """
    Read a CSV file in chunks to handle large files efficiently.
    
    Args:
        filepath: Path to the CSV file
        chunk_size: Number of rows per chunk (default: 10,000)
        encoding: File encoding (default: utf-8)
        **kwargs: Additional arguments passed to pd.read_csv
        
    Yields:
        DataFrame chunks of the specified size
        
    Example:
        >>> for chunk in read_csv_chunked('large_file.csv', chunk_size=5000):
        ...     process_chunk(chunk)
    """
    filepath = Path(filepath)
    
    if not filepath.exists():
        raise FileNotFoundError(f"CSV file not found: {filepath}")
    
    # Determine file size for logging
    file_size_mb = filepath.stat().st_size / (1024 * 1024)
    logger.info(f"Starting chunked read of {filepath.name} ({file_size_mb:.2f} MB)")
    
    # Default CSV reading parameters optimized for financial data
    csv_params = {
        'encoding': encoding,
        'chunksize': chunk_size,
        'parse_dates': True,
        'infer_datetime_format': True,
        'keep_default_na': True,
        'na_values': ['', 'N/A', 'NA', 'null', 'NULL', 'none', 'None'],
    }
    
    # Override with user-provided parameters
    csv_params.update(kwargs)
    
    try:
        chunk_count = 0
        with pd.read_csv(filepath, **csv_params) as reader:
            for chunk in reader:
                chunk_count += 1
                logger.debug(f"Processing chunk {chunk_count} ({len(chunk)} rows)")
                yield chunk
                
        logger.info(f"Completed reading {filepath.name}: {chunk_count} chunks processed")
        
    except UnicodeDecodeError as e:
        logger.warning(f"Unicode decode error for {filepath}, trying latin-1 encoding")
        # Retry with latin-1 encoding
        csv_params['encoding'] = 'latin-1'
        
        chunk_count = 0
        with pd.read_csv(filepath, **csv_params) as reader:
            for chunk in reader:
                chunk_count += 1
                yield chunk
                
    except pd.errors.EmptyDataError:
        logger.warning(f"Empty CSV file: {filepath}")
        # Return empty DataFrame with expected structure
        yield pd.DataFrame()
        
    except Exception as e:
        logger.error(f"Error reading CSV file {filepath}: {e}")
        raise


def process_csv_file_streaming(
    filepath: str | Path,
    processor_func: callable,
    chunk_size: int = 10000,
    encoding: str = 'utf-8',
    **csv_kwargs: Any
) -> pd.DataFrame:
    """
    Process a CSV file in chunks and combine the results.
    
    Args:
        filepath: Path to the CSV file
        processor_func: Function to process each chunk (must accept DataFrame, return DataFrame)
        chunk_size: Number of rows per chunk
        encoding: File encoding
        **csv_kwargs: Additional arguments for pd.read_csv
        
    Returns:
        Combined DataFrame with all processed chunks
        
    Example:
        >>> def clean_chunk(df):
        ...     return df.dropna()
        >>> result = process_csv_file_streaming('data.csv', clean_chunk)
    """
    processed_chunks = []
    
    for chunk in read_csv_chunked(filepath, chunk_size, encoding, **csv_kwargs):
        if not chunk.empty:
            processed_chunk = processor_func(chunk)
            if not processed_chunk.empty:
                processed_chunks.append(processed_chunk)
    
    if not processed_chunks:
        logger.warning(f"No data to combine from {filepath}")
        return pd.DataFrame()
    
    # Combine all processed chunks
    result = pd.concat(processed_chunks, ignore_index=True)
    logger.info(f"Combined {len(processed_chunks)} chunks into {len(result)} total rows")
    
    return result


def estimate_memory_usage(filepath: str | Path, sample_size: int = 1000) -> dict[str, float]:
    """
    Estimate memory usage for a CSV file by sampling.
    
    Args:
        filepath: Path to the CSV file
        sample_size: Number of rows to sample for estimation
        
    Returns:
        Dictionary with memory usage estimates in MB
    """
    filepath = Path(filepath)
    
    # Read sample
    sample_df = pd.read_csv(filepath, nrows=sample_size)
    
    # Calculate memory usage per row
    memory_per_row_bytes = sample_df.memory_usage(deep=True).sum() / len(sample_df)
    
    # Count total rows (efficient line counting)
    with open(filepath, 'rb') as f:
        total_rows = sum(1 for _ in f) - 1  # Subtract header row
    
    # Estimate total memory
    estimated_memory_mb = (memory_per_row_bytes * total_rows) / (1024 * 1024)
    
    return {
        'sample_rows': sample_size,
        'total_rows': total_rows,
        'memory_per_row_kb': memory_per_row_bytes / 1024,
        'estimated_total_memory_mb': estimated_memory_mb,
        'file_size_mb': filepath.stat().st_size / (1024 * 1024),
    }


def should_use_streaming(
    filepath: str | Path, 
    memory_threshold_mb: float = 500.0
) -> bool:
    """
    Determine if streaming should be used based on file size and estimated memory usage.
    
    Args:
        filepath: Path to the CSV file
        memory_threshold_mb: Memory threshold in MB (default: 500 MB)
        
    Returns:
        True if streaming is recommended, False otherwise
    """
    try:
        estimates = estimate_memory_usage(filepath)
        
        if estimates['estimated_total_memory_mb'] > memory_threshold_mb:
            logger.info(
                f"Streaming recommended for {Path(filepath).name}: "
                f"estimated {estimates['estimated_total_memory_mb']:.2f} MB > "
                f"threshold {memory_threshold_mb:.2f} MB"
            )
            return True
        else:
            return False
            
    except Exception as e:
        logger.warning(f"Could not estimate memory usage: {e}. Using file size heuristic.")
        # Fallback: use file size as proxy (assume 10x expansion in memory)
        file_size_mb = Path(filepath).stat().st_size / (1024 * 1024)
        return file_size_mb * 10 > memory_threshold_mb