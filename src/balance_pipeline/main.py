"""
Main CLI Entry Point for the Unified BALANCE Pipeline (v2).

This script provides a command-line interface to run the unified data
processing pipeline, allowing users to specify input files, configuration
overrides, output formats, and other processing options.

It uses the Click library for creating a clean and user-friendly CLI.
"""
import logging
import sys
from pathlib import Path
from typing import Tuple, Optional, List

import click
import pandas as pd

# Local application imports
# Assuming these modules are in the same package or PYTHONPATH is set up
from .pipeline_v2 import UnifiedPipeline
from .outputs import PowerBIOutput, ExcelOutput, BaseOutputAdapter
from .config_v2 import PipelineConfig, pipeline_config_v2 as global_config # Import the global instance

# Setup a basic logger for the CLI itself.
# The pipeline modules will have their own loggers.
cli_logger = logging.getLogger("balance_pipeline_cli")

def setup_logging(log_level_str: str):
    """Configures logging for the application."""
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout, # Output logs to stdout
    )
    cli_logger.info(f"Logging configured with level: {log_level_str}")


@click.group()
@click.version_option(version="2.0.0", prog_name="balance-pipe") # Placeholder version
def balance_pipe_cli():
    """
    BALANCE Unified Data Pipeline CLI (v2).

    Process financial CSV files through a unified pipeline,
    applying consistent rules and outputting to various formats.
    """
    pass

