# debug_single_file.py
import sys
import os # For os.environ
from pathlib import Path
import logging # logging needs to be configured AFTER path setup if it depends on local modules

# --- Path Setup ---
# This should be one of the very first things.
# Ensure 'src' directory is at the front of sys.path to prioritize local modules.
# This helps avoid conflicts if other versions of 'balance_pipeline' are in PYTHONPATH.

# Get the directory of the current script (debug_single_file.py)
# Assuming debug_single_file.py is in the project root (e.g., c:/BALANCE/BALANCE-pyexcel)
script_dir = Path(__file__).resolve().parent
project_root = script_dir # If script is at project root

# Construct the path to the 'src' directory
src_path = project_root / 'src'

# Prepend 'src' to sys.path if it's not already there and at the front
# This is crucial for ensuring that 'from balance_pipeline...' imports the local version.
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
elif sys.path[0] != str(src_path):
    # If src_path is in sys.path but not at the front, move it to the front
    try: # Defensive removal
        sys.path.remove(str(src_path))
    except ValueError:
        pass # Not found, though the outer condition implies it should be
    sys.path.insert(0, str(src_path))

# --- Logging Setup ---
# Now configure logging.
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)-8s | %(name)-25s | %(lineno)d | %(message)s', # Added lineno
    stream=sys.stdout # Ensure logs go to stdout for visibility
)
logger = logging.getLogger("debug_single_file") # Use a specific logger for this script

logger.debug(f"Initial sys.path: {sys.path}")
logger.debug(f"PYTHONPATH environment variable: {os.environ.get('PYTHONPATH')}")
logger.debug(f"Project root determined as: {project_root}")
logger.debug(f"Src path for imports: {src_path}")

# --- Main Application Logic ---
logger.info("Attempting to import application modules...")
process_csv_files = None # Initialize to None
try:
    from balance_pipeline.csv_consolidator import process_csv_files
    logger.info("Successfully imported 'process_csv_files' from balance_pipeline.csv_consolidator.")
except ImportError as e:
    logger.error(f"Failed to import 'process_csv_files': {e}")
    logger.exception("Full traceback for import error:")
    sys.exit(1) # Exit if core import fails
except Exception as e:
    logger.error(f"An unexpected error occurred during import: {e}")
    logger.exception("Full traceback for unexpected import error:")
    sys.exit(1)

if process_csv_files is None:
    logger.error("Critical error: 'process_csv_files' could not be imported. Exiting.")
    sys.exit(1)

# Process just one file with debug mode
# Path relative to project_root. Adjust if your CSVs are located elsewhere.
test_file_relative = "sample_data_multi/Ryan/BALANCE - Monarch Money - 041225.csv"
test_file_path = project_root / test_file_relative

logger.info(f"\n{'='*60}")
logger.info(f"Starting debug processing of: {test_file_path}")
logger.info(f"Full absolute path: {test_file_path.resolve()}")
logger.info(f"{'='*60}\n")

if not test_file_path.exists():
    logger.error(f"Test file not found: {test_file_path.resolve()}")
    logger.error(f"Please ensure the 'test_file_relative' variable in debug_single_file.py points to a valid CSV file within the project structure (e.g., under '{project_root}').")
    sys.exit(1)

try:
    # Assuming process_csv_files expects a list of file paths (as strings or Path objects)
    result_df = process_csv_files(
        [str(test_file_path)], # Pass as a list of strings
        debug_mode=True
    )
    if result_df is not None:
        logger.info(f"\nDebug processing complete. Result DataFrame shape: {result_df.shape}")
        # logger.debug(f"Result DataFrame head:\n{result_df.head().to_string()}")
    else:
        logger.info("\nDebug processing complete. Result is None (no data processed or error upstream).")

except Exception as e:
    logger.error(f"\nError during 'process_csv_files' execution: {e}")
    logger.exception("Full error trace for process_csv_files:")

logger.info("debug_single_file.py finished.")
