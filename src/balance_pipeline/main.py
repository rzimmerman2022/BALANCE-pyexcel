#!/usr/bin/env python3
################################################################################
#                                                                              #
#                         BALANCE PIPELINE MAIN ENTRY                         #
#                                                                              #
################################################################################
"""
Main entry point for the Balance Pipeline application.

This module provides the command-line interface for processing financial CSV files
through the unified pipeline. It handles argument parsing, logging setup, and
orchestrates the data processing workflow.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd
from balance_pipeline.config import DEFAULT_OUTPUT_FORMAT, SUPPORTED_OUTPUT_FORMATS

# Import the unified pipeline - adjust import based on your project structure
from balance_pipeline.pipeline_v2 import UnifiedPipeline

# Configure logging format for consistency across the application
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def setup_logging(verbosity: int = 0) -> None:
    """
    Configure logging based on verbosity level.
    
    The logging system uses a hierarchical approach where higher verbosity
    levels provide more detailed output. This helps with debugging while
    keeping normal operation output clean.
    
    Args:
        verbosity: Logging verbosity level (0=WARNING, 1=INFO, 2+=DEBUG)
    """
    # Map verbosity counts to logging levels
    level_map = {
        0: logging.WARNING,
        1: logging.INFO,
        2: logging.DEBUG,
    }
    
    # Use DEBUG for any verbosity > 2
    log_level = level_map.get(verbosity, logging.DEBUG)
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=LOG_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set specific loggers if needed
    logging.getLogger("balance_pipeline").setLevel(log_level)


def validate_file_paths(file_paths: list[str]) -> list[Path]:
    """
    Validate that all provided file paths exist and are readable.
    
    This function converts string paths to Path objects and verifies
    that each file exists and is accessible. This early validation
    prevents processing errors later in the pipeline.
    
    Args:
        file_paths: List of file path strings from command line
        
    Returns:
        List of validated Path objects
        
    Raises:
        FileNotFoundError: If any file doesn't exist
        PermissionError: If any file isn't readable
    """
    validated_paths: list[Path] = []
    
    for file_path_str in file_paths:
        path = Path(file_path_str)
        
        # Check if file exists
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        # Check if it's actually a file (not a directory)
        if not path.is_file():
            raise ValueError(f"Path is not a file: {path}")
        
        # Check if file is readable
        try:
            with path.open('r') as f:
                # Try to read first byte to confirm readability
                f.read(1)
        except PermissionError:
            raise PermissionError(f"File is not readable: {path}")
        except Exception as e:
            raise PermissionError(f"Cannot access file {path}: {e}")
        
        # Check if file has CSV extension
        if not path.suffix.lower() == '.csv':
            raise ValueError(f"File is not a CSV: {path}")
            
        validated_paths.append(path)
    
    return validated_paths


def process_files_command(
    files: list[str],
    schema_path: str | None = None,
    merchant_path: str | None = None,
    output_path: str | None = None,
    output_format: str = DEFAULT_OUTPUT_FORMAT,
    debug: bool = False
) -> None:
    """
    Process CSV files using the unified pipeline.
    
    This is the main command function that orchestrates the entire
    file processing workflow. It handles path conversions, initializes
    the pipeline, processes files, and saves the output.
    
    Args:
        files: List of CSV file paths as strings
        schema_path: Optional custom schema registry YAML path
        merchant_path: Optional custom merchant lookup CSV path
        output_path: Optional output file path (defaults to stdout)
        output_format: Output format (csv, parquet, excel)
        debug: Enable debug mode for detailed logging
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Step 1: Validate and convert file paths
        logger.info(f"Processing {len(files)} files")
        validated_file_paths = validate_file_paths(files)
        
        # Step 2: Convert optional paths to Path objects if provided
        # These variables are properly typed as Optional[Path]
        schema_registry_override: Path | None = None
        merchant_lookup_override: Path | None = None
        
        if schema_path is not None:
            schema_registry_override = Path(schema_path)
            if not schema_registry_override.exists():
                raise FileNotFoundError(f"Schema registry not found: {schema_registry_override}")
                
        if merchant_path is not None:
            merchant_lookup_override = Path(merchant_path)
            if not merchant_lookup_override.exists():
                raise FileNotFoundError(f"Merchant lookup not found: {merchant_lookup_override}")
        
        # Step 3: Initialize the pipeline with debug mode
        logger.info("Initializing unified pipeline")
        pipeline = UnifiedPipeline(debug_mode=debug)
        
        # Step 4: Process files through the pipeline
        # The pipeline accepts List[Union[str, Path]] for flexibility
        logger.info("Starting file processing")
        processed_df = pipeline.process_files(
            file_paths=validated_file_paths,  # Pass Path objects
            schema_registry_override_path=schema_registry_override,
            merchant_lookup_override_path=merchant_lookup_override
        )
        
        # Step 5: Validate processing results
        if processed_df.empty:
            logger.warning("No data was processed from input files")
            return
            
        logger.info(f"Processed {len(processed_df)} total transactions")
        
        # Step 6: Save or display the output
        save_output(processed_df, output_path, output_format)
        
    except FileNotFoundError as e:
        logger.error(f"File error: {e}")
        sys.exit(1)
    except ValueError as e:
        logger.error(f"Value error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unexpected error during processing: {e}")
        sys.exit(1)