@balance_pipe_cli.command("process")
@click.argument(
    "input_files",
    nargs=-1,  # Allows multiple input files
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    required=True,
)
@click.option(
    "--schema-mode",
    type=click.Choice(["flexible", "strict"], case_sensitive=False),
    default=None, # Will use global_config's default if None
    help="Schema mode for processing: 'flexible' or 'strict'. Overrides config file.",
)
@click.option(
    "--output-type",
    type=click.Choice(["powerbi", "excel", "none"], case_sensitive=False),
    default="powerbi",
    help="Format for the output: 'powerbi' (Parquet), 'excel', or 'none' (no output file).",
)
@click.option(
    "--output-path",
    type=click.Path(dir_okay=False, writable=True, resolve_path=True),
    default=None,
    help="Full path for the output file. If not provided, a default name will be generated in the configured output directory.",
)
@click.option(
    "--schema-registry",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    default=None,
    help="Path to a custom schema registry YAML file. Overrides default.",
)
@click.option(
    "--merchant-lookup",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    default=None,
    help="Path to a custom merchant lookup CSV file. Overrides default.",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False),
    default=None, # Will use global_config's default
    help="Set the logging level.",
)
@click.option(
    "--explain-config",
    is_flag=True,
    help="Show the current pipeline configuration and exit.",
)
def process_files_command(
    input_files: Tuple[str, ...], # Click converts nargs=-1 to a tuple
    schema_mode: Optional[str],
    output_type: str,
    output_path: Optional[str],
    schema_registry: Optional[str],
    merchant_lookup: Optional[str],
    log_level: Optional[str],
    explain_config: bool,
):
    """
    Process one or more financial CSV INPUT_FILES.
    """
    # --- 1. Configuration Setup ---
    # Create a config instance, allowing CLI options to override defaults/env vars
    # Start with global_config defaults, then update with CLI args if provided
    effective_config_params = {}
    if schema_mode:
        effective_config_params["schema_mode"] = schema_mode
    if schema_registry:
        effective_config_params["schema_registry_path"] = Path(schema_registry)
    if merchant_lookup:
        effective_config_params["merchant_lookup_path"] = Path(merchant_lookup)
    if log_level:
        effective_config_params["log_level"] = log_level.upper()
    
    # Create a new config instance if there are overrides, otherwise use global_config
    if effective_config_params:
        # Create a new instance based on global_config, then update
        current_config_dict = global_config.to_dict()
        current_config_dict.update(effective_config_params)
        # Path objects need to be Path objects for PipelineConfig constructor
        for key, value in current_config_dict.items():
            if key.endswith("_path") or key in ["project_root", "rules_dir", "default_output_dir"]:
                 if value and isinstance(value, str):
                    current_config_dict[key] = Path(value)
        
        config = PipelineConfig(**current_config_dict)
    else:
        config = global_config

    setup_logging(config.log_level) # Setup logging based on final effective log level

    if explain_config:
        click.echo("Current Effective Pipeline Configuration:")
        click.echo(config.explain())
        return

    if not input_files:
        cli_logger.error("No input files provided.")
        click.echo("Error: No input files specified. Use --help for more information.", err=True)
        sys.exit(1)
    
    cli_logger.info(f"Processing {len(input_files)} file(s).")
    cli_logger.debug(f"Input files: {input_files}")
    cli_logger.info(f"Schema mode: {config.schema_mode}")
    cli_logger.info(f"Output type: {output_type}")

    # --- 2. Initialize Pipeline ---
    try:
        pipeline = UnifiedPipeline(schema_mode=config.schema_mode)
    except ValueError as e:
        cli_logger.error(f"Configuration error: {e}", exc_info=True)
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    # --- 3. Process Files ---
    processed_df: Optional[pd.DataFrame] = None
    try:
        # Convert tuple of file paths to list of strings for the pipeline
        file_paths_list: List[str] = list(input_files)
        
        processed_df = pipeline.process_files(
            file_paths=file_paths_list,
            schema_registry_override_path=str(config.schema_registry_path), # Pass as string
            merchant_lookup_override_path=str(config.merchant_lookup_path), # Pass as string
        )
        cli_logger.info(f"Pipeline processing completed. Resulting DataFrame shape: {processed_df.shape if processed_df is not None else 'None'}")
    except Exception as e:
        cli_logger.error(f"An error occurred during pipeline processing: {e}", exc_info=True)
        click.echo(f"Pipeline Error: {e}", err=True)
        sys.exit(1)

    if processed_df is None or processed_df.empty:
        cli_logger.warning("Processing resulted in an empty or None DataFrame. No output will be generated.")
        click.echo("Warning: No data processed. Output file will not be created.")
        sys.exit(0) # Successful exit, but no data

    # --- 4. Handle Output ---
    if output_type == "none":
        cli_logger.info("Output type is 'none'. No output file will be written.")
        click.echo("Processing complete. No output file generated as per --output-type=none.")
        sys.exit(0)

    # Determine final output path
    final_output_path: Path
    if output_path:
        final_output_path = Path(output_path)
    else:
        # Generate default output path
        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        if output_type == "powerbi":
            final_output_path = config.default_output_dir / f"balance_output_{timestamp}.parquet"
        elif output_type == "excel":
            final_output_path = config.default_output_dir / f"balance_output_{timestamp}.xlsx"
        else: # Should not happen due to earlier check, but defensive
            cli_logger.error(f"Unsupported output type '{output_type}' for default path generation.")
            sys.exit(1)
    
    cli_logger.info(f"Output will be written to: {final_output_path}")

    output_adapter: Optional[BaseOutputAdapter] = None
    try:
        if output_type == "powerbi":
            output_adapter = PowerBIOutput(final_output_path)
        elif output_type == "excel":
            output_adapter = ExcelOutput(final_output_path)
        
        if output_adapter:
            output_adapter.write(processed_df)
            click.echo(f"Successfully processed files. Output written to: {final_output_path}")
        else:
            # This case should ideally be caught by output_type == "none"
            cli_logger.info("No specific output adapter selected, though output was expected.")
            click.echo("Processing complete. No output file generated (unexpected state).")

    except Exception as e:
        cli_logger.error(f"An error occurred during output generation: {e}", exc_info=True)
        click.echo(f"Output Error: {e}", err=True)
        sys.exit(1)

if __name__ == "__main__":
    # This allows running the CLI directly, e.g., python src/balance_pipeline/main.py process ...
    # For development, it's often better to install the package and run the entry point.
    balance_pipe_cli()
