"""
Output Adapters for the Unified Pipeline.

This module provides classes for formatting and writing the processed DataFrame
from the UnifiedPipeline to various output targets, such as Power BI optimized
formats (e.g., Parquet) and Excel files (optionally with review templates).

Each adapter:
- Accepts a processed pandas DataFrame.
- Handles format-specific transformations.
- Manages file writing with error handling.
- Is designed to be independent and testable.
"""
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Any, Union

import pandas as pd

# Placeholder for potential future imports like openpyxl for Excel templating
# import openpyxl

logger = logging.getLogger(__name__)

class BaseOutputAdapter(ABC):
    """
    Abstract base class for output adapters.

    Defines the common interface for all output adapters, ensuring they
    can process a DataFrame and write it to a specified path.
    """

    def __init__(self, output_path: Union[str, Path]):
        """
        Initializes the BaseOutputAdapter.

        Args:
            output_path (Union[str, Path]): The path where the output file will be saved.
        """
        self.output_path = Path(output_path)
        # Ensure parent directory exists
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def write(self, df: pd.DataFrame, **kwargs: Any) -> None:
        """
        Processes the DataFrame and writes it to the specified output path.

        Args:
            df (pd.DataFrame): The DataFrame to be written.
            **kwargs: Additional format-specific options.
        """
        pass

class PowerBIOutput(BaseOutputAdapter):
    """
    Output adapter for Power BI optimized formats (e.g., Parquet).
    """

    def __init__(self, output_path: Union[str, Path]):
        """
        Initializes the PowerBIOutput adapter.

        The output path should typically have a .parquet extension.

        Args:
            output_path (Union[str, Path]): Path to save the Parquet file.
        """
        super().__init__(output_path)
        if self.output_path.suffix.lower() != ".parquet":
            logger.warning(
                f"PowerBIOutput typically saves to .parquet files, but got: {self.output_path}. "
                "Ensure the chosen format is Power BI compatible."
            )

    def write(self, df: pd.DataFrame, **kwargs: Any) -> None:
        """
        Writes the DataFrame to a Parquet file, optimized for Power BI.

        Args:
            df (pd.DataFrame): The DataFrame to write.
            **kwargs: Additional arguments for pd.DataFrame.to_parquet()
                      (e.g., engine, compression).
        """
        if df.empty:
            logger.warning(f"DataFrame is empty. No Parquet file will be written to {self.output_path}.")
            return

        logger.info(f"Writing DataFrame to Parquet file for Power BI: {self.output_path}")
        try:
            # Example: Ensure string columns with all NA are not object type if possible,
            # though to_parquet handles this reasonably well.
            # For Power BI, it's often good to ensure data types are explicit.
            # The csv_consolidator already does some defensive typing.

            df.to_parquet(self.output_path, index=False, **kwargs)
            logger.info(f"Successfully wrote Parquet file: {self.output_path} with {len(df)} rows.")
        except Exception as e:
            logger.error(f"Failed to write Parquet file to {self.output_path}: {e}", exc_info=True)
            raise


class ExcelOutput(BaseOutputAdapter):
    """
    Output adapter for Excel files.
    Handles Excel export, with future potential for review templates.
    """

    def __init__(self, output_path: Union[str, Path]):
        """
        Initializes the ExcelOutput adapter.

        The output path should typically have a .xlsx extension.

        Args:
            output_path (Union[str, Path]): Path to save the Excel file.
        """
        super().__init__(output_path)
        if self.output_path.suffix.lower() not in [".xlsx", ".xlsm"]:
            logger.warning(
                f"ExcelOutput typically saves to .xlsx or .xlsm files, but got: {self.output_path}."
            )

    def write(self, df: pd.DataFrame, sheet_name: str = "Data", **kwargs: Any) -> None:
        """
        Writes the DataFrame to an Excel file.

        Args:
            df (pd.DataFrame): The DataFrame to write.
            sheet_name (str): The name of the sheet to write data to. Defaults to "Data".
            **kwargs: Additional arguments for pd.DataFrame.to_excel()
                      (e.g., engine, freeze_panes).
        """
        if df.empty:
            logger.warning(f"DataFrame is empty. No Excel file will be written to {self.output_path}.")
            # Optionally, write an empty Excel file with headers if desired
            # For now, just return.
            return

        logger.info(f"Writing DataFrame to Excel file: {self.output_path} (Sheet: {sheet_name})")
        try:
            # Convert datetime columns to timezone-unaware for Excel compatibility if they are aware
            for col in df.select_dtypes(include=['datetime64[ns, tz]']).columns:
                logger.debug(f"Converting timezone-aware column '{col}' to naive for Excel export.")
                df[col] = df[col].dt.tz_localize(None)
            
            df.to_excel(self.output_path, sheet_name=sheet_name, index=False, **kwargs)
            logger.info(f"Successfully wrote Excel file: {self.output_path} with {len(df)} rows to sheet '{sheet_name}'.")
        except Exception as e:
            logger.error(f"Failed to write Excel file to {self.output_path}: {e}", exc_info=True)
            raise

if __name__ == "__main__":
    # Example Usage (for basic testing)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')

    # Create a dummy DataFrame
    data = {
        'colA': [1, 2, 3],
        'colB': ['apple', 'banana', 'cherry'],
        'colC': pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03'])
    }
    sample_df = pd.DataFrame(data)

    # Test PowerBIOutput
    parquet_output_path = Path("temp_test_output.parquet")
    try:
        pb_adapter = PowerBIOutput(parquet_output_path)
        pb_adapter.write(sample_df)
        # Verify file creation (manual check or add os.path.exists)
        if parquet_output_path.exists():
            logger.info(f"Test Parquet file created: {parquet_output_path}")
            # parquet_output_path.unlink() # Clean up
        else:
            logger.error(f"Test Parquet file FAILED to create: {parquet_output_path}")
    except Exception as e:
        logger.error(f"Error testing PowerBIOutput: {e}")

    # Test ExcelOutput
    excel_output_path = Path("temp_test_output.xlsx")
    try:
        excel_adapter = ExcelOutput(excel_output_path)
        excel_adapter.write(sample_df, sheet_name="SampleData")
        if excel_output_path.exists():
            logger.info(f"Test Excel file created: {excel_output_path}")
            # excel_output_path.unlink() # Clean up
        else:
            logger.error(f"Test Excel file FAILED to create: {excel_output_path}")
    except Exception as e:
        logger.error(f"Error testing ExcelOutput: {e}")

    # Test with empty DataFrame
    empty_df = pd.DataFrame()
    try:
        pb_adapter_empty = PowerBIOutput("temp_empty.parquet")
        pb_adapter_empty.write(empty_df) # Should log a warning and not create file
        
        excel_adapter_empty = ExcelOutput("temp_empty.xlsx")
        excel_adapter_empty.write(empty_df) # Should log a warning
    except Exception as e:
        logger.error(f"Error testing with empty DataFrame: {e}")

    logger.info("Output adapter example usage finished.")
    logger.info("Remember to manually delete 'temp_test_output.parquet', 'temp_test_output.xlsx', 'temp_empty.parquet', 'temp_empty.xlsx' if created.")