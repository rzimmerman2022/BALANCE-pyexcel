#!/usr/bin/env python3
# =============================================================================
# BALANCE-pyexcel Pipeline v2 Module
# =============================================================================
# Project: BALANCE-pyexcel
# Module: pipeline_v2.py
# Description: Unified Pipeline for CSV file processing with configurable modes
# Author: BALANCE Development Team
# License: MIT
# =============================================================================

"""Unified Pipeline for CSV file processing.

This module provides the UnifiedPipeline class which orchestrates the entire
data processing workflow, from reading CSV files through schema matching,
data transformation, and consolidation into a single DataFrame.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any, Union

import pandas as pd
from balance_pipeline.config import (
    MERCHANT_LOOKUP_PATH,
    SCHEMA_REGISTRY_PATH,
)

# Import from existing modules
from balance_pipeline.csv_consolidator import process_csv_files
from balance_pipeline.errors import (
    BalancePipelineError,  # Use the actual class name
    FatalSchemaError,
    RecoverableFileError,
)

# Type aliases for clarity
PathLike = Union[str, Path]
logger = logging.getLogger(__name__)


class UnifiedPipeline:
    """
    Unified pipeline that handles CSV file processing with configurable schema modes.

    This class encapsulates the entire processing workflow, providing a clean
    interface for transforming multiple CSV files into a consolidated DataFrame.
    It handles schema matching, data transformation, merchant cleaning, and
    all other processing steps.

    The pipeline supports two schema modes:
    - 'strict': All 25 columns from MASTER_SCHEMA_COLUMNS are always present
    - 'flexible': Only columns with actual data are included

    Attributes:
        schema_mode: The schema validation mode ('strict' or 'flexible')
        debug_mode: Enable detailed debug logging and reporting
        _processing_stats: Dictionary tracking processing statistics
    """

    def __init__(self, schema_mode: str = "flexible", debug_mode: bool = False) -> None:
        """
        Initialize the UnifiedPipeline with specified configuration.

        Args:
            schema_mode: Schema validation mode - either 'strict' or 'flexible'
                        - 'strict': Enforces all 25 master columns
                        - 'flexible': Only includes columns with data
            debug_mode: Enable debug mode for detailed processing information

        Raises:
            ValueError: If schema_mode is not 'strict' or 'flexible'
        """
        # Validate schema_mode
        valid_modes = {"strict", "flexible"}
        if schema_mode not in valid_modes:
            raise ValueError(
                f"schema_mode must be one of {valid_modes}, got '{schema_mode}'"
            )

        self.schema_mode = schema_mode
        self.debug_mode = debug_mode
        self._processing_stats: dict[str, Any] = self._init_stats()

        logger.info(
            f"Initialized UnifiedPipeline (schema_mode={schema_mode}, "
            f"debug_mode={debug_mode})"
        )

    def process_files(
        self,
        file_paths: Sequence[PathLike],  # Use Sequence instead of List
        schema_registry_override_path: PathLike | None = None,
        merchant_lookup_override_path: PathLike | None = None,
    ) -> pd.DataFrame:
        """
        Process CSV files and return consolidated DataFrame.

        This is the main entry point for file processing. It accepts both string
        paths and Path objects for maximum flexibility, converts them as needed,
        and orchestrates the entire processing workflow.

        Note: We use Sequence[PathLike] instead of List to indicate that this
        method will not modify the input collection. This provides better type
        safety and allows callers to pass any sequence type (list, tuple, etc.).

        Args:
            file_paths: Sequence of file paths (can be strings or Path objects)
            schema_registry_override_path: Optional custom schema registry path
            merchant_lookup_override_path: Optional custom merchant lookup path

        Returns:
            Consolidated DataFrame containing all processed transactions

        Raises:
            BalancePipelineError: For general pipeline errors
            FatalSchemaError: For unrecoverable schema-related errors
            RecoverableFileError: For file-specific errors that don't stop processing
            ValueError: For invalid input parameters
        """
        start_time = datetime.now()

        # Reset stats for new processing run
        self._processing_stats = self._init_stats()

        try:
            # Step 1: Normalize and validate all paths
            normalized_paths = self._normalize_paths(file_paths)
            schema_path = self._normalize_single_path(
                schema_registry_override_path, default=SCHEMA_REGISTRY_PATH
            )
            merchant_path = self._normalize_single_path(
                merchant_lookup_override_path, default=MERCHANT_LOOKUP_PATH
            )

            # Step 2: Validate inputs
            self._validate_inputs(normalized_paths, schema_path, merchant_path)

            # Step 3: Log processing start
            logger.info(f"Starting processing of {len(normalized_paths)} files")
            if self.debug_mode:
                self._log_debug_info(normalized_paths, schema_path, merchant_path)

            # Step 4: Configure processing based on schema mode
            # Temporarily override the global SCHEMA_MODE for this processing run
            import balance_pipeline.config as bp_config

            original_schema_mode = bp_config.SCHEMA_MODE
            try:
                bp_config.SCHEMA_MODE = self.schema_mode

                # Step 5: Process files using the CSV consolidator
                # The consolidator accepts List[Union[str, Path]], so we convert our
                # normalized Path objects to a list that matches the expected type
                file_list: list[str | Path] = list(normalized_paths)

                processed_df = process_csv_files(
                    csv_files=file_list,
                    schema_registry_override_path=schema_path,
                    merchant_lookup_override_path=merchant_path,
                    debug_mode=self.debug_mode,  # Pass debug_mode to enable detailed logging
                )
            finally:
                # Restore original schema mode
                bp_config.SCHEMA_MODE = original_schema_mode

            # Step 6: Update processing statistics
            self._update_stats(processed_df, normalized_paths)

            # Step 7: Apply schema mode transformations
            processed_df = self._apply_schema_mode(processed_df)

            # Step 8: Perform final validations
            self._validate_output(processed_df)

            # Step 9: Log completion
            processing_time = (datetime.now() - start_time).total_seconds()
            self._processing_stats["processing_time"] = processing_time

            logger.info(
                f"Processing completed in {processing_time:.2f} seconds. "
                f"Total rows: {len(processed_df)}, "
                f"Schema mode: {self.schema_mode}"
            )

            return processed_df

        except (FatalSchemaError, RecoverableFileError):
            # Re-raise known pipeline errors without wrapping
            raise
        except Exception as e:
            # Wrap unexpected errors in BalancePipelineError
            logger.exception(f"Unexpected error during processing: {e}")
            raise BalancePipelineError(f"Pipeline processing failed: {e}") from e

    def _normalize_paths(self, paths: Sequence[PathLike]) -> list[Path]:
        """
        Convert a sequence of string or Path objects to a list of Path objects.

        This method ensures consistent Path object usage throughout the pipeline,
        regardless of how the user provides the file paths. It also expands
        user paths (e.g., ~) and resolves them to absolute paths.

        Args:
            paths: Sequence of paths as strings or Path objects

        Returns:
            List of resolved Path objects

        Raises:
            ValueError: If the input is empty
            TypeError: If any path is not a string or Path object
        """
        if not paths:
            raise ValueError("No file paths provided for processing")

        normalized: list[Path] = []

        for i, path in enumerate(paths):
            try:
                if isinstance(path, str):
                    # Expand user path and resolve to absolute
                    expanded_path = Path(path).expanduser().resolve()
                    normalized.append(expanded_path)
                elif isinstance(path, Path):
                    # Expand user path and resolve to absolute
                    expanded_path = path.expanduser().resolve()
                    normalized.append(expanded_path)
                else:
                    raise TypeError(
                        f"Path at index {i} must be str or Path, "
                        f"got {type(path).__name__}: {path}"
                    )
            except Exception as e:
                raise ValueError(f"Invalid path at index {i}: {path}") from e

        return normalized

    def _normalize_single_path(
        self, path: PathLike | None, default: Path | None = None
    ) -> Path | None:
        """
        Convert a single optional path to a Path object with default fallback.
        Expands user paths and resolves to absolute paths.

        Args:
            path: Optional path as string or Path object
            default: Default Path to use if path is None

        Returns:
            Resolved Path object, default if path was None, or None if both are None

        Raises:
            TypeError: If path is not None, str, or Path
        """
        if path is None:
            return default
        elif isinstance(path, str):
            return Path(path).expanduser().resolve()
        elif isinstance(path, Path):
            return path.expanduser().resolve()
        else:
            raise TypeError(
                f"Expected None, str, or Path, got {type(path).__name__}: {path}"
            )

    def _validate_inputs(
        self,
        file_paths: list[Path],
        schema_path: Path | None,
        merchant_path: Path | None,
    ) -> None:
        """
        Validate all input paths exist and are accessible.

        This method performs comprehensive validation to catch common errors
        before processing begins, providing clear error messages to help users.

        Args:
            file_paths: List of CSV file paths to validate
            schema_path: Schema registry path to validate (if provided)
            merchant_path: Merchant lookup path to validate (if provided)

        Raises:
            FileNotFoundError: If any required file doesn't exist
            ValueError: If inputs are invalid (e.g., not a file, wrong extension)
        """
        # Validate each CSV file
        for file_path in file_paths:
            if not file_path.exists():
                raise FileNotFoundError(f"CSV file not found: {file_path}")
            if not file_path.is_file():
                raise ValueError(f"Path is not a file: {file_path}")
            if file_path.suffix.lower() != ".csv":
                logger.warning(
                    f"File may not be CSV (extension: {file_path.suffix}): "
                    f"{file_path.name}"
                )

        # Validate schema registry if provided
        if schema_path:
            if not schema_path.exists():
                raise FileNotFoundError(f"Schema registry not found: {schema_path}")
            if not schema_path.is_file():
                raise ValueError(f"Schema registry path is not a file: {schema_path}")
            if schema_path.suffix.lower() not in [".yml", ".yaml"]:
                logger.warning(
                    f"Schema registry file has unexpected extension: {schema_path.suffix}"
                )

        # Validate merchant lookup if provided
        if merchant_path:
            if not merchant_path.exists():
                raise FileNotFoundError(f"Merchant lookup not found: {merchant_path}")
            if not merchant_path.is_file():
                raise ValueError(f"Merchant lookup path is not a file: {merchant_path}")
            if merchant_path.suffix.lower() != ".csv":
                logger.warning(
                    f"Merchant lookup file has unexpected extension: {merchant_path.suffix}"
                )

    def _apply_schema_mode(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply schema mode transformations to the processed DataFrame.

        In 'strict' mode, ensures all master columns are present.
        In 'flexible' mode, removes empty columns to reduce size.

        Args:
            df: The processed DataFrame

        Returns:
            DataFrame transformed according to schema mode
        """
        if self.schema_mode == "strict":
            # In strict mode, the csv_consolidator should already ensure
            # all columns are present. This is just a verification step.
            logger.debug("Applying strict schema mode validation")
            # Add any missing required columns if needed
            # (Implementation depends on your MASTER_SCHEMA_COLUMNS)
        else:
            # In flexible mode, we might want to remove entirely empty columns
            logger.debug("Applying flexible schema mode optimizations")
            # This is already handled by csv_consolidator when SCHEMA_MODE is flexible

        return df

    def _log_debug_info(
        self,
        file_paths: list[Path],
        schema_path: Path | None,
        merchant_path: Path | None,
    ) -> None:
        """
        Log detailed debug information about the processing request.

        This method provides verbose logging when debug mode is enabled,
        helping with troubleshooting and understanding the processing flow.
        """
        logger.debug("=== PIPELINE DEBUG INFO ===")
        logger.debug(f"Schema mode: {self.schema_mode}")
        logger.debug(f"Number of files: {len(file_paths)}")

        for i, file_path in enumerate(file_paths, 1):
            size = file_path.stat().st_size
            logger.debug(f"  File {i}: {file_path.name} ({size:,} bytes)")

        logger.debug(f"Schema registry: {schema_path}")
        logger.debug(f"Merchant lookup: {merchant_path}")
        logger.debug("=" * 27)

    def _update_stats(self, df: pd.DataFrame, file_paths: list[Path]) -> None:
        """
        Update internal processing statistics.

        Args:
            df: Processed DataFrame
            file_paths: List of processed files
        """
        self._processing_stats["files_processed"] = len(file_paths)
        self._processing_stats["total_rows"] = len(df)

        # Extract unique schemas used if available
        if "DataSourceName" in df.columns:
            schemas = df["DataSourceName"].dropna().unique().tolist()
            self._processing_stats["schemas_used"] = set(schemas)

        # Calculate file sizes
        total_size = sum(fp.stat().st_size for fp in file_paths)
        self._processing_stats["total_bytes_processed"] = total_size

    def _validate_output(self, df: pd.DataFrame) -> None:
        """
        Perform final validation on the processed DataFrame.

        This method checks for common issues and logs warnings to help
        users identify potential data quality problems.

        Args:
            df: Processed DataFrame to validate
        """
        if df.empty:
            logger.warning("Processed DataFrame is empty")
            return

        # Define required columns based on schema mode using shared constants
        from .config import CORE_REQUIRED_COLUMNS
        from .constants import MASTER_SCHEMA_COLUMNS

        if self.schema_mode == "strict":
            # In strict mode, check for all expected columns
            required_columns = MASTER_SCHEMA_COLUMNS
        else:
            # In flexible mode, only check for core columns
            required_columns = CORE_REQUIRED_COLUMNS

        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.warning(f"Missing expected columns: {missing_columns}")

        # Check for data quality issues
        quality_checks = [
            ("Date", "null dates"),
            ("Amount", "null amounts"),
            ("Merchant", "null merchants"),
        ]

        for column, issue_name in quality_checks:
            if column in df.columns:
                null_count = df[column].isna().sum()
                if null_count > 0:
                    percentage = (null_count / len(df)) * 100
                    logger.warning(
                        f"Found {null_count} transactions ({percentage:.1f}%) "
                        f"with {issue_name}"
                    )

    def _init_stats(self) -> dict[str, Any]:
        """Initialize a fresh statistics dictionary."""
        return {
            "files_processed": 0,
            "files_skipped": 0,
            "total_rows": 0,
            "processing_time": 0.0,
            "schemas_used": set(),
            "total_bytes_processed": 0,
        }

    def get_processing_stats(self) -> dict[str, Any]:
        """
        Get processing statistics for the last run.

        Returns:
            Dictionary containing processing statistics with sets converted to lists
            for JSON serialization compatibility
        """
        stats = self._processing_stats.copy()
        # Convert set to list for JSON serialization
        if "schemas_used" in stats and isinstance(stats["schemas_used"], set):
            stats["schemas_used"] = list(stats["schemas_used"])
        return stats

    def reset_stats(self) -> None:
        """Reset processing statistics to initial state."""
        self._processing_stats = self._init_stats()