def save_output(
    df: pd.DataFrame,
    output_path: str | None,
    output_format: str
) -> None:
    """
    Save the processed DataFrame to the specified output.
    
    This function handles different output formats and destinations,
    including writing to stdout for pipeline compatibility.
    
    Args:
        df: Processed DataFrame to save
        output_path: Output file path (None for stdout)
        output_format: Format to save in (csv, parquet, excel)
    """
    logger = logging.getLogger(__name__)
    
    # Validate output format
    if output_format not in SUPPORTED_OUTPUT_FORMATS:
        raise ValueError(f"Unsupported output format: {output_format}")
    
    if output_path is None:
        # Write to stdout for pipeline compatibility
        if output_format == 'csv':
            df.to_csv(sys.stdout, index=False)
        else:
            logger.warning(f"Cannot write {output_format} to stdout, using CSV")
            df.to_csv(sys.stdout, index=False)
    else:
        # Write to file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        if output_format == 'csv':
            df.to_csv(output_file, index=False)
        elif output_format == 'parquet':
            df.to_parquet(output_file, index=False)
        elif output_format == 'excel':
            df.to_excel(output_file, index=False)
        
        logger.info(f"Output saved to: {output_file}")


def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create and configure the command-line argument parser.
    
    This function defines all available command-line options and their
    behaviors, providing a user-friendly interface to the pipeline.
    
    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        description="Balance Pipeline - Process financial CSV files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a single file
  python -m balance_pipeline.main process file1.csv
  
  # Process multiple files with custom schema
  python -m balance_pipeline.main process file1.csv file2.csv --schema-path custom_schema.yml
  
  # Process with debug output
  python -m balance_pipeline.main process *.csv --debug
  
  # Save to parquet format
  python -m balance_pipeline.main process *.csv --output processed.parquet --format parquet
        """
    )
    
    # Global options
    parser.add_argument(
        '-v', '--verbose',
        action='count',
        default=0,
        help='Increase verbosity (can be repeated: -v, -vv, -vvv)'
    )
    
    # Create subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Process command
    process_parser = subparsers.add_parser(
        'process',
        help='Process CSV files through the pipeline'
    )
    
    process_parser.add_argument(
        'files',
        nargs='+',
        help='CSV files to process'
    )
    
    process_parser.add_argument(
        '-s', '--schema-path',
        type=str,
        help='Path to custom schema registry YAML file'
    )
    
    process_parser.add_argument(
        '-m', '--merchant-path',
        type=str,
        help='Path to custom merchant lookup CSV file'
    )
    
    process_parser.add_argument(
        '-o', '--output',
        type=str,
        help='Output file path (default: stdout)'
    )
    
    process_parser.add_argument(
        '-f', '--format',
        type=str,
        choices=SUPPORTED_OUTPUT_FORMATS,
        default=DEFAULT_OUTPUT_FORMAT,
        help=f'Output format (default: {DEFAULT_OUTPUT_FORMAT})'
    )
    
    process_parser.add_argument(
        '-d', '--debug',
        action='store_true',
        help='Enable debug mode for detailed processing information'
    )
    
    return parser


def main() -> None:
    """
    Main entry point for the Balance Pipeline application.
    
    This function parses command-line arguments, sets up logging,
    and dispatches to the appropriate command handler.
    """
    # Parse command-line arguments
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Setup logging based on verbosity
    setup_logging(args.verbose)
    
    # Dispatch to appropriate command
    if args.command == 'process':
        process_files_command(
            files=args.files,
            schema_path=args.schema_path,
            merchant_path=args.merchant_path,
            output_path=args.output,
            output_format=args.format,
            debug=args.debug
        )
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()