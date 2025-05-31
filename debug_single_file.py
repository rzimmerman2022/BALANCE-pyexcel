# debug_single_file.py
"""
Debug script for testing the BALANCE-pyexcel pipeline with a single CSV file.
This script is designed to test with ACTUAL data from your CSVs directory,
not the old sample_data_multi directory.

The key insight here is that we need to test with the exact type of data that's
causing problems - in this case, CSV files with YYYY-MM-DD date formats.
"""
import sys
import os
from pathlib import Path
import logging
from datetime import datetime

# --- Path Setup ---
# This section ensures Python can find your local balance_pipeline modules.
# We do this FIRST, before any imports from balance_pipeline, to avoid
# accidentally importing from somewhere else on your system.

# Find where this script lives and establish our bearings
script_dir = Path(__file__).resolve().parent
project_root = script_dir  # Since debug_single_file.py is in project root

# The 'src' directory contains all our application code
src_path = project_root / 'src'

# Make sure Python looks in our src directory first
# This is like saying "use the local version, not any installed version"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
elif sys.path[0] != str(src_path):
    # If it's there but not first, make it first
    try:
        sys.path.remove(str(src_path))
    except ValueError:
        pass
    sys.path.insert(0, str(src_path))

# --- Logging Setup ---
# Good logging is like having a conversation with your code as it runs
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)-8s | %(name)-25s | %(lineno)d | %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("debug_single_file")

logger.debug(f"Initial sys.path: {sys.path}")
logger.debug(f"PYTHONPATH environment variable: {os.environ.get('PYTHONPATH')}")
logger.debug(f"Project root determined as: {project_root}")
logger.debug(f"Src path for imports: {src_path}")

# --- Import our processing function ---
logger.info("Attempting to import application modules...")
process_csv_files = None

try:
    from balance_pipeline.csv_consolidator import process_csv_files
    logger.info("Successfully imported 'process_csv_files' from balance_pipeline.csv_consolidator.")
except ImportError as e:
    logger.error(f"Failed to import 'process_csv_files': {e}")
    logger.exception("Full traceback for import error:")
    sys.exit(1)
except Exception as e:
    logger.error(f"An unexpected error occurred during import: {e}")
    logger.exception("Full traceback for unexpected import error:")
    sys.exit(1)

if process_csv_files is None:
    logger.error("Critical error: 'process_csv_files' could not be imported. Exiting.")
    sys.exit(1)

# --- Configure Test File Path ---
# This is where we fix the main issue: we need to use REAL data, not sample data

# The actual CSVs directory is one level up from our project
csvs_dir = project_root.parent / "CSVs" / "Ryan"

# Try to find a Monarch Money file with the YYYY-MM-DD format issue
# You can change this to match your actual filename
test_filename = "Ryan - Monarch Money - 20250524.csv"
test_file_path = csvs_dir / test_filename

# Let's be extra helpful and show what files are available if our target doesn't exist
if not test_file_path.exists():
    logger.error(f"Test file not found: {test_file_path}")
    logger.info("Let me help you find the right file...")
    
    # Check if the CSVs directory exists
    if not csvs_dir.exists():
        logger.error(f"CSVs directory doesn't exist at: {csvs_dir}")
        logger.info(f"Expected location relative to project: ../CSVs/Ryan/")
        
        # Let's see what directories DO exist at the parent level
        parent_contents = list(project_root.parent.iterdir())
        logger.info(f"Directories at parent level ({project_root.parent}):")
        for item in parent_contents:
            if item.is_dir():
                logger.info(f"  - {item.name}/")
    else:
        # The directory exists, so let's show what CSV files are in it
        csv_files = list(csvs_dir.glob("*.csv"))
        if csv_files:
            logger.info(f"Available CSV files in {csvs_dir.name}:")
            for csv_file in sorted(csv_files):
                # Show file info to help identify the right one
                stat = csv_file.stat()
                mod_time = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
                size_kb = stat.st_size / 1024
                logger.info(f"  - {csv_file.name} ({size_kb:.1f} KB, modified {mod_time})")
            
            # Suggest files that look like Monarch Money exports
            monarch_files = [f for f in csv_files if "monarch" in f.name.lower()]
            if monarch_files:
                logger.info("\nMonarch Money files found:")
                for f in monarch_files:
                    logger.info(f"  - {f.name}")
                logger.info(f"\nTo use one of these, update the 'test_filename' variable in this script")
        else:
            logger.warning(f"No CSV files found in {csvs_dir}")
    
    sys.exit(1)

# If we get here, the file exists!
logger.info(f"\n{'='*60}")
logger.info(f"Starting debug processing of: {test_file_path.name}")
logger.info(f"Full absolute path: {test_file_path.resolve()}")
logger.info(f"File size: {test_file_path.stat().st_size / 1024:.1f} KB")
logger.info(f"{'='*60}\n")

# --- Process the file ---
try:
    # process_csv_files expects a list of file paths
    # We pass debug_mode=True to get extra debugging output
    result_df = process_csv_files(
        [str(test_file_path)],  # Convert Path to string
        debug_mode=True
    )
    
    if result_df is not None and not result_df.empty:
        logger.info(f"\nDebug processing complete. Result DataFrame shape: {result_df.shape}")
        
        # Let's peek at the Date column to see if our date parsing worked
        if 'Date' in result_df.columns:
            # Check how many dates were successfully parsed
            valid_dates = result_df['Date'].notna().sum()
            total_rows = len(result_df)
            logger.info(f"Date parsing results: {valid_dates}/{total_rows} dates successfully parsed")
            
            # Show a sample of the dates
            if valid_dates > 0:
                logger.info("Sample of parsed dates:")
                sample_dates = result_df[result_df['Date'].notna()]['Date'].head(3)
                for idx, date_val in enumerate(sample_dates):
                    logger.info(f"  Row {idx}: {date_val}")
            else:
                logger.warning("No dates were successfully parsed - this suggests a date format mismatch")
                # Show what the raw date strings looked like
                logger.info("This is expected if the file has M/D/YYYY dates but schema expects YYYY-MM-DD")
    else:
        logger.warning("\nDebug processing complete but result is empty or None")
        
except TypeError as e:
    # This specific error often indicates the debug_mode parameter isn't recognized
    if "debug_mode" in str(e):
        logger.warning("The process_csv_files function doesn't accept debug_mode parameter")
        logger.info("Retrying without debug_mode...")
        try:
            result_df = process_csv_files([str(test_file_path)])
            if result_df is not None:
                logger.info(f"\nProcessing complete. Result DataFrame shape: {result_df.shape}")
        except Exception as retry_error:
            logger.error(f"Retry also failed: {retry_error}")
            logger.exception("Full error trace:")
    else:
        logger.error(f"TypeError during processing: {e}")
        logger.exception("Full error trace:")
        
except Exception as e:
    logger.error(f"\nError during 'process_csv_files' execution: {e}")
    logger.exception("Full error trace:")

logger.info("\n" + "="*60)
logger.info("Debug script finished.")
logger.info("="*60)