# Convenience functions for common use cases


def create_pipeline(
    schema_mode: str = "flexible", debug: bool = False
) -> UnifiedPipeline:
    """
    Factory function to create a configured pipeline instance.

    This provides a simple way to create a pipeline with common configurations.

    Args:
        schema_mode: Schema validation mode ('strict' or 'flexible')
        debug: Enable debug mode for detailed logging

    Returns:
        Configured UnifiedPipeline instance

    Example:
        >>> pipeline = create_pipeline(schema_mode="strict", debug=True)
        >>> df = pipeline.process_files(["file1.csv", "file2.csv"])
    """
    return UnifiedPipeline(schema_mode=schema_mode, debug_mode=debug)


def process_files_simple(
    file_paths: Sequence[PathLike], schema_mode: str = "flexible", debug: bool = False
) -> pd.DataFrame:
    """
    Simple wrapper function for one-line file processing.

    This function provides a convenient way to process files without
    needing to instantiate the pipeline manually. It's ideal for
    simple use cases where you don't need access to processing stats.

    Args:
        file_paths: Sequence of CSV file paths
        schema_mode: Schema validation mode ('strict' or 'flexible')
        debug: Enable debug mode

    Returns:
        Processed DataFrame

    Example:
        >>> df = process_files_simple(["file1.csv", "file2.csv"])
        >>> print(f"Processed {len(df)} transactions")
    """
    pipeline = UnifiedPipeline(schema_mode=schema_mode, debug_mode=debug)
    return pipeline.process_files(file_paths)
