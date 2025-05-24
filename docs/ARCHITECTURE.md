# BALANCE-pyexcel Unified Pipeline Architecture (v2)

This document outlines the architecture of the refactored data processing pipeline (v2)
for the BALANCE-pyexcel project. The primary goal of this redesign is to create a
single, unified, and maintainable pipeline that consolidates previous processing
logic, enhances flexibility, and provides a clear structure for future development.

## 1. Core Principles

The v2 architecture is built upon the following principles:

- **Unified Processing:** All data flows through a single, consistent processing engine.
- **Modularity:** Clear separation of concerns between data processing, configuration, and output generation.
- **Configurability:** Centralized and flexible configuration management.
- **Extensibility:** Designed to be easily extended with new data sources, transformations, or output formats.
- **Backward Compatibility:** Existing interfaces (legacy CLI, Excel `etl_main`) are maintained by routing them through the new pipeline.
- **Testability:** Components are designed to be independently testable.

## 2. System Components

The unified pipeline consists of the following key Python modules within the `src/balance_pipeline/` directory:

### 2.1. `pipeline_v2.py`: The Unified Pipeline Engine

- **`UnifiedPipeline` Class:** This is the heart of the new architecture.
    - **Responsibilities:**
        - Orchestrates the entire data processing workflow.
        - Wraps the core data ingestion and transformation logic previously found in `csv_consolidator.py`.
        - Accepts a `schema_mode` (`"strict"` or `"flexible"`) to control output columns.
        - Takes a list of input file paths.
        - Utilizes `config_v2.py` for paths to schema registry and merchant lookup files.
        - Applies business rules and data validation consistently.
        - Returns a standardized pandas DataFrame ready for output.
    - **Key Method:** `process_files(...)`

### 2.2. `csv_consolidator.py`: Core Data Transformation (Leveraged)

- This module remains crucial as it contains the detailed logic for:
    - Reading individual CSV files.
    - Matching CSVs to schemas defined in `schema_registry.yml`.
    - Applying schema-specific transformations (column mapping, date parsing, amount signing, derived columns).
    - Generating `TxnID`.
    - Initial merchant name cleaning.
    - Handling `schema_mode` ("strict" vs. "flexible") to determine final columns.
- The `UnifiedPipeline` class calls the `process_csv_files` function from this module. The `schema_mode` is passed from `UnifiedPipeline` by temporarily setting a global variable in `balance_pipeline.config` which `csv_consolidator.py` reads.

### 2.3. `outputs.py`: Output Adapters

- Provides a structured way to output the processed DataFrame to various formats.
- **`BaseOutputAdapter` (Abstract Class):** Defines the interface for all output adapters (`__init__`, `write`).
- **Concrete Adapters:**
    - **`PowerBIOutput`:** Saves the DataFrame to Parquet format, suitable for Power BI.
    - **`ExcelOutput`:** Saves the DataFrame to an Excel (`.xlsx`) file. Can be extended to support templates.
- **Usage:** Instantiated by the main CLI (`main.py`) based on user choice. They receive the processed DataFrame from `UnifiedPipeline`.

### 2.4. `config_v2.py`: Centralized Configuration

- **`PipelineConfig` Dataclass:**
    - Centralizes all pipeline configurations (e.g., file paths for rules, default output directories, schema mode, log level).
    - Supports initialization from defaults, environment variables, or direct instantiation.
    - Includes validation for configuration values.
    - Provides an `explain()` method to display the current configuration.
- **`pipeline_config_v2` (Global Instance):** A globally accessible instance of `PipelineConfig`, initialized with defaults/env vars, providing a single source of truth for configuration across the new pipeline modules.

### 2.5. `main.py`: Primary CLI Entry Point

- Provides the new, recommended command-line interface: `balance-pipe`.
- Built using the `click` library for a user-friendly experience.
- **Responsibilities:**
    - Parses command-line arguments.
    - Initializes `PipelineConfig` based on CLI options, overriding defaults where specified.
    - Sets up logging.
    - Instantiates `UnifiedPipeline`.
    - Invokes `pipeline.process_files(...)` with appropriate parameters.
    - Instantiates the chosen output adapter (`PowerBIOutput` or `ExcelOutput`).
    - Calls the adapter's `write()` method to save the results.
    - Includes an `--explain-config` flag to show the effective configuration.

### 2.6. Legacy Compatibility Layers

- **`cli.py` (Legacy CLI):**
    - Modified to use `UnifiedPipeline` internally for its full ETL mode.
    - Maintains its existing command-line arguments and behavior for backward compatibility.
    - Includes a deprecation warning, guiding users to the new `balance-pipe` CLI.
    - The `--raw-dir` functionality remains as a separate, simpler path within this legacy CLI.
- **`__init__.py` (Package Entry for Excel):**
    - The `etl_main(csv_inbox)` function (called by Excel) is modified to use `UnifiedPipeline` internally.
    - It scans for CSVs in the `csv_inbox` and passes them to the `UnifiedPipeline`.
    - Defaults to `schema_mode="flexible"` for compatibility with existing Excel usage.
    - Includes a log warning about its legacy status.

## 3. Data Flow

1.  **Invocation:**
    - User calls `balance-pipe process ...` (new CLI).
    - Or, user calls the legacy `balance-pyexcel ...` CLI.
    - Or, Excel calls `etl_main()` from `balance_pipeline/__init__.py`.
