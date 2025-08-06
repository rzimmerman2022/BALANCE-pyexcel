"""
Configuration for the Unified Pipeline (v2).

This module defines the PipelineConfig dataclass, which centralizes all
configuration parameters for the unified data processing pipeline.
It supports default values, validation, and an explain() method to display
the current configuration.
"""
import logging
import os
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default paths - these can be overridden by PipelineConfig instances or environment variables
DEFAULT_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent # Assumes config_v2.py is in src/balance_pipeline/
DEFAULT_RULES_DIR = DEFAULT_PROJECT_ROOT / "rules"
DEFAULT_SCHEMA_REGISTRY_PATH = DEFAULT_RULES_DIR / "schema_registry.yml"
DEFAULT_MERCHANT_LOOKUP_PATH = DEFAULT_RULES_DIR / "merchant_lookup.csv"
DEFAULT_OUTPUT_DIR = DEFAULT_PROJECT_ROOT / "output" / "unified_pipeline" # New default output location

@dataclass
class PipelineConfig:
    """
    Configuration settings for the UnifiedPipeline.

    Attributes:
        project_root (Path): The root directory of the BALANCE-pyexcel project.
        rules_dir (Path): Directory containing schema rule YAML files and other rule files.
        schema_registry_path (Path): Path to the schema registry YAML file.
        merchant_lookup_path (Path): Path to the merchant lookup CSV file.
        default_output_dir (Path): Default directory for pipeline outputs.
        schema_mode (str): The schema mode for processing ("strict" or "flexible").
        log_level (str): Logging level for the pipeline operations.
        # Add other relevant configurations as needed, e.g.:
        # default_powerbi_output_filename (str): "balance_powerbi.parquet"
        # default_excel_output_filename (str): "balance_excel.xlsx"
    """
    project_root: Path = field(default_factory=lambda: Path(os.getenv("BALANCE_PROJECT_ROOT", DEFAULT_PROJECT_ROOT)))
    rules_dir: Path = field(default_factory=lambda: Path(os.getenv("BALANCE_RULES_DIR", DEFAULT_RULES_DIR)))
    schema_registry_path: Path = field(default_factory=lambda: Path(os.getenv("BALANCE_SCHEMA_REGISTRY_PATH", DEFAULT_SCHEMA_REGISTRY_PATH)))
    merchant_lookup_path: Path = field(default_factory=lambda: Path(os.getenv("BALANCE_MERCHANT_LOOKUP_PATH", DEFAULT_MERCHANT_LOOKUP_PATH)))
    default_output_dir: Path = field(default_factory=lambda: Path(os.getenv("BALANCE_OUTPUT_DIR", DEFAULT_OUTPUT_DIR)))
    schema_mode: str = field(default_factory=lambda: os.getenv("BALANCE_SCHEMA_MODE", "flexible"))
    log_level: str = field(default_factory=lambda: os.getenv("BALANCE_LOG_LEVEL", "INFO").upper())

    # FIX 1: Added return type annotation -> None to resolve MyPy error
    def __post_init__(self) -> None:
        """Validate configuration values after initialization."""
        # Ensure paths are resolved and absolute for consistency
        self.project_root = self.project_root.resolve()
        self.rules_dir = self.rules_dir.resolve()
        self.schema_registry_path = self.schema_registry_path.resolve()
        self.merchant_lookup_path = self.merchant_lookup_path.resolve()
        self.default_output_dir = self.default_output_dir.resolve()

        # Validate schema_mode
        if self.schema_mode not in ["strict", "flexible"]:
            raise ValueError(f"Invalid schema_mode: '{self.schema_mode}'. Must be 'strict' or 'flexible'.")

        # Validate log_level
        if self.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            raise ValueError(f"Invalid log_level: '{self.log_level}'. Must be one of DEBUG, INFO, WARNING, ERROR, CRITICAL.")

        # Ensure directories exist or can be created for outputs
        try:
            self.default_output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error(f"Could not create default output directory {self.default_output_dir}: {e}")
            # Depending on strictness, could raise an error here.

        # Check existence of key rule files
        if not self.schema_registry_path.is_file():
            logger.warning(f"Schema registry file not found at configured path: {self.schema_registry_path}")
        if not self.merchant_lookup_path.is_file():
            logger.warning(f"Merchant lookup file not found at configured path: {self.merchant_lookup_path}")

        logger.info(f"PipelineConfig initialized. Schema mode: {self.schema_mode}, Log level: {self.log_level}")
        logger.debug(f"Full configuration: {self}")


    def explain(self) -> str:
        """
        Returns a human-readable string explaining the current configuration.
        """
        explanation = ["Current Pipeline Configuration:"]
        for f in fields(self):
            value = getattr(self, f.name)
            explanation.append(f"  - {f.name}: {value}")
        return "\n".join(explanation)

    def to_dict(self) -> dict[str, Any]:
        """
        Converts the configuration to a dictionary.
        Path objects are converted to strings.
        """
        config_dict = {}
        for f in fields(self):
            value = getattr(self, f.name)
            if isinstance(value, Path):
                config_dict[f.name] = str(value)
            else:
                config_dict[f.name] = value
        return config_dict


# Global instance of the configuration that can be imported by other modules.
# This allows for a single point of truth for configuration.
# It will be initialized with defaults or environment variables.
pipeline_config_v2 = PipelineConfig()

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG) # Set to DEBUG to see init logs

    # Test default initialization
    print("--- Default Configuration ---")
    config_default = PipelineConfig()
    print(config_default.explain())
    print(f"Schema Registry Exists: {config_default.schema_registry_path.exists()}")
    print(f"Merchant Lookup Exists: {config_default.merchant_lookup_path.exists()}")


    # Test initialization with overrides (simulating CLI args or direct instantiation)
    print("\n--- Custom Configuration ---")
    # FIX 2: Changed from dict unpacking to explicit parameter passing
    # This resolves the MyPy error about incompatible types in dict unpacking
    config_custom = PipelineConfig(
        schema_mode="strict",
        log_level="DEBUG",
        default_output_dir=Path("./custom_output_test"),
        # project_root=Path("/tmp/custom_project")  # Example
    )
    print(config_custom.explain())
    print(f"Custom output dir: {config_custom.default_output_dir}")
    if config_custom.default_output_dir.exists():
        logger.info(f"Custom output directory '{config_custom.default_output_dir}' was created or already exists.")
        # Clean up if needed: import shutil; shutil.rmtree(config_custom.default_output_dir)

    # Test environment variable override (manual setup needed for this test)
    # Example:
    # export BALANCE_SCHEMA_MODE="strict"
    # export BALANCE_LOG_LEVEL="DEBUG"
    # python src/balance_pipeline/config_v2.py
    print("\n--- Environment Variable Test (if set) ---")
    # The global pipeline_config_v2 instance would pick up env vars if set before import
    print("Global 'pipeline_config_v2' instance:")
    print(pipeline_config_v2.explain())


    # Test validation errors
    print("\n--- Validation Error Tests ---")
    try:
        PipelineConfig(schema_mode="invalid_mode")
    except ValueError as e:
        print(f"Caught expected error: {e}")

    try:
        PipelineConfig(log_level="SUPERDEBUG")
    except ValueError as e:
        print(f"Caught expected error: {e}")

    logger.info("Config v2 example usage finished.")