2.  **Configuration:**
    - `main.py` (new CLI) or legacy interfaces establish the `PipelineConfig`.
    - Logging is set up based on this configuration.
3.  **Pipeline Initialization:**
    - `UnifiedPipeline` is instantiated with the desired `schema_mode`.
4.  **File Processing (`UnifiedPipeline.process_files`):**
    - The `UnifiedPipeline` receives a list of input file paths.
    - It temporarily sets the global `balance_pipeline.config.SCHEMA_MODE` based on its own `schema_mode`.
    - It calls `csv_consolidator.process_csv_files()`, providing the file list and paths to the schema registry and merchant lookup files (obtained from `config_v2.pipeline_config_v2`).
    - `csv_consolidator.process_csv_files()` then:
        - Iterates through each CSV file.
        - Matches it to a schema from `schema_registry.yml`.
        - Applies all transformations (mapping, derived columns, date parsing, amount signing, TxnID, etc.) based on the matched schema and the active `schema_mode`.
        - Consolidates data from all processed files into a single DataFrame.
    - `UnifiedPipeline` receives this processed DataFrame.
    - The original global `balance_pipeline.config.SCHEMA_MODE` is restored.
5.  **Output Generation (via `main.py` or legacy interfaces):**
    - The processed DataFrame is passed to an appropriate output adapter (`PowerBIOutput` or `ExcelOutput`).
    - The adapter formats and writes the data to the specified file (e.g., Parquet, Excel).
    - Legacy interfaces (`cli.py`, `__init__.py`) handle their specific output requirements (e.g., writing to Excel sheets, Parquet files).

## 4. Configuration Options

Configuration is primarily managed by `src/balance_pipeline/config_v2.py:PipelineConfig`. Key configurable aspects include:

- **`project_root`**: Root directory of the project.
- **`rules_dir`**: Directory for all rule files.
- **`schema_registry_path`**: Path to `schema_registry.yml`.
- **`merchant_lookup_path`**: Path to `merchant_lookup.csv`.
- **`default_output_dir`**: Default location for output files generated by the new `balance-pipe` CLI.
- **`schema_mode`**: `"strict"` (all 25 master columns) or `"flexible"` (core columns + only relevant optional columns).
- **`log_level`**: Logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL).

These can be set via:
- Defaults in `config_v2.py`.
- Environment variables (e.g., `BALANCE_SCHEMA_MODE`, `BALANCE_SCHEMA_REGISTRY_PATH`).
- Command-line arguments in the new `balance-pipe` CLI.

The `balance-pipe process --explain-config` command can be used to see the active configuration values.

## 5. Extending the System

### 5.1. Adding a New Data Source (CSV Schema)

1.  Analyze the new CSV format.
2.  Create a new YAML schema definition file in the `rules/` directory (or a subdirectory).
3.  Define `filename_patterns` or `header_patterns` to uniquely identify the CSV.
4.  Specify `column_map` to map source columns to canonical master schema columns.
5.  Define `date_format`, `sign_rule`, `amount_regex` (if needed).
6.  Add `derived_columns` or `extra_static_cols` as required.
7.  Register the new schema YAML file path in `rules/schema_registry.yml`.
8.  Test thoroughly using `tests/test_unified_pipeline.py` and the `scripts/validate_migration.py` script with sample files.

### 5.2. Adding a New Output Format

1.  Create a new class in `src/balance_pipeline/outputs.py` that inherits from `BaseOutputAdapter`.
2.  Implement the `__init__(self, output_path)` method.
3.  Implement the `write(self, df: pd.DataFrame, **kwargs: Any)` method to handle the specifics of the new format.
4.  Update `src/balance_pipeline/main.py` to include the new format as an option for the `--output-type` argument and instantiate your new adapter.
5.  Add tests for the new adapter in `tests/test_unified_pipeline.py`.

### 5.3. Modifying Business Logic

- Most business logic related to data transformation is within `csv_consolidator.py` or defined declaratively in the schema YAML files.
- For changes to core processing steps (e.g., TxnID generation, fundamental schema matching), modify `csv_consolidator.py`.
- For changes to how the overall pipeline is orchestrated, modify `pipeline_v2.py`.
- Ensure any changes are covered by tests.

## 6. Best Practices

- **Schema Definitions:** Keep schema YAML files clear, concise, and well-documented. Use specific patterns for matching.
- **Configuration:** Prefer environment variables or CLI arguments for overriding default configurations in deployment or specific runs.
- **Logging:** Utilize the structured logging provided. Check logs for detailed information during processing, especially for warnings or errors.
- **Testing:** Add new test cases to `tests/test_unified_pipeline.py` for any new functionality or significant changes. Use the `scripts/validate_migration.py` script to ensure consistency when refactoring core components.
- **Sample Data:** Maintain a comprehensive set of sample CSV files in `sample_data/` or `sample_data_multi/` that cover all supported schemas and edge cases. This is crucial for testing and validation.
- **Idempotency:** The pipeline aims to be idempotent; running it multiple times with the same input data and configuration should produce the same output (excluding timestamped filenames).

This unified architecture provides a more robust, maintainable, and understandable foundation for the BALANCE-pyexcel project, facilitating easier debugging, consistent data handling, and future enhancements